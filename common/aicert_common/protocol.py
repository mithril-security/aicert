from pydantic import BaseModel, Field
from typing import Literal, Union, Annotated, List, Optional

class FileResource(BaseModel):
    resource_type: Literal["file"]
    url: str
    path: str


class ArchiveResource(BaseModel):
    resource_type: Literal["archive"]
    url: str
    compression: Literal["none", "gzip"]
    path: str


class GitResource(BaseModel):
    resource_type: Literal["git"]
    repo: str
    branch: str
    path: str
    dependencies: Literal["none", "poetry"]


Resource = Annotated[Union[FileResource, ArchiveResource, GitResource], Field(discriminator="resource_type")]


class BuildRequest(BaseModel):
    image: str
    cmdline: str
    inputs: List[Resource]
    outputs: str


class ConfigFile(BuildRequest):
    version: str
    cloud: Literal["azure"]
    machine: str
