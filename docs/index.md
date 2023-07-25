# 👋 Welcome to AICert!
________________________________________________________

<font size="5"><span style="font-weight: 200">
Making AI Traceable and Transparent
</font></span>

## 📜 What is AICert?
________________________________________________________


🛠️ **AICert** aims to make AI **traceable** and **transparent** by enabling **AI builders** to create certificates with **cryptographic proofs binding the weights to the training data and code**. AI builders can be foundational model providers or companies that finetune the foundational models to their needs.

👩‍💻 **End users** are the final consumers of the AI builders’ models. They can then verify these AI certificates to have proof that the model they talk to comes from a specific training set and code, and therefore **alleviates copyright, security and safety issues**.

🔐 We leverage **Trusted Platform Modules (TPMs)** in order to attest the whole stack used for producing the model, from the UEFI, all the way to the code and data, through the OS. Measuring the whole hardware/software stack and binding the final weights produced (by registering them in the last PCR) allows the derivation of certificates that contain **irrefutable proof of model provenance**.

### Use cases

AICert addresses some of the most urgent concerns related to **AI provenance**. It allows AI builders to:

+ Prove their AI model was not trained on copyrighted, biased or non-consensual PII data
+ Provide an AI Bill of Material about the data and code used, which makes it harder to poison the model by injecting backdoors in the weights
+ Provide a strong audit trail with irrefutable proof for compliance and transparency

!!! warning
  
	AICert is still **under development**. Do not use it in production!

	If you want to contribute to this project, do not hesitate to raise an issue.

## 🔍 Features
________________________________________________________

+ **AI model traceability:** create AI model ID cards that provide cryptographic proof binding model weights to a specific training set and code
+ **Non-forgeable proofs:** leverage TPMs to ensure non-forgeable AI model ID cards
+ **Flexible training:** use your preferred tooling for training
+ **No slowdown** induced during training
+ **Azure support**

**Coming soon:**

+ **Benchmark linking:** provide cryptographic binding of model weights to specific benchmarks that were run for this specific model
+ **Multi-Cloud support** with AWS and GCP coverage
+ **Single and multi-GPU support**

## 🚀 Getting started
________________________________________________________

- Check out our [“Getting started guide”](./docs/getting-started/get-started.md), which will walk you through an example!
- [Discover](./docs/getting-started/tech-overview.md) the technologies we use under the hood!

## ⚠️ Limitations
________________________________________________________

While we provide traceability and ensure that a given set of weights comes from applying a specific training code on a specific dataset, there are still challenges to solve:

+ The training code and data have to be inspected. AICert does not audit the code or input data for threats, such as backdoors injected into a model by the code or poisonous data. It will simply allow us to prove model provenance. It is up to the AI community or end-user to inspect or prove the trustworthiness of the code and data. 
+ AICert itself has to be inspected, all the way from the OS we choose to the HTTP server and the app we provide to run the code on the training data.

We are well aware that AICert is not a silver bullet, as to have a fully trustworthy process, it requires scrutiny of both our code and the code and data of the AI builder.

However, by combining both, one can have a solid foundation for the AI supply chain.

## 🙋 Getting help
________________________________________________________

- Go to our [Discord](https://discord.com/invite/TxEHagpWd4) *#support* channel
<!-- - Report bugs by [opening an issue on our AICert Github](https://github.com/mithril-security/aicert/issues) -->
- [Book a meeting](https://calendly.com/contact-mithril-security/15mins?month=2022-11) with us

<!--
## 📚 How is the documentation structured?
____________________________________________
<!--
- [Tutorials](./docs/tutorials/core/installation.md) take you by the hand to install and run BlindBox. We recommend you start with the **[Quick tour](./docs/getting-started/quick-tour.ipynb)** and then move on to the other tutorials!  

- [Concepts](./docs/concepts/nitro-enclaves.md) guides discuss key topics and concepts at a high level. They provide useful background information and explanations, especially on cybersecurity.

- [How-to guides](./docs/how-to-guides/deploy-API-server.md) are recipes. They guide you through the steps involved in addressing key problems and use cases. They are more advanced than tutorials and assume some knowledge of how BlindBox works.

- [API Reference](https://blindai.mithrilsecurity.io/en/latest/blindai/client.html) contains technical references for BlindAI’s API machinery. They describe how it works and how to use it but assume you have a good understanding of key concepts.

- [Security](./docs/security/remote_attestation/) guides contain technical information for security engineers. They explain the threat models and other cybersecurity topics required to audit BlindBox's security standards.

- [Advanced](./docs/how-to-guides/build-from-sources/client/) guides are destined to developers wanting to dive deep into BlindBox and eventually collaborate with us to the open-source code.

- [Past Projects](./docs/past-projects/blindai) informs you of our past audited project BlindAI, of which BlindBox is the evolution. 
-->

<!-- ## ❓ Why trust us?
___________________________

+ **Our core security features are open source.** We believe that transparency is the best way to ensure security and you can inspect the code yourself on our [GitHub page](https://github.com/mithril-security/blindbox).

+ **Our historical project [BlindAI](docs/past-projects/blindai.md) was successfully audited** by Quarkslab. Although both projects differ (BlindAI was meant for the confidential deployment of ONNX models inside Intel SGX enclaves), we want to highlight that we are serious about our security standards and know how to code secure remote attestation. -->

## 🔒 Who made AICert?
________________________________________________________

AICert was developed by **Mithril Security**. **Mithril Security** is a startup focused on AI privacy solutions based on **Confidential Computing** technologies. We provide several **open-source tools** for **querying** and **deploying AI solutions** to improve AI provider's security posture and compliance.