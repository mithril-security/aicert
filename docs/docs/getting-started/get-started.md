To get started, we will walk you through the steps needed to configure and launch AICert using an example where we finetune a Falcon 7B model with proof that the model was derived from the pre-trained model, code, and data that we specified.

The end-user can then use our client SDK to verify that the AICert proof file is genuine and verify the inputs used (pre-trained model, dataset, and code) to produce our model.

> All the files shown in this example are available [on Github](https://github.com/mithril-security/AICert-example).

**The workflow is as follows:**

<img src="https://github.com/mithril-security/aicert/raw/readme/docs/assets/workflow.png" alt="workflow">


**AI builder POV:**

+ The AI builder prepares **a GitHub or HuggingFace source repository** containing their training script and input files (alternatively, input files can also be added as **resources** in the config file)
+ The AI builder modifies the config yaml file, for example, to specify their project repo link
+ The AI builder launches AICert using the CLI tool

**Under the hood:**
+ AICert provisions a VM with the required hardware/software stack
+ AICert executes the training entry script as specified in the AICert config file
+ AICert returns the scripts outputs, along with a cryptographic proof file with measurements relating to the software stack, the training code and inputs used and the training outputs (e.g. the trained model)

**End-user POV:**
+ The end user can verify this certificate and all the elements used to create the trained model (where they have access to the original data)

Let’s now take a look at the steps that the AI builder and end users must follow in more detail.

### AI builder POV: creating an AI model certificate

### Step 1: Preparing project source repository

You will need to place all the files needed to train your model into one repository, hosted either by GitHub or Hugging Face. This can be a private or public repository.

**This repository should include:**
+ A requirements.txt file with all dependencies needed
+ A script file (main.py by default) which will be executed by AICert
+ The inputs required to complete training, such as the dataset or the base model will be fine-tuned. These can alternatively be downloaded from a URL specified in the AICert config file.

**The GitHub repo file structure for our example is as follows:**

```bash
AICert-example/
├─ inputs/
│  ├─ alpaca-fr.csv
├─ src/
│  ├─ main.py
├─ .gitignore
├─ README.md
```

**The requirements for your script file are as follows:**
+ Your requirements.txt file should be in the root of your GitHub repository.
+ When your main.py script is executed at runtime, the contents of your GitHub repo provided as a source in the AICert config file will be accessible in the /workspace/src folder. You should therefore modify any paths in your scripts accordingly.
```python
# load dataset from location specified in AICert config
dataset = load_dataset('csv', data_files='workspace/src/inputs/alpaca-fr.csv')
dataset = dataset['train'].select(range(number_elements_for_training))
```

+ Any input files provided as resources in the config file, outside of your main GitHub repo, will be accessible in the /workspace/resources folder at runtime.
+ Your script must save any output artifacts, such as your trained model, to the specified outputs folder, which is /workspace/outputs by default. AICert will then include them in the proof file and return them to you.
```python
# launch the training
trainer.train()

# Save model in location specified in AICert config
torch.save(model.state_dict(), '/workspace/outputs/finetuned.pth')
```

+ Your script must not download any external input files as we cannot reliably attest resources downloaded in this way. These inputs should be provided in the project repository or as URLs in the AICert config file and loaded from the workspace.

AICert records:
+ A SHA1 hash of any GitHub repo commits listed in the AICert config file
+ A SHA256 hash of any additional inputs listed in the AICert config file

#### Step 2: Modifying the AICert config file

Before launching AICert, the AI builder will need to modify the template AICert config file.

This file allows you to specify:

+ The base Docker image which AICert will use when launching the training
+ The commands to be executed in this environment
+ The inputs that will be required for your program (e.g. datasets) and their locations within the workspace
+ The location of any outputs

In our example, all the files we need to launch our finetuning program are contained within our GitHub repository, so we will add this to our inputs section. Otherwise, we leave all other options with their default values.

```yaml
kind: python 

pythonVersion: 11
# available at /workspace/src/
source: 
type: git 
gitRepo: "https://github.com/mithril-security/AICert-example" 	 
pythonEntryPoint: "src/main.py" 
```

We will provide full details on all the AICert config file options in a tutorial **coming soon**!

### Step 3: Launching the traceable training

Finally, to launch the traceable training process and get back our AI certificate, we can use the AICert CLI tool and run the `aicert` command.

**We will need to specify:**
+ `output-bom`: File name for your cryptographic proof file

```bash
aicert --output-bom "falcon-finetuned-proof.json"
```

Once the training process is over, we obtain a signed AI certificate, our `falcon-finetuned-proof.json`, which binds the hashes of the weights with the training code and dataset used, as well as the software stack of the VM used for training. 

This proof file can now be shared with outside parties to prove to them the model comes from using the specified training code and data.

## End user POV: Verifying and inspecting the AI certificate

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
+ The authenticity of the certificate's signature, allowing us to know that the proof file was created using genuine secure hardware.
+ The validity of the hashed values of the whole software stack or boot chain of the VM used to train the dataset. This ensures that the certification process is valid and not compromised. It does not attest that the script and data are trustworthy. Those have to be audited independently. However, if the certification process is valid, the AI builder can now be held accountable- if they use, for instance, poisoned data to train the model, this can be verified `a posteriori``. 

If the proof file contains a false signature or any false values, an error will be raised. False hashed values could signal that the software stack of the VM used for training was misconfigured or even tampered with.

If the `verify()`` method passes, it means that the AI certificate is genuine. However, the dataset and training code have to be verified themselves too.

#### The proof file

We can also use the proof file to manually check the hashed values of the model's inputs or output hash against known values.

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

This contains the SHA1 hash of our GitHub repository commit provided in the AICert config file, which contains our finetuning code and dataset. The end user could then check this against the SHA1 hash value of the official GitHub repository.