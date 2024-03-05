from fastapi.testclient import TestClient
import os
import pytest
from aicert_common.protocol import Build, Resource
from aicert_server.config_parser import AxolotlConfig
from aicert_server.main import app


test_client = TestClient(app)

def test_parsing_axolotl():
    print("testing axolotl parsing")
    config_content = ''
    config_test_path = "qlora_test.yml"

    with open(config_test_path, 'rb') as file:
        config_content = file.read()
    axolotl_config = AxolotlConfig()
    axolotl_config.initialize(config_content)

    axolotl_config.parse('/workspace')
    assert axolotl_config.config['base_model'] == "codellama/CodeLlama-7b-hf"


def test_build_axolotl():
    # example config used : https://github.com/OpenAccess-AI-Collective/axolotl/blob/main/examples/code-llama/7b/lora.yml
    # dataset : https://huggingface.co/datasets/mhenrichsen/alpaca_2k_test
    # model : https://huggingface.co/codellama/CodeLlama-7b-hf/commit/7f22f0a5f7991355a2c3867923359ec4ed0b58bf
    config_test_path = "./qlora_test.yml"
    build_request_test = Build(
        image="aicertbase",
        cmdline="",
        inputs=list(),
        outputs=""
    ).json()
    print(build_request_test)
    if os.path.isfile(config_test_path):
        with open(config_test_path, 'rb') as file:
            content = file.read()
            print(content)
        _files = {'uploadFile': open(config_test_path, 'rb')}

        response = test_client.post(
            "/build_axolotl", 
            params=build_request_test,
            files=_files
        )
        print(response)
        assert response.status_code == 200
    else:
        print("OS file get failed ")



