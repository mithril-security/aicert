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


### ✅ Use cases

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


## Workflow:
<img align="center" src="https://github.com/mithril-security/aicert/blob/main/docs/assets/aicert-axolotl.png?raw=true" alt="Workflow">


## Prerequisites
To run this example, you will need acess to an Azure subscription with quota for VMs with GPUs.
Install terraform and az cli. The client code requires python 3.11 or later.
```console
# qemu-utils to resize disk to conform to azure disk specifications
sudo apt-get update && sudo apt-get install qemu-utils tpm2-tools pesign jq
# Azure CLI
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
# azcopy to copy disk to azure 
https://aka.ms/downloadazcopy-v10-linux
# Install python 3.11
sudo apt-get install python3.11
# Install terraform
wget -O- https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt update && sudo apt install terraform
# Install earthly
sudo /bin/sh -c 'wget https://github.com/earthly/earthly/releases/latest/download/earthly-linux-amd64 -O /usr/local/bin/earthly && chmod +x /usr/local/bin/earthly && /usr/local/bin/earthly bootstrap --with-autocomplete'
# Install poetry
curl -sSL https://install.python-poetry.org | python3 -
```

## 1 - Configuration
We must first configure the Azure region and resource names before we begin creating the Mithril OS image.

The resource group name, gallery name and region can be set in the [upload_config.sh](upload_config.sh)
```console
AZ_RESOURCE_GROUP="your-resource-group"
AZ_REGION="your-region"
GALLERY_NAME="your-gallery-name"
```

The size of the Azure VM can be set in [variables.tf](client/aicert/cli/deployment/deploy/variables.tf)
```console
variable "instance_type" {
  type        = string
  default     = "Standard_NC24ads_A100_v4"
  description = "Type/Size of VM to create."
}
```
The default size is Standard_NC24ads_A100_v4

## 2 - Preparing the image
AIcert finetunes models inside Mithril OS enclaves.
The OS image packages the server, reverse proxy and axolotl container images within it.

To make subsequent finetunes easier, the OS disk only needs to be built once and uploaded to Azure.

The "create_MithrilOS.sh" script creates the disk, uploads it to Azure, and converts it into an OS image. It also generates the OS measurements.
```console
# log in to Azure CLI
az login

# Create OS image
sudo ./create_MithrilOS.sh
```

## 3 - Install the client
```console
cd client
# If your default python is below python3.10
poetry env use python3.11
poetry shell
poetry install
```

## 4 - Finetune a model
AIcert pefroms the following functions when the finetune command is run:
- Creates a VM with the Mithril OS image
- Connects to the server VM using aTLS
- Sends the axolotl configuration in the aicert.yaml
- Waits for the finetuned model and attestation report to be returned
```console
cd axolotl_yaml
# There is a sample axolotl configuration present in this folder named aicert.yaml
# This specifies the model, dataset, and training parameters
aicert finetune
```

## 5 - Network policy

While the network policy is part of the OS image, it is interesting to explore it further, as it is important for security and privacy. 

The network policy that will be used will be included in the measurement of the OS. For instance, we will use the following one to allow data to be loaded inside the enclave, but nothing will leave it except the output of the AI model that will be sent back to the requester.

The network policy file can be found in the annex.

The measurement file contains the PCR values of the OS. A sample measurement file is as follows:
```json
{
    "measurements": {
        "0": "f3a7e99a5f819a034386bce753a48a73cfdaa0bea0ecfc124bedbf5a8c4799be",
        "1": "3d458cfe55cc03ea1f443f1562beec8df51c75e14a9fcf9a7234a13f198e7969",
        "2": "3d458cfe55cc03ea1f443f1562beec8df51c75e14a9fcf9a7234a13f198e7969",
        "3": "3d458cfe55cc03ea1f443f1562beec8df51c75e14a9fcf9a7234a13f198e7969",
        "4": "dd2ccfebe24db4c43ed6913d3cbd7f700395a88679d3bb3519ab6bace1d064c0",
        "12": "0000000000000000000000000000000000000000000000000000000000000000",
        "13": "0000000000000000000000000000000000000000000000000000000000000000"
    }
}
```

To understand better what it means, each PCR measures different parts of the stack:
PCRs  0, 1, 2, and 3 are firmware related measurements.
PCR 4 measures the UKI (initrd, kernel image, and boot stub)
PCR 12 and 13 measure the kernel command line and system extensions. We do not want any of those to be enabled, so we ensure they are 0s.


## Annex - Information on network Policy and Isolation
The network policy is implemented individually for the k3s pods as well as for the host.
The host network is controlled by iptables rules. The exact rules are:
```
*filter
# Allow localhost connections to permit communication between k3s components
-A INPUT -p tcp -s localhost -d localhost -j ACCEPT
-A OUTPUT -p tcp -s localhost -d localhost -j ACCEPT
# Allow connection to Azure IMDS to get the VM Instance userdata
-A INPUT -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT
-A OUTPUT -p tcp -d 169.254.169.254 --dport 80 -j ACCEPT
-A OUTPUT -p tcp -d 168.63.129.16 --dport 80 -j ACCEPT
# DNS over UDP
-A INPUT -p udp --sport 53 -j ACCEPT
-A INPUT -p udp --dport 53 -j ACCEPT
-A OUTPUT -p udp --sport 53 -j ACCEPT
-A OUTPUT -p udp --dport 53 -j ACCEPT
# DNS over TCP
-A INPUT -p tcp --sport 53 -j ACCEPT
-A INPUT -p tcp --dport 53 -j ACCEPT
-A OUTPUT -p tcp --sport 53 -j ACCEPT
-A OUTPUT -p tcp --dport 53 -j ACCEPT
# Drop all other traffic
-A OUTPUT -j DROP
-A INPUT -j DROP
COMMIT
```
In the repository they can be found in [rules.v4](mithril-os/mkosi/rootfs/mkosi.extra/etc/iptables/rules.v4) and [rules.v6](mithril-os/mkosi/rootfs/mkosi.extra/etc/iptables/rules.v6)

These rules block all incoming and outgoing traffic except for DNS queries and localhost connections. The rules are applied on boot by the iptables-persistent package. You can verify that the package is installed if you take a look at the [mkosi.conf](mithril-os/mkosi/rootfs/mkosi.conf.j2) file.

When the client tries to connect to the server it first retrieves the attestation report which is a quote from the TPM. The client uses the measurements stored in the `security_config` to validate the quote received from the TPM. 

If there are any changes in the host networking rules, it will reflect in the PCR values (PCR 4) of the OS measurement and the connection will be terminated.

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
