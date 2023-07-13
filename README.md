<a name="readme-top"></a>

<!-- [![Contributors][contributors-shield]][contributors-url]
[![Forks][forks-shield]][forks-url]
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]
[![Apache License][license-shield]][license-url] -->


<!-- PROJECT LOGO -->
<br />
<div align="center">
  <a href="https://github.com/mithril-security/aicert">
    <img src="https://github.com/mithril-security/blindai/raw/main/docs/assets/logo.png" alt="Logo" width="80" height="80">
  </a>

<h1 align="center">AICert</h1>

[![Website][website-shield]][website-url]
[![Blog][blog-shield]][blog-url]
</div>

 <p align="center">
    <b>Making AI Traceable and Transparent</b><br /><br />
   <!-- 
    <a href="https://aicert.mithrilsecurity.io/en/latest"><strong>Explore the docs »</strong></a>
    <br />
    <br />
    <a href="https://aicert.mithrilsecurity.io/en/latest/docs/getting-started/quick-tour/">Get started</a>
    ·
    <a href="https://github.com/mithril-security/aicert/issues">Report Bug</a>
    ·
    <a href="https://github.com/mithril-security/aicert/issues">Request Feature</a>
  </p>
</div>

<!-- TABLE OF CONTENTS -->
<details>
  <summary>Table of Contents</summary>
  <ol>
    <li><a href="#-about-the-project">About The Project</a></li>
	  <li><a href="#-why-use-aicert">Why use AICert?</a></li>
    <li><a href="#-roadmap">Roadmap</a></li>
    <li><a href="#-usage">Usage</a></li>
    <li><a href="#-technology-overview">Technology Overview</a></li>
    <li><a href="#-trust-model">Trust Model</a></li>
    <li><a href="#-limitations">Technology Overview</a></li>

    <li><a href="#-contact">Contact</a></li>
  </ol>
</details>

## 🔒 About The Project

**AICert** aims to make AI **traceable** and **transparent** by enabling **AI Builders** to create certificates with **cryptographic proofs binding the weights of their models to the data and code used for training**, as well as the software stack of the machine used to train the model. **End users** can then verify these certificates to have proof that the model they talk to comes from a specific training set and code, which therefore **alleviates copyright, security and safety issues**.

We leverage **Trusted Platform Modules (TPMs)** in order to attest the whole stack used for producing the model, from the lowest-levels of the software stack, all the way to the model code and input data. Measuring the whole software stack and binding the final weights produced (by registering them in the last PCR) allows the derivation of certificates that contain **irrefutable proof of model provenance**.

AICert addresses some of the most urgent concerns related to **AI provenance**, such as **security**, enabling AI builders to:

+ Prove their AI model was not trained on copyrighted data
+ Provide an AI Bill of Material about the data and code used, which makes it harder to poison the model by injecting backdoors in the weights
+ Provide a strong audit trail with irrefutable proof for compliance and transparency

  ⚠️ **WARNING:** AICert is still under development.
    We are currently building a POC of AICert. This initial version will not include the full hardware-based verification features that we will introduce in the full release and **should not be used in production!** 

## 🎯 Roadmap

### **Coming soon**: POC release

+ Compatible with Azure VMs
+ CLI tool
+ Automated VM provisioning and configuration
+ Hardware-based generation of cryptographic proofs of software stack and model inputs and outputs
+ Standardization of proofs into one proof file
+ Proof file verification tool

⚠️ Our initial POC version will not be able to endorse the authenticity of the VM's hardware-based (TPM) signature of cryptographic proofs. This is to allow time for on-going discussions with Cloud providers over the implementation of this feature. This is why our POC release is not yet **production-ready**!

### Full release

+ Compatible with multiple major Cloud platforms ✅
+ Production-ready release with full security and verification features ✅

## 🔍 Features

+ **AI model traceability:** Create AI model ID cards that provide cryptographic proof binding model weights to a specific training set and code
+ **Non-forgeable proofs:** Leverage TPMs to ensure non-forgeable AI model ID cards
+ **Flexible training:** Use your preferred tooling for training- the only requirement is that it can be packaged into a Docker image
+ **Easy to install and use**

