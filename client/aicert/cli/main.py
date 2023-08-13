import os
from pathlib import Path
import typer
from typing import Annotated

from .client import Client, log_errors_and_warnings
from .logging import log


SIMULATION_MODE = os.getenv("AICERT_SIMULATION_MODE") is not None


app = typer.Typer(rich_markup_mode="rich")


@app.command()
def new(
    dir: Annotated[Path, typer.Option()] = Path.cwd(),
    interactive: Annotated[bool, typer.Option()] = True,
):
    """Create a new aicert.yaml file in the current directory"""
    client = Client(
        interactive=interactive,
        simulation_mode=SIMULATION_MODE,
    )
    client.new_config(dir)


@app.command()
def build(
    dir: Annotated[Path, typer.Option()] = Path.cwd(),
    interactive: Annotated[bool, typer.Option()] = True,
):
    """Launch build process on an AICert runner
    - create a runner by sending a request to the daemon, connect to it
    - submit a build request to the runner
    - wait for the build to complete and retreive the attestation
    - download build outputs
    - destroy the runner by sending a request to the daemon
    """
    with log_errors_and_warnings():
        client = Client.from_config_file(
            dir=dir,
            interactive=interactive,
            simulation_mode=SIMULATION_MODE,
        )
        
        log.info(f"Connecting to runner at {client.daemon_address}")
        client.connect()

        log.info("Sumitting build request")
        client.submit_build()
        attestation = client.wait_for_attestation()
        log.info(f"Received attestation")

        with (dir / "attestation.json").open("wb") as f:
            f.write(attestation)

        log.info(f"Downloading build outputs")
        client.download_outputs(dir, verbose=True)

        if client.requires_serve:
            client.submit_serve()
            log.info(f"Deployment running")

        # TODO: do not kill instance if it serves something...
        client.disconnect()


@app.command()
def verify(
    dir: Annotated[Path, typer.Option()] = Path.cwd(),
    interactive: Annotated[bool, typer.Option()] = True,
):
    """Verify attestation and output files"""

    client = Client.from_config_file(
        dir=dir,
        interactive=interactive,
        simulation_mode=SIMULATION_MODE,
    )

    with (dir / "attestation.json").open("rb") as f:
            attestation = f.read()

    client.verify_build_response(attestation, verbose=True)
