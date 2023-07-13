from datasets import load_dataset
from transformers import AutoModelForCausalLM, AutoTokenizer
from trl import SFTTrainer
import torch


dataset_name = 'Innermost47/alpaca-fr'
model_id = "tiiuae/falcon-7b"
question_column = 'instruction'
answer_column = 'output'
number_elements_for_training = 40

# Load model directly
from transformers import AutoModelForCausalLM
model = AutoModelForCausalLM.from_pretrained(model_id, trust_remote_code=True)
tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
tokenizer.pad_token = tokenizer.eos_token

# load dataset from location specified in Dockerfile
dataset = load_dataset('csv', data_files='tmp/alpaca-fr.csv')
dataset= dataset['train'].select(range(number_elements_for_training))

#format the data
def formatting_prompts_func(example):
    text = f"### Question: {example['instruction']}\n ### Answer: {example['output']}"
    return text

trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=dataset,
    dataset_text_field=question_column,
    max_seq_length=512,
    formatting_func=formatting_prompts_func,
    packing=True,
)

#launch the training
trainer.train()
torch.save(model.state_dict(), '/tmp/model/finetuned.pth')