import tempfile
from cryptography.hazmat.primitives import serialization
from cryptography.x509 import load_der_x509_certificate
import json
from pathlib import Path
import pkgutil
import requests
import shutil
import subprocess
import sys
from time import sleep
import typer
from typing import List, Optional
import urllib.parse
import yaml

from aicert_common.protocol import ConfigFile, FileList
from .logging import log
from .requests_adapter import ForcedIPHTTPSAdapter
from .verify import (
    PCR_FOR_MEASUREMENT,
    check_event_log,
    check_quote,
    decode_b64_encoding,
    verify_ak_cert,
)


class Client:
    def __init__(
        self,
        cfg: Optional[ConfigFile] = None,
        interactive: bool = True,
        auto_approve: bool = True,
        simulation_mode: bool = False,
    ) -> None:
        self.__cfg: Optional[ConfigFile] = cfg
        self.__tf_available: Optional[bool] = None
        self.__interactive = interactive
        self.__auto_approve = auto_approve
        self.__simulation_mode = simulation_mode

        if self.__simulation_mode:
            log.warning("Running in simulation mode")

    def __copy_template(
        self,
        src_path: str,
        dst_path: Path,
        executable: bool = False,
        replace: bool = False,
        confirm_replace: bool = False,
        merge: bool = False,
    ):
        data = pkgutil.get_data(__name__, src_path)

        if dst_path.exists():
            if confirm_replace:
                replace = (
                    typer.confirm(f"Replace file {dst_path}?")
                    if self.__interactive
                    else True
                )

            if not replace and not merge:
                return

            if merge:
                with dst_path.open("rb") as f:
                    existing_data = f.read()

                if data not in existing_data:
                    existing_data += bytes("\n", "utf-8")
                    existing_data += data
                data = existing_data

        with dst_path.open("wb") as f:
            f.write(data)

        if executable:
            dst_path.chmod(0o775)

    def __assert_tf_available(self):
        if self.__tf_available is None:
            # Check if the terraform binary is installed
            try:
                res = subprocess.run(
                    ["terraform", "--version"],
                    capture_output=True,
                    text=True,
                )
                self.__tf_available = res.returncode == 0
            except FileNotFoundError:
                self.__tf_available = False

        if not self.__tf_available:
            log.error(
                "Terraform CLI was not found in PATH. Follow the instructions at [underline]https://developer.hashicorp.com/terraform/tutorials/aws-get-started/install-cli[/]."
            )
            raise typer.Exit(code=1)

    def __tf_init(self, dir: Path):
        self.__assert_tf_available()

        if not (dir / ".terraform").exists():
            self.__run_subprocess(["terraform", "init"], dir=dir)

    def __tf_apply(self, dir: Path, vars: dict = {}):
        self.__assert_tf_available()

        args = ["terraform", "apply"]
        if not self.__interactive or self.__auto_approve:
            args += ["-auto-approve"]
        for k, v in vars.items():
            args += ["--var", f"{k}={v}"]

        self.__run_subprocess(args, dir=dir)

    def __tf_destroy(self, dir: Path, vars: dict = {}):
        self.__assert_tf_available()

        args = ["terraform", "destroy"]
        if not self.__interactive or self.__auto_approve:
            args += ["-auto-approve"]
        for k, v in vars.items():
            args += ["--var", f"{k}={v}"]

        self.__run_subprocess(args, dir=dir)

    def __run_subprocess(
        self,
        command: List[str],
        cwd: Optional[Path] = None,
        text: bool = False,
        return_stdout: bool = False,
        quiet: bool = False,
        assert_returncode: bool = True,
    ) -> Optional[str]:
        human_readable_command = " ".join(command)
        if not quiet:
            log.info(f"Running `{human_readable_command}`...")

        try:
            res = subprocess.run(
                command,
                cwd=str(cwd.absolute()),
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

    def __load_config(self, dir: Path):
        with (dir / "aicert.yaml").open("rb") as file:
            try:
                data = yaml.safe_load(file)
            except yaml.YAMLError as e:
                e.context_mark.name = "aicert.yaml"
                e.problem_mark.name = "aicert.yaml"
                log.error(f"Failed to parse aicert.yaml file")
                log.error(f"{e}")
                raise typer.Exit(code=1)

        self.__cfg = ConfigFile(**data)

    def __save_config(self, dir: Path):
        with (dir / "aicert.yaml").open("wb") as file:
            yaml.safe_dump(dict(self.__cfg), file)

    @staticmethod
    def from_config_file(
        dir: Path,
        interactive: bool = True,
        auto_approve: bool = False,
        simulation_mode=False,
    ) -> "Client":
        client = Client(
            interactive=interactive,
            auto_approve=auto_approve,
            simulation_mode=simulation_mode,
        )
        client.__load_config(dir)

        return client

    def new_cmd(self, dir: Path) -> None:
        """Set up the workspace by copying template files"""
        dir.mkdir(exist_ok=True)
        self.__copy_template(
            "templates/aicert.yaml", dir / "aicert.yaml", confirm_replace=True
        )

        log.info("AICert project has been initialized.")

    def build_cmd(self, dir: Path, control_plane_url: str) -> None:
        """Run the actual build on a server
        - copy terraform templates to ~/.aicert
        - run terraform init on ~/.aicert
        - run terraform apply on ~/.aicert
        - send a request to the server
        - save outputs to a file (attestation and artifacts)
        - run terraform destroy on ~/.aicert
        """
        if not self.__simulation_mode:
            log.info("Launching the runner...")
            r = requests.post(f"{control_plane_url}/launch_runner")
            log.info("Runner is ready.")
            r.raise_for_status()
            r = r.json()

            base_url = "https://aicert_worker"

            session = requests.Session()
            session.mount(
                "https://aicert_worker", ForcedIPHTTPSAdapter(dest_ip=r["runner_ip"])
            )

            client_crt_file = tempfile.NamedTemporaryFile(mode="w+t")
            client_key_file = tempfile.NamedTemporaryFile(mode="w+t")
            server_ca_crt_file = tempfile.NamedTemporaryFile(mode="w+t")

            client_crt_file.write(r["client_cert"])
            client_crt_file.flush()
            client_key_file.write(r["client_private_key"])
            client_key_file.flush()
            server_ca_crt_file.write(r["server_ca_cert"])
            server_ca_crt_file.flush()

            session.verify = server_ca_crt_file.name
            session.cert = (client_crt_file.name, client_key_file.name)
        else:
            base_url = "http://localhost:8000"
            session = requests.Session()

        # Submit build request
        log.info("Submitting build request")
        log_and_exit_for_status(
            session.post(
                f"{base_url}/submit",
                data=self.__cfg.build.json(),
                headers={"Content-Type": "application/json"},
            ),
            "Cannot submit build to server",
        )

        # Wait until attestation is available
        while True:
            res = session.get(f"{base_url}/attestation")
            if res.status_code == 204:
                sleep(1)
                continue
            log_and_exit_for_status(
                res, "Cannot retrieve attestation, build likely failed"
            )

            with (dir / "attestation.json").open("wb") as f:
                f.write(res.content)
            break
        log.info("Attestation received")

        # Download output files
        pattern = urllib.parse.quote(self.__cfg.build.outputs, safe="")
        res = session.get(f"{base_url}/outputs?pattern={pattern}")
        log_and_exit_for_status(res, "Cannot download outputs list")
        file_list = FileList.parse_raw(res.text)

        for filename in file_list.file_list:
            log.info(f"Downloading output: {filename}")
            res = session.get(f"{base_url}/outputs/{filename}")
            log_and_exit_for_status(res, f"Cannot download output file {filename}")
            with (dir / filename).open("wb") as f:
                f.write(res.content)

        if not self.__simulation_mode:
            log.info("Destoying runner")
            requests.post("http://localhost:8082/destroy_runner")
            log.info("Runner destroyed successfully")

    def verify_cmd(self, dir: Path) -> None:
        """Launch verification process

        Example:
        aicert verify "/workspaces/aicert_dev/server/aicert_server/sample_build_response.json"
        """
        with (dir / "attestation.json").open("r") as f:
            build_response = json.load(f)

        if "simulation_mode" in build_response["remote_attestation"]:
            if self.__simulation_mode:
                typer.secho(
                    f"👀 Attestation generated in simulation mode",
                    fg=typer.colors.YELLOW,
                )
                typer.secho(f"✨✨✨ ALL CHECKED PASSED", fg=typer.colors.GREEN)
            else:
                typer.secho(
                    f"❌ Attestation generated in simulation mode", fg=typer.colors.RED
                )
                typer.secho(f"💀 INVALID ATTESTATION", fg=typer.colors.RED)
            return

        build_response["remote_attestation"]["cert_chain"] = [
            decode_b64_encoding(cert_b64_encoded)
            for cert_b64_encoded in build_response["remote_attestation"]["cert_chain"]
        ]

        ak_cert = verify_ak_cert(
            cert_chain=build_response["remote_attestation"]["cert_chain"]
        )

        typer.secho(f"✅ Valid certificate chain", fg=typer.colors.GREEN)

        ak_cert_ = load_der_x509_certificate(ak_cert)
        ak_pub_key = ak_cert_.public_key()
        ak_pub_key_pem = ak_pub_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

        build_response["remote_attestation"]["quote"] = {
            k: decode_b64_encoding(v)
            for k, v in build_response["remote_attestation"]["quote"].items()
        }
        att_document = check_quote(
            build_response["remote_attestation"]["quote"], ak_pub_key_pem
        )

        typer.secho(f"✅ Valid quote", fg=typer.colors.GREEN)

        log.info(
            f"Attestation Document > PCRs :  \n{yaml.safe_dump(att_document['pcrs']['sha256'])}"
        )

        # We should check the PCR to make sure the system has booted properly
        # This is an example ... the real thing will depend on the system.
        assert (
            att_document["pcrs"]["sha256"][0]
            == "d0d725f21ba5d701952888bcbc598e6dcef9aff4d1e03bb3606eb75368bab351"
        )
        assert (
            att_document["pcrs"]["sha256"][1]
            == "fe72566c7f411900f7fa1b512dac0627a4cac8c0cb702f38919ad8c415ca47fc"
        )
        assert (
            att_document["pcrs"]["sha256"][2]
            == "3d458cfe55cc03ea1f443f1562beec8df51c75e14a9fcf9a7234a13f198e7969"
        )
        assert (
            att_document["pcrs"]["sha256"][3]
            == "3d458cfe55cc03ea1f443f1562beec8df51c75e14a9fcf9a7234a13f198e7969"
        )
        assert (
            att_document["pcrs"]["sha256"][4]
            == "1f0105624ab37b9af59da6618a406860e33ef6f42a38ddaf6abfab8f23802755"
        )
        assert (
            att_document["pcrs"]["sha256"][5]
            == "d36183a4ce9f539d686160695040237da50e4ad80600607f84eff41cf394dcd8"
        )

        typer.secho(f"✅ Checking reported PCRs are as expected", fg=typer.colors.GREEN)

        # To make test easier we use the PCR 16 since it is resettable `tpm2_pcrreset 16`
        # But because it is resettable it MUST NOT be used in practice.
        # An unused PCR that cannot be reset (SRTM) MUST be used instead
        # PCR 14 or 15 should do it
        event_log = check_event_log(
            build_response["event_log"],
            att_document["pcrs"]["sha256"][PCR_FOR_MEASUREMENT],
        )

        typer.secho(f"✅ Valid event log", fg=typer.colors.GREEN)

        print(yaml.safe_dump(event_log))

        typer.secho(f"✨✨✨ ALL CHECKS PASSED", fg=typer.colors.GREEN)


def log_and_exit_for_status(res: requests.Response, message: str) -> None:
    if not res.ok:
        log.error(message)
        log.error(f"{res.status_code} - {res.reason}")
        log.error(f"{res.text}")
        raise typer.Exit(code=1)
