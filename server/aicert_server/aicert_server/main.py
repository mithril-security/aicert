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
from fastapi import FastAPI, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import Response, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import uvicorn
import hashlib
import yaml
import logging
from sh import tail
import time
from sse_starlette.sse import EventSourceResponse

from aicert_common.protocol import FileList, AxolotlConfigString
from aicert_server.config_parser import AxolotlConfig
from aicert_server.builder import Builder, SIMULATION_MODE
from aicert_server.tpm import tpm_extend_pcr, tpm_read_pcr

PCR_FOR_CERTIFICATE = 15
WORKSPACE = Path("/workspace")
WORKSPACE.mkdir(exist_ok=True)

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
axolotl_config = AxolotlConfig()

async def logGenerator():
    for line in tail("-f", WORKSPACE / "log_model_dataset.log", _iter=True):
        # if await request.is_disconnected():
        #     print("client disconnected")
        #     break
        print("data chunk : {} ".format(line))
        yield line
        time.sleep(0.2)


@app.get("/build/status", status_code=200)
async def build_status():
    # log_generator = logGenerator()
    return StreamingResponse(logGenerator())

@app.post("/finetune", status_code=202)
def start_finetune() -> None:
    Builder.start_finetune(WORKSPACE, axolotl_config)

# TODO: Implementation needed
@app.post("/finetune/status", status_code=200)
def finetune_status() -> None:
    pass


@app.get("/attestation")
def attestation() -> Response:
    if not Builder.poll_finetune():
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


def get_caddy_rootca():
    import requests
    from requests.adapters import HTTPAdapter
    from requests.packages.urllib3.util.retry import Retry

    s = requests.Session()
    retries = Retry(total=5, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504])
    s.mount("http://", HTTPAdapter(max_retries=retries))
    
    r = s.get("http://caddy-in-constrained-attestation-generator-network:2019/pki/ca/local")
    r.raise_for_status()
    caddy_root_ca = r.json()['root_certificate']
    
    if not caddy_root_ca:
    	raise ValueError("Expected a Caddy root CA, got nothing")
    	
    return caddy_root_ca


@app.get("/aTLS")
def aTLS() -> Response:
    # Extends PCR 15 with the CA certificate and generates and returns the attestation
    
    ca_cert = get_caddy_rootca()

    cert_hash = hashlib.sha256(ca_cert.encode("utf-8")).hexdigest()
    
    tpm_value = tpm_read_pcr(PCR_FOR_CERTIFICATE)
    if tpm_value == "0000000000000000000000000000000000000000000000000000000000000000":
        tpm_extend_pcr(PCR_FOR_CERTIFICATE, cert_hash)

    return jsonable_encoder(
        Builder.get_attestation(ca_cert),
        custom_encoder={
            bytes: lambda v: {"base64": base64.b64encode(v).decode("utf-8")}
        },
    )


### Axolotl endpoints
@app.post("/axolotl/configuration")
def config_axolotl(axolotl_conf_string: AxolotlConfigString) -> JSONResponse:
    # initialize config
    if axolotl_config.valid:
        return JSONResponse(content={"Error":"Cannot upload more than one configuration to the server"}, status_code=406)

    print("Setting up axolotl configuration.")
    axolotl_config.initialize(axolotl_conf_string.axolotl_config)
    axolotl_config.parse()
    axolotl_config_location = WORKSPACE / "user_axolotl_config.yaml"
    axolotl_config.set_filename("user_axolotl_config.yaml")
    serialized_config = yaml.dump(axolotl_config.config)
    with open(axolotl_config_location, 'wb') as config:
        config.write(serialized_config.encode("utf-8"))

    return JSONResponse(content={"yaml file status": "OK"}, status_code=202)


def main():
    if SIMULATION_MODE:
        print("WARNING: running in SIMULATION MODE, the TPM will not be used")
    
    uvicorn.run(app, host="0.0.0.0", port=80)

if __name__ == "__main__":
    main()