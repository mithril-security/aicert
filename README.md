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
    <b>Making AI Traceable and Transparent<br /><br />
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
    <li><a href="#-usage">Usage</a></li>
    <li><a href="#-technology-overview">Technology Overview</a></li>
    <li><a href="#-contact">Contact</a></li>
  </ol>
</details>

## 🔒 About The Project

**AICert** aims to make AI **traceable** and **transparent** by enabling **AI Vendors** to create **cryptographic proofs** relating to their models and the data they have been trained with. **End users** can then use these proofs to **verify they are using authentic models** that have not been tampered with.

We leverage **Trusted Platform Modules (TPMs)** in order to measure models, their training data and the machines they were trained on. We bind these measures into a single cryptographic proof file.

AICert addresses some of the most urgent concerns related to **privacy, security, and compliance** surrounding AI, enabling AI vendors to:

+ Prove AI model provenance
+ Keep a traceable record of the model training process
+ Safeguard against the threat of model poisoning
+ Achieve compliance and improve security posture

| ⚠️ **WARNING:** AICert is still under development. **Do not use in production!** |
| --- |

## 🔍 Why use AICert?

+ **AI model traceability:** create AI model ID cards that provide cryptographic proof binding model weights to a specific training set and code
+ **Non-forgeable proofs:** leverage TPMs to ensure non-forgeable AI model ID cards
+ **Flexible training:** use your preferred tooling for training- the only requirement is that it can be packaged into a Docker image
+ **Easy to install and use**

> You can check out [the project code on our GitHub](https://github.com/mithril-security/aicert/).

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## 📜 Usage

### How to create an AICert proof file during model training

![AICert workflow](https://github.com/mithril-security/aicert/blob/readme/assets/aicert-workflow.png?raw=true)

To start the secure training process, you need to provide the docker image you intend to use for the training of your model and the training dataset. You can also specify the names you wish your output model and cryptographic proof file to have.

```bash
aicert --input-container "santacoder_training:v1" --dataset-source "data/train.csv" --output-model "santacoder.pth" --output-bom "proof.json"
```

AICert will then create a VM that will be used for the training process. 

> Note, the training process might take a while, depending on your input model and the training dataset. 

During the training process, AICert will store the hashes of the 'software bill of materials'. This includes:
+ The user dataset
+ The input model
+ The output model
+ The engine used for the training

These hashes are signed using the TPM's Attestation Key (AK), which is derived from a tamper-proof TPM Endorsement Key (EK). 

This data is also stored inside the TPM. 

Once the training process is over, the signed hashes will be stored inside a cryptographic proof file, and the trained model is then exported, ready to be used.

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

+ TPMs are **specialized hardware chips** that exist on most modern laptop or computers that were designed to enhance security.

+ When we store data on a machine in RAM or on a hardrive, that memory can be accessed and manipulated by the system's OS. Data stored on TPMs, however, **cannot be manipulated ot tampered with by the OS!**

+ TPMS have various use cases such as the **secure storage of secrets** and **attesation**.

+ A key capability of TPMs is that they can **create measurements of the state of a device**. They can measure information relating to the firmware, bootloader and OS and OS confugration of the device.


### Usage in AICert

In AICert, we use TPMs to:

- **Measure the script used to create a model and dataset** used to train the model and use this information to create a **robust AI model ID card**.
- **Sign a model** with an **attestation key (AK)** derived from the unique **forge-proof TPM Endorsement Key (EK)**. 
- **Measure the identity of the machine** a model was created on.

<p align="right">(<a href="#readme-top">back to top</a>)</p>
<!-- CONTACT -->

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
