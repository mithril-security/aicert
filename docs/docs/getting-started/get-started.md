# ☀️ Getting started with AICert!
________________________________________________________


To get started, we will walk you through the steps needed to configure and launch AICert using an example where we finetune a [Falcon 7B LLM model](https://huggingface.co/tiiuae/falcon-7b) with proof that the model was derived from the official Falcon-7b pre-trained model, our open-source training code and the dataset that we specify.

The end-user can then use our **Python client SDK** to verify that the AICert proof file is genuine and check the inputs used (pre-trained model, dataset, and code) to produce our model.

> All the files shown in this example are available [on Github](https://github.com/mithril-security/AICert-example).

**The workflow is as follows:**

![workflow](../../assets/workflow.png)

**AI builder workflow 🛠️**

+ The AI builder prepares **a GitHub or HuggingFace source repository** containing their training script and input files
+ The AI builder can optionally modify the config yaml file, for example, to add additional resources outside of their github source repository
+ The AI builder launches AICert using the CLI tool, specifying their source folder repo and the file name of their proof file

> Alternatively, input files can also be added as **resources** in the config file

**AICert workflow ⚙️**

+ AICert provisions a VM with the required hardware/software stack
+ AICert executes the training script provided
+ AICert returns the training outputs and a cryptographic proof file 
	
> The proof file contains measurements relating to the software stack, the training code and inputs and the training outputs (e.g. the trained model)

**End user workflow 👩🏻‍💻**

+ The end user verifies the certificate and the inputs and code used to create the trained model

> End users will only be able to verify the inputs and code where they have access to the original data

Let’s now take a look at the steps that the AI builder and end users must follow in more detail.

## AI builder POV: creating an AI model certificate
________________________________________________________

### Step 1: Preparing project source repository

We will place all the files needed to train our model into [one GitHub repository](https://github.com/mithril-security/AICert-example)

> This can be a private or public repository

**This repository should include:**

+ A **requirements.txt** file with all dependencies needed
+ A script file (**src/main.py** by default) which will be executed by AICert
+ The **inputs** required to complete training, such as the **dataset** or the **base model** to be fine-tuned

> Inputs can alternatively be downloaded from a URL specified in the AICert config file. We consider these as project `resources` and individually hash these files.

> You can place your input files wherever you like in your GitHub repo. 

The whole repo will be moved to a `/workspace/src` folder within our Docker container at runtime and can be accessed in your `main.py` script within this folder.

**The GitHub repo file structure for our example is as follows:**

```bash
AICert-example/
├─ inputs/
│  ├─ alpaca-fr.csv
├─ src/
│  ├─ main.py
├─ .gitignore
├─ README.md
├─ requirements.txt
```

**The requirements for our script file are as follows:**
+ We need to make sure the paths to load any inputs in our scripts are relative to the default path `(/workspace/src)` where our source GitHub repo is moved to at runtime.
```python
# load dataset from location specified in AICert config
dataset = load_dataset('csv', data_files='workspace/src/inputs/alpaca-fr.csv')
dataset = dataset['train'].select(range(number_elements_for_training))
```

+ Our script must save any output artifacts, such as your trained model, to the specified outputs folder, which is /workspace/outputs by default. AICert will then include them in the proof file and return them to you.

```python
# launch the training
trainer.train()

# Save model in location specified in AICert config
torch.save(model.state_dict(), '/workspace/outputs/finetuned.pth')
```

+ Our script must not download any external input files as we cannot reliably attest resources downloaded in this way. These inputs should be provided in the project repository or as URLs in the AICert config file and loaded from the workspace.

AICert records:

+ A SHA1 hash of any GitHub repo commits listed in the AICert config file
+ A SHA256 hash of any additional inputs listed in the AICert config file

### Step 2: Modifying the AICert config file

For our example, we can use the default configuration file by providing a `src/main.py` Python script in our GitHub repository and placing all the files we need for our script within this GitHub repository.

> There may be some use cases where users want to customize their AICert configuration. We will provide full details of all the AICert config file options and how to implement them in our AICert config file tutorial **coming soon**!

### Step 3: Launching the traceable training

Finally, to launch the traceable training process and get back our AI certificate, we can use the AICert CLI tool and run the `aicert` command.

**We will need to specify:**

+ `source-repo`: The URL for your source GitHub/HuggingFace repo
+ `output-bom`: File name for your cryptographic proof file

```bash
aicert --source-repo="https://github.com/mithril-security/AICert-example" --output-bom "falcon-finetuned-proof.json"
```

Once the training process is complete, we obtain a signed AI certificate, our `falcon-finetuned-proof.json`, which binds the hashes of the weights with the training code and inputs, as well as the software stack of the VM used for training. 

This proof file can now be shared with outside parties to prove to them the model comes from using the specified training code and data.

## End user POV: Verifying and inspecting the AI certificate
________________________________________________________

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

+ The authenticity of the certificate's signature
+ The validity of the hashed values of the whole software stack or boot chain of the VM used to train the dataset. This guarantees that the certification process is valid and not compromised.

!!! warning

	The verify() method does not attest that the script and data are trustworthy. They have to be audited independently. However, if the certification process is valid, the AI builder can now be held accountable- if they use, for instance, poisoned data to train the model, this can be verified a posteriori. 

If the proof file contains a false signature or any false values, an error will be raised. False hashed values could signal that the software stack of the VM used for training was misconfigured or even tampered with.

If the `verify()`` method does not return any errors, it means that the AI certificate is genuine.

### Inspecting the proof file

We can use the proof file to manually check the hashed values of the model's inputs or output hash against known values.

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

This contains the SHA1 hash of our GitHub repository commit provided in the AICert config file, which contains our finetuning code and dataset. The end user can then check this against the SHA1 hash value of the official GitHub repository.
