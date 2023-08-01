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
SIMULATION_MODE = os.getenv('AICERT_SIMULATION_MODE') is not None


def sha256_file(file_path) -> str:
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as file:
        for chunk in iter(lambda: file.read(4096), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


class Builder:
    __thread_lock = Lock()
    __used = False
    __thread: Optional[Thread] = None

    __event_log_lock = Lock()
    __event_log = EventLog(simulation_mode=SIMULATION_MODE)
    __exception: Optional[HTTPException] = None
    __resolved_images: Dict[str, Any] = {}

    @classmethod
    def __register_build_request(cls, build_request: BuildRequest) -> None:
        cls.__event_log.build_request_event(build_request)

    @classmethod
    def __docker_run(cls, cmd: Union[str, CmdLine], workspace: Union[str, Path, str], image: str = BASE_IMAGE) -> str:
        if not image in cls.__resolved_images:
            resolved_image = (
                docker_client.images.get(image.split("/")[-1])
                if image.startswith("@local/") else
                docker_client.images.pull(image)
            )
            cls.__event_log.input_image_event(image, resolved_image.id)
            cls.__resolved_images[image] = resolved_image
        else:
            resolved_image = cls.__resolved_images[image]
        return docker_client.containers.run(
            resolved_image,
            str(cmd),
            volumes={str(workspace.absolute()): {"bind": "/mnt", "mode": "rw"}},
            working_dir="/mnt",
        ).decode("utf8").strip()

    @classmethod
    def __fetch_resource(cls, spec: Resource, workspace: Path) -> None:
        print(f"Fetchin resource : {spec.path}")
        path = Path(spec.path)
        if path.is_absolute():
            raise HTTPException(status_code=403, detail=f"Ressource path must be relative: {path}")

        resource_hash = ""
        if spec.resource_type == "git":
            cls.__docker_run(
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
                cls.__docker_run(
                    cmd=CmdLine(["poetry", "lock", "--no-update"]),
                    workspace=workspace / path
                )
            resource_hash = cls.__docker_run(
                cmd=CmdLine(["git", "rev-parse", "--verify", "HEAD"]),
                workspace=workspace / path
            )
            resource_hash = f"sha1:{resource_hash}"
        else:
            print(f"Resource is not git")
            download_path = (
                f"/tmp/000_aicert_{str(path).replace('/', '_')}"
                if spec.resource_type == "archive" or spec.compression == "gzip" else
                path.name
            )
            final_dir = (workspace / path) if spec.resource_type == "archive" else (workspace / path.parent)
            final_dir.mkdir(exist_ok=True, parents=True)
            print(f"Created final dir: {final_dir}")
            cmd = CmdLine(["curl", "-s", "-o", download_path, "-L", spec.url])
            if spec.resource_type == "archive":
                cmd.extend(["tar", "-xzf" if spec.compression == "gzip" else "-xf", download_path])
            elif spec.compression == "gzip":
                cmd.extend(["gzip", "-c", "-d", download_path])
                cmd.redirect(path.name)
            cmd.extend(["sha256sum", download_path])
            cmd.pipe(["cut", "-d", " ", "-f", "1"])
            resource_hash = cls.__docker_run(
                cmd=cmd,
                workspace=final_dir,
            )
            resource_hash = f"sha256:{resource_hash}"
        
        cls.__event_log.input_resource_event(spec, resource_hash)

    @classmethod
    def __register_outputs(cls, ouput_pattern: str, workspace: Path) -> None:
        matches = list(workspace.glob(ouput_pattern))
        outputs = [
            (str(path.relative_to(workspace)), sha256_file(path))
            for path in matches
            if path.is_file()
        ]
        if not outputs:
            raise HTTPException(status_code=404, detail=f"No files matching output pattern: '{ouput_pattern}'")
        cls.__event_log.outputs_event(outputs)

    @classmethod
    def get_attestation(cls) -> Dict[str, Any]:
        with cls.__event_log_lock:
            return cls.__event_log.attest()

    @classmethod
    def build(cls, build_request: BuildRequest, workspace: Path) -> None:
        try:
            with cls.__event_log_lock:
                cls.__register_build_request(build_request)

                # install inputs
                for input in build_request.inputs:
                    cls.__fetch_resource(input, workspace)

                cls.__docker_run(
                    image=build_request.image,
                    cmd=build_request.cmdline,
                    workspace=workspace,
                )

                cls.__register_outputs(build_request.outputs, workspace)
        except HTTPException as e:
            cls.__exception = e
        except Exception as e:
            print(f"ERROR: {e}")
            cls.__exception = HTTPException(status_code=500, detail=str(e))

    
    @classmethod
    def submit_build(cls, build_request: BuildRequest, workspace: Path) -> None:
        with cls.__thread_lock:
            if cls.__used:
                raise HTTPException(status_code=409, detail=f"Cannot build more than once")
            cls.__used = True
            cls.__thread = Thread(target=lambda: cls.build(build_request, workspace))
            cls.__thread.start()
    
    @classmethod
    def poll_build(cls) -> bool:
        with cls.__thread_lock:
            if cls.__thread is not None and not cls.__thread.is_alive():
                with cls.__event_log_lock:
                    if cls.__exception is not None:
                        raise cls.__exception
                return True
            else:
                return False
