from fastapi import HTTPException
import hashlib
import docker
import os
from pathlib import Path
from threading import Lock, Thread
from typing import Union, Dict, Any, Optional

from aicert_common.protocol import Resource, Build, Serve
from .cmd_line import CmdLine
from .event_log import EventLog


docker_client = docker.from_env()
BASE_IMAGE = "mithrilsecuritysas/aicertbase:latest"
SIMULATION_MODE = os.getenv("AICERT_SIMULATION_MODE") is not None


def sha256_file(file_path) -> str:
    """Returns the SHA256 hash of a file"""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as file:
        for chunk in iter(lambda: file.read(4096), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


class Builder:
    """AICert Builder Interface
    
    As a build can be only be run once on an AICert Runner,
    this class provides only class attributes and class methods.

    Class attributes:
        __thread_lock (Lock): Lock that controls shared access to the `__used`
            and `__thread` attributes
        __used (bool): Whether a run has already been done
        __thread (Optional[Thread]): Thread that runs the build

        __event_log_lock (Lock): Lock that controls shared access to the
            `__event_log`, `__exception` and `__resolved_images` attributes
        __event_log (EventLog): Event log that contains all measurements
        __exception (Optional[HTTPException]): May contain an exception
            originating from the build thrad if it failed
        __resolved_images (Dict[str, Any]): Maps image names with already
            downloaded and measured images

        __serve_thread_lock (Lock): Lock that controls shared access to the
            `__serve_ready`, `__serve_image` and `__serve_thread` attributes
        __serve_ready (bool): whether the server is ready to be started
            (i.e. after the build has completed)
        __serve_image (Optional[str]): resolved image to use to launch the server
            (same as the one used for build)
        __serve_thread (Optional[Thread]): Thread that runs the server
    """
    __thread_lock = Lock()
    __used = False
    __thread: Optional[Thread] = None

    __event_log_lock = Lock()
    __event_log = EventLog(simulation_mode=SIMULATION_MODE)
    __exception: Optional[HTTPException] = None
    __resolved_images: Dict[str, Any] = {}

    __serve_thread_lock = Lock()
    __serve_ready = False
    __serve_image: Optional[str] = None
    __serve_thread: Optional[Thread] = None

    @classmethod
    def __register_build_request(cls, build_request: Build) -> None:
        """Private method: add a build request to the event log
        
        Args:
            build_request (Build): build request to measure
        """
        cls.__event_log.build_request_event(build_request)

    @classmethod
    def __docker_run(
        cls,
        cmd: Union[str, CmdLine],
        workspace: Union[str, Path],
        image: str = BASE_IMAGE,
    ) -> str:
        """Private method: run command in a docker container, return stdout

        If the requested image has not been downloaded and measured
        yet, this method handles it and add an entry to the `__resolved images`
        attribute.
        
        Args:
            cmd (Union[str, CmdLine]): command to run
            workspace (Union[str, Path]): host directory to mount at /mnt
                on the container
            image (str): name of the image to use for the run
        
        Returns:
            str
        """
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
        return (
            docker_client.containers.run(
                resolved_image,
                str(cmd),
                volumes={str(workspace.absolute()): {"bind": "/mnt", "mode": "rw"}},
                working_dir="/mnt",
            )
            .decode("utf8")
            .strip()
        )

    @classmethod
    def __fetch_resource(cls, spec: Resource, workspace: Path) -> None:
        """Private method: download a build resource and install it in the host's workspace

        Git repositories are cloned and checked out (to use the right branch) to the host's
        workspace using a docker run. If a package manager is specified, its lock file is
        generated/checked and measured.

        Files and archives are downloaded, uncompressed and extracted to the host's
        workspace using a docker run.

        All docker run commands use the AICert base image that is built upon alpine
        and that contains a minimal set of tools (git, curl, gzip, tar, etc.)
        
        Args:
            spec (Resource): specification of the resource (see aicert-common's protocol)
            workspace (Union[str, Path]): host's working directory
        """
        path = Path(spec.path)
        if path.is_absolute():
            raise HTTPException(
                status_code=403, detail=f"Ressource path must be relative: {path}"
            )

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
                if (
                    not (workspace / path / "poetry.lock").exists()
                    and not (workspace / path / "pyproject.toml").exists()
                ):
                    raise HTTPException(
                        status_code=404,
                        detail="Cannot resolve poetry dependencies without a `poetry.lock` or a `pyproject.toml` file",
                    )
                cls.__docker_run(
                    cmd=CmdLine(["poetry", "lock", "--no-update"]),
                    workspace=workspace / path,
                )
            resource_hash = cls.__docker_run(
                cmd=CmdLine(["git", "rev-parse", "--verify", "HEAD"]),
                workspace=workspace / path,
            )
            resource_hash = f"sha1:{resource_hash}"
        else:
            download_path = (
                f"/tmp/000_aicert_{str(path).replace('/', '_')}"
                if spec.resource_type == "archive" or spec.compression == "gzip" else
                path.name
            )
            final_dir = (workspace / path) if spec.resource_type == "archive" else (workspace / path.parent)
            final_dir.mkdir(exist_ok=True, parents=True)
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
        """Private method: add hashes of output files to the event log
        
        Args:
            output_pattern (str): glob pattern to select output files from
                the workspace
            workspace (Path)
        """
        matches = list(workspace.glob(ouput_pattern))
        outputs = [
            (str(path.relative_to(workspace)), sha256_file(path))
            for path in matches
            if path.is_file()
        ]
        if not outputs:
            raise HTTPException(
                status_code=404,
                detail=f"No files matching output pattern: '{ouput_pattern}'",
            )
        cls.__event_log.outputs_event(outputs)

    @classmethod
    def __build_fn(cls, build_request: Build, workspace: Path) -> None:
        """Private method: implements the build process, run by the build thread

        1. Add build request to the event log
        2. Fetch all resources (download and measure)
        3. Run the build in a docker container using specified image
        4. List and add the hashes of the output files to the event log
        
        Args:
            build_request (Build): build spec (see aicert-common's protocol)
            workspace (Path): directory to mount at /mnt on every containers
                used during the build, this will contain the outputs
        """
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

            with cls.__serve_thread_lock:
                cls.__serve_ready = True
                cls.__serve_image = build_request.image

        except HTTPException as e:
            cls.__exception = e
        except Exception as e:
            print(f"ERROR: {e}")
            cls.__exception = HTTPException(status_code=500, detail=str(e))
    
    @classmethod
    def __serve_fn(cls, serve_request: Serve, workspace: Path) -> None:
        """Private method: implements the serving process, run by the serve thread
        
        Args:
            serve_request (Serve): serve spec (see aicert-common's protocol)
            workspace (Path): directory to mount at /mnt on the container and
                that contains the result of the build
        """
        docker_client.containers.run(
            cls.__resolved_images[cls.__serve_image],
            serve_request.cmdline,
            volumes={str(workspace.absolute()): {"bind": "/mnt", "mode": "rw"}},
            working_dir="/mnt",
            ports={f'{serve_request.container_port}/tcp': serve_request.host_port}
        )
    
    @classmethod
    def get_attestation(cls) -> Dict[str, Any]:
        """Return the event log and the corresponding TPM measurement
        
        Blocks until the event log lock is released (i.e. when the build is over).
        """
        with cls.__event_log_lock:
            return cls.__event_log.attest()

    @classmethod
    def submit_build(cls, build_request: Build, workspace: Path) -> None:
        """Start the execution of the build in a separate thread

        If a build has already been done, an exception is raised.

        Args:
            build_request (Build): build specs (see aicert-common's protocol)
            workspace (Path): directory where inputs are downloaded and that will
                be mounted on the build container at /mnt
        """
        with cls.__thread_lock:
            if cls.__used:
                raise HTTPException(
                    status_code=409, detail=f"Cannot build more than once"
                )
            cls.__used = True
            cls.__thread = Thread(target=lambda: cls.__build_fn(build_request, workspace))
            cls.__thread.start()
    
    @classmethod
    def submit_serve(cls, serve_request: Serve, workspace: Path) -> None:
        """Start the execution of the build in a separate thread

        If a build has not been done yet, an exception is raised.

        Args:
            serve_request (Serve): serve specs (see aicert-common's protocol)
            workspace (Path): directory containing the outputs of the build
                and that willbe mounted on the serve container at /mnt
        """
        with cls.__serve_thread_lock:
            if not cls.__serve_ready:
                raise HTTPException(
                    status_code=409, detail=f"Cannot serve before a build has been completed"
                )
            cls.__serve_thread = Thread(target=lambda: cls.__serve_fn(serve_request, workspace))
            cls.__serve_thread.start()

    @classmethod
    def poll_build(cls) -> bool:
        """Check build status
        
        Returns False while the build thread has not completed, True if it has
        completed successfully and (re)raises an error if one occured in the thread.
        """
        with cls.__thread_lock:
            if cls.__thread is not None and not cls.__thread.is_alive():
                with cls.__event_log_lock:
                    if cls.__exception is not None:
                        raise cls.__exception
                return True
            else:
                return False
