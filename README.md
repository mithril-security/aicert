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
    <li><a href="#-about-the-project">About the project</a></li>
    <li><a href="#-getting-started">Getting started</a></li>
    <li><a href="#-technology-overview">Technology Overview</a></li>
    <li><a href="#-trust-model">Trust Model</a></li>
    <li><a href="#-limitations">Technology Overview</a></li>
    <li><a href="#-contact">Contact</a></li>
  </ol>
</details>

## 🔒 About The Project

**AICert** aims to make AI **traceable** and **transparent** by enabling **AI builders** to create certificates with **cryptographic proofs binding the weights to the training data and code**. AI builders can be foundational model providers or companies that finetune the foundational models to their needs.

**End users** are the final consumers of the AI builders’ models. They can then verify these AI certificates to have proof that the model they talk to comes from a specific training set and code, and therefore **alleviates copyright, security and safety issues**.

We leverage **Trusted Platform Modules (TPMs)** in order to attest the whole stack used for producing the model, from the UEFI, all the way to the code and data, through the OS. Measuring the whole hardware/software stack and binding the final weights produced (by registering them in the last PCR) allows the derivation of certificates that contain **irrefutable proof of model provenance**.

### Use cases

AICert addresses some of the most urgent concerns related to **AI provenance**. It allows AI builders to:

+ Prove their AI model was not trained on copyrighted, biased or non-consensual PII data
+ Provide an AI Bill of Material about the data and code used, which makes it harder to poison the model by injecting backdoors in the weights
+ Provide a strong audit trail with irrefutable proof for compliance and transparency

  ⚠️ **WARNING:** AICert is still under development. Do not use it in production!
  If you want to contribute to this project, do not hesitate to raise an issue.

### 🔍 Features

+ **AI model traceability:** create AI model ID cards that provide cryptographic proof binding model weights to a specific training set and code
+ **Non-forgeable proofs:** leverage TPMs to ensure non-forgeable AI model ID cards
+ **Flexible training:** use your preferred tooling for training- the only requirement is that it can be packaged into a Docker image
+ **No slowdown** induced during training
+ **Azure support**

**Coming soon:**
+ **Benchmark linking:** provide cryptographic binding of model weights to specific benchmarks that were run for this specific model
+ **Multi-Cloud support** with AWS and GCP coverage
+ **Single and multi-GPU support**


<p align="right">(<a href="#readme-top">back to top</a>)</p>

## 📜 Getting started

To get started, we will walk you through the steps needed to configure and launch AICert using an example where we finetune a Falcon 7B model with proof that the model was derived from the pre-trained model, code, and data that we specified.

The end-user can then use our client SDK to verify that the AICert proof file is genuine and verify the inputs used (pre-trained model, dataset, and code) to produce our model.

