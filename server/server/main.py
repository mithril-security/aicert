#!/usr/bin/python3

import json
import uvicorn
from fastapi import FastAPI
from fastapi.responses import Response
from io import BytesIO
from typing import Annotated
import hashlib
import subprocess
import docker
import docker
import subprocess
from pathlib import Path


app = FastAPI()

docker_client = docker.from_env()


def sha256_file(file_path) -> str:
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as file:
        for chunk in iter(lambda: file.read(4096), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


def extend_pcr(pcr_index: int, hex_hash_value: str) -> None:
    """
    Extend PCR pcr_index from SHA256 bank with a hash

    >>> hex_hash_value = (
    ...     "0x0000000000000000000000000000000000000000000000000000000000000000"
    ... )
    >>> pcr_index = 15
    >>> extend_pcr(pcr_index, hex_hash_value)
    """

    subprocess.run(
        ["tpm2_pcrextend", f"{pcr_index}:sha256={hex_hash_value}"], check=True
    )


def read_pcr(pcr_index):
    """
    Read the value of a PCR at index pcr_index from bank sha256
    returns the hash value of the PCR

    >>> _ = read_pcr(15)
    """
    x = subprocess.run(
        ["tpm2_pcrread", f"sha256:{pcr_index}"], capture_output=True, check=True
    ).stdout
    x = x.decode("utf-8")
    x = x.splitlines()
    assert len(x) == 2
    assert "sha256:" == x[0].strip()
    idx, hash = x[1].split(":")
    assert idx.strip() == str(pcr_index)
    hash = hash.strip()
    return hash[2:].lower()


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
        extend_pcr(15, hash_event)
        self.event_log.append(event_json)

    def get(self):
        return self.event_log


from pydantic import BaseModel


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
    >>> res == {
    ...     "event_log": [
    ...         '{"event_type": "start_build", "image": "python", "command": "python3 main.py", "artifact_pattern": "output.txt", "git_repo_url": "https://github.com/mithril-security/sample-test-repo.git"}',
    ...         '{"event_type": "pull_image", "image": "python", "resolved": {"id": "sha256:c0e63845ae986c52da5cd6ac4d56eebf293439bb22a3cee198dd818fd12ba555"}}',
    ...         '{"event_type": "git_clone", "url": "https://github.com/mithril-security/sample-test-repo.git", "resolved": {"git_hash": "af9321dfcaf355e87f85c33305c746f3ca9880c7"}}',
    ...         '{"event_type": "build_artifacts", "artifacts": [{"path": "output.txt", "digest": {"sha256": "0a54f42edd65c2537ae69c6afcc207f93c24c7f887c054d15598a6ae7398aa5f"}}]}',
    ...     ]
    ... }
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

    # TODO: get quote
    # subprocess.run(
    #     ["tpm2_quote", "-c", "ak.ctx", "-l", "sha256:0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15", "-q", "1234", "-m", "quote.msg", "-s", "quote.sig", "-o", "quote.pcrs", "-g", "sha256"],
    # )

    return {"event_log": event_log.get()}


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
