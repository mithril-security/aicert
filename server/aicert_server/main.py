#!/usr/bin/python3

"""Defines the FastAPI server that runs in the AICert Runners

Endpoints:
    GET /outputs?pattern=...: get the list of all output files matching the given glob pattern
    GET /outputs/filename: download an output file
    POST /submit_build [body: Build]: start the build with given specs (see aicert-common's protocol for the request specs)
    POST /submit_server [body: Serve]: start serving according to given specs (see aicert-common's protocol for the request specs)
        Available only if the build has completed.
    GET /attestation: returns 204 if the build has not completed and the attesation (event log, quote and certificate chain) otherwise
"""

import base64
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import Response, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import TypeAdapter
from typing import List
from pathlib import Path
import uvicorn
import hashlib
import yaml
import logging

from aicert_common.protocol import Build, Serve, FileList, Resource
from .config_parser import AxolotlConfig
from .builder import Builder, SIMULATION_MODE
from .tpm import tpm_extend_pcr

CA_PATH = "/home/azureuser/root.crt"
CERT_PATH = "/home/azureuser/aicert_worker.crt"
PCR_FOR_CERTIFICATE = 15
WORKSPACE = Path.cwd() / "workspace"
WORKSPACE.mkdir(exist_ok=SIMULATION_MODE)

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
app.mount("/outputs", StaticFiles(directory=WORKSPACE), name="outputs")
axolotl_config = AxolotlConfig()

@app.get("/outputs")
def list_outputs(pattern: str) -> FileList:
    if Path(pattern).is_absolute():
        raise HTTPException(
            status_code=403, detail="Cannot list files outside of workdir"
        )
    return FileList(
        pattern=pattern,
        file_list=[
            str(sub.relative_to(WORKSPACE))
            for sub in WORKSPACE.glob(pattern)
            if sub.is_file()
        ],
    )

# @app.post("/submit_build", status_code=202)
@app.post("/build", status_code=202)
def submit_build(build_request: Build) -> None:
    Builder.submit_build(build_request, WORKSPACE, axolotl_config)

# TODO: Implementation needed
@app.get("/build/status", status_code=200)
def build_status() -> None:
    pass

@app.post("/submit_serve", status_code=202)
def submit_serve(serve_request: Serve) -> None:
    Builder.submit_serve(serve_request, WORKSPACE)

@app.post("/finetune", status_code=202)
def start_finetune() -> None:
    Builder.start_finetune(WORKSPACE, axolotl_config)

# TODO: Implementation needed
@app.post("/finetune/status", status_code=200)
def finetune_status() -> None:
    pass


@app.get("/attestation")
def attestation() -> Response:
    if not Builder.poll_build():
        return Response(status_code=204)
    # FastAPI encodes the response as json, but the quote contains raw bytes...
    # so we have to base64 encode them, this is ugly.
    # Ideally we'd like another serialization format like CBOR or messagepack
    # but FastAPI does not support those :(
    return jsonable_encoder(
        Builder.get_attestation(),
        custom_encoder={
            bytes: lambda v: {"base64": base64.b64encode(v).decode("utf-8")}
        },
    )

@app.get("/aTLS")
def aTLS() -> Response:
    # Extends PCR 15 with the CA certificate and generates and returns the attestation
    
    with open(CA_PATH, "r") as r:
        ca_cert = r.read()

    cert_hash = hashlib.sha256(ca_cert.encode("utf-8")).hexdigest()
    
    tpm_extend_pcr(PCR_FOR_CERTIFICATE, cert_hash)

    return jsonable_encoder(
        Builder.get_attestation(ca_cert),
        custom_encoder={
            bytes: lambda v: {"base64": base64.b64encode(v).decode("utf-8")}
        },
    )



### Axolotl endpoints
@app.post("/axolotl/configuration")
async def config_axolotl(file: UploadFile = File(...)) -> JSONResponse:
    # initialize config
    print("Setting up axolotl configuration.")
    config_str = await file.read()

    axolotl_config.initialize(config_str)
    axolotl_config.parse()
    axolotl_config_location = WORKSPACE / "user_axolotl_config.yaml"
    serialized_config = yaml.dump(axolotl_config.config)
    print(serialized_config)
    with open(axolotl_config_location, 'wb') as config:
        config.write(serialized_config.encode("utf-8"))

    return JSONResponse(content={"yaml file status": "OK"})


def main():
    if SIMULATION_MODE:
        print("WARNING: running in SIMULATION MODE, the TPM will not be used")
    
    uvicorn.run(app, host="0.0.0.0", port=8000) #, ssl_keyfile="./key.pem", ssl_certfile="./cert.pem")
