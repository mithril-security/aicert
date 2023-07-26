#!/usr/bin/python3

from fastapi import HTTPException
import hashlib
import json
import docker
from pathlib import Path
from typing import Union, Dict, Any, List

from aicert_common.protocol import Resource, BuildRequest
from .tpm import quote, cert_chain, tpm_extend_pcr, PCR_FOR_MEASUREMENT
from .cmd_line import CmdLine


docker_client = docker.from_env()
BASE_IMAGE = "mithrilsecuritysas/aicertbase:latest"


def sha256_file(file_path) -> str:
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as file:
        for chunk in iter(lambda: file.read(4096), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


class EventLog:
    """
    >>> event_log = EventLog()
    >>> image = "python"
    >>> command = ("python3 main.py",)
    >>> artifact_pattern = "output.txt"
    >>> git_repo_url = "https://github.com/mithril-security/sample-test-repo.git"
    >>> event_start_build = {
    ...     "event_type": "start_build",
    ...     "image": image,
    ...     "command": command,
    ...     "artifact_pattern": artifact_pattern,
    ...     "git_repo_url": git_repo_url,
    ... }
    >>> event_log.append(event_start_build)
    """

    def __init__(self, debug: bool = False):
        self._event_log = []
        self._resolved_images: Dict[str, Any] = {}
        self._debug = debug

    def append(self, event: Dict[str, Any]):
        event_json = json.dumps(event)
        if self._debug:
            print(f"DEBUG: {event}")
        else:
            hash_event = hashlib.sha256(event_json.encode()).hexdigest()
            tpm_extend_pcr(PCR_FOR_MEASUREMENT, hash_event)
        self._event_log.append(event_json)

    def attest(self):
        return {
            "event_log": self._event_log,
            "remote_attestation": {"quote": quote(), "cert_chain": cert_chain()} if not self._debug else {"debug": True},
        }
    
    def docker_run(self, cmd: Union[str, CmdLine], workspace: Union[Path, str], image: str = BASE_IMAGE) -> str:
        if not image in self._resolved_images:
            resolved_image = docker_client.images.pull(image)
            self.append(
                {
                    "event_type": "pull_image",
                    "image": image,
                    "resolved": {"id": resolved_image.id},
                }
            )
            self._resolved_images[image] = resolved_image
        else:
            resolved_image = self._resolved_images[image]
        return docker_client.containers.run(
            resolved_image,
            str(cmd),
            volumes={str(workspace.absolute()): {"bind": "/mnt", "mode": "rw"}},
            working_dir="/mnt",
        ).decode("utf8").strip()
    
    def start_build(self, build_request: BuildRequest) -> None:
        self.append({
            "event_type": "start_build",
            "build_request": build_request.dict(),
        })
    
    def build_artifacts(self, artifacts: Any) -> None:
        self.append({"event_type": "build_artifacts", "artifacts": artifacts})

    def fetch_resource(self, spec: Resource, workspace: Path) -> None:
        path = Path(spec.path)
        if path.is_absolute():
            raise HTTPException(status_code=403, detail=f"Ressource path must be relative: {path}")

        resource_hash = ""
        if spec.resource_type == "git":
            self.docker_run(
                cmd=CmdLine(
                    ["git", "clone", spec.repo, path],
                    ["cd", path],
                    ["git", "checkout", spec.branch],
                ),
                workspace=workspace,
            )
            if spec.dependencies == "poetry":
                if not (workspace / path / "poetry.lock").exists() and not (workspace / path / "pyproject.toml").exists():
                    raise HTTPException(status_code=404, detail="Cannot resolve poetry dependencies without a `poetry.lock` or a `pyproject.toml` file")
                self.docker_run(
                    cmd=CmdLine(["poetry", "lock", "--no-update"]),
                    workspace=workspace / path
                )
            resource_hash = self.docker_run(
                cmd=CmdLine(["git", "rev-parse", "--verify", "HEAD"]),
                workspace=workspace / path
            )
        else:
            download_path = f"/tmp/000_aicert_{str(path).replace('/', '_')}" if spec.resource_type == "archive" else path
            cmd = CmdLine(["curl", "-o", download_path, "-L", spec.url])
            if spec.resource_type == "archive":
                cmd.extend(["tar", "-xzf" if spec.compression == "gzip" else "-xf", download_path])
            self.docker_run(
                cmd=cmd,
                workspace=workspace,
            )
            resource_hash = sha256_file(download_path)
        
        self.append(
            {
                "event_type": "fetch_resource",
                "resource": spec.dict(),
                "resolved": {"hash": resource_hash},
            }
        )
