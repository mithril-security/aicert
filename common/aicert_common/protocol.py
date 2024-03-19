"""AICert Protocol

Both HTTP messages and configuration files are based on the classes
defined in this module.
"""

from pydantic import BaseModel, Field
from typing import Literal, Union, Annotated, List, Optional

class FileResource(BaseModel):
    """File Resource

    A file required as input to the build
    that may or may not be compressed.

    Attributes:
        resource_type (Literal["file", "archive"]): resources discriminant,
            use file for simple files and archive for files containing multiple files
            and that need to be extracted
        url (str): location of the file
        compression (Literal["none", "gzip"]): compression algo
        path (str): intallation path
    """
    resource_type: Literal["file", "archive"]
    url: str
    compression: Literal["none", "gzip"]
    path: str


class GitResource(BaseModel):
    """Git Resource

    A git repository required as input to the build.
    If the repository uses a package manager for its
    dependencies, the server can generate and measure
    the lockfile for improved provenance.

    Attributes:
        resource_type (Literal["git"]): resources discriminant
        repo (str): url of the repository
        barnch (str): branch to use
        path (str): intallation path
        dependencies (Literal["none", "poetry"]): package system
    """
    resource_type: Literal["git"]
    repo: str
    branch: str
    path: str
    dependencies: Literal["none", "poetry"]


class AxolotlResource(BaseModel):
    """
    Model resource definition

    Attributes: 
        resource_type (Literal["model"]): resource type
        repo (str): Huggingface repo 
        hash (str): commit hash or version requested
        path (str): installation path
    """
    resource_type: Literal["model", "dataset"]
    repo: str
    hash: str
    path: str


Resource = Annotated[Union[FileResource, GitResource, AxolotlResource], Field(discriminator="resource_type")]


class Framework(BaseModel):
    """
    Defines framework to use for build request
    
    Attributes:
        framework (Literal["default", "axolotl"])
    """
    framework: Literal["default", "axolotl"]


class Build(BaseModel):
    """Build section

    Build section of the configuration file also
    used stand alone in `submit_build` requests to
    the server.

    Defines:
    - all the necessary input resources that will be doenloaded
    and measured by the server prior to the build
    - the base image for the build
    - the build command
    - a glob pattern to retrieve the outputs

    Note that the inputs will be downloaded in the working directory
    of the server. This directory is mount on the image at /mnt during build.

    Attributes:
        image (str): name of the base docker image for the build
        (we advise you to pin a specific hash and to build your images
        with a CI for improved auditability)
        cmdline (str): build command to be run
        inputs (List[Resource]): list of resources necessary for the build
        outputs (str): glob pattern to retrieve the outputs
    """
    image: str
    cmdline: str
    inputs: Optional[List[Resource]]
    outputs: str
    framework: Framework


class Runner(BaseModel):
    """Runner section

    Runner section of the configuration file also
    used stand alone in `launch_runner` requests to
    the daemon (NOT YET IMPLEMENTED).

    Defines:
    - the cloud provider and technology
    - the instance type
    - the address of the daemon

    Attributes:
        platform (Literal["azure-tpm"]): cloud provider and technology spec
        instance_type (str): type of instance
        daemon (str): address of the daemon
    """
    platform: Literal["azure-tpm"]
    instance_type: str
    daemon: str


class Serve(BaseModel):
    """Serve section

    Serve section of the configuration file also
    used stand alone in `submit_serve` requests to
    the server.

    Defines:
    - the server's start command
    - the host port
    - the container port

    Attributes:
        cmdline (str)
        host_port (int)
        container_port (int)
    """
    cmdline: str
    host_port: int
    container_port: int


class ConfigFile(BaseModel):
    """Configuration file

    Contains:
    - a version specifier
    - runner, build and serve sections (runner and serve are optional)

    Attributes:
        version (str)
        runner (Optional[Runner])
        build (Build)
        serve (Optional[Serve])
    """
    version: str
    runner: Optional[Runner]
    build: Build
    serve: Optional[Serve]


class FileList(BaseModel):
    """List of files matching a pattern

    Returned by the outputs endpoint.
    """
    pattern: str
    file_list: List[str]
