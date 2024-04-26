---
description: "Learn about TPMs and how we use them to create trustable proof of AI provenance through the attestation process"
---

# 📜 Attestation with Trusted Platform Modules
________________________________________________________

[Trusted Platform Modules](https://en.wikipedia.org/wiki/Trusted_Platform_Module) (TPMs) are at the core of AICert, enabling us to cryptographically bind a model’s weights to its training code and data, as well as the software stack of the machine it was trained on.

In this section, we will cover:

+ How TPMs work
+ How we leverage them in AICert
+ The hardware/software stack we provide with AICert

## 🔐 Trusted Platform Modules (TPMs)
________________________________________________________

### Overview

TPMs are secure hardware components that can be used to ensure the integrity of a whole software supply chain. They are able to attest the whole software stack of a machine, from the UEFI to the OS. 

They can also attest additional customizable items- in our case, we also attest the base AI model, inputs and outputs.

#### How does it work?

When a TPM-enabled system boots, various measurements are taken, such as hashes of firmware, boot loaders, and critical system files. These measurements are then stored in the TPM's PCRs (Platform Configuration Registers), a set of registers within the TPM. PCRs can be considered a log of the system state, capturing the integrity of various components during the boot process and other critical stages. 

We can then check the values stored in the PCRs against known values, allowing us to attest that the software stack has not changed from the expected values.

To do this, we can request a signed quote from the TPM which contains these PCR values and is signed by the TPM's Attestation Key (AK), which is derived from a tamper-proof TPM Endorsement Key (EK), and thus cannot be falsified by a third party.

Measuring the whole software stack and binding the inputs used in the training process and the final weights produced (by registering them to the last two PCRs) allows the derivation of certificates that contain irrefutable proof of model provenance. 

### Usage in AICert

To see how it works in practice, let’s see how AICert uses TPMs to prove a specific code and data were loaded, and how they were used to produce a specific model.

![proof-file](../../assets/proof-file.png)

#### Software stack

We provide a base image containing all software elements up to the server application that will execute the code on the training data. This base image is fixed and can be publicly audited.

At the boot stage, the stack is loaded piece by piece, starting with the UEFI. The TPM will measure and store each of these elements in their corresponding PCR. 

#### Inputs

We then download the base model and any resources as specified in the AICert config file. These inputs are hashed and stored in PCR16.

#### Outputs

After performing training, we hash the outputs and store these hashes in PCR16.

![PCR-values](../../assets/PCR-values.png)

AICert will then request a “quote”, containing all these measurements, which is signed by a hardware-derived key verified by the Cloud provider.

### Verification

![verification](../../assets/verification-cropped.png)

When end users use the `verify()` method provided in our AICert Python library, AICert will check the values of each PCR in our AICert proof file against known values. This allows us to verify the full software stack used by AICert.

However, the hashes in PCR15 and PCR16 are not known values to AICert, so end users should verify these manually by comparing the values in our AICert proof file against known SHA256 (for GitHub commits) or SHA1 hashes (for other input files) for the input data.