import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import List, Optional

from aicert_common.logging import log
from aicert_common.errors import AICertException


class AICertTfUnavailable(AICertException):
    """Terraform is not available"""
    def __init__(self) -> None:
        err = "Terraform CLI was not found in PATH. Follow the instructions at [underline]https://developer.hashicorp.com/terraform/tutorials/aws-get-started/install-cli[/]."
        super().__init__(err)

class AICertSubProcessException(AICertException):
    """Subprocess failure (non zero return code)"""
    def __init__(self, command: str, retcode: int, stdout: str, stderr: str) -> None:
        self.__command = command
        self.__retcode = retcode
        self.__stdout = stdout
        self.__stderr = stderr
        err = f"Command `{self.__command}` terminated with non-zero return code: {self.__retcode}\nstdout: {self.__stdout}\nstderr: {self.__stderr}"
        super().__init__(err)

class Deployer:
    """Python API of the Deployer.
    
    This class contains methods that cover the main steps for launching AICert runners.
    These methods rely on terraform to deploy runners.
    """

    __tf_available: Optional[bool] = None

    @classmethod
    def __assert_tf_available(cls) -> None:
        """Private method: check if terraform is installed"""
        if cls.__tf_available is None:
            # Check if the terraform binary is installed
            try:
                cls.__run_subprocess(["terraform", "--version"])
            except FileNotFoundError:
                raise AICertTfUnavailable()
            except AICertSubProcessException:
                raise AICertTfUnavailable()

    @classmethod
    def __tf_init(cls, dir: Path) -> None:
        """Private method: run terraform init as a subprocess

        Args:
            dir (Path): Working directory
        """
        cls.__assert_tf_available()

        if not (dir / ".terraform").exists():
            cls.__run_subprocess(["terraform", "init"], cwd=dir)

    @classmethod
    def __tf_apply(cls, dir: str, vars: dict = {}) -> None:
        """Private method: run terraform apply as a subprocess

        Args:
            dir (Path): Working directory
            vars (dict): Values for the terraform variables as a dict
        """
        cls.__assert_tf_available()

        args = ["terraform", "apply", "-auto-approve"]
        for k, v in vars.items():
            args += ["--var", f"{k}={v}"]

        cls.__run_subprocess(args, cwd=dir)

    @classmethod
    def __tf_destroy(cls, dir: str, vars: dict = {}) -> None:
        """Private method: run terraform destroy as a subprocess

        Args:
            dir (Path): Working directory
            vars (dict): Values for the terraform variables as a dict
        """
        cls.__assert_tf_available()

        args = ["terraform", "destroy", "-auto-approve"]
        for k, v in vars.items():
            args += ["--var", f"{k}={v}"]

        cls.__run_subprocess(args, cwd=dir)
    
    @classmethod
    def __tf_exclude(cls, resource_type: str, dir: str, vars: dict = {}) -> None:
        """Private method: run terraform state rm to exlude resource from plan
        
        Args:
            dir (Path): Working directory
            vars (dict): Values for the terraform variables as a dict
        """
        cls.__assert_tf_available()

        resource_list = cls.__run_subprocess(command=["terraform", "state", "list"], cwd=dir, string_flag=False)
        resource = subprocess.run(["grep", resource_type], input=resource_list, capture_output=True, cwd=dir)
        resource_name = resource.stdout.decode("utf-8")

        args = ["terraform", "state", "rm", resource_name]

        cls.__run_subprocess(args, cwd=dir)

    @classmethod
    def __run_subprocess(
        self,
        command: List[str],
        cwd: Optional[Path] = None,
        verbose: bool = False,
        assert_returncode: bool = True,
        string_flag = True,
    ) -> str:
        """Private method: run a command as a subprocess and return its stdout as a string
        
        Args:
            command (List[str]): Command to run in a subprocess
            cwd (Path, optional): Working directory of the subprocess
            text (bool, default = False): Text mode
            verbose (bool, default = False): Whether to print info about the subprocess
            assert_returncode (bool, default = True): Raise an error if the return code is non zero
        
        Returns:
            str
        """
        human_readable_command = " ".join(command)
        if verbose:
            log.info(f"Running `{human_readable_command}`...")
        
        if cwd is None:
            cwd = Path.cwd()

        try:
            res = subprocess.run(
                command,
                cwd=str(cwd.absolute()),
                stdin=sys.stdin,
                capture_output=True,
                text=string_flag,
            )
        except KeyboardInterrupt:
            exit(1)

        if assert_returncode and res.returncode != 0:
            raise AICertSubProcessException(
                human_readable_command,
                res.returncode,
                res.stdout,
                res.stderr
            )

        return res.stdout

    @classmethod
    def init(cls, dir: Path) -> None:
        """Initailize the Deployer

        - Check dependencies
        - Create workding directory
        - Install runner code

        Args:
            dir (Path): Working directory
        """
        cls.__assert_tf_available()

        dir.mkdir(exist_ok=True)

        deploy_folder = Path(__file__).parent/ "deploy"
        shutil.copytree(deploy_folder, dir, dirs_exist_ok=True)

    @classmethod
    def launch_runner(cls, dir: Path) -> dict:
        """Launch runner

        Take terraform configuration from working directory

        Args:
            dir (Path): Working directory
        """
        Deployer.__tf_init(dir)
        Deployer.__tf_apply(dir)

        vm_ip = Deployer.__run_subprocess(
            ["terraform", "output", "-raw", "public_ip_address"],
            cwd=dir,
        )
        storage_account = Deployer.__run_subprocess(
            ["terraform", "output", "-raw", "storage_account_name"],
            cwd=dir,
        )
        storage_container = Deployer.__run_subprocess(
            ["terraform", "output", "-raw", "storage_container_name"],
            cwd=dir,
        )

        return {
            "runner_ip": vm_ip,
            "storage_account": storage_account,
            "storage_container": storage_container
        }

    @classmethod
    def destroy_runner(cls, dir: Path) -> None:
        """Destroy runner

        Args:
            dir (Path): Working directory
        """
        cls.__tf_exclude("azurerm_storage_account", dir)
        cls.__tf_exclude("azurerm_storage_container", dir)
        
        cls.__tf_destroy(dir)
