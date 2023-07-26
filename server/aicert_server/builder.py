import asyncio
from fastapi import HTTPException
import hashlib
import docker
import os
from pathlib import Path
from threading import Lock, Thread
from typing import Union, Dict, Any, Optional

from aicert_common.protocol import Resource, BuildRequest
from .cmd_line import CmdLine
from .event_log import EventLog


docker_client = docker.from_env()
BASE_IMAGE = "mithrilsecuritysas/aicertbase:latest"
DEBUG = os.getenv('AICERT_DEBUG') is not None


def sha256_file(file_path) -> str:
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as file:
        for chunk in iter(lambda: file.read(4096), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


class Builder:
    _thread_lock = Lock()
    _used = False
    _thread: Optional[Thread] = None

    _event_log_lock = Lock()
    _event_log = EventLog(debug=DEBUG)
    _exception: Optional[HTTPException] = None
    _resolved_images: Dict[str, Any] = {}

    @classmethod
    def _register_build_request(cls, build_request: BuildRequest) -> None:
        cls._event_log.build_request_event(build_request)

    @classmethod
    def _docker_run(cls, cmd: Union[str, CmdLine], workspace: Union[str, Path, str], image: str = BASE_IMAGE) -> str:
        if not image in cls._resolved_images:
            resolved_image = docker_client.images.pull(image)
            cls._event_log.input_image_event(image, resolved_image.id)
            cls._resolved_images[image] = resolved_image
        else:
            resolved_image = cls._resolved_images[image]
        return docker_client.containers.run(
            resolved_image,
            str(cmd),
            volumes={str(workspace.absolute()): {"bind": "/mnt", "mode": "rw"}},
            working_dir="/mnt",
        ).decode("utf8").strip()

    @classmethod
    def _fetch_resource(cls, spec: Resource, workspace: Path) -> None:
        path = Path(spec.path)
        if path.is_absolute():
            raise HTTPException(status_code=403, detail=f"Ressource path must be relative: {path}")

        resource_hash = ""
        if spec.resource_type == "git":
            cls._docker_run(
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
                cls._docker_run(
                    cmd=CmdLine(["poetry", "lock", "--no-update"]),
                    workspace=workspace / path
                )
            resource_hash = cls._docker_run(
                cmd=CmdLine(["git", "rev-parse", "--verify", "HEAD"]),
                workspace=workspace / path
            )
        else:
            download_path = f"/tmp/000_aicert_{str(path).replace('/', '_')}" if spec.resource_type == "archive" else path
            cmd = CmdLine(["curl", "-o", download_path, "-L", spec.url])
            if spec.resource_type == "archive":
                cmd.extend(["tar", "-xzf" if spec.compression == "gzip" else "-xf", download_path])
            cls._docker_run(
                cmd=cmd,
                workspace=workspace,
            )
            resource_hash = sha256_file(download_path)
        
        cls._event_log.input_resource_event(spec, resource_hash)

    @classmethod
    def _register_outputs(cls, ouput_pattern: str, workspace: Path) -> None:
        matches = list(workspace.glob(ouput_pattern))
        outputs = [
            (str(path.relative_to(workspace)), sha256_file(path))
            for path in matches
            if path.is_file()
        ]
        if not outputs:
            raise HTTPException(status_code=404, detail=f"No files matching output pattern: '{ouput_pattern}'")
        cls._event_log.outputs_event(outputs)

    @classmethod
    def get_attestation(cls) -> Dict[str, Any]:
        with cls._event_log_lock:
            return cls._event_log.attest()

    @classmethod
    def build(cls, build_request: BuildRequest, workspace: Path) -> None:
        try:
            with cls._event_log_lock:
                cls._register_build_request(build_request)

                # install inputs
                for input in build_request.inputs:
                    cls._fetch_resource(input, workspace)

                cls._docker_run(
                    image=build_request.image,
                    cmd=build_request.cmdline,
                    workspace=workspace,
                )

                cls._register_outputs(build_request.outputs, workspace)
        except HTTPException as e:
            cls._exception = e
        except Exception as e:
            print(f"ERROR: {e}")
            cls._exception = HTTPException(status_code=500, detail=str(e))

    
    @classmethod
    def submit_build(cls, build_request: BuildRequest, workspace: Path) -> None:
        with cls._thread_lock:
            if cls._used:
                raise HTTPException(status_code=409, detail=f"Cannot build more than once")
            cls._used = True
            cls._thread = Thread(target=lambda: cls.build(build_request, workspace))
            cls._thread.start()
    
    @classmethod
    def poll_build(cls) -> bool:
        with cls._thread_lock:
            if cls._thread is not None and not cls._thread.is_alive():
                with cls._event_log_lock:
                    if cls._exception is not None:
                        raise cls._exception
                return True
            else:
                return False
