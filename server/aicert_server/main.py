#!/usr/bin/python3

import base64
import docker
from fastapi import FastAPI, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import Response
import os
from pathlib import Path
import uvicorn

from aicert_common.protocol import BuildRequest
from .event_log import EventLog, sha256_file


DEBUG = os.getenv('AICERT_DEBUG') is not None


app = FastAPI()
docker_client = docker.from_env()


@app.post("/build", status_code=200)
def build(build_request: BuildRequest) -> Response:
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
    event_log = EventLog(debug=DEBUG)
    event_log.start_build(build_request)

    # create a workspace folder
    workspace = Path.cwd() / "workspace"

    # install inputs
    for input in build_request.inputs:
        event_log.fetch_resource(input, workspace)

    event_log.docker_run(
        cmd=build_request.cmdline,
        workspace=workspace,
        image=build_request.image,
    )

    matches = list(workspace.glob(build_request.outputs))

    if not matches:
        raise HTTPException(status_code=404, detail=f"No files matching output pattern: '{build_request.artifact_pattern}'")

    artifacts = []
    for path in matches:
        if path.is_file():
            artifact = {
                "path": str(path.relative_to(workspace)),
                "digest": {"sha256": sha256_file(path)},
            }
            artifacts.append(artifact)

    if not artifacts:
        raise HTTPException(status_code=404, detail=f"No files matching output pattern: '{build_request.artifact_pattern}'")

    event_log.build_artifacts(artifacts)
    res = event_log.attest()

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


def main():
    if DEBUG:
        print("Warning: running in debug mode, the TPM will not be used")
    uvicorn.run(app, host="0.0.0.0", port=8000)