> You can check out [the project code on our GitHub](https://github.com/mithril-security/aicert/).

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## 📜 Getting started

### AI Builder POV: Creating an AI model certificate

### Step 1: Preparing dataset and training Dockerfiles

AICert requires AI Builders to provide their training data preparation and code in two separate Dockerfiles in order to get cryptographic measure for these two components individually. This allows end users to know if a difference in hash values relates to the input data or the input model in the case of a difference in their expected values.

In order to separate these two elements, we use Docker's multi-stage builds functionality.

AI Builder's can use the following examples as templates to create their Dockerfiles.

#### Dataset Dockerfile

```Dockerfile
# define first part of Dockerfile as build stage
FROM python AS build

# download dependencies
RUN pip install datasets

# run script to load, prepare and save dataset as .csv file in /home/tmp/datasets
RUN mkdir -p tmp/datasets
COPY dataset_script.py tmp/
RUN python tmp/dataset_script.py

# define second binaries stage
FROM scratch AS binaries

# waits for build stage to finish before copying files from /home/tmp/datasets to AICert default location: /home/aicert/data
COPY --from=build /home/tmp/datasets /
```

AI Builder's can use this Dockerfile as a template by simply adding any additional download dependencies to the Dockerfile and ensuring they provide a data preparing script called `dataset_script.py`.

Let's now take a look at our `dataset_script.py` file:

```python
from datasets import load_dataset

dataset_name = 'Innermost47/alpaca-fr'

question_column = 'instruction'
answer_column = 'output'
number_elements_for_training = 40

# pull dataset
dataset = load_dataset(dataset_name)

# prep dataset as required
dataset= dataset['train'].select(range(number_elements_for_training))
dataset = dataset.select_columns(['instruction', 'output'])

# save dataset for measurement and reuse in training stage
dataset.to_csv('tmp/datasets/alpaca-fr.csv')
```
This script largely follows a typical data preparation workflow. We can load our dataset from the source of our choice and prepare it in any way we wish.

The key step to remember here is we need to make sure we save our prepared dataset in the location stated in the final line of Dockerfile:

`COPY --from=build /home/tmp/datasets /`

Our prepared dataset will then be copied outside of the Docker environment to our destination folder ready to be used in the training stage!

#### Finetuning Dockerfile

In this second Dockerfile, we will copy our dataset from the previous build stage into our finetuning stage, run our training script before exporting our final trained model back into the AICert default data folder.

AICert will organize files in such a way that the datasets exported from the first dataset Docker stages will be available in the Docker environment when we build the training dataset. AI builders can therefore use the `COPY` instruction and name the dataset(s) they exported in the dataset Docker stage, knowing that they will be available upon build.

```Dockerfile
# define first part of Dockerfile as build stage
FROM python AS build

# download dependencies required for training script
RUN pip install datasets \
    trl==0.4.5 \
    einops \
    torch==2.0.1  \
    transformers==4.26.1 \
    --extra-index-url https://download.pytorch.org/whl/cpu

# copy our training script
RUN mkdir -p tmp/model
COPY train_script.py tmp

# copy dataset exported in previous data preparing Dockerfile
COPY ./alpaca-fr.csv tmp

# run script to finetune model using dataset
RUN python tmp/train_script.py

# export trained model to our VM for measurement and use
FROM scratch AS binaries
COPY --from=build tmp/model /
```

AI builders can use this example as a template by replacing the dependencies with those required for their own training script and changing the name of any datasets to be imported to those they exported in their previous Dockerfiles.

```python
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

# launch the training
trainer.train()

# save model to path defined in final Dockerfile command: COPY --from=build tmp/model /
torch.save(model.state_dict(), '/tmp/model/finetuned.pth')
```

All the files shown in this example are available in our [docs/resources/falcon-example folder](https://github.com/mithril-security/aicert/blob/readme/docs/resources/falcon-example) on our github.

### Step 2: Launching the traceable training

To launch the traceable training process and get back our AICert proof file, we can use the AICert CLI tool and run the `aicert` command.

We will ned to specify:
+ `input-source`: The dockerfile for the training of your model 
+ `dataset-source`: The dockerfile for the loading and preparing of your dataset(s)
+ `output-model`: File name for your trained model
+ `output-bom`: File name for your cryptographic proof file

```bash
aicert --input-source "./train/Dockerfile" --dataset-source "./data/Dockerfile" --output-model "falcon-finetuned.pth" --output-bom "falcon-finetune-proof.json"
```

Once the training process is over, we obtain a signed AI certificate, our `proof.json`, binding the hashes of the weights with the training code and data. 

It can now be shared with outside parties to prove to them the model comes from the use of the specified training code and data.

## End user POV: Verifying and inspecting the AI certificate

The end user can then use our Python SDK to:

+ Verifying the AI certificate is legitimate
+ Verifying the software stack of the VM used for training
+ Verifying the input model or dataset used for training

### Verification of the AI certificate and VM software stack

End users can verify the exported proof file is genuine and does contain any unexpected measurements by using the `verify()` method provided by the **AICert Python package** with no arguments.

```python
import aicert

# Load the AI certificate
cert = aicert.load("proof.json")

# Verify the validity of the certificate
cert.verify()
```

The `verify()` method checks two things:
+ The authenticity of the certificate's signature, allowing us to know that the proof file was created using a genuine secure hardware.
+ The validity of the hashed values of the whole software stack or boot chain of the VM used to train the dataset.

If the proof file contains a false signature or any false values an error will be raised! False hashed values could signal that the software stack of the VM used for training was misconfigured or even tampered with.

### Verification of the input model, dataset and training code

The `verify()` method also contains optional arguments where we can check the hash values of the dataset, input model and training code against hashes when they are known.

This is useful for open source models, datasets or training codes and allow us to have irrefutable proof that a certain model or dataset were used and not tampered with.

This can also be useful for closed sourced organizations wishing to make internal checks.

```python
ALPACA_DATASET = "4DE6702C739D8C9ED907F4C031FD0ABC54EE1BF372603A585E139730772CC0B8"
FALCON_MODEL = "A84571394B5E99FE70AAE39ECE25F844ACBAF83479E27F39A30732E092B19677"
TRAINING_CODE = "C2FB788C7DEEDBEAA296E424D4C2921B871A4F6CB4CF393C1C1105653AB399B4"

cert.verify(model=FALCON_MODEL, code=TRAINING_CODE, data=ALPACA_DATASET)
```

If any of these values do not match with the hash values of the input model, dataset or code used for training, an error will be returned to the user.

#### The proof file

We can equally find these hash values in our standardized final proof file file directly.

This file contains the hash values of the input model, training data, output model as well as the certificate signature and the hash of the low level quote which contains the hashes of the whole boot chain of the VM the model was trained on.

Here is an example of what your final proof file may look like:

```json
{
  "version": "v1",
  "inputs": [
    {
      "type": "dataset",
      "name": "wikipedia_dataset",
      "download_url": "http://huggingface.com/...",
      "hash": "0fab2467b..."
    },
    {
      "type": "input model",
      "name": "awesome_algo",
      "download_url": "http://github.com/...",
      "hash": "0fab2467b..."
    },
  ],
  "output_model_hash": "0fab2467b...",
  "platform_hash": "0fab2467b...",
  "signature": "0fab2467b...",
  "low_level_quote": "0fab2467b...",
}
```

## 💡 Technology Overview

### Trusted Platform Modules (TPMs)

+ TPMs are **specialized hardware chips** that exist on most modern laptops or computers that were designed to enhance security.

+ When we store data on a machine in RAM or on a hard drive, that memory can be accessed and manipulated by the system's OS. Data stored on TPMs, however, **cannot be manipulated or tampered with by the OS!**

+ TPMs have various use cases such as the **secure storage of secrets** and **attestation**.

+ A key capability of TPMs is that they can **create measurements of the state of a device**. They measure information relating to the firmware, bootloader, and OS and OS configuration of the device.


### Usage in AICert

In AICert, we use TPMs to perform attestation. We use TPMs **to measure the software stack, input and output model and training data**. This information forms a quote which is signed with an **attestation key (AK)** derived from the unique **forge-proof TPM Endorsement Key (EK)**. We then verify and use this quote to create our standardized cryptographic proof file.

Let's dive a bit deeper into the values included in the TPM quote used by AICert.

The quote includes is made up of the following hashed values, which are stored in a designated Platform Configuration Register (PCR). We have grouped some values together to make this more digest.

<img src="https://github.com/mithril-security/aicert/raw/readme/docs/assets/PCR-values.png" alt="TPM-quote-values" width="60%">

Each hash value generated is dependent on the previous hash, that is to say that it is a mix of the previous hashed value, plus the value of the new element being added to the quote.

#### How does verification work?

!!!TODO make this explanation accurate!

Let's imagine, we download GPT-J-6B. The model is open-source and reputed, but the version we have downloaded has been poisoned by malicious input data.

When we verify this model against the official GPT-J-6B model, AICert will compare the hash values of our malicious version against the original model.

!!!TODO GET COOL DIAGRAM/IMAGE FROM EDGAR TOMORROW

Because the input data was manipulated in order to poison the model, there will be a difference in our hash value for PCR15, which encompasses the model's training data, compared to the original model. The user will get an error back for our dedicated AICert verification tool and will be able to avoid using this malicious model and even be able to alert the platform provider.

This example shows how crucial a tool like AICert in verifying models and increasing the security posture of AI platforms.

<p align="right">(<a href="#readme-top">back to top</a>)</p>
<!-- CONTACT -->

## 🤝 Trust Model
!!!TODO write this section

!!!TODO Get Edgar to fix image

<img src="https://github.com/mithril-security/aicert/raw/readme/docs/assets/TCB.png" alt="TCB" width="70%">

## ⚠️ Limitations

While we provide traceability and ensure that a given set of weights comes from applying a specific training code on a specific dataset, there are still challenges to solve:

+ The training code and data have to be inspected. AICert does not audit the code or input data for threats, such as backdoors injected into a model. It will simply allow us to prove model provenance. It is up to the AI community or model builder to inspect or prove the trustworthiness of the code and data. 

+ AICert itself has to be inspected- all the way from the OS we choose to the HTTP server and the app we provide to run the code on the training data. 

We are aware that AICert is not a silver bullet, but we believe that by building this critical piece of infrastructure in the open, we will be able to provide enough scrutiny to ensure AI can be made trustworthy!

## 📇 Contact

[![Contact us][contact]][contact-url]
[![Twitter][twitter]][website-url]
[![LinkedIn][linkedin-shield]][linkedin-url]

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- MARKDOWN LINKS & IMAGES -->
<!-- https://github.com/alexandresanlim/Badges4-README.md-Profile#-blog- -->
<!-- [contributors-shield]: https://img.shields.io/github/contributors/mithril-security/aicert.svg?style=for-the-badge
[contributors-url]: https://github.com/mithril-security/aicert/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/mithril-security/aicert.svg?style=for-the-badge
[forks-url]: https://github.com/mithril-security/blindbox/network/members
[stars-shield]: https://img.shields.io/github/stars/mithril-security/aicert.svg?style=for-the-badge
[stars-url]: https://github.com/mithril-security/blindbox/stargazers
[issues-shield]: https://img.shields.io/github/issues/mithril-security/aicert.svg?style=for-the-badge
<!-- [issues-url]: https://github.com/mithril-security/aicert/issues -->
[project-url]: https://github.com/mithril-security/aicert
[twitter-url]: https://twitter.com/MithrilSecurity
[contact-url]: https://www.mithrilsecurity.io/contact
[license-shield]: https://img.shields.io/github/license/mithril-security/aicert.svg?style=for-the-badge
[contact]: https://img.shields.io/badge/Contact_us-000000?style=for-the-badge&colorB=555
[project]: https://img.shields.io/badge/Project-000000?style=for-the-badge&colorB=555
[license-url]: https://github.com/mithril-security/aicert/blob/master/LICENSE.txt
[linkedin-shield]: https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white&colorB=555
[twitter]: https://img.shields.io/badge/Twitter-1DA1F2?style=for-the-badge&logo=twitter&logoColor=white
[linkedin-url]: https://www.linkedin.com/company/mithril-security-company/
[website-url]: https://www.mithrilsecurity.io
[website-shield]: https://img.shields.io/badge/website-000000?style=for-the-badge&colorB=555
[blog-url]: https://blog.mithrilsecurity.io/
[blog-shield]: https://img.shields.io/badge/Blog-000?style=for-the-badge&logo=ghost&logoColor=yellow&colorB=555
[product-screenshot]: images/screenshot.png
[Python]: https://img.shields.io/badge/Python-FFD43B?style=for-the-badge&logo=python&logoColor=blue
[Python-url]: https://www.python.org/
[Rust]: https://img.shields.io/badge/rust-FFD43B?style=for-the-badge&logo=rust&logoColor=black
[Rust-url]: https://www.rust-lang.org/fr
[Intel-SGX]: https://img.shields.io/badge/SGX-FFD43B?style=for-the-badge&logo=intel&logoColor=black
[Intel-sgx-url]: https://www.intel.fr/content/www/fr/fr/architecture-and-technology/software-guard-extensions.html
[Tract]: https://img.shields.io/badge/Tract-FFD43B?style=for-the-badge
<!-- [tract-url]: https://github.com/mithril-security/tract/tree/6e4620659837eebeaba40ab3eeda67d33a99c7cf -->
<!-- Done using https://github.com/othneildrew/Best-README-Template -->
