#!/usr/bin/python3

import base64
from fastapi import FastAPI, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
import os
from pathlib import Path
import uvicorn

from aicert_common.protocol import BuildRequest
from .builder import Builder


DEBUG = os.getenv('AICERT_DEBUG') is not None
WORKSPACE = Path.cwd() / "workspace"


if not WORKSPACE.exists():
    WORKSPACE.mkdir()


app = FastAPI()
app.mount("/outputs", StaticFiles(directory=WORKSPACE), name="outputs")


@app.post("/submit", status_code=202)
def submit(build_request: BuildRequest) -> None:
    Builder.submit_build(build_request, WORKSPACE)
    
@app.get("/attestation")
def attestation() -> Response:
    if not Builder.poll_build():
        return Response(status_code=204)
    # FastAPI encodes the response as json, but the quote contains raw bytes...
    # so we have to base64 encode then, this is ugly.
    # Ideally we'd like another serialization format like CBOR or messagepack
    # but FastAPI does not support those :(
    return jsonable_encoder(
        Builder.get_attestation(),
        custom_encoder={
            bytes: lambda v: {"base64": base64.b64encode(v).decode("utf-8")}
        },
    )


def main():
    if DEBUG:
        print("Warning: running in debug mode, the TPM will not be used")
    uvicorn.run(app, host="0.0.0.0", port=8000)
