---
description: "Learn more about the architecture, workflow and trust model of AICert"
---

# 📜 AICert tech overview
________________________________________________________

## 🧰 AICert Architecture
________________________________________________________

![toolkit-dark](../../assets/toolkit-dark.png#only-dark)
![toolkit-light](../../assets/toolkit.png#only-light)
</br></br>

AICert is composed of the following elements:

+ **Base image**  containing our selected OS for reproducibility
+ **The Server**, which is responsible for running training and creating our cryptographic proof file
+ **CLI tool**, which enables AI builders to supply model inputs, launch training and receive proof file
+ **Client-side Python SDK** to verify and inspect AI certificates


## ➡️ Workflow of AICert
________________________________________________________

![under-the-hood-dark](../../assets/under-the-hood-dark.png#only-dark)
![under-the-hood-light](../../assets/under-the-hood-light.png#only-light)
</br>


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

AICert makes it easy for AI builders to spin a machine with the right hardware/software stack by leveraging Cloud infrastructure (e.g. Azure). We will therefore include the Cloud provider in the Trust Model here. 

Therefore, there are three parties present:

+ The **AI builder** who is responsible for the training code and data
+ **AICert**, which is responsible for the server-side tooling, including the base OS image, the server to launch the training code and client SDK to verify those elements
+ The **Cloud provider** (who is also the **hardware provider**) who is responsible for administrating the machines and providing the virtual TPM

</br></br>
![trust-model-dark](../../assets/trust-model-dark.png#only-dark)
![trust-model-light](../../assets/trust-model.png#only-light)
</br></br>

🚩 In the current climate, there is blind trust in the AI builder. If they are compromised, malicious backdoors can be inserted into their models, and there is no way for end users to verify the AI models they provide have not been tampered with.

💡 With AICert, we can remove this need for blind trust in the AI builder. There is now a cryptographic binding between the weights and the data and code.

⚠️ We do however need to trust that AICert itself does not contain backdoors, either in the base OS we provide, the server that executes training and generates the proof file, or the client-side SDK in charge of the verification. AICert is open-source and should be inspected by the community.

☁️ The Cloud provider who operates the platform is trusted.