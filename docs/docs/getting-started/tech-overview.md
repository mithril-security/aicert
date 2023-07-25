# 📜 AICert tech overview
________________________________________________________

## 🧰 AICert Architecture
________________________________________________________

![toolkit](https://github.com/mithril-security/aicert/blob/readme/docs/assets/toolkit.png?raw=true)

AICert is composed of the following elements:

+ **Base image** containing our selected OS for reproducibility
+ **Server** on top that takes inputs specified in the AICert config file, applies the algorithm to the data and uses TPM primitives to create a certificate
+ **CLI tool** to provision the VM with our predefined hardware/software stack, launches AI builder’s program and returns outputs and proof files to them
+ **Client-side Python SDK** to verify and inspect AI certificates

## ➡️ Workflow of AICert
________________________________________________________

![under-the-hood](../../assets/under-the-hood.png)

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

## 🛡️ Trust model
________________________________________________________

### Overview

![trust-model](../../assets/trust-model.png)

AICert makes it easy for AI builders to spin a machine with the right hardware/software stack by leveraging Cloud infrastructure (e.g. Azure). We will therefore include the Cloud provider in the Trust Model here. 

Therefore, there are three parties present:
+ The **AI builder** who is responsible for the training code and data
+ **AICert**, which is responsible for the server-side tooling, including the base OS image, the server to launch the training code and client SDK to verify those elements
+ The **Cloud provider** who is responsible for administrating the machines and providing the virtual TPM

In the current climate, there is blind trust in the AI builder. If they are compromised, malicious backdoors can be inserted into their models, and there is no way for end users to verify the AI models they provide.

With AICert, we can remove this need for blind trust in the AI builder, as now there is a cryptographic binding between the weights and the data and code, using the PCR values requested by our server.

We should however trust that AICert does not contain backdoors, either in the base OS we provide, the HTTP server in charge of running user scripts in containers and registering the PCR values, and the client-side SDK in charge of the verification. AICert is open-source and should be inspected by the community.

The Cloud provider who operates the platform is trusted.