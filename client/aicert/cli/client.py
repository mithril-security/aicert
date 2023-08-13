from contextlib import contextmanager
from cryptography.hazmat.primitives import serialization
from cryptography.x509 import load_der_x509_certificate
import json
from pathlib import Path
import pkgutil
import requests
import subprocess
import sys
import tempfile
from time import sleep
import typer
from typing import List, Optional
import urllib.parse
import yaml
import warnings

from aicert_common.protocol import ConfigFile, FileList, Runner, Build, Serve
from .logging import log
from .requests_adapter import ForcedIPHTTPSAdapter
from .verify import (
    PCR_FOR_MEASUREMENT,
    check_event_log,
    check_quote,
    decode_b64_encoding,
    verify_ak_cert,
)


class AICertClientException(Exception):
    def __init__(self, message: str, *args: object) -> None:
        self.message = message
        super().__init__(self.message, *args)


class AICertClientSubProcessException(AICertClientException):
    def __init__(self, command: str, retcode: int, stdout: str, stderr: str) -> None:
        self.__command = command
        self.__retcode = retcode
        self.__stdout = stdout
        self.__stderr = stderr
        self.message = f"Command `{self.__command}` terminated with non-zero return code: {self.__retcode}\nstdout: {self.__stdout}\nstderr: {self.__stderr}"
        super().__init__(self.message)


class AICertClientConfigFileException(AICertClientException):
    def __init__(self, err: yaml.YAMLError) -> None:
        self.__err = err
        self.__err.context_mark.name = "aicert.yaml"
        self.__err.problem_mark.name = "aicert.yaml"
        self.message = f"Failed to parse aicert.yaml file\n{self.__err}"
        super().__init__(self.message)


class AICertClientHTTPException(AICertClientException):
    def __init__(self, message: str, response: requests.Response) -> None:
        self.__res = response
        self.message = f"Protocol error: {message}\nReceived HTTP response: {response.status_code} - {response.reason}\n{response.text}"
        super().__init__(self.message)


class AICertClientInvalidAttestationFormatException(AICertClientException):
    def __init__(self, err: Exception) -> None:
        self.__err = err
        self.message = f"Invalid attestation format\n{self.__err}"
        super().__init__(self.message)


class AICertClientInvalidAttestationException(AICertClientException):
    pass


@contextmanager
def log_errors_and_warnings():
    try:
        yield None
    except AICertClientException as e:
        log.error(f"{e.message}")
        raise typer.Exit(code=1)
    finally:
        with warnings.catch_warnings(record=True) as ws:
            for w in ws:
                log.warning(w.message)


