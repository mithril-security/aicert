"""AICert CLI

CLI tool for certified builds and deployments

Typical workflow:
1. use new subcommand to set up a configuration
2. modify the configuration to suit your needs
3. use build subcommand to run the build on an
   aicert runner and get back your build
   artifacts and an attestation
4. if your configuration file specifies a serve
   section, the correponding server (whose code
   is now attested) will be launched by the runner
5. verify the attestation

AICert can be run:
- either locally in simulation mode, in which case
  youn need no daemon but a running instance of the
  aicert server (use the aicert-server package)
- either on Azure CVMs, in which case you need to setup
  a local daemon to interact with Azure
  (use the aicert-daemon package)

See the aicert-common package for more on the configuration file.
"""

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
def axolotl_config(
    config: Optional[str] = None,
    dir: Annotated[Path, typer.Option()] = Path.cwd(),
    interactive: Annotated[bool, typer.Option()] = True,
):
    """Creates an axolotl configuration instance on the server"""
    with log_errors_and_warnings():
        client = Client.from_config_file(
            dir=dir,
            interactive=interactive,
            simulation_mode=SIMULATION_MODE,
        )
        config = config if config is not None else "axolotl_config.yaml"

        client.submit_axolotl_config(dir, config)


@app.command()
def finetune(
    dir: Annotated[Path, typer.Option()] = Path.cwd(),
    interactive: Annotated[bool, typer.Option()] = True,
):
    """Finetune a model using the previously transferred
    axolotl configuration
    """
    with log_errors_and_warnings():
        client = Client.from_config_file(
            dir=dir,
            interactive=interactive,
            simulation_mode=SIMULATION_MODE,
        )
        client.submit_finetune()


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

    (See aicert.cli.Client)
    """
    with log_errors_and_warnings():
        client = Client.from_config_file(
            dir=dir,
            interactive=interactive,
            simulation_mode=SIMULATION_MODE,
        )
        log.info(f"Connecting to runner at {client.daemon_address}")
        #client.connect()

        log.info("Sumitting build request")
        client.submit_build()

        if not client.is_simulation:
            attestation = client.wait_for_attestation()
            log.info(f"Received attestation")

            with (dir / "attestation.json").open("wb") as f:
                f.write(attestation)

        log.info(f"Downloading build outputs")
        client.download_outputs(dir, verbose=True)

        if client.requires_serve:
            client.submit_serve()
            log.info(f"Deployment running")
        else:
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
