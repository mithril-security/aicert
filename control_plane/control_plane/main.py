import os
from pathlib import Path
import shutil
import subprocess
from fastapi import FastAPI

from control_plane.requests_adapter import ForcedIPHTTPSAdapter
from .utils import Client
from .logging import log
import requests

app = FastAPI()
client = Client()
aicert_home = Path.home() / ".aicert"

@app.post("/launch_runner")
async def launch_runner():
    # Check if terraform is installed
    client._assert_tf_available()

    # Make ~/.aicert folder (if not exists)
    os.makedirs(aicert_home, exist_ok=True)

    deploy_folder = Path(__file__).parent  / ".." / ".." / "deploy"
    shutil.copytree(deploy_folder, aicert_home, dirs_exist_ok=True)

    # Terrible : We create symlinks to the server source code
    # to be deployed this assumes that the client was installed
    # via git clone + poetry install
    try:
        os.symlink(
            Path(__file__).parent  / ".." / ".." / "server",
            aicert_home / "server",
        )
    except FileExistsError:
        pass
    try:
        os.symlink(
            Path(__file__).parent / ".." / ".." / "common",
            aicert_home / "common",
        )
    except FileExistsError:
        pass

    client._tf_init(aicert_home)
    client._tf_apply(aicert_home)

    # run bash script to provision the VM
    subprocess.run(["bash", "provision.sh"], cwd=aicert_home)
    tf_output_vm_ip = subprocess.run(
        ["terraform", "output", "-raw", "public_ip_address"],
        cwd=aicert_home,
        text=True,
        capture_output=True,
        check=True,
    )

    vm_ip = tf_output_vm_ip.stdout

    session = requests.Session()
    session.mount("https://aicert_worker", ForcedIPHTTPSAdapter(dest_ip=vm_ip))

    client_cert = aicert_home / "client.crt"
    client_private_key = aicert_home / "client.key"
    server_ca_cert = aicert_home / "tls_ca.crt"
    session.verify = server_ca_cert
    session.cert = (client_cert, client_private_key)

    # Check if the server is up
    print(session.post("https://aicert_worker/build").content)

    return {
        "runner_ip": vm_ip,
        "client_cert": client_cert.read_text(),
        "client_private_key": client_private_key.read_text(),
        "server_ca_cert": server_ca_cert.read_text()
    }


@app.post("/destroy_runner")
def destroy_runner():
    client._tf_destroy(aicert_home)