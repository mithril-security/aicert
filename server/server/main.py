#!/usr/bin/python3

import base64
import json
import tempfile

import subprocess
import requests
import uvicorn
from fastapi import FastAPI
from fastapi.responses import Response
import hashlib
import docker
from pathlib import Path
from fastapi.encoders import jsonable_encoder
import yaml

from pydantic import BaseModel


app = FastAPI()

docker_client = docker.from_env()

PCR_FOR_MEASUREMENT = 16


def sha256_file(file_path) -> str:
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as file:
        for chunk in iter(lambda: file.read(4096), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


def tpm_nvread(offset: str) -> bytes:
    return subprocess.run(
        ["tpm2_nvread", "-Co", offset], capture_output=True, check=True
    ).stdout


def tpm_extend_pcr(pcr_index: int, hex_hash_value: str) -> None:
    """
    Extend PCR pcr_index from SHA256 bank with a hash

    >>> hex_hash_value = (
    ...     "0x0000000000000000000000000000000000000000000000000000000000000000"
    ... )
    >>> pcr_index = 15
    >>> tpm_extend_pcr(pcr_index, hex_hash_value)
    """

    subprocess.run(
        ["tpm2_pcrextend", f"{pcr_index}:sha256={hex_hash_value}"], check=True
    )


def tpm_read_pcr(pcr_index):
    """
    Read the value of a PCR at index pcr_index from bank sha256
    returns the hash value of the PCR

    >>> _ = tpm_read_pcr(15)
    """
    tpm2_pcrread = subprocess.run(
        ["tpm2_pcrread", f"sha256:{pcr_index}"],
        capture_output=True,
        check=True,
        text=True,
    )
    pcrread_output = yaml.load(tpm2_pcrread.stdout, Loader=yaml.BaseLoader)
    # The result we get from tpm2_pcrread is something in this format '0x31A6F553CC0F9FC156877E35D35CA63AD9514A67C1B231B73665127CD6867631'
    # This format is not the same as the one output by python hashlib .hexdigest() function
    # so we transform it so that it is in this format '31a6f553cc0f9fc156877e35d35ca63ad9514a67c1b231b73665127cd6867631'
    return pcrread_output["sha256"][str(pcr_index)].lower().removeprefix("0x")


def get_azure_cert_chain():
    def get_certificate_from_url(url: str):
        req = requests.get(url)
        req.raise_for_status()
        return req.content

    intermediate_cert = get_certificate_from_url(
        "http://crl.microsoft.com/pkiinfra/Certs/BL2PKIINTCA01.AME.GBL_AME%20Infra%20CA%2002(4).crt"
    )
    root_cert = get_certificate_from_url(
        "http://crl.microsoft.com/pkiinfra/certs/AMERoot_ameroot.crt"
    )
    AIK_CERT_INDEX = "0x01C101D0"
    cert = tpm_nvread(AIK_CERT_INDEX)
    cert_chain = [cert, intermediate_cert, root_cert]
    return cert_chain


def test_get_azure_cert_chain():
    get_azure_cert_chain()


def quote():
    """
    Produce a quote attesting the all PCR from the SHA256 PCR bank

    Quote is signed using the key AIK_PUB_INDEX

    """
    AIK_PUB_INDEX = "0x81000003"
    with (
        tempfile.NamedTemporaryFile() as quote_msg_file,
        tempfile.NamedTemporaryFile() as quote_sig_file,
        tempfile.NamedTemporaryFile() as quote_pcr_file,
    ):
        # fmt:off
        subprocess.run(["tpm2_quote", "--quiet",
                        "--key-context", AIK_PUB_INDEX, 
                        "--pcr-list", "sha256:0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23", 
                        "--message" , quote_msg_file.name, 
                        "--signature", quote_sig_file.name, 
                        "--pcr", quote_pcr_file.name, 
                        "--hash-algorithm", "sha256"], check=True)
        # fmt:on

        quote_msg = quote_msg_file.read()
        quote_sig = quote_sig_file.read()
        quote_pcr = quote_pcr_file.read()

    return {"message": quote_msg, "signature": quote_sig, "pcr": quote_pcr}


class EventLog:
    """
    >>> event_log = EventLog()
    >>> image = "python"
    >>> command = ("python3 main.py",)
    >>> artifact_pattern = "output.txt"
    >>> git_repo_url = "https://github.com/mithril-security/sample-test-repo.git"
    >>> event_start_build = {
    ...     "event_type": "start_build",
    ...     "image": image,
    ...     "command": command,
    ...     "artifact_pattern": artifact_pattern,
    ...     "git_repo_url": git_repo_url,
    ... }
    >>> event_log.append(event_start_build)
    """

    def __init__(self):
        self.event_log = []

    def append(self, event):
        event_json = json.dumps(event)
        hash_event = hashlib.sha256(event_json.encode()).hexdigest()
        tpm_extend_pcr(PCR_FOR_MEASUREMENT, hash_event)
        self.event_log.append(event_json)

    def get(self):
        return self.event_log




class BuildRequest(BaseModel):
    image: str
    command: str
    artifact_pattern: str
    git_repo_url: str


@app.post("/build", status_code=200)
def build(
    build_request: BuildRequest,
) -> Response:
    """
    >>> res = build(
    ...     BuildRequest(
    ...         image="python",
    ...         git_repo_url="https://github.com/mithril-security/sample-test-repo.git",
    ...         command="python3 main.py",
    ...         artifact_pattern="output.txt",
    ...     )
    ... )
    >>> res['event_log'] ==  [
    ...         '{"event_type": "start_build", "image": "python", "command": "python3 main.py", "artifact_pattern": "output.txt", "git_repo_url": "https://github.com/mithril-security/sample-test-repo.git"}',
    ...         '{"event_type": "pull_image", "image": "python", "resolved": {"id": "sha256:c0e63845ae986c52da5cd6ac4d56eebf293439bb22a3cee198dd818fd12ba555"}}',
    ...         '{"event_type": "git_clone", "url": "https://github.com/mithril-security/sample-test-repo.git", "resolved": {"git_hash": "af9321dfcaf355e87f85c33305c746f3ca9880c7"}}',
    ...         '{"event_type": "build_artifacts", "artifacts": [{"path": "output.txt", "digest": {"sha256": "0a54f42edd65c2537ae69c6afcc207f93c24c7f887c054d15598a6ae7398aa5f"}}]}',
    ...     ]
    True
    """
    event_log = EventLog()
    event_start_build = {
        "event_type": "start_build",
        "image": build_request.image,
        "command": build_request.command,
        "artifact_pattern": build_request.artifact_pattern,
        "git_repo_url": build_request.git_repo_url,
    }
    event_log.append(event_start_build)

    # pull image (the image is the build environment)
    image = docker_client.images.pull(build_request.image)
    event_log.append(
        {
            "event_type": "pull_image",
            "image": build_request.image,
            "resolved": {"id": image.id},
        }
    )

    # create a workspace folder with the user code
    path = Path.cwd() / "workspace"

    # git clone
    subprocess.run(["rm", "-rf", "workspace"])
    subprocess.run(
        ["git", "clone", build_request.git_repo_url, "workspace"],
        check=True,
        capture_output=True,
    )

    git_hash = (
        subprocess.run(
            ["git", "rev-parse", "--verify", "HEAD"],
            cwd="workspace",
            capture_output=True,
            check=True,
        )
        .stdout.decode("utf-8")
        .strip()
    )

    event_log.append(
        {
            "event_type": "git_clone",
            "url": build_request.git_repo_url,
            "resolved": {"git_hash": git_hash},
        }
    )

    container = docker_client.containers.run(
        image,
        build_request.command,
        volumes={str(path): {"bind": "/workspace", "mode": "rw"}},
        working_dir="/workspace",
    )

    matches = list(Path("workspace").glob(build_request.artifact_pattern))

    if not matches:
        raise ValueError(
            f"No files matching the pattern '{build_request.artifact_pattern}'"
        )

    artifacts = []
    for path in matches:
        if path.is_file():
            artifact = {
                "path": str(path.relative_to(Path("workspace"))),
                "digest": {"sha256": sha256_file(path)},
            }
            artifacts.append(artifact)

    if not artifacts:
        raise ValueError(
            f"No files matching the pattern '{build_request.artifact_pattern}'"
        )

    event_log.append({"event_type": "build_artifacts", "artifacts": artifacts})

    res = {
        "event_log": event_log.get(),
        "remote_attestation": {"quote": quote(), "cert_chain": get_azure_cert_chain()},
    }

    # FastAPI encodes the response as json, but the quote contains raw bytes...
    # so we have to base64 encode them, this is ugly.
    # Ideally we'd like another serialization format like CBOR or messagepack
    # but FastAPI does not support those :(
    json_res = jsonable_encoder(
        res,
        custom_encoder={
            bytes: lambda v: {"base64": base64.b64encode(v).decode("utf-8")}
        },
    )

    return json_res


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)


from fastapi.testclient import TestClient

test_client = TestClient(app)


def test_read_main():
    response = test_client.post(
        "/build",
        json={
            "image": "python",
            "git_repo_url": "https://github.com/mithril-security/sample-test-repo.git",
            "command": "python3 main.py",
            "artifact_pattern": "output.txt",
        },
    )
    print(response.json())
    # Use assert False to get stdout/stderr
    # assert False
    # assert response.status_code == 200
    # assert response.json() == {"msg": "Hello World"}
