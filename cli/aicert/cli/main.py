import json
import os
import shutil
import subprocess
import requests
import typer
from typing import Annotated, Optional

import yaml

from aicert.cli.verify import PCR_FOR_MEASUREMENT, check_event_log, check_quote, decode_b64_encoding, verify_ak_cert

from .client import Client
from .requests_adapter import ForcedIPHTTPSAdapter
from .logging import log
import importlib
import importlib.resources
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.x509 import load_der_x509_certificate

app = typer.Typer(rich_markup_mode="rich")

@app.command()
def new():
    """Create a new aicert.yaml file in the current directory"""
    init_yaml = importlib.resources.read_text(  # type: ignore
        __package__, "aicert_new.yaml"
    )
    try:
        with open("aicert.yaml", "x") as f:
            f.write(init_yaml)
    except FileExistsError:
        typer.secho(f"ERROR: aicert.yaml already exists", fg=typer.colors.RED)


@app.command()
def build():
    """Launch build process"""

    # Read aicert.yaml
    try:
        f = Path("aicert.yaml").read_text()
    except FileNotFoundError:
        typer.secho(f"ERROR: No aicert.yaml file found in current directory", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    # Parse aicert.yaml
    try:
        conf = yaml.safe_load(f)
    except yaml.YAMLError as e:
        e.context_mark.name = "aicert.yaml"
        e.problem_mark.name = "aicert.yaml"
        typer.secho(f"ERROR: Failed to parse aicert.yaml file", fg=typer.colors.RED)
        typer.secho(f"ERROR: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    client = Client()

    # Check if terraform is installed
    client._assert_tf_available()

    # Make ~/.aicert folder (if not exists)
    aicert_home = Path.home() / ".aicert"
    os.makedirs(aicert_home, exist_ok = True)
    
    deploy_folder = (importlib.resources.files(__package__) / "deploy")
    shutil.copytree(deploy_folder, aicert_home, dirs_exist_ok=True)

    # Terrible : We create symlinks to the server source code
    # to be deployed this assumes that the client was installed
    # via git clone + poetry install 
    try:
        os.symlink(Path(__file__).parent / ".." /".."/".." /"server", aicert_home / "server")
    except FileExistsError:
        pass
    try:
        os.symlink(Path(__file__).parent / ".." /".."/".." /"common", aicert_home / "common")
    except FileExistsError:
        pass

    client._tf_init(aicert_home)
    client._tf_apply(aicert_home)

    # run bash script to provision the VM
    subprocess.run(["bash", "provision.sh"], cwd=aicert_home)

    # Issue request to build to the server

    tf_output_vm_ip = subprocess.run(['terraform', 'output', '-raw', 'public_ip_address'], cwd=aicert_home, text=True, capture_output=True, check=True)
    vm_ip = tf_output_vm_ip.stdout
    session = requests.Session()
    session.mount("https://aicert_worker", ForcedIPHTTPSAdapter(dest_ip=vm_ip))

    client_cert = (aicert_home / 'client.crt', aicert_home / 'client.key')
    server_ca_cert =  aicert_home/'tls_ca.crt'
    session.verify = server_ca_cert
    session.cert = client_cert

    # TODO: replace with a real request (with a BuildRequest object matching the aicert.yaml)
    print(session.post("https://aicert_worker/build").content)

    # TODO : Write the output "proof file" somewhere
    # TODO : Download the output artifacts also

    # Clean up
    client._tf_destroy(aicert_home)


@app.command()
def verify(path: str):
    """Launch verification process
    
    Example:
    aicert verify "/workspaces/aicert_dev/server/aicert_server/sample_build_response.json"
    """
    # path is the path to the proof file
    # Path(path).read_text()
    with open(path, "r") as f:
        build_response = json.load(f)

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


    log.info(f"Attestation Document > PCRs :  \n{yaml.safe_dump(att_document['pcrs']['sha256'])}")

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

    # print(build_response)
    # raise NotImplementedError

# @app.command()
# def certify(
#     input_container: Annotated[Optional[str], typer.Option()] = None,
#     dataset_source: Annotated[Optional[str], typer.Option()] = None,
#     output_model: Annotated[Optional[str], typer.Option()] = None,
#     output_bom: Annotated[Optional[str], typer.Option()] = None,
# ):
#     log.debug(input_container)
#     log.debug(dataset_source)
#     log.debug(output_model)
#     log.debug(output_bom)
