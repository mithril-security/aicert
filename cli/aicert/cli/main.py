import typer
from typing import Annotated, Optional

import yaml

from .logging import log
import importlib
import importlib.resources
from pathlib import Path

app = typer.Typer(rich_markup_mode="rich")

@app.command()
def new():
    """Create a new aicert.yaml file in the current directory"""
    init_yaml = importlib.resources.read_text(  # type: ignore
        __package__, "aicert_new.yaml"
    )
    try:
        with open("aicert.yaml", "x") as f:
            f.write(init_yaml)
    except FileExistsError:
        typer.secho(f"ERROR: aicert.yaml already exists", fg=typer.colors.RED)


@app.command()
def build():
    """Launch build process"""
    try:
        f = Path("aicert.yaml").read_text()
    except FileNotFoundError:
        typer.secho(f"ERROR: No aicert.yaml file found in current directory", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    try:
        conf = yaml.safe_load(f)
    except yaml.YAMLError as e:
        e.context_mark.name = "aicert.yaml"
        e.problem_mark.name = "aicert.yaml"
        typer.secho(f"ERROR: Failed to parse aicert.yaml file", fg=typer.colors.RED)
        typer.secho(f"ERROR: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    
    log.info(conf)


@app.command()
def verify():
    """Launch verification process"""
    raise NotImplementedError

# @app.command()
# def certify(
#     input_container: Annotated[Optional[str], typer.Option()] = None,
#     dataset_source: Annotated[Optional[str], typer.Option()] = None,
#     output_model: Annotated[Optional[str], typer.Option()] = None,
#     output_bom: Annotated[Optional[str], typer.Option()] = None,
# ):
#     log.debug(input_container)
#     log.debug(dataset_source)
#     log.debug(output_model)
#     log.debug(output_bom)
