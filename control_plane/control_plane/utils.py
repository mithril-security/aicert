import os
import pkgutil
import subprocess
import sys
from typing import List, Optional
import yaml
from .logging import log


class Client:
    def __init__(
        self,
        interactive: bool = True,
        auto_approve: bool = True,
    ) -> None:
        self._tf_available: Optional[bool] = None
        self._interactive = interactive
        self._auto_approve = auto_approve


    def _assert_tf_available(self):
        if self._tf_available is None:
            # Check if the terraform binary is installed
            try:
                res = subprocess.run(
                    ["terraform", "--version"],
                    capture_output=True,
                    text=True,
                )
                self._tf_available = res.returncode == 0
            except FileNotFoundError:
                self._tf_available = False

        if not self._tf_available:
            log.error(
                "Terraform CLI was not found in PATH. Follow the instructions at [underline]https://developer.hashicorp.com/terraform/tutorials/aws-get-started/install-cli[/]."
            )
            raise typer.Exit(code=1)

    def _tf_init(self, dir: str):
        self._assert_tf_available()

        if not os.path.exists(os.path.join(dir, ".terraform")):
            self._run_subprocess(["terraform", "init"], dir=dir)

    def _tf_apply(self, dir: str, vars: dict = {}):
        self._assert_tf_available()

        args = ["terraform", "apply"]
        if not self._interactive or self._auto_approve:
            args += ["-auto-approve"]
        for k, v in vars.items():
            args += ["--var", f"{k}={v}"]

        self._run_subprocess(args, dir=dir)

    def _tf_destroy(self, dir: str, vars: dict = {}):
        self._assert_tf_available()

        args = ["terraform", "destroy"]
        if not self._interactive or self._auto_approve:
            args += ["-auto-approve"]
        for k, v in vars.items():
            args += ["--var", f"{k}={v}"]

        self._run_subprocess(args, dir=dir)

    def _run_subprocess(
        self,
        command: List[str],
        text: bool = False,
        return_stdout: bool = False,
        dir: Optional[str] = None,
        quiet: bool = False,
        assert_returncode: bool = True,
    ):
        human_readable_command = " ".join(command)
        if not quiet:
            log.info(f"Running `{human_readable_command}`...")

        try:
            res = subprocess.run(
                command,
                cwd=dir,
                stdin=sys.stdin,
                capture_output=return_stdout,
                text=text,
            )
        except KeyboardInterrupt:
            exit(1)

        if assert_returncode and res.returncode != 0:
            if return_stdout:
                log.info(f"stdout: {res.stdout}")
                log.info(f"stderr: {res.stderr}")
            log.error(
                f"Command `{human_readable_command}` terminated with non-zero return code: {res.returncode}"
            )
            exit(1)

        if return_stdout:
            return res.stdout

    def _load_config(self, dir: str):
        with open(os.path.join(dir, "aicert.yaml"), "rb") as file:
            dict = yaml.safe_load(file)
        self._cfg = ConfigFile(**dict)

    def _save_config(self, dir: str):
        with open(os.path.join(dir, "aicert.yaml"), "wb") as file:
            yaml.safe_dump(dict(self._cfg), file)

    @staticmethod
    def from_config_file(
        dir: str, interactive: bool = True, auto_approve: bool = False
    ) -> "Client":
        client = Client(interactive=interactive, auto_approve=auto_approve)
        client._load_config(dir)

        return client