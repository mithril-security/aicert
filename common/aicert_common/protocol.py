from pydantic import BaseModel, Field
from typing import Literal, Union, Annotated, List, Optional

class FileResource(BaseModel):
    resource_type: Literal["file", "archive"]
    url: str
    compression: Literal["none", "gzip"]
    path: str


class GitResource(BaseModel):
    resource_type: Literal["git"]
    repo: str
    branch: str
    path: str
    dependencies: Literal["none", "poetry"]


Resource = Annotated[Union[FileResource, GitResource], Field(discriminator="resource_type")]


class Build(BaseModel):
    image: str
    cmdline: str
    inputs: List[Resource]
    outputs: str


class Runner(BaseModel):
    platform: Literal["azure-tpm"]
    instance_type: str
    daemon: str


class Serve(BaseModel):
    cmdline: str
    host_port: int
    container_port: int


class ConfigFile(BaseModel):
    version: str
    runner: Optional[Runner]
    build: Build
    serve: Optional[Serve]


class FileList(BaseModel):
    pattern: str
    file_list: List[str]