class Client:
    def __init__(
        self,
        cfg: Optional[ConfigFile] = None,
        interactive: bool = False,
        simulation_mode: bool = False,
    ) -> None:
        self.__cfg: Optional[ConfigFile] = cfg
        self.__interactive = interactive
        self.__simulation_mode = simulation_mode
        self.__base_url = "http://localhost:8000"
        self.__session = requests.Session()

        if self.__simulation_mode:
            warnings.warn("Running in simulation mode", RuntimeWarning)
    
    @property
    def daemon_address(self) -> str:
        return self.__cfg.runner.daemon if self.__cfg.runner is not None else ""
        

    @property
    def requires_serve(self) -> str:
        return not self.__cfg.serve is None

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

    def __run_subprocess(
        self,
        command: List[str],
        cwd: Optional[Path] = None,
        text: bool = False,
        verbose: bool = False,
        assert_returncode: bool = True,
    ) -> str:
        human_readable_command = " ".join(command)
        if verbose:
            log.info(f"Running `{human_readable_command}`...")

        try:
            res = subprocess.run(
                command,
                cwd=str(cwd.absolute()),
                stdin=sys.stdin,
                capture_output=True,
                text=text,
            )
        except KeyboardInterrupt:
            exit(1)

        if assert_returncode and res.returncode != 0:
            raise AICertClientSubProcessException(
                human_readable_command,
                res.returncode,
                res.stdout,
                res.stderr
            )

        return res.stdout

    def __load_config(self, dir: Path):
        with (dir / "aicert.yaml").open("rb") as file:
            try:
                data = yaml.safe_load(file)
            except yaml.YAMLError as e:
                raise AICertClientConfigFileException(e)

        self.__cfg = ConfigFile(**data)

    def __save_config(self, dir: Path):
        with (dir / "aicert.yaml").open("wb") as file:
            yaml.safe_dump(dict(self.__cfg), file)

    @staticmethod
    def from_config_file(
        dir: Path,
        interactive: bool = False,
        simulation_mode=False,
    ) -> "Client":
        client = Client(
            interactive=interactive,
            simulation_mode=simulation_mode,
        )
        client.__load_config(dir)

        return client
    
    def connect(self, runner_cfg: Optional[Runner] = None) -> None:
        if not self.__simulation_mode:
            runner_cfg = runner_cfg if runner_cfg is not None else self.__cfg.runner
            if runner_cfg is None:
                raise AICertClientException("No runner has been configured")
            
            res = requests.post(f"{runner_cfg.daemon}/launch_runner")
            raise_for_status(res, "Cannot create runner")
            res = res.json()

            self.__base_url = "https://aicert_worker"

            self.__session = requests.Session()
            self.__session.mount(
                self.__base_url, ForcedIPHTTPSAdapter(dest_ip=res["runner_ip"])
            )

            client_crt_file = tempfile.NamedTemporaryFile(mode="w+t")
            client_key_file = tempfile.NamedTemporaryFile(mode="w+t")
            server_ca_crt_file = tempfile.NamedTemporaryFile(mode="w+t")

            client_crt_file.write(res["client_cert"])
            client_crt_file.flush()
            client_key_file.write(res["client_private_key"])
            client_key_file.flush()
            server_ca_crt_file.write(res["server_ca_cert"])
            server_ca_crt_file.flush()

            self.__session.verify = server_ca_crt_file.name
            self.__session.cert = (client_crt_file.name, client_key_file.name)
        else:
            self.__base_url = "http://localhost:8000"
            self.__session = requests.Session()
            warnings.warn("Ignoring machine settings in simulation mode")
    
    def disconnect(self):
        if not self.__simulation_mode:
            raise_for_status(requests.post("http://localhost:8082/destroy_runner"), "Cannot destroy runner")
            self.__base_url = "http://localhost:8000"
            self.__session = requests.Session()

    def submit_build(self, build_cfg: Optional[Build] = None) -> None:
        build_cfg = build_cfg if build_cfg is not None else self.__cfg.build
        raise_for_status(
            self.__session.post(
                f"{self.__base_url}/submit_build",
                data=build_cfg.json(),
                headers={"Content-Type": "application/json"},
            ),
            "Cannot submit build to server",
        )
    
    def submit_serve(self, serve_cfg: Optional[Serve] = None) -> None:
        serve_cfg = serve_cfg if serve_cfg is not None else self.__cfg.serve
        if serve_cfg is not None:
            raise_for_status(
                self.__session.post(
                    f"{self.__base_url}/submit_serve",
                    data=serve_cfg.json(),
                    headers={"Content-Type": "application/json"},
                ),
                "Cannot submit serve request to server",
            )
    
    def wait_for_attestation(self) -> bytes:
        while True:
            res = self.__session.get(f"{self.__base_url}/attestation")
            if res.status_code == 204:
                sleep(1)
                continue
            raise_for_status(
                res, "Cannot retrieve attestation, build likely failed"
            )
            return res.content
    
    def download_outputs(self, dir: Path, pattern: Optional[str] = None, verbose: bool = False) -> None:
        pattern = pattern if pattern is not None else self.__cfg.build.outputs
        pattern = urllib.parse.quote(pattern, safe="")
        
        res = self.__session.get(f"{self.__base_url}/outputs?pattern={pattern}")
        raise_for_status(res, "Cannot download outputs list")
        file_list = FileList.parse_raw(res.text)

        for filename in file_list.file_list:
            if verbose:
                log.info(f"Downloading output: {filename}")
            res = self.__session.get(f"{self.__base_url}/outputs/{filename}")
            raise_for_status(res, f"Cannot download output file {filename}")
            with (dir / filename).open("wb") as f:
                f.write(res.content)

    def new_config(self, dir: Path) -> None:
        """Set up the workspace by copying template files"""
        dir.mkdir(exist_ok=True)
        self.__copy_template(
            "templates/aicert.yaml", dir / "aicert.yaml", confirm_replace=True
        )

    def verify_build_response(self, build_response: bytes, verbose: bool = False):
        try:
            build_response = json.loads(build_response)
        except Exception as e:
            AICertClientInvalidAttestationFormatException(e)
        
        if "simulation_mode" in build_response["remote_attestation"]:
            if self.__simulation_mode:
                warnings.warn(f"👀 Attestation generated in simulation mode", RuntimeWarning)
                return
            else:
                raise AICertClientInvalidAttestationException(f"❌ Attestation generated in simulation mode")

        build_response["remote_attestation"]["cert_chain"] = [
            decode_b64_encoding(cert_b64_encoded)
            for cert_b64_encoded in build_response["remote_attestation"]["cert_chain"]
        ]

        ak_cert = verify_ak_cert(
            cert_chain=build_response["remote_attestation"]["cert_chain"]
        )
        warnings.warn(f"⚠️ Bypassing certificate chain verification", RuntimeWarning)

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

        if verbose:
            typer.secho(f"✅ Valid quote", fg=typer.colors.GREEN)

            log.info(
                f"Attestation Document > PCRs :  \n{yaml.safe_dump(att_document['pcrs']['sha256'])}"
            )

        # We should check the PCR to make sure the system has booted properly
        # This is an example ... the real thing will depend on the system.
        # assert (
        #     att_document["pcrs"]["sha256"][0]
        #     == "d0d725f21ba5d701952888bcbc598e6dcef9aff4d1e03bb3606eb75368bab351"
        # )
        # assert (
        #     att_document["pcrs"]["sha256"][1]
        #     == "fe72566c7f411900f7fa1b512dac0627a4cac8c0cb702f38919ad8c415ca47fc"
        # )
        # assert (
        #     att_document["pcrs"]["sha256"][2]
        #     == "3d458cfe55cc03ea1f443f1562beec8df51c75e14a9fcf9a7234a13f198e7969"
        # )
        # assert (
        #     att_document["pcrs"]["sha256"][3]
        #     == "3d458cfe55cc03ea1f443f1562beec8df51c75e14a9fcf9a7234a13f198e7969"
        # )
        # assert (
        #     att_document["pcrs"]["sha256"][4]
        #     == "1f0105624ab37b9af59da6618a406860e33ef6f42a38ddaf6abfab8f23802755"
        # )
        # assert (
        #     att_document["pcrs"]["sha256"][5]
        #     == "d36183a4ce9f539d686160695040237da50e4ad80600607f84eff41cf394dcd8"
        # )

        # if verbose:
        #     typer.secho(f"✅ Checking reported PCRs are as expected", fg=typer.colors.GREEN)

        # To make test easier we use the PCR 16 since it is resettable `tpm2_pcrreset 16`
        # But because it is resettable it MUST NOT be used in practice.
        # An unused PCR that cannot be reset (SRTM) MUST be used instead
        # PCR 14 or 15 should do it
        event_log = check_event_log(
            build_response["event_log"],
            att_document["pcrs"]["sha256"][PCR_FOR_MEASUREMENT],
        )

        if verbose:
            typer.secho(f"✅ Valid event log", fg=typer.colors.GREEN)
            print(yaml.safe_dump(event_log))
            typer.secho(f"✨✨✨ ALL CHECKS PASSED", fg=typer.colors.GREEN)

def raise_for_status(res: requests.Response, message: str) -> None:
    if not res.ok:
        raise AICertClientHTTPException(message=message, response=res)
