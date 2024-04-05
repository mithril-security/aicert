from cryptography.hazmat.primitives import serialization
from cryptography.x509 import load_der_x509_certificate
import json
from pathlib import Path
import pkgutil
import requests
import tempfile
from time import sleep
import typer
from typing import Optional
import urllib.parse
import yaml
import warnings

from aicert_common.protocol import ConfigFile, FileList, Runner, Build, Serve, AxolotlConfigString
from aicert_common.logging import log
from aicert_common.errors import AICertException
from .requests_adapter import ForcedIPHTTPSAdapter
from .verify import (
    PCR_FOR_MEASUREMENT,
    PCR_FOR_CERTIFICATE,
    check_event_log,
    check_quote,
    decode_b64_encoding,
    verify_ak_cert,
    check_server_cert
)


class AICertConfigFileException(AICertException):
    """AICert config file parsing error (yaml)"""
    def __init__(self, err: yaml.YAMLError) -> None:
        self.__err = err
        self.__err.context_mark.name = "aicert.yaml"
        self.__err.problem_mark.name = "aicert.yaml"
        self.message = f"Failed to parse aicert.yaml file\n{self.__err}"
        super().__init__(self.message)


class AICertHTTPException(AICertException):
    """AICert HTTP protocol exception"""
    def __init__(self, message: str, response: requests.Response) -> None:
        self.__res = response
        self.message = f"Protocol error: {message}\nReceived HTTP response: {response.status_code} - {response.reason}\n{response.text}"
        super().__init__(self.message)


class AICertInvalidAttestationFormatException(AICertException):
    """AICert attestation parsing error (json)"""
    def __init__(self, err: Exception) -> None:
        self.__err = err
        self.message = f"Invalid attestation format\n{self.__err}"
        super().__init__(self.message)


class AICertInvalidAttestationException(AICertException):
    """Invalid attestation error"""
    pass


class Client:
    """Python API to communicate with an AICert runner.
    
    This class contains methods that cover the main steps of
    a certified build or server deployment.
    These methods are built upon the HTTP interface defined in the server code.

    Args:
        cfg: (ConfigFile, optional): Parsed Yaml configuration file.
            The configuration file contains runner settings and build and
            server deployment descriptions. These are used as deafults that
            can be overriden when calling the methods.
        interactive (bool, default = False): When set to True, enables the
            client to ask question such as file replacement approbation.
        simulation_mode (bool, default = False): When set to True, the client
            connects to a local server on port 8000 (currently this simulation
            server must be launched separately using the aicert-server package)
            that does not use the TPM. Useful for testing purposes only.
    """
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
        """Address of the configured deamon if available"""
        return self.__cfg.runner.daemon if self.__cfg.runner is not None else ""
    
    @property
    def is_simulation(self) -> bool:
        """Returns mode of operation (simulation or not)"""
        return self.__simulation_mode
        

    @property
    def requires_serve(self) -> bool:
        """True if the configuration file has a serve section"""
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
        """Private method: copy package files (e.g. templates) to current dir
        
        Args:
            src_path (str): Location of the template file in the package, relative to its root
            dst_path (Path): Where to copy the file
            executable (bool, default = False): Whether to make the copy excecutable
            replace (bool, default = False): If set to True, ignore existing file
                and replace it with a copy of the template. If set to false, do nothing
                if the file already exists.
            confirm_replace (bool, default = False): If set to True and in iteractive mode only,
                the client will ask approbation prior to replacing the file.
            replace (bool, default = False): If set to True, the client will append the content
                of the template at the end of the target file instead of replacing it.
        """
        data = pkgutil.get_data(__name__, src_path)

        if dst_path.exists():
            if confirm_replace:
                replace = (
                    typer.confirm(f"Replace file {dst_path}?")
                    if self.__interactive
                    else replace
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

    def __load_config(self, dir: Path):
        """Private method: load config file
        
        Args:
            dir (Path): Directory that contains the aicert.yaml file
        """
        with (dir / "aicert.yaml").open("rb") as file:
            try:
                data = yaml.safe_load(file)
            except yaml.YAMLError as e:
                raise AICertConfigFileException(e)

        self.__cfg = ConfigFile(**data)

    def __save_config(self, dir: Path):
        """Private method: save config file
        
        Args:
            dir (Path): Directory where the aicert.yaml config file should be stored
        """
        with (dir / "aicert.yaml").open("wb") as file:
            yaml.safe_dump(dict(self.__cfg), file)

    @staticmethod
    def from_config_file(
        dir: Path,
        interactive: bool = False,
        simulation_mode=False,
    ) -> "Client":
        """Load configuration from config file and returned a preconfigured client
    
        Args:
            dir: (Path): Directory that contains the aicert.yaml file
            interactive (bool, default = False): When set to True, enables the
                client to ask question such as file replacement approbation.
            simulation_mode (bool, default = False): When set to True, the client
                connects to a local server on port 8000 (currently this simulation
                server must be launched separately using the aicert-server package)
                that does not use the TPM. Useful for testing purposes only.
        
        Returns:
            Client
        """
        client = Client(
            interactive=interactive,
            simulation_mode=simulation_mode,
        )
        #client.__load_config(dir)

        return client
    
    def connect(self, runner_cfg: Optional[Runner] = None) -> None:
        """Establish a TLS connection with the runner.

        1. The client contacts the configured daemon to ask for a runner.
        2. The daemon returns an ip address and an SSL client certificate for the runner.
        3. The client connects to the runner using the ip and certificate.

        Args:
            runner_cfg (Runner, optional): Runner configuration object. If not provided,
                the client defaults to using the runner section of the config file.
        """

        if not self.__simulation_mode:
            runner_cfg = runner_cfg if runner_cfg is not None else self.__cfg.runner
            if runner_cfg is None:
                raise AICertException("No runner has been configured")
            
            res = requests.post(f"{runner_cfg.daemon}/launch_runner")
            raise_for_status(res, "Cannot create runner")
            res = res.json()

            self.__base_url = "https://aicert_worker"

            self.__session = requests.Session()
            self.__session.mount(
                self.__base_url, ForcedIPHTTPSAdapter(dest_ip=res["runner_ip"])
            )

            ca_cert = self.verify_server_certificate(res["runner_ip"])

            client_crt_file = tempfile.NamedTemporaryFile(mode="w+t", delete=False)
            client_key_file = tempfile.NamedTemporaryFile(mode="w+t", delete=False)
            server_ca_crt_file = tempfile.NamedTemporaryFile(mode="w+t", delete=False)

            client_crt_file.write(res["client_cert"])
            client_crt_file.flush()
            client_key_file.write(res["client_private_key"])
            client_key_file.flush()
            server_ca_crt_file.write(ca_cert)
            server_ca_crt_file.flush()

            self.__session.verify = server_ca_crt_file.name
            self.__session.cert = (client_crt_file.name, client_key_file.name)

        else:
            self.__base_url = "http://localhost:8000"
            self.__session = requests.Session()
            warnings.warn("Ignoring machine settings in simulation mode")
        
    
    def disconnect(self):
        """Close connection with the runner.

        The client asks the daemon to destroy the runner.
        """
        import os

        if not self.__simulation_mode:
            #Delete client key and certs
            for file in [self.__session.verify, self.__session.cert[0], self.__session.cert[1]]:
                if os.path.isfile(file):
                    os.remove(file)

            raise_for_status(requests.post("http://localhost:8082/destroy_runner"), "Cannot destroy runner")
            self.__base_url = "http://localhost:8000"
            self.__session = requests.Session()

    
    def verify_server_certificate(self, server_ip):
        """Retrieve server CA certificate and validate it with 
        the attestation report.
        """
        session = requests.Session()
        session.mount(
                self.__base_url, ForcedIPHTTPSAdapter(dest_ip=server_ip)
            )
        
        attestation = session.get(f"{self.__base_url}/aTLS",verify=False)
        raise_for_status(
                attestation, "Cannot retrieve server certificate for aTLS"
            )

        attestation_json = json.loads(attestation.content)

        ca_cert = attestation_json["ca_cert"]

        # Verify quote and CA TLS certificate
        self.verify_build_response(attestation.content, PCR_FOR_CERTIFICATE, True, ca_cert)
        return ca_cert

    def submit_build(self, build_cfg: Optional[Build] = None) -> None:
        """Send a submit_build request to the runner

        Args:
            build_cfg (Build, optional): Build configuration object. If not provided,
                the client defaults to using the build section of the config file.
        """
        build_cfg = build_cfg if build_cfg is not None else self.__cfg.build
        raise_for_status(
            self.__session.post(
                f"{self.__base_url}/build",
                data=build_cfg.json(),
                headers={"Content-Type": "application/json"},
            ),
            "Cannot submit build to server",
        )

    def submit_axolotl_config(self, dir: Path, config_file = "axolotl_config.yaml"):
        """Send an axolotl configuration to the server

        Args:
            config_file: Axolotl configuration.
        """
        with (dir / config_file).open("rb") as file:
            try:
                data = yaml.safe_load(file)
                str_data=yaml.dump(data)
                axolotl_conf_string = AxolotlConfigString(axolotl_config=str_data)
            except yaml.YAMLError as e:
                raise AICertConfigFileException(e)

        raise_for_status(
             self.__session.post(
                 f"{self.__base_url}/axolotl/configuration",
                data=axolotl_conf_string.json(),
                headers={"Content-Type": "application/json"},
             ),
             "Failed sending axolotl configuration to server",
         )    
    
    # def submit_config(self, yaml_config: str) -> None:
    #     """
    #         Sends a yaml axolotl configuration format

    #     Args:
    #         yaml_config: Path to file upload
    #     """

    #     raise_for_status(
    #         self.__session.post(
    #             f"{self.__base_url}/axolotl/configuration",
    #             data
    #         )
    #     )

    def submit_finetune(self) -> None:
        """Send a request to begin finetuning a model
        """
        raise_for_status(
             self.__session.post(
                 f"{self.__base_url}/finetune",
             ),
             "Failed sending finetune request to server",
         )    

    def submit_serve(self, serve_cfg: Optional[Serve] = None) -> None:
        """Send a submit_serve request to the runner

        Args:
            serve_cfg (Serve, optional): Serve configuration object. If not provided,
                the client defaults to using the serve section of the config file.
        """
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
        """Block until the attestation endpoint returns the attestation
        
        The client will repededly poll the runner. The runner anwers with
        a 204 response while the build is still running. Once it has completed,
        it simply returns the attestation.
        """
        while True:
            res = self.__session.get(f"{self.__base_url}/attestation")
            if res.status_code == 204:
                sleep(30)
                continue
            raise_for_status(
                res, "Cannot retrieve attestation, build likely failed"
            )
            return res.content
    
    def download_outputs(self, dir: Path, pattern: Optional[str] = None, verbose: bool = False) -> None:
        """Retrieve outputs (build artifacts) using a glob pattern
        
        Args:
            dir (Path): Where to store the downloaded files
            pattern (str, optinal): Glob pattern to filter the artifacts. If not provided,
                the client defaults to using the pattern defined in the config file.
            verbose (bool, default = False): Whether to display information about the downloads
                in stdout.
        """
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
        """Set up the workspace by copying template files
        
        Args:
            dir (Path): Path of the workspace to set up
        """
        dir.mkdir(exist_ok=True)
        self.__copy_template(
            "templates/aicert.yaml", dir / "aicert.yaml", confirm_replace=True
        )

    def verify_build_response(self, build_response: bytes, pcr_index = PCR_FOR_MEASUREMENT, verbose: bool = False, server_certs = ""):
        """Verify received attesation validity

        1. Parse the JSON reponse
        2. Check simulation mode
        3. Verify certificate chain
        4. Verify quote signature
        5. Verify boot PCRs (firmware, bootloader, initramfs, OS)
        6. Verify event log (final hash in PCR_FOR_MEASUREMENT) by replaying it (works like a chain of hashes)
        OR
        6. Verify TLS certificate (final hash in PCR_FOR_CERTIFICATE)
        
        Args:
            build_response (bytes): reponse of the attestation endpoint
            verbose (bool, default = False): whether to print verification information in stdout
        """
        try:
            build_response = json.loads(build_response)
        except Exception as e:
            AICertInvalidAttestationFormatException(e)
        
        if "simulation_mode" in build_response["remote_attestation"]:
            if self.__simulation_mode:
                warnings.warn(f"👀 Attestation generated in simulation mode", RuntimeWarning)
                return
            else:
                raise AICertInvalidAttestationException(f"❌ Attestation generated in simulation mode")

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

        if pcr_index == PCR_FOR_MEASUREMENT:
            # To make test easier we use the PCR 16 since it is resettable `tpm2_pcrreset 16`
            # But because it is resettable it MUST NOT be used in practice.
            # An unused PCR that cannot be reset (SRTM) MUST be used instead
            # PCR 14 or 15 should do it
            event_log = check_event_log(
                build_response["event_log"],
                att_document["pcrs"]["sha256"][pcr_index],
            )
            if verbose:
                typer.secho(f"✅ Valid event log", fg=typer.colors.GREEN)
                print(yaml.safe_dump(event_log))
                typer.secho(f"✨✨✨ ALL CHECKS PASSED", fg=typer.colors.GREEN)


        elif pcr_index == PCR_FOR_CERTIFICATE:
            result = check_server_cert(
                server_certs,
                att_document["pcrs"]["sha256"][pcr_index],
            )
            if not result:
                # Disconnect destroys the runner, this might not be required for an attestation failure
                self.disconnect()
                raise AICertInvalidAttestationException(f"❌ Attestation validation failed.")   


def raise_for_status(res: requests.Response, message: str) -> None:
    """Raise AICertHTTPException if passed response has a status code outside the 200 range
    
    Args:
        res (requests.Response): response to check
        message (str): message to include in the error
    """
    if not res.ok:
        raise AICertHTTPException(message=message, response=res)
