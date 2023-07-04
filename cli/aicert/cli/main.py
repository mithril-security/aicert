import inquirer
import os
import typer
from typing import Annotated, Optional

from .logging import log
from .context import Context

app = typer.Typer(rich_markup_mode="rich")

@app.command()
def certify(
    input_container: Annotated[Optional[str], typer.Option()] = None,
    dataset_source: Annotated[Optional[str], typer.Option()] = None,
    output_model: Annotated[Optional[str], typer.Option()] = None,
    output_bom: Annotated[Optional[str], typer.Option()] = None,
):
    log.debug(input_container)
    log.debug(dataset_source)
    log.debug(output_model)
    log.debug(output_bom)