"""AICert Daemon

Endpoits are defined using FastAPI.
They use the abstractions provided by the Daemon interface.
"""

from fastapi import FastAPI
from pathlib import Path
import uvicorn

from .daemon import Dameon


aicert_home = Path.home() / ".aicert"
Dameon.init(aicert_home)


app = FastAPI()


@app.post("/launch_runner")
async def launch_runner():
    return Dameon.launch_runner(aicert_home)


@app.post("/destroy_runner")
def destroy_runner():
    Dameon.destroy_runner(aicert_home)


def main():
    uvicorn.run(app, host="0.0.0.0", port=8080)
