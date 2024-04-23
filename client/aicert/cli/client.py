from cryptography.hazmat.primitives import serialization
from cryptography.x509 import load_der_x509_certificate
from pathlib import Path
import pkgutil
import requests
import tempfile
from time import sleep
import typer
from rich import print
from typing import Optional
import urllib.parse
import yaml
import warnings
import json

from aicert_common.protocol import ConfigFile, FileList, AxolotlConfigString
from aicert_common.logging import log
from aicert_common.errors import AICertException
from .deployment.deployer import Deployer
from .requests_adapter import ForcedIPHTTPSAdapter
from .verify import (
    PCR_FOR_MEASUREMENT,
    PCR_FOR_CERTIFICATE,
    check_event_log,
    check_quote,
    decode_b64_encoding,
    verify_ak_cert,
    check_server_cert,
    check_os_pcrs
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
        self.__base_url = "http://localhost:80"
        self.__session = requests.Session()
        self.__tf_home = Path.home() / ".aicert"

        if self.__simulation_mode:
            warnings.warn("Running in simulation mode", RuntimeWarning)
    
    @property
    def is_simulation(self) -> bool:
        """Returns mode of operation (simulation or not)"""
        return self.__simulation_mode


    @staticmethod
    def from_config_file(
        interactive: bool = False,
        simulation_mode=False,
    ) -> "Client":
        """Load configuration from config file and returned a preconfigured client
    
        Args:
            interactive (bool, default = False): When set to True, enables the
                client to ask question such as file replacement approbation.
            simulation_mode (bool, default = False): When set to True, the client
                connects to a local server on port 80 (currently this simulation
                server must be launched separately using the aicert-server package)
                that does not use the TPM. Useful for testing purposes only.
        
        Returns:
            Client
        """
        client = Client(
            interactive=interactive,
            simulation_mode=simulation_mode,
        )

        return client
    
    def connect(self) -> None:
        """Establish a TLS connection with the runner.

        1. The client contacts the configured Deployer to ask for a runner.
        2. The Deployer returns an ip address and an SSL client certificate for the runner.
        3. The client connects to the runner using the ip and certificate.

        Args:
            runner_cfg (Runner, optional): Runner configuration object. If not provided,
                the client defaults to using the runner section of the config file.
        """

        if not self.__simulation_mode:           
            Deployer.init(self.__tf_home)
            res = Deployer.launch_runner(self.__tf_home)

            self.__base_url = "https://aicert_worker"

            self.__session = requests.Session()
            self.__session.mount(
                self.__base_url, ForcedIPHTTPSAdapter(dest_ip=res["runner_ip"])
            )

            ca_cert = self.verify_server_certificate(res["runner_ip"])

            server_ca_crt_file = tempfile.NamedTemporaryFile(mode="w+t", delete=False)

            server_ca_crt_file.write(ca_cert)
            server_ca_crt_file.flush()

            self.__session.verify = server_ca_crt_file.name

        else:
            self.__base_url = "http://localhost:80"
            self.__session = requests.Session()
            warnings.warn("Ignoring machine settings in simulation mode")
        
    
    def disconnect(self):
        """Close connection with the runner.

        The client asks the Deployer to destroy the runner.
        """
        import os

        if not self.__simulation_mode:
            #Delete server cert
            for file in [self.__session.verify]:
                if os.path.isfile(file):
                    os.remove(file)

            Deployer.destroy_runner()
        
        self.__base_url = "http://localhost:80"
        self.__session.close()

    
    def verify_server_certificate(self, server_ip):
        """Retrieve server CA certificate and validate it with 
        the attestation report.
        """
        from requests.packages.urllib3.util.retry import Retry

        session = requests.Session()
        retries = Retry(total=15, backoff_factor=0.2, status_forcelist=[429, 500, 502, 503, 504])
        session.mount(
                self.__base_url, ForcedIPHTTPSAdapter(dest_ip=server_ip, max_retries=retries)
            )
        attestation = session.get(f"{self.__base_url}/aTLS",verify=False)
        raise_for_status(
                attestation, "Cannot retrieve server certificate for aTLS"
            )

        attestation_json = json.loads(attestation.content)

        ca_cert = attestation_json["ca_cert"]

        # Verify quote and CA TLS certificate
        self.verify_attestation(attestation.content, PCR_FOR_CERTIFICATE, True, ca_cert)
        return ca_cert


    def submit_axolotl_config(self, dir: Path, config_file = "aicert.yaml"):
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

        res = self.__session.post(
                 f"{self.__base_url}/axolotl/configuration",
                data=axolotl_conf_string.json(),
                headers={"Content-Type": "application/json"},
             )
        raise_for_status(
             res,
             "Failed sending axolotl configuration to server",
         )
        return res    

    def submit_finetune(self) -> None:
        """Send a request to begin finetuning a model
        """
        raise_for_status(
             self.__session.post(
                 f"{self.__base_url}/finetune",
             ),
             "Failed sending finetune request to server",
         )    
        sleep(2)
    
        with self.__session.get(f"{self.__base_url}/build/status", stream=True) as stream_resp:
            event_data = ""
            for line in stream_resp.iter_lines():
                if line != b'':
                    event_data = line.decode("utf-8")
                    if "EOF" in event_data:
                        break
                    event_data = event_data[92:]
                    if len(event_data) >= 10:
                        event_data = event_data[:-10]
                    print(event_data.replace("\\", ""))


    
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


    def verify_attestation(self, build_response: bytes, pcr_index = PCR_FOR_MEASUREMENT, verbose: bool = False, server_certs = ""):
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
            
        check_os_pcrs(att_document, self.__simulation_mode)

        if verbose:
            typer.secho(f"✅ Checking reported PCRs are as expected", fg=typer.colors.GREEN)

        if pcr_index == PCR_FOR_MEASUREMENT:
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
