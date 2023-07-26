import os
import shutil
import subprocess
import requests
import typer
from typing import Annotated, Optional

import yaml

from .client import Client
from .requests_adapter import ForcedIPHTTPSAdapter
from .logging import log
import importlib
import importlib.resources
from pathlib import Path

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
def verify():
    """Launch verification process"""
    raise NotImplementedError

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
