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
[![LinkedIn][linkedin-shield]][linkedin-url]
</div>

  <!-- <p align="center">
    <b>Quickly deploy your SaaS solutions while preserving your users' data privacy.
	<br /><br />
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
    <li><a href="#-technology-overview">Technology Overview</a></li>
    <li><a href="#-contact">Contact</a></li>
  </ol>
</details>
<!-- ABOUT THE PROJECT -->

## 🔒 About The Project

**AICert** aims to make AI **traceable** and **transparent** and provide **input and output integrity for AI models**. By leveraging **Trusted Platform Modules (TPMs)**, we are able to **verify** the identity of models, training data and the machines they were trained on. This means users can **verify** they are using an authentic model that has not been tampered with. By measuring the training data used by models, **AICert** also allows us to safeguard against the threat of model poisoning. AICert addresses some of the most urgent concerns related to **privacy, security, and compliance** surrounding AI.

| ⚠️ **WARNING:** AICert is still under development. **Do not use in production!** |
| --- |

## 🔍 Why use AICert?

+ **AI model traceability:** create AI model ID cards that provide cryptographic proof binding model weights to a specific training set and code.
+ **Non-forgeable proofs:** leverage TPMs to ensure non-forgeable AI model ID cards.
+ **Flexible training:** use your preferred tooling for training- the only requirement is that it can be packaged into a Docker image.
+ **Easy to install and use**

> You can check out [the project code on our GitHub](https://github.com/mithril-security/aicert/).

<p align="right">(<a href="#readme-top">back to top</a>)</p>

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

Mithril Security - [@MithrilSecurity](https://twitter.com/MithrilSecurity) - contact@mithrilsecurity.io

Project Link: [https://github.com/mithril-security/aicert](https://github.com/mithril-security/aicert)

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
[license-shield]: https://img.shields.io/github/license/mithril-security/aicert.svg?style=for-the-badge
[license-url]: https://github.com/mithril-security/aicert/blob/master/LICENSE.txt
[linkedin-shield]: https://img.shields.io/badge/-Jobs-black.svg?style=for-the-badge&logo=linkedin&colorB=555
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
