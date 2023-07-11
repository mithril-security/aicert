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
    <li><a href="#-roadmap">Where are we on our roadmap?</a></li>
    <li><a href="#-usage">Usage</a></li>
    <li><a href="#-technology-overview">Technology Overview</a></li>
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

| ⚠️ **WARNING:** AICert is still under development.
    We are currently building a POC of AICert. This initial version will not include the full hardware-based verification features that we will introduce in the full release and **should not be used in production!** 
|
| --- |

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

## 📜 Usage

### How to create an AICert proof file during model training

To start the secure training process, you will need to specify the:
+ `input-container`: The docker image containing the application for the training of your model 
+ `dataset-source`: The training dataset
+ `output-model`: File name for your trained model
+ `output-bom`: File name for your cryptographic proof file

```bash
aicert --input-container "santacoder_training:v1" --dataset-source "data/train.csv" --output-model "santacoder.pth" --output-bom "proof.json"
```

This will trigger the following automated workflow:

![AICert workflow](https://github.com/mithril-security/aicert/blob/readme/assets/aicert-workflow.png?raw=true)

1. AICert will create the VM that will be used for the training process. 

> Note, the training process might take a while, depending on your input model and the training dataset. 

2. AICert will then create the hashes of the _software bill of materials_. This includes:
+ The user dataset
+ The input model and training data
+ The output model
+ The engine used for the training

These hashes are signed using the TPM's Attestation Key (AK), which is derived from a tamper-proof TPM Endorsement Key (EK). This data is also stored inside the TPM.

3. The training process is then executed.

4. Once the training process is over, the signed hashes will be stored inside a standardized cryptographic proof file, and the trained model is exported, ready to be used.

#### The proof file

The standardized final proof file is a JSON file containing the hash values of the input model, training data, output model as well as information relating to the machine the model was trained on.

Here is an example of what your final proof file may look like:

```json
{
  "version": "v1",
  "inputs": [
    {
      "type": "data",
      "name": "wikipedia_dataset",
      "download_url": "http://huggingface.com/...",
      "hash": "0fab2467b..."
    },
    {
      "type": "code",
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

### How to verify the integrity of an AICert cryptographic proof file

You can verify at any time the exported proof file to make sure the proof file is genuine, using the `verify() method` provided by AICert

```python
import aicert.

# Verify the validity of the data within the proof file
aicert.verify("proof.json") 
```

AICert is able to verify that each data value is genuine by matching it against the TPM that was used for the validation. 

⚠️ An error will be raised if the cryptographic proof is invalid or does not match the data available on the TPM!

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

![TPM-quote-values](./assets/PCR-values.png)

Each hash value generated is dependent on the previous hash, that is to say that it is a mix of the previous hashed value, plus the value of the new element being added to the quote.

#### So how does verification work?

!!!TODO make this explanation accurate!

Let's imagine, we download GPT-J-6B. The model is open-source and reputed, but the version we have downloaded has been poisoned by malicious input data.

When we verify this model against the official GPT-J-6B model, AICert will compare the hash values of our malicious version against the original model.

!!!TODO GET COOL DIAGRAM/IMAGE FROM EDGAR TOMORROW

Because the input data was manipulated in order to poison the model, there will be a difference in our hash value for PCR15, which encompasses the model's training data, compared to the original model. The user will get an error back for our dedicated AICert verification tool and will be able to avoid using this malicious model and even be able to alert the platform provider.

This example shows how crucial a tool like AICert in verifying models and increasing the security posture of AI platforms.

<p align="right">(<a href="#readme-top">back to top</a>)</p>
<!-- CONTACT -->

## Trust model
!!!TODO write this section

![TCB](./assets/TCB.png)

## Limitations
!!!TODO write this section


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