> All the files shown in this example are available [on Github](https://github.com/mithril-security/AICert-example).

**The workflow is as follows:**

<img src="https://github.com/mithril-security/aicert/raw/readme/docs/assets/workflow.png" alt="workflow">


**AI builder POV:**

+ The AI builder prepares **a GitHub or HuggingFace source repository** containing their training script and input files (alternatively, input files can also be added as **resources** in the config file)
+ The AI builder modifies the config yaml file, for example, to specify their project repo link
+ The AI builder launches AICert using the CLI tool

**Under the hood:**
+ AICert provisions a VM with the required hardware/software stack
+ AICert executes the training entry script as specified in the AICert config file
+ AICert returns the scripts outputs, along with a cryptographic proof file with measurements relating to the software stack, the training code and inputs used and the training outputs (e.g. the trained model)

**End-user POV:**
+ The end user can verify this certificate and all the elements used to create the trained model (where they have access to the original data)

Let’s now take a look at the steps that the AI builder and end users must follow in more detail.

### AI builder POV: creating an AI model certificate

### Step 1: Preparing project source repository

You will need to place all the files needed to train your model into one repository, hosted either by GitHub or Hugging Face. This can be a private or public repository.

**This repository should include:**
+ A requirements.txt file with all dependencies needed
+ A script file (main.py by default) which will be executed by AICert
+ The inputs required to complete training, such as the dataset or the base model will be fine-tuned. These can alternatively be downloaded from a URL specified in the AICert config file.

**The GitHub repo file structure for our example is as follows:**

```bash
AICert-example/
├─ inputs/
│  ├─ alpaca-fr.csv
├─ src/
│  ├─ main.py
├─ .gitignore
├─ README.md
```

**The requirements for your script file are as follows:**
+ Your requirements.txt file should be in the root of your GitHub repository.
+ When your main.py script is executed at runtime, the contents of your GitHub repo provided as a source in the AICert config file will be accessible in the /workspace/src folder. You should therefore modify any paths in your scripts accordingly.
```python
# load dataset from location specified in AICert config
dataset = load_dataset('csv', data_files='workspace/src/inputs/alpaca-fr.csv')
dataset = dataset['train'].select(range(number_elements_for_training))
```

+ Any input files provided as resources in the config file, outside of your main GitHub repo, will be accessible in the /workspace/resources folder at runtime.
+ Your script must save any output artifacts, such as your trained model, to the specified outputs folder, which is /workspace/outputs by default. AICert will then include them in the proof file and return them to you.
```python
# launch the training
trainer.train()

# Save model in location specified in AICert config
torch.save(model.state_dict(), '/workspace/outputs/finetuned.pth')
```

+ Your script must not download any external input files as we cannot reliably attest resources downloaded in this way. These inputs should be provided in the project repository or as URLs in the AICert config file and loaded from the workspace.

AICert records:
+ A SHA1 hash of any GitHub repo commits listed in the AICert config file
+ A SHA256 hash of any additional inputs listed in the AICert config file

#### Step 2: Modifying the AICert config file

Before launching AICert, the AI builder will need to modify the template AICert config file.

This file allows you to specify:

+ The base Docker image which AICert will use when launching the training
+ The commands to be executed in this environment
+ The inputs that will be required for your program (e.g. datasets) and their locations within the workspace
+ The location of any outputs

In our example, all the files we need to launch our finetuning program are contained within our GitHub repository, so we will add this to our inputs section. Otherwise, we leave all other options with their default values.

```yaml
kind: python 

pythonVersion: 11
# available at /workspace/src/
source: 
type: git 
gitRepo: "https://github.com/mithril-security/AICert-example" 	 
# tag: "v0.0.1" 
# branch: "mybranch"
# requirements.txt should be at root of this repo
pythonEntryPoint: "src/main.py" 

# Resources are downloaded in /workspace/resources 
# Resources are inputs that are measured resources: 
# type: file
# path still relative to /workspace/resources
# destinationPath: "input_weight.parquet" 			
# will create a file at /workspace/resources/input_weight.parquet 	 
# url: "https://huggingface.co/datasets/Open-Orca/OpenOrca/resolve/main/3_5M-GPT3_5-Augmented.parquet"
```

We will provide full details on all the AICert config file options in a tutorial **coming soon**!

### Step 3: Launching the traceable training

Finally, to launch the traceable training process and get back our AI certificate, we can use the AICert CLI tool and run the `aicert` command.

**We will need to specify:**
+ `output-bom`: File name for your cryptographic proof file

```bash
aicert --output-bom "falcon-finetuned-proof.json"
```

Once the training process is over, we obtain a signed AI certificate, our `falcon-finetuned-proof.json`, which binds the hashes of the weights with the training code and dataset used, as well as the software stack of the VM used for training. 

This proof file can now be shared with outside parties to prove to them the model comes from using the specified training code and data.

## End user POV: Verifying and inspecting the AI certificate

The end user can then use our Python SDK to:

+ Verify that the AICert proof file is legitimate
+ Verify the software stack of the VM used for training
+ Verify the inputs used for training against known hash values

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
+ The authenticity of the certificate's signature, allowing us to know that the proof file was created using genuine secure hardware.
+ The validity of the hashed values of the whole software stack or boot chain of the VM used to train the dataset. This ensures that the certification process is valid and not compromised. It does not attest that the script and data are trustworthy. Those have to be audited independently. However, if the certification process is valid, the AI builder can now be held accountable- if they use, for instance, poisoned data to train the model, this can be verified `a posteriori``. 

If the proof file contains a false signature or any false values, an error will be raised. False hashed values could signal that the software stack of the VM used for training was misconfigured or even tampered with.

If the `verify()`` method passes, it means that the AI certificate is genuine. However, the dataset and training code have to be verified themselves too.

#### The proof file

We can also use the proof file to manually check the hashed values of the model's inputs or output hash against known values.

For example, for our example repository, we would get a proof file back like this:

```json
{
  "version": "v1",
  "inputs": [
    {
      "type": "inputs",
      "name": "AICert-example",
      "download_url": "http://github.com/mithril-security/AICert-example",
      "hash": "0fab2467b..."
    }
  ],
  "output_model_hash": "0fab2467b...",
  "platform_hash": "0fab2467b...",
  "signature": "0fab2467b...",
  "low_level_quote": "0fab2467b...",
}
```

This contains the SHA1 hash of our GitHub repository commit provided in the AICert config file, which contains our finetuning code and dataset. The end user could then check this against the SHA1 hash value of the official GitHub repository.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Technology overview

TPMs are at the core of AICert, enabling us to cryptographically bind a model’s weights to its training code and data, as well as the software stack of the machine it was trained on.

In this section, we will cover:
+ How TPMs work
+ How we leverage them in AICert
+ The hardware/software stack we provide with AICert

### Trusted Platform Modules (TPMs)

#### Overview

[Trusted Platform Modules](https://en.wikipedia.org/wiki/Trusted_Platform_Module) (TPMs) can be used to ensure the integrity of a whole software supply chain. Such devices have the property of being able to attest the whole stack used for producing the model, from the UEFI, all the way to the code and data, through the OS.

The TPM PCRs (Platform Configuration Registers) are a set of registers within the TPM that store measurements of system configuration and integrity. They can be considered a log of the system state, capturing the integrity of various components during the boot process and other critical stages. The PCRs are typically used to attest to the integrity of a system or to verify that the system has not been tampered with.

When a system boots, various measurements are taken, such as hashes of firmware, boot loaders, and critical system files. These measurements are then stored in the TPM PCRs. The values stored in the PCRs can then be compared against known values.

We can request a signed quote from the TPM which contains these PCR values and is signed by the TPM's Attestation Key (AK), which is derived from a tamper-proof TPM Endorsement Key (EK), and thus cannot be falsified by a third party.

Measuring the whole software stack and binding the inputs used in the training process and the final weights produced (by registering them to the last two PCRs) allows the derivation of certificates that contain irrefutable proof of model provenance. 

#### Usage in AICert

To see how it works in practice, let’s see how AICert uses TPMs to prove a specific code and data were loaded, and how they were used to produce a specific model.

<img src="https://github.com/mithril-security/aicert/raw/readme/docs/assets/proof-file.png" alt="AICert proof file">

**Software stack**

We provide a base image containing all software elements up to the server application that will execute the code on the training data. This base image is fixed and can be publicly audited.

At the boot stage, the stack is loaded piece by piece, starting with the UEFI. The TPM will measure and store each of these elements in their corresponding PCR. 

**Inputs**

We then download the project repository and any resources as specified in the AICert config file. These inputs are hashed and stored in PCR14.

**Outputs**

After performing training, we hash the outputs and store these hashes in PCR15.

<img src="https://github.com/mithril-security/aicert/raw/readme/docs/assets/PCR-values.png" alt="PCR values" width="40%">

AICert will then request a “quote”, containing all these measurements, which is signed by a hardware-derived key verified by the Cloud provider.

#### Verification

<img src="https://github.com/mithril-security/aicert/raw/readme/docs/assets/verication-cropped.png" alt="verification" width="40%">

When end users use the `verify()` method provided in our AICert Python library, AICert will check the values of each PCR in our AICert proof file against known values. This allows us to verify the full software stack used by AICert.

However, the hashes in PCR14 and PCR15 are not known values to AICert, so end users should verify these manually by comparing the values in our AICert proof file against known SHA256 (for GitHub commits) or SHA1 hashes (for other input files) for the input data.

#### AICert Architecture

<img src="https://github.com/mithril-security/aicert/raw/readme/docs/assets/toolkit.png" alt="AICert toolkit" width="40%">

AICert is composed of the following elements:
+ **Base image** containing our selected OS for reproducibility
+ **Server** on top that takes inputs specified in the AICert config file, applies the algorithm to the data and uses TPM primitives to create a certificate
+ **CLI tool** to provision the VM with our predefined hardware/software stack, launches AI builder’s program and returns outputs and proof files to them
+ **Client-side Python SDK** to verify and inspect AI certificates

#### Workflow of AICert

When the AI builder launches the `aicert` CLI command. Under the hood, AICert will:

+ Provision a VM with the correct hardware/software stack, PCR registers 0-13 will be updated at boot time
+ Hash input values and register them to PCR14
+ Build a container with all the necessary inputs
+ Execute main.py code or alternative entrypoint command
+ Hash outputs and register them to PCR15
+ Request a signed quote from the Cloud provider containing all PCR values
+ Standardize quote details and return AI certificate to the end user

When the end user verifies the certificate, AICert will:
+ Verify the certificate comes from a genuine TPM and that the expected software stack has indeed been loaded, all the way up to our server.

The end user can then inspect input and output hashes manually.

> Note that AICert can only certify that a specific piece of code was executed on some data. The content of the code and data itself have to be verified independently.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Trust model

### Overview

<img src="https://github.com/mithril-security/aicert/raw/readme/docs/assets/trust-model.png" alt="AICert trust model">

AICert makes it easy for AI builders to spin a machine with the right hardware/software stack by leveraging Cloud infrastructure (e.g. Azure). We will therefore include the Cloud provider in the Trust Model here. 

Therefore, there are three parties present:
+ The **AI builder** who is responsible for the training code and data
+ **AICert**, which is responsible for the server-side tooling, including the base OS image, the server to launch the training code and client SDK to verify those elements
+ The **Cloud provider** who is responsible for administrating the machines and providing the virtual TPM

In the current climate, there is blind trust in the AI builder. If they are compromised, malicious backdoors can be inserted into their models, and there is no way for end users to verify the AI models they provide.

With AICert, we can remove this need for blind trust in the AI builder, as now there is a cryptographic binding between the weights and the data and code, using the PCR values requested by our server.

We should however trust that AICert does not contain backdoors, either in the base OS we provide, the HTTP server in charge of running user scripts in containers and registering the PCR values, and the client-side SDK in charge of the verification. AICert is open-source and should be inspected by the community.

The Cloud provider who operates the platform is trusted.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Limitations

While we provide traceability and ensure that a given set of weights comes from applying a specific training code on a specific dataset, there are still challenges to solve:

+ The training code and data have to be inspected. AICert does not audit the code or input data for threats, such as backdoors injected into a model by the code or poisonous data. It will simply allow us to prove model provenance. It is up to the AI community or end-user to inspect or prove the trustworthiness of the code and data. 
+ AICert itself has to be inspected, all the way from the OS we choose to the HTTP server and the app we provide to run the code on the training data.

We are well aware that AICert is not a silver bullet, as to have a fully trustworthy process, it requires scrutiny of both our code and the code and data of the AI builder.

However, by combining both, one can have a solid foundation for the AI supply chain.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

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
