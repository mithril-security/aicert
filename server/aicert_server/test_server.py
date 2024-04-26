from aicert_common.protocol import Build
from pydantic import TypeAdapter
from typing import List
import requests
from aicert_common.protocol import Resource
ResourceListAdapter = TypeAdapter(List[Resource])
WORKSPACE = Path.cwd() / "workspace"
model_resource = [{
        "resource_type":"model",
        "repo":"https://huggingface.co/codellama/CodeLlama-7b-hf",
        "hash": "7f22f0a5f7991355a2c3867923359ec4ed0b58bf",
        "path": "workspace"
    }]
file = {'file': open('qlora_test.yml', 'rb')}
url = 'http://127.0.0.1:8000/axolotl/configuration'
url_build = "http://127.0.0.1:8000/axolotl/build"
file = {'file': open('./qlora_test.yml', 'rb')}
resp = requests.post(url=url, files=file)
resp_build = requests.post(url=url_build, data=build_request, headers={"Content-Type": "application/json"})