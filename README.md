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
    <li><a href="#-limitations">Limitations</a></li>
    <li><a href="#-contact">Contact</a></li>
  </ol>
</details>

## 🔒 About The Project

🛠️ **AICert** aims to make AI **traceable** and **transparent** by enabling **AI builders** to create certificates with **cryptographic proofs binding the weights to the training data and code**. AI builders can be foundational model providers or companies that finetune the foundational models to their needs.

👩‍💻 **End users** are the final consumers of the AI builders’ models. They can then verify these AI certificates to have proof that the model they talk to comes from a specific training set and code, and therefore **alleviates copyright, security and safety issues**.

</br>

<img align="left" src="https://github.com/mithril-security/aicert/blob/readme/docs/assets/TPM.png?raw=true" width="110" alt="TPM"> We leverage **Trusted Platform Modules (TPMs)** in order to attest the whole stack used for producing the model, from the UEFI, all the way to the code and data, through the OS. 

Measuring the software stack, training code and inputs and binding them to the final weights allows the derivation of certificates that contain **irrefutable proof of model provenance**.


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
+ **Flexible training:** use your preferred tooling for training
+ **No slowdown** induced during training
+ **Azure support**

#### 🎯 Coming soon
+ **Benchmark linking:** provide cryptographic binding of model weights to specific benchmarks that were run for this specific model
+ **Multi-Cloud support** with AWS and GCP coverage
+ **Single and multi-GPU support**
<p align="right">(<a href="#readme-top">back to top</a>)</p>

## 🚀 Getting started

- Check out our [“Getting started guide”](https://aicert.readthedocs.io/en/latest/docs/getting-started/get-started/), which will walk you through an example!
- [Discover](https://aicert.readthedocs.io/en/latest/docs/getting-started/attestation/) how we bind model weights to training inputs and code
- [Learn more](https://aicert.readthedocs.io/en/latest/docs/getting-started/tech-overview/) about the AICert architecture & workflow

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## ⚠️ Limitations

While we provide traceability and ensure that a given set of weights comes from applying a specific training code on a specific dataset, there are still challenges to solve:

+ The training code and data have to be inspected. AICert does not audit the code or input data for threats, such as backdoors injected into a model by the code or poisonous data. It will simply allow us to prove model provenance. It is up to the AI community or end-user to inspect or prove the trustworthiness of the code and data. 
+ AICert itself has to be inspected, all the way from the OS we choose to the HTTP server and the app we provide to run the code on the training data.

We are well aware that AICert is not a silver bullet, as to have a fully trustworthy process, it requires scrutiny of both our code and the code and data of the AI builder.

However, by combining both, we can have a solid foundation for the AI supply chain.

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
