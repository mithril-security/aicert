import os
from pathlib import Path
import typer
from typing import Annotated, Optional

from .client import Client
from aicert_common.logging import log
from aicert_common.errors import log_errors_and_warnings

SIMULATION_MODE = os.getenv("AICERT_SIMULATION_MODE") is not None

app = typer.Typer(rich_markup_mode="rich")


@app.command()
def finetune(
    config: Optional[str] = "aicert.yaml",
    dir: Annotated[Path, typer.Option()] = Path.cwd(),
    interactive: Annotated[bool, typer.Option()] = True,
):
    """Finetune a model using the previously transferred
    axolotl configuration
    """
    with log_errors_and_warnings():
        client = Client.from_config_file(
            interactive=interactive,
            simulation_mode=SIMULATION_MODE,
        )

        # Creates a VM and connects to it using aTLS
        print("Deploying VM and initializing server")
        client.connect()

        print("Submitting finetune request")
        res = client.submit_axolotl_config(dir, config)
        
        client.submit_finetune()

        if not client.is_simulation:
            attestation = client.wait_for_attestation()
            log.info(f"Received attestation")

            with (dir / "attestation.json").open("wb") as f:
                f.write(attestation)
        
        # Verify attestation report
        # client.verify_attestation(attestation, verbose=True)

        print("Sample Output Link: https://aicertstorage.blob.core.windows.net/aicertcontainer/finetuned-model.zip")

        print("Destroying VM")
        #client.disconnect()


@app.command()
def verify(
    dir: Annotated[Path, typer.Option()] = Path.cwd(),
    interactive: Annotated[bool, typer.Option()] = True,
):
    """Verify attestation and output files"""

    client = Client.from_config_file(
        interactive=interactive,
        simulation_mode=SIMULATION_MODE,
    )

    with (dir / "attestation.json").open("rb") as f:
            attestation = f.read()

    client.verify_attestation(attestation, verbose=True)

