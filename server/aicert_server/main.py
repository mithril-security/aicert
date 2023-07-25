#!/usr/bin/python3

import base64
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
import docker
from pathlib import Path
from fastapi.encoders import jsonable_encoder

from aicert_common.protocol import BuildRequest
from .tpm import quote, cert_chain
from .event_log import EventLog, BASE_IMAGE, sha256_file


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
    event_log = EventLog()
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

    matches = list(Path("workspace").glob(build_request.outputs))

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

    res = {
        "event_log": event_log.get(),
        "remote_attestation": {"quote": quote(), "cert_chain": cert_chain()},
    }

    # FastAPI encodes the response as json, but the quote contains raw bytes...
    # so we have to base64 encode then, this is ugly.
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
