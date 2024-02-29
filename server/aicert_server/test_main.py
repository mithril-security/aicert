from fastapi.testclient import TestClient
import os
import pytest
from aicert_common.protocol import Build, Resource
from .main import app


test_client = TestClient(app)


# def test_read_main():
#     response = test_client.post(
#         "/build",
#         json={
#             "image": "python",
#             "git_repo_url": "https://github.com/mithril-security/sample-test-repo.git",
#             "command": "python3 main.py",
#             "artifact_pattern": "output.txt",
#         },
#     )
#     print(response.json())



def test_build_axolotl():
    # example config used : https://github.com/OpenAccess-AI-Collective/axolotl/blob/main/examples/code-llama/7b/lora.yml
    # dataset : https://huggingface.co/datasets/mhenrichsen/alpaca_2k_test
    # model : https://huggingface.co/codellama/CodeLlama-7b-hf/commit/7f22f0a5f7991355a2c3867923359ec4ed0b58bf
    axolotl_config_test = """
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

    config_test_path = "./qlora_test.yml"
    build_request_test = Build(
        image="aicertbase",
        cmdline="",
        inputs=list(),
        outputs=""
    )
    if os.path.isfile(config_test_path):
        _files = {'uploadFile': open(config_test_path, 'rb')}

        response = test_client.post(
            "/build_axolotl", 
            params=build_request_test,
            files=_files
        )

        assert response.status_code == 200
    else:
        pytest.fail("OS file get failed ")