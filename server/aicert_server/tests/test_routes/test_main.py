from fastapi.testclient import TestClient
import os
import pytest
from pydantic import TypeAdapter
from typing import List
from aicert_common.protocol import Build, Resource
from aicert_server.config_parser import AxolotlConfig
from aicert_server.main import app
from pathlib import Path

WORKSPACE = Path.cwd() / "workspace"
test_client = TestClient(app)

def test_parsing_axolotl():
    print("testing axolotl parsing")
    config_content = ''
    config_test_path = "/home/azureuser/aicert/server/aicert_server/tests/qlora_test.yml"

    with open(config_test_path, 'rb') as file:
        config_content = file.read()
    axolotl_config = AxolotlConfig()
    axolotl_config.initialize(config_content)

    axolotl_config.parse('/workspace')
    print(axolotl_config.config['base_model'])
    assert axolotl_config.config['base_model'] == "codellama/CodeLlama-7b-hf"


def test_config_axolotl():
    # example config used : https://github.com/OpenAccess-AI-Collective/axolotl/blob/main/examples/code-llama/7b/lora.yml
    # dataset : https://huggingface.co/datasets/mhenrichsen/alpaca_2k_test
    # model : https://huggingface.co/codellama/CodeLlama-7b-hf/commit/7f22f0a5f7991355a2c3867923359ec4ed0b58bf
    print("\ntesting config_axolotl endpoint")
    config_test_path = "/home/azureuser/aicert/server/aicert_server/tests/qlora_test.yml"
   

    files = {'file': ('qlora_test.yml', open(config_test_path, 'rb'), 'application/x-yaml')}
    response = test_client.post("/axolotl/configuration", files=files)

    print(response.content)
    assert response.status_code == 200, response.text


axolotl_config = AxolotlConfig()
configuration_test = """
base_model: codellama/CodeLlama-7b-hf@sha256:7f22f0a5f7991355a2c3867923359ec4ed0b58bf
model_type: LlamaForCausalLM
tokenizer_type: CodeLlamaTokenizer

load_in_8bit: true
load_in_4bit: false
strict: false

datasets:
  - path: mhenrichsen/alpaca_2k_test@sha256:d05c1cb585e462b16532a44314aa4859cb7450c6
    type: alpaca
dataset_prepared_path:
val_set_size: 0.05
output_dir: ./lora-out

sequence_len: 4096
sample_packing: true
pad_to_sequence_len: true

adapter: lora
lora_model_dir:
lora_r: 32
lora_alpha: 16
lora_dropout: 0.05
lora_target_linear: true
lora_fan_in_fan_out:

wandb_project:
wandb_entity:
wandb_watch:
wandb_name:
wandb_log_model:

gradient_accumulation_steps: 4
micro_batch_size: 2
num_epochs: 4
optimizer: adamw_bnb_8bit
lr_scheduler: cosine
learning_rate: 0.0002

train_on_inputs: false
group_by_length: false
bf16: auto
fp16:
tf32: false

gradient_checkpointing: true
early_stopping_patience:
resume_from_checkpoint:
local_rank:
logging_steps: 1
xformers_attention:
flash_attention: true
s2_attention:

warmup_steps: 10
evals_per_epoch: 4
saves_per_epoch: 1
debug:
deepspeed:
weight_decay: 0.0
fsdp:
fsdp_config:
special_tokens:
  bos_token: "<s>"
  eos_token: "</s>"
  unk_token: "<unk>"
"""

axolotl_config.initialize(config_file=configuration_test)
axolotl_config.parse(WORKSPACE)
def test_build_axolotl():
    print("\ntesting build_axolotl endpoint")
    # model_resource = AxolotlResource(
    #     resource_type="model",
    #     repo="https://huggingface.co/codellama/CodeLlama-7b-hf",
    #     hash="7f22f0a5f7991355a2c3867923359ec4ed0b58bf",
    #     path=str(WORKSPACE)
    # )
    model_resource = [{
        "resource_type":"model",
        "repo":"https://huggingface.co/codellama/CodeLlama-7b-hf",
        "hash": "7f22f0a5f7991355a2c3867923359ec4ed0b58bf",
        "path": str(WORKSPACE)
    }]
    ResourceListAdapter = TypeAdapter(List[Resource])
    build_request = Build(
        image="mithrilsecuritysas/aicertbase",
        cmdline="/bin/sh -c 'apt update && apt install -y build-essential && echo Hello > hello_world.txt",
        inputs=ResourceListAdapter.validate_python(model_resource),
        outputs="hello_world.txt",
    ).model_dump_json()

    response = test_client.post("/axolotl/build", data=build_request, headers={"Content-Type": "application/json"})
    print(response.content)
    assert response.status_code == 200


