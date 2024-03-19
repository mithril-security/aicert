# testing procecudes and running examples 

## Setup 
Aicert must be and all the dependencies must be installed. 

## Testing examples
On two terminals. 

The first one running `aicert-server` :
```bash 
export AICERT_SIMULATION_MODE=1
poetry shell && poetry install && aicert-server
```

On the second one, which will be the client :
run `python3` interpreter after a poetry shell. 

```python
from pydantic import TypeAdapter
from typing import List
from aicert_common.protocol import Build, Resource, Framework
from aicert_server.config_parser import AxolotlConfig
from pathlib import Path
import requests

ResourceListAdapter = TypeAdapter(List[Resource])
WORKSPACE = Path.cwd() / "workspace"
model_resource = [{
         "resource_type":"model",
         "repo":"https://huggingface.co/codellama/CodeLlama-7b-hf",
         "hash": "7f22f0a5f7991355a2c3867923359ec4ed0b58bf",
         "path": "workspace"
    }]

## Sending a configuration 
file = {'file': open('qlora_test.yml', 'rb')}
url = 'http://127.0.0.1:8000/axolotl/configuration'
resp = requests.post(url=url, files=file)

## Sending building request
ResourceListAdapter = TypeAdapter(List[Resource])
framework={"framework": "axolotl"}
FrameworkAdapter = TypeAdapter(Framework)
url_build = "http://127.0.0.1:8000/build"
build_request = Build(
        image="@local/aicertbase:latest",
        cmdline="/bin/sh -c 'echo Hello > hello_world.txt'",
        inputs=ResourceListAdapter.validate_python(model_resource),
        outputs="hello_world.txt",
        framework=FrameworkAdapter.validate_python(framework),
).model_dump_json()
resp_build = requests.post(url=url_build, data=build_request, headers={"Content-Type": "application/json"})
```

- [ ] Inputs must be removed as it is taken from the the configuration file. 
