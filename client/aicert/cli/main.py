import os
from pathlib import Path
import typer
from typing import Annotated

from .client import Client


SIMULATION_MODE = os.getenv('AICERT_SIMULATION_MODE') is not None


app = typer.Typer(rich_markup_mode="rich")


@app.command()
def new(
    dir: Annotated[Path, typer.Option()] = Path.cwd(),
    interactive: Annotated[bool, typer.Option()] = True,
    auto_approve: Annotated[bool, typer.Option()] = False,
):
    """Create a new aicert.yaml file in the current directory"""
    client = Client(
        interactive=interactive,
        auto_approve=auto_approve,
        simulation_mode=SIMULATION_MODE
    )
    client.new_cmd(dir)


@app.command()
def build(
    dir: Annotated[Path, typer.Option()] = Path.cwd(),
    interactive: Annotated[bool, typer.Option()] = True,
    auto_approve: Annotated[bool, typer.Option()] = False,
):
    """Launch build process on an AICert VM"""

    client = Client.from_config_file(
        dir=dir,
        interactive=interactive,
        auto_approve=auto_approve,
        simulation_mode=SIMULATION_MODE
    )
    client.build_cmd(dir)


@app.command()
def verify(
    dir: Annotated[Path, typer.Option()] = Path.cwd(),
    interactive: Annotated[bool, typer.Option()] = True,
    auto_approve: Annotated[bool, typer.Option()] = False,
):
    """Verify attestation and output files"""
    
    client = Client.from_config_file(
        dir=dir,
        interactive=interactive,
        auto_approve=auto_approve,
        simulation_mode=SIMULATION_MODE
    )
    client.verify_cmd(dir)
