from fastapi import HTTPException
import hashlib
import docker
import os
from pathlib import Path
from threading import Lock, Thread
from typing import Union, Dict, Any, Optional
import logging
import yaml
import zipfile

from aicert_common.protocol import Resource
from aicert_server.cmd_line import CmdLine
from aicert_server.event_log import EventLog
from aicert_server.config_parser import AxolotlConfig
from aicert_server.log_streamer import LogStreamer

docker_client = docker.from_env()
BASE_IMAGE = "@local/aicert-base:latest"
AXOLOTL_IMAGE = "@local/axolotl:latest"
SIMULATION_MODE = os.getenv("AICERT_SIMULATION_MODE") is not None

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        __docker_output_stream (str): Docker output container stream

        __event_log_lock (Lock): Lock that controls shared access to the
            `__event_log`, `__exception` and `__resolved_images` attributes
        __event_log (EventLog): Event log that contains all measurements
        __exception (Optional[HTTPException]): May contain an exception
            originating from the build thrad if it failed
        __resolved_images (Dict[str, Any]): Maps image names with already
            downloaded and measured images

        __finetune_thread_lock (Lock): Lock that controls shared access to the 
            `__finetune_thread_in_use`, `__finetune_framework` and `__finetune_thread` attributes
        __finetune_thread_in_use (bool): whether the server is ready to be started
            (i.e. after the build has completed)
        __finetune_framework (Optional[str]): resolved image to use to launch the server
            (same as the one used for build)
        __finetune_thread (Optional[Thread]): Thread that runs the server
        

    """
    __docker_output_stream : str = ""

    __event_log_lock = Lock()
    __event_log = EventLog(simulation_mode=SIMULATION_MODE)
    __exception: Optional[HTTPException] = None
    __resolved_images: Dict[str, Any] = {}

    __fineture_thread_lock = Lock()
    __fineture_thread_in_use = False
    __finetune_thread: Optional[Thread] = None 
    __finetune_framework : str = "axolotl"

    
    @classmethod
    def __register_axolotl_config(cls, workspace: Path, axolotl_config: AxolotlConfig) -> None:
        """Private method: add an axolotl configuration to the event log
        
        Args: 
            axolotl_config (AxolotlConfig): Axolotl configuration to measure
        """
        with open(workspace / axolotl_config.filename, 'rb') as config:
            configuration_content = yaml.safe_load(config)
        cls.__event_log.configuration_event(configuration_file=configuration_content, configuration_file_hash=sha256_file(workspace / axolotl_config.filename))


    @classmethod
    def __docker_run(
        cls,
        cmd: Union[str, CmdLine],
        workspace: Union[str, Path],
        image: str = BASE_IMAGE,
        gpus: Optional[str] = "",
        env: Optional[list] = [],
        network_disabled: bool = False, 
        network_mode: str = 'host',
        detach: bool = False,
        remove: bool = False, 
    ) -> Union[str, docker.models.containers.Container]:
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

        if gpus == "":
            return (
                docker_client.containers.run(
                    resolved_image,
                    str(cmd),
                    volumes={str(workspace.absolute()): {"bind": "/mnt", "mode": "rw"}},
                    working_dir="/mnt",
                    environment=env,                    
                    detach=detach,
                    remove=remove
                )
            )
        else:
            count = 0
            try: 
                count = int(gpus)
            except ValueError as verr:
                if gpus=="all":
                    count = -1
                else:
                    logger.exception("ValueError: gpu option not All and not integer" + verr)
            except Exception as e: 
                logger.exception(e)
            return (
                docker_client.containers.run(
                    resolved_image,
                    str(cmd),
                    volumes={str(workspace.absolute()) : {"bind": "/mnt", "mode":"rw"}},
                    working_dir="/mnt",
                    device_requests=[
                        docker.types.DeviceRequest(count=count, capabilities=[['gpu']])
                    ],
                    environment=env,
                    network_disabled=network_disabled,
                    network_mode=network_mode,
                    detach=detach,
                    remove=remove
                )
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
                status_code=403, detail=f"Resource path must be relative: {path}"
            )

        resource_hash = ""
        logger.info("resource type is : ")
        logger.info(spec.resource_type)

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
        elif spec.resource_type == "model" or spec.resource_type == "dataset":
            container_hash = cls.__docker_run(
                cmd=CmdLine(
                    ["git", "lfs", "install"],
                    ["git", "clone", spec.repo, path],
                    ["cd", path], 
                    ["git", "fetch", "origin", spec.hash], 
                    ["git", "reset", "--hard", "FETCH_HEAD"]
                ),
                workspace=workspace,
                detach=True, 
            )
            
            log_streamer_dataset = LogStreamer(workspace / "log_model_dataset.log")
            log_streamer_dataset.write_stream(container_hash, False)

            resource_hash = cls.__docker_run(
                cmd=CmdLine(["git", "rev-parse", "--verify", "HEAD"]),
                workspace=workspace / path,
                detach=False, 
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
    def __axolotl_run(cls, 
        axolotl_config: AxolotlConfig,
        axolotl_image: str,
        workspace: Path
        ) -> None:
        try: 
            cmd_accelerate = CmdLine(
                #['CUDA_VISIBLE_DEVICES=""', "python", "-m", "axolotl.cli.preprocess", axolotl_config.filename], # Axolotl preprocessing
                ["accelerate", "launch", "-m", "axolotl.cli.train", axolotl_config.filename],
            )

            # These environment variables should make HuggingFace run only locally. 
            # The huggingface hub location should also be changed to workspace where models and datasets are available
            # The other environment variable that changes the cache is TRANSFORMERS_CACHE
            env_offline = ["HF_DATASETS_OFFLINE=1", "TRANSFORMERS_OFFLINE=1"] #, f"HUGGINGFACE_HUB_CACHE={workspace}"]
            container_hash = cls.__docker_run(
                image=axolotl_image,
                cmd=cmd_accelerate,
                workspace=workspace,
                gpus="all",
                env=env_offline,
                network_disabled=True,
                network_mode='none',
                detach=True,
            )

            # Log streamer registers the stdout for the docker into the log file log_axolotl.log
            log_streamer_finetune = LogStreamer(workspace / "log_model_dataset.log")
            log_streamer_finetune.write_stream(container_hash, True)

        except HTTPException as e:
            cls.__exception = e
        except Exception as e:
            print(f"error : {e}")
            cls.__exception = HTTPException(status_code=500, detail=str(e))

    @classmethod
    def __finetune_fn(cls,
            workspace: Path, 
            axolotl_config: AxolotlConfig, 
            finetune_image: str = AXOLOTL_IMAGE, 
        ) -> None:
        """Private method: starts the finetuning with a framework (axolotl in this example) and the data fetched previously 

        Args: 
            workspace (Path): directory to mount at /mnt on the container and 
                that contains the result of the finetuning 
        """
        import json
        try:
            with cls.__event_log_lock:
                cls.__finetune_framework = "axolotl"
                cls.__register_axolotl_config(workspace=workspace, axolotl_config=axolotl_config)

                # install inputs
                for input in axolotl_config.resources:
                    logger.info(input)
                    cls.__fetch_resource(input, workspace)
                    logger.info(cls.__docker_output_stream)

                if cls.__finetune_framework == "axolotl":
                    import time
                    start_time = time.time()
                    cls.__axolotl_run(axolotl_config=axolotl_config, axolotl_image=finetune_image, workspace=workspace)
                    training_time = time.time() - start_time
                    cls.__event_log.finetune_timing(training_time)

                # Registering output and compression 
                with zipfile.ZipFile(workspace / 'finetuned-model.zip','w', zipfile.ZIP_DEFLATED) as zipf:
                    for root, dirs, files in os.walk(workspace / "lora-out"):
                        for file in files:
                            zipf.write(os.path.join(root, file),
                                    os.path.relpath(os.path.join(root,file), os.path.join(workspace /"lora-out", '..'))
                            )
                            if file == "trainer_state.json":
                                path = os.path.join(root, file)
                                with open(path) as file:
                                    trainer_state = json.load(file)
                                    cls.__event_log.finetune_flos(trainer_state["total_flos"])
        
                cls.__register_outputs('finetuned-model.zip', workspace)
        
        except HTTPException as e:
            cls.__exception = e
        except Exception as e:
            print(f"ERROR: {e}")
            cls.__exception = HTTPException(status_code=500, detail=str(e))        


    @classmethod
    def get_output_stream(cls) -> str: 
        return cls.__docker_output_stream

    
    @classmethod
    def get_attestation(cls, ca_cert = "") -> Dict[str, Any]:
        """Return the event log and the corresponding TPM measurement
        
        Blocks until the event log lock is released (i.e. when the build is over).
        """
        with cls.__event_log_lock:
            return cls.__event_log.attest(ca_cert)

    

    @classmethod
    def start_finetune(cls, workspace: Path, axolotl_config: AxolotlConfig) -> None:
        """Starts the finetuning with axolotl 

        Args: 
            axolotl_config (AxolotlConfig): Axolotl's parsed configuration
            workspace (Path): directory containing the results and build components 
                mounted at /mnt
        
        """
        with cls.__fineture_thread_lock:
            if cls.__fineture_thread_in_use:
                raise HTTPException(
                    status_code=409, detail=f"Finetuning thread in use"
                )
            cls.__fineture_thread_in_use = True
            cls.__finetune_thread = Thread(target=lambda: cls.__finetune_fn(workspace, axolotl_config))
            cls.__finetune_thread.start()


    
    @classmethod
    def poll_finetune(cls) -> bool:
        """Check build status
        
        Returns False while the finetune thread has not completed, True if it has
        completed successfully and (re)raises an error if one occured in the thread.
        """
        with cls.__fineture_thread_lock:
            if cls.__finetune_thread is not None and not cls.__finetune_thread.is_alive():
                with cls.__event_log_lock:
                    if cls.__exception is not None:
                        raise cls.__exception
                return True
            else:
                return False
    