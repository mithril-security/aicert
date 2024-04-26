---
description: "Get started with AICert: Understand the workflow and implementation of AICert, enabling AI providers to provide proof of AI provenance and code integrity for safer AI"
---

# Getting started with AICert!
________________________________________________________

To get started, we will walk you through the steps needed to configure and launch AICert using an example where we finetune a [TinyLlama-1.1B model](https://huggingface.co/TinyLlama/TinyLlama-1.1B-intermediate-step-1431k-3T) with proof that the model was derived from the official TinyLlama-1.1B pre-trained model, our open-source training code and the dataset that we specify.

The end-user can then use our **Python client SDK** to verify that the AICert proof file is genuine and check the inputs used (pre-trained model, dataset, and code) to produce our model.

## Fix this link to correct repo
> All the files shown in this example are available [on Github](https://github.com/mithril-security/AICert-example).

**The workflow is as follows:**

![workflow](../../assets/workflow.png)

**AI builder workflow 🛠️**

+ The AI builder prepares **an axolotl configuration file** containing the name of the pretrained model, dataset and finetuning parameters
+ The AI builder launches AICert using the CLI tool

**AICert workflow ⚙️**

+ AICert provisions a VM with the required hardware/software stack
+ AICert executes the finetuning as described in the configuration file
+ AICert returns a link to access the training outputs and a cryptographic proof file 
	
> The proof file contains measurements relating to the software stack, the training code and inputs and the training outputs (e.g. the trained model)

**End user workflow 👩🏻‍💻**

+ The end user verifies the certificate and the inputs and configuration used to create the trained model

> End users will only be able to verify the inputs and configuration where they have access to the original data

Let’s now take a look at the steps that the AI builder and end users must follow in more detail.

## AI builder POV: creating an AI model certificate
________________________________________________________

### Step 1: Preparing the OS image (Only performed once)

#### Step 1-A: Set Azure configuration
We must first configure the Azure region and resource names before we begin creating the Mithril OS image.
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

#### Step 1-B: Create the Mithril OS image

We use mkosi to create an oS image containing the required containers for finetuning and attestation.
The OS is a minimal image with all unnecessary services and modules removed and network restrictions in place.

We've grouped a few steps into a script named `create_MithrilOS.sh`. This script creates the Mithril OS in a disk, uploads it to Azure and converts it into an image, and finally generates the measurements of the OS (which attest the contents of the disk)

```console
# log in to Azure CLI
az login

# create Mithril OS image
./create_MithrilOS.sh
```

**Mithril OS contains the following containers:**

+ aicert-server: This container contains the aicert server, it is the server the client communicates with.
+ aicert-base: This is a minimal image that is used to download the model and dataset specified in the configuration.
+ caddy: Caddy is a reverse-proxy container.
+ axolotl: Axolotl is a container containing the axolotl finetuning framework.

> Inputs (pre-trained model, datasets) are downloaded from as specified in the AICert config file. We consider these as project `resources` and individually hash these files.

The whole repo will be moved to a `/workspace/src` folder within our Docker container.


### Step 2: Modifying the AICert config file

We have a default config in the axolotl_yaml folder in the client. You can either modify this file or create your own configuration yaml file.


### Step 3: Launching the traceable training

Finally, to launch the traceable training process and get back our AI certificate, we can use the AICert CLI tool and run the `aicert finetune` command.

```bash
aicert finetune
```

AICert will look for a yaml file names aicert.yaml in the current working directory and load it. If you want to use a configuration file with another name, you may use the config option (it must be in the current working directory).

```bash
aicert finetune --config custom_config.yaml
```

Once the training process is complete, we obtain an attestation report named `attestation.json`, which binds the hashes of the weights with the training code and inputs, as well as the software stack of the VM used for training. 

This proof file can now be shared with outside parties to prove to them the model comes from using the specified training code and data.

## End user POV: Verifying and inspecting the AI certificate
________________________________________________________

The end user can then use our Python SDK to:

+ Verify that the AICert proof file is legitimate
+ Verify the software stack of the VM used for training
+ Verify the inputs used for training against known hash values

### Verification of the AI certificate and VM software stack

End users can verify the exported proof file is genuine and does contain any unexpected measurements by using the `verify()` method provided by the **AICert Python package** with no arguments.

```bash
aicert verify
```

The `verify()` method checks two things:

+ The authenticity of the certificate's signature
+ The validity of the hashed values of the whole software stack or boot chain of the VM used to train the dataset. This guarantees that the certification process is valid and not compromised.

!!! warning

	The verify() method does not attest that the base model and dataset are trustworthy. They have to be audited independently. However, if the certification process is valid, the AI builder can now be held accountable- if they use, for instance, poisoned data to train the model, this can be verified a posteriori. 

If the proof file contains a false signature or any false values, an error will be raised. False hashed values could signal that the software stack of the VM used for training was misconfigured or even tampered with.

If the `verify()`` method does not return any errors, it means that the AI certificate is genuine.

### Inspecting the proof file

We can use the proof file to manually check the hashed values of the model's inputs or output hash against known values.

For example, an attestation report loks like this:

```json
{
    "ca_cert": "",
    "event_log": [
        "{\"event_type\": \"axolotl_configuration\", \"content\": {\"spec\": {\"config_file\": {\"adapter\": \"lora\", \"base_model\": \"model/TinyLlama/TinyLlama-1.1B-intermediate-step-1431k-3T\", \"bf16\": \"auto\", \"dataset_prepared_path\": null, \"datasets\": [{\"path\": \"dataset/mhenrichsen/alpaca_2k_test\", \"type\": \"alpaca\"}], \"debug\": null, \"deepspeed\": null, \"early_stopping_patience\": null, \"eval_sample_packing\": false, \"evals_per_epoch\": 4, \"flash_attention\": false, \"fp16\": null, \"fsdp\": null, \"fsdp_config\": null, \"gradient_accumulation_steps\": 4, \"gradient_checkpointing\": true, \"group_by_length\": false, \"learning_rate\": 0.0002, \"load_in_4bit\": false, \"load_in_8bit\": true, \"local_rank\": null, \"logging_steps\": 1, \"lora_alpha\": 16, \"lora_dropout\": 0.05, \"lora_fan_in_fan_out\": null, \"lora_model_dir\": null, \"lora_r\": 32, \"lora_target_linear\": true, \"lr_scheduler\": \"cosine\", \"micro_batch_size\": 2, \"model_type\": \"LlamaForCausalLM\", \"num_epochs\": 4, \"optimizer\": \"adamw_bnb_8bit\", \"output_dir\": \"./lora-out\", \"pad_to_sequence_len\": true, \"resume_from_checkpoint\": null, \"sample_packing\": true, \"saves_per_epoch\": 1, \"sequence_len\": 4096, \"special_tokens\": null, \"strict\": false, \"tf32\": false, \"tokenizer_type\": \"LlamaTokenizer\", \"train_on_inputs\": false, \"val_set_size\": 0.05, \"wandb_entity\": null, \"wandb_log_model\": null, \"wandb_name\": null, \"wandb_project\": null, \"wandb_watch\": null, \"warmup_steps\": 10, \"weight_decay\": 0.0, \"xformers_attention\": null}}, \"resolved\": {\"hash\": \"156cd3d4b6f38dda838dbf7e95f8935268f91f091b1af3209f3a4239eea3db9f\"}}}",
        "{\"event_type\": \"input_image\", \"content\": {\"spec\": {\"image_name\": \"@local/aicert-base:latest\"}, \"resolved\": {\"id\": \"sha256:2f1361151ba80d5d0493463b63330c2a6f00e8d92e449c7d6a6febb9a03dafc1\"}}}",
        "{\"event_type\": \"input_resource\", \"content\": {\"spec\": {\"resource_proto\": {\"resource_type\": \"model\", \"repo\": \"https://huggingface.co/TinyLlama/TinyLlama-1.1B-intermediate-step-1431k-3T\", \"hash\": \"036fa4651240b9a1487f709833b9e4b96b4c1574\", \"path\": \"model/TinyLlama/TinyLlama-1.1B-intermediate-step-1431k-3T\"}}, \"resolved\": {\"hash\": \"sha1:b'036fa4651240b9a1487f709833b9e4b96b4c1574\\\\n'\"}}}",
        "{\"event_type\": \"input_resource\", \"content\": {\"spec\": {\"resource_proto\": {\"resource_type\": \"dataset\", \"repo\": \"https://huggingface.co/datasets/mhenrichsen/alpaca_2k_test\", \"hash\": \"d05c1cb585e462b16532a44314aa4859cb7450c6\", \"path\": \"dataset/mhenrichsen/alpaca_2k_test\"}}, \"resolved\": {\"hash\": \"sha1:b'd05c1cb585e462b16532a44314aa4859cb7450c6\\\\n'\"}}}",
        "{\"event_type\": \"input_image\", \"content\": {\"spec\": {\"image_name\": \"@local/axolotl:latest\"}, \"resolved\": {\"id\": \"sha256:dcc5b2108616a303e544faf68a060304fe514788e72e17264966bebb5ef99062\"}}}",
        "{\"event_type\": \"outputs\", \"content\": [{\"spec\": {\"path\": \"finetuned-model.zip\"}, \"resolved\": {\"hash\": \"8739c76e681f900923b900c9df0ef75cf421d39cabb54650c4b9ad19b6a76d85\"}}]}"
    ],
    "remote_attestation": {
        "quote": {
            "message": {
                "base64": "/1RDR4AYACIAC14LdKX3smznOCoo8tCef86t1BXz8V9Vv54XgYYGs4cSAAAAAAAAABGlJgAAAAIAAAAAASAgAxIAEgADAAAAAQALA////wAgz8Uc1hRbl+IPWqW0XVjdXr6CsNgjo0V877qEZ2mcAcc="
            },
            "signature": {
                "base64": "ABQACwEAGretfAiEAr2t1yHYHI0ACELTgttOANErHrmPaUf26QH6kWElEBwaW4JsqPusiGl3q4eh8QIe3J5qKm8mHTvbhlSIgIfav+K2xrjFvAjDi/qeuwWmO5oYhDSCbnNlFZ1BQU3396Wj6k8ebAL8dsHbWFqyJFcZ4LJGnmU/YIF3rAw4g9689LNn2ogK/a6pdfyH/IuVxWfM0Mn4C7GnchHc6gspDNGjnF4f486dAoErIsaULfDhbvKzmoHHsW9amrOGBBHSWH6t491q4NEGeYwtWc5kpeuJreVA2JHP/7z1dTGExg7zLXCBcrwDSzDmWyav7gEzDGFcXY6pRhojqQxF/g=="
            },
            "pcr": {
                "base64": "AQAAAAsAA////wAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAwAAAAgAAAAgAEhH7b5/+wcFgeHabU8D+AGf1GuGz5fyB5zEAMYqZi4KAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgAD1FjP5VzAPqH0Q/FWK+7I31HHXhSp/PmnI0oT8ZjnlpAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgAD1FjP5VzAPqH0Q/FWK+7I31HHXhSp/PmnI0oT8ZjnlpAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgAD1FjP5VzAPqH0Q/FWK+7I31HHXhSp/PmnI0oT8ZjnlpAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgAJ7DpT+pLO5stMn7Rm0U/hgMFZ3iy3Kl0IjA9sHRy78xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgANOgiawJua6C1l4zmxTnbj0vo1E22aKitdyynNFWw7POAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgAH/XN1DnJmKy2It01Llj55C69JtHVRdLwbjcKkhqnHZnAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgABJNr0e01nF5p33DwbzKGYrh7h0JSiqHmXSELkSrmLsGAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAIAAAAIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAIAC0ioF4ZFBeCxRaUX6FEDxLdaz+1RI4o7VlQMEoi/3OwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAIAD1Y2yea2iWWWXlH/Bm1ztjcbXwrzVXho1d1z7iN3jwygAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAIADQw2bgBqYUXB43ganXvp8qDadoumyBatFv7SK19LKpAgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAIACcw+/4dl2XWHHvlP11SuUQMq8/q2VH683cmgevCjfingAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAAAACAAFVzem/Ko3uzgrQAo999fn60lLiAe0ggWbGakRyucJPMAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAA//////////////////////////////////////////8AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAA//////////////////////////////////////////8AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAA//////////////////////////////////////////8AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAA//////////////////////////////////////////8AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAA//////////////////////////////////////////8AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAA//////////////////////////////////////////8AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=="
            }
        },
        "cert_chain": [
            {
                "base64": "MIID2zCCAsOgAwIBAgIQQpRcvoWm+kbNHrDmS7NUezANBgkqhkiG9w0BAQsFADAlMSMwIQYDVQQDExpHbG9iYWwgVmlydHVhbCBUUE0gQ0EgLSAwMTAeFw0yNDA0MjAwMDAwMDBaFw0yNTEwMzAwMDAwMDBaMDExLzAtBgNVBAMTJmUyODA2YWFlYzM5Ni5UcnVzdGVkVk0uQXp1cmUuTWljcm9zb2Z0MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAwcIO6AAAr2LnQjkq3Xbd7eBdDDV2diqCyp+BLdRnFlcoRWytAzEZcI7cygEvEHa277fvxQqkuZ91qUGCb7LMIS9Agw72Vfmsb3z6h9RcjseLCRhYjTu89Eza4qQnm23R2XiASa04YP5sMwwRJbYJp8x+i2LIZNwCJSxESXVmTTmEx0c96+XIHnGLbGAUQODcRTAZP7bzopIc7rAtfwAFZh/4SiKnDl+4JYYZtn471yeP0I2sXhxnQFvncG2Nn2cYZRDORHpfOvJy5eRAY1N/gCyRlHysPG5FKP/qHA0ehZNGIjE08llVc/ypBIeul/gk30aCo8UsQpACT1+Dz0zFBQIDAQABo4H6MIH3MA4GA1UdDwEB/wQEAwIHgDAVBgNVHSAEDjAMMAoGCCsGAQQBgjdsMBwGA1UdJQQVMBMGCisGAQQBgjcKAwwGBWeBBQgDMB0GA1UdDgQWBBRDo5YOb70eccbhLjG0bNzljCxH3zAaBgorBgEEAYI3DQIDBAwWCjYuMi45MjAwLjIwVAYJKwYBBAGCNxUUBEcwRQIBBQwPQkwyMUExMDYzNTA3MDM1DBpXT1JLR1JPVVBcQkwyMUExMDYzNTA3MDM1JAwTVlRwbVByb3Zpc2lvbmVyLmV4ZTAfBgNVHSMEGDAWgBT/9s7nqMFIaSjLikvy2IGBtW2AgTANBgkqhkiG9w0BAQsFAAOCAQEApFhYY6rzlvYK4liqJmhzEDo4RilGKqToQIc8/Pe5P4N88O96zBzToe19Z4NER0ePgYgkkIMBNNwOu/DH23oKRxi9D1X4eWM7pSsEH9BFfrCwd6PlxAhAxyPiJH18/A/Hmt+YpIX4w2T+YYWBqR1CaJtWB0kFSwjMHbyTfe4UsW1+ZMFTCxwMIeNNOCrY4UZ5cL6yAzo/nwKqTr2U7WyD6aeZYCT+CWR0bqMms9uHNvXXZBg2Ryfdi0JIssuSF9phs7+yFMHtKujohVm6QcfhIvDnJXSJnQEk8X2IKRmqxlplJmLo0AY+4AFJ8CN9shGA+nCX/wcOq6q1agSfED7inA=="
            },
            {
                "base64": "LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUZuRENDQTRTZ0F3SUJBZ0lUTXdBQUFBTEEwWHRMajVlY05RQUFBQUFBQWpBTkJna3Foa2lHOXcwQkFRd0YKQURCcE1Rc3dDUVlEVlFRR0V3SlZVekVlTUJ3R0ExVUVDaE1WVFdsamNtOXpiMlowSUVOdmNuQnZjbUYwYVc5dQpNVG93T0FZRFZRUURFekZCZW5WeVpTQldhWEowZFdGc0lGUlFUU0JTYjI5MElFTmxjblJwWm1sallYUmxJRUYxCmRHaHZjbWwwZVNBeU1ESXpNQjRYRFRJek1EWXdPREUzTlRNd05Gb1hEVEkxTVRFd016RTNOVE13TkZvd0pURWoKTUNFR0ExVUVBeE1hUjJ4dlltRnNJRlpwY25SMVlXd2dWRkJOSUVOQklDMGdNREV3Z2dFaU1BMEdDU3FHU0liMwpEUUVCQVFVQUE0SUJEd0F3Z2dFS0FvSUJBUUMvTnFvdUhHQm92VGFkdzFHTE1RWU54V3JFY2lQU2g3Z0U3VnhzCmZiYlBDRTBTZlRPODBPRjJyYUxkUllOMmdFV0UyRHI4K1REVXVBYi9XQkZ5Y3poVTFhSEZQc3NnOEIzL0RUNnAKVFhsRGxvaExMUFdrallVK091VDEvTHM3UnpqUUJlMnNlL01KeVBhSUpYSTZLZ0N3ZVB3N0VjV0ZDaGU4YUNUVQpNSFlCRzBKdTR4TmxNVFVkL3RjdTZhNTNDWG42TnE0OHVtd2xhSmVsUmgraTFmMHZjd0IyQ1kvditSbGl3Yi84CkRNNUVkOUZVSFpPS3lwNVZuYXc5R1dsb000NnNMUVQvZmRIQjBqbXVnZk5aemFma2toUUFZaU5MM2pZTllGWkgKNS9JZ1VmWUoveXlid253b3hPZFYyTlYwUTJpK1A1UGNiMFdOR2FKWTQ3YXFPajhCQWdNQkFBR2pnZ0YvTUlJQgplekFTQmdOVkhSTUJBZjhFQ0RBR0FRSC9BZ0VBTUE0R0ExVWREd0VCL3dRRUF3SUNCREFYQmdOVkhTVUVFREFPCkJnVm5nUVVJQVFZRlo0RUZDQU13SFFZRFZSME9CQllFRlAvMnp1ZW93VWhwS011S1MvTFlnWUcxYllDQk1COEcKQTFVZEl3UVlNQmFBRkV2K0pscVV3Zll6dzROSUp0M3o1YkJrc3FxVk1IWUdBMVVkSHdSdk1HMHdhNkJwb0dlRwpaV2gwZEhBNkx5OTNkM2N1YldsamNtOXpiMlowTG1OdmJTOXdhMmx2Y0hNdlkzSnNMMEY2ZFhKbEpUSXdWbWx5CmRIVmhiQ1V5TUZSUVRTVXlNRkp2YjNRbE1qQkRaWEowYVdacFkyRjBaU1V5TUVGMWRHaHZjbWwwZVNVeU1ESXcKTWpNdVkzSnNNSUdEQmdnckJnRUZCUWNCQVFSM01IVXdjd1lJS3dZQkJRVUhNQUtHWjJoMGRIQTZMeTkzZDNjdQpiV2xqY205emIyWjBMbU52YlM5d2EybHZjSE12WTJWeWRITXZRWHAxY21VbE1qQldhWEowZFdGc0pUSXdWRkJOCkpUSXdVbTl2ZENVeU1FTmxjblJwWm1sallYUmxKVEl3UVhWMGFHOXlhWFI1SlRJd01qQXlNeTVqY25Rd0RRWUoKS29aSWh2Y05BUUVNQlFBRGdnSUJBRWhUd3gyNlcrWGFwN3pYRXhiQXduSFl0TjZrQjRkSUdYZGdRSWlReTVPUQpsdHNTajJqeDdxWi9hZjVuNU9uVEJRK2dYTThzaVZpcGdhQUlkQmtiR2dPakNiNmI2TVRlMVlwRkFINGZRdjhlClZ3VFZEemlCTUQwRUtJMzBoMEpiRktMZFNkS2U0OE85THcrVDJiMFBCWHZNRkpPU2RaVDdtZUdJa3BOeFNxbUEKWitSTnlyZUx4aWw5a25OakY1eW1QVDBSY0dLNTIrTXdHbEVsQmIvamMrc25ocitaSloxZ3JqRmt5OU56akNUaQpFNVNHKzZIM1lnaUhDcWZYcjBMM05SdC9RWjVJZ2t1R2tOUGVNdm40SmpldkZ3QWhYRnhCcUpZSjdtWTYxTUp1CldUZHloaG9VSmd6bVpvMWhTK0dOeXVNS2FLQkxyZVV3dGMxeTdMUkgzWUdHZWQ1N0hiUTlibXlNZGhPN3g4S1oKTnJCRFgyL2NSTHpyQ21wU1VsZG1LTXU5RzRkcHpYcGRlNHBGTU9iaVZGckdScTgvOUhNT0p3WmxRdnpod1FwMApQVU1ZL2dJVTVyZjIzbjFNMU0zNnRNNWc1Q0V6eFFVR3RWYUc5QUJUSlEyemlqRDV3RG84NDB2YnpueUt0M2loCmltclVzK0xxcFBETlh5eGJ3dmliY1ppZHdTZGh1MFFtVW95WXNnU1AyWmZmNUU4a3M1M2gyeFFTTTN6ejJxYVcKVlMxdlZxRzR6QzBFZlJuTzY1b2dQUGZydEs2WmlGbVZIU1dQOXZQa0ZjVU5ZRG5ZUVhXL1RBck8vSkNlMkkrKwpHQ2xNN0FjRFF3V0x4Y29wenNrR1FkSE5NMXpNc3ByUlJ3WWFWcFRKSDY3eGVOZGE2K1k3SU9QSllUdnlvWEhQCi0tLS0tRU5EIENFUlRJRklDQVRFLS0tLS0="
            },
            {
                "base64": "LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUZzRENDQTVpZ0F3SUJBZ0lRVWZReDJpeVNDSXBPS2VEWktkNUtwekFOQmdrcWhraUc5dzBCQVF3RkFEQnAKTVFzd0NRWURWUVFHRXdKVlV6RWVNQndHQTFVRUNoTVZUV2xqY205emIyWjBJRU52Y25CdmNtRjBhVzl1TVRvdwpPQVlEVlFRREV6RkJlblZ5WlNCV2FYSjBkV0ZzSUZSUVRTQlNiMjkwSUVObGNuUnBabWxqWVhSbElFRjFkR2h2CmNtbDBlU0F5TURJek1CNFhEVEl6TURZd01URTRNRGcxTTFvWERUUTRNRFl3TVRFNE1UVTBNVm93YVRFTE1Ba0cKQTFVRUJoTUNWVk14SGpBY0JnTlZCQW9URlUxcFkzSnZjMjltZENCRGIzSndiM0poZEdsdmJqRTZNRGdHQTFVRQpBeE14UVhwMWNtVWdWbWx5ZEhWaGJDQlVVRTBnVW05dmRDQkRaWEowYVdacFkyRjBaU0JCZFhSb2IzSnBkSGtnCk1qQXlNekNDQWlJd0RRWUpLb1pJaHZjTkFRRUJCUUFEZ2dJUEFEQ0NBZ29DZ2dJQkFMb01Nd3ZkUko3K2JXMDAKYWRLRTFWZW1OcUpTKzI2OFVyZThRY2ZaWFZPc1ZPMjIrUEw5V1JvUG5XbzByNWRWb29tWUdib2JoNEhDNzJzOQpzR1k2QkdSZStVaTJMTXd1V25pckJ0T2phSjM0cjFaaWVOTWNWTkpUL2RYVzVITi9ITGxtL2dTS2xXenFDRXg2CmdGRkFRVHZ5WWwvNWpZSTRPZTA1eko3b2pnaksvNlpIWHBGeXNYbnlVSVRKOXFnam41NDZJSmgvRzVPTUMzbUQKZkZVN0EvR0FpK0xZYU9IU3pYajY5TGsxdkNmdE5xOURjUUh0QjdvdE8wVnhGa1JMYVVMY2Z1L0FZSE03RkMvUwpxNmNKYjlBdThLL0lVaHcvNWxKU1haYXdMSndIcGNFWXpFVG0yYmxhZDBWSHNBQ2FMTnVjWkw1d0JpOEdFdXNRCjlXbzhXMXAxclVDTXA4OXB1ZnhhM0FyOXNZWnZXZUpsdktnZ1djUVZVbGh2dklaRW5UK2Z0ZUV2d1Rkb2FqbDUKcVN2WmJEUEdDUGpiOTFyU3pub2lMcThYcWdRQkJGam5FaVRMK1ZpYVpteVpQWVVzQnZCWTNsS1hCMWwyaGdnYQpoZkJJYWc0ajB3Y2dxbEw4MlNMN3BBZEdqcTBGb3U2U0tnSG5ra3JWNUNOeFVCQlZNTkN3VW9qNW12RWpkNW1GCjdYUGdmTTk4cU5BQmIyQXF0ZmwrVnVDa1UvRzFYdkZvVHFTOUFrd2JMVEdGTVM5K2pDRVUycnc2d25LdUd2MVQKeDlpdVNkTnZzWHQ4c3R4NGZrVmVKdm5GcEplQUl3QlpWZ0tSU1RhM3czMDk5azBtVzhxR2lNbndDSTVTZmRaMgpTSnlENHVFbXN6c25pZUU2d0FXZDF0TExnMWp2QWdNQkFBR2pWREJTTUE0R0ExVWREd0VCL3dRRUF3SUJoakFQCkJnTlZIUk1CQWY4RUJUQURBUUgvTUIwR0ExVWREZ1FXQkJSTC9pWmFsTUgyTThPRFNDYmQ4K1d3WkxLcWxUQVEKQmdrckJnRUVBWUkzRlFFRUF3SUJBREFOQmdrcWhraUc5dzBCQVF3RkFBT0NBZ0VBTGdOQXlnOEkwQU5OTy84SQoyQmhwVE9zYnl3TjJZU21TaEFtaWc1aDRzQ3RhSlNNMWRSWHdBK2tlWTZQQ1hRRXQvUFJBUUFpSE5jT0Y1emJ1Ck9VMUJ3L1o1WjdrOW9rdDA0ZXU4Q3NTMkJwYytQT2c5anM2bEJ0bWlnTTVMV0pDSDFnb01EMGtKWXB6a2FDengKMVRkRDN5am8weFN4Z0doYWJrNUl1MXNvRDNPeGhVeUlGY3hhbHVod2tpVklOdDNKaHk3RzdWSlRsRXdrazIxQQpvT3JReFVzSkgwZjJHWGpZU2hTMXI5cUxQekxmN3lrY09tNjJqSEdtTFpWWnVqQnpMSWROazFibGpQOVZ1R1crCmNJU0J3emtOZUVNTUZ1ZmNMMnhoNnMvb2lVblhpY0ZXdkc3RTZpb1BuYXlZWHJIeTNSaDY4WExuaGZwemVDenYKYnovSTR5TVYzOHFHby9jQVkyT0pwWFV1dUQvWmJJNXJUK2xSQkVrRFcxa3hIUDhjcHdrUndHb3BWOCtnWDJLUwpVdWNJSU40bDgvcnJOREVYOFQwYjVVK0JVcWlPN1o1WW54Q3lhL0gwWkl3bVFuVGxMUlRVMmZXK09HRyt4eUlyCmpNaS8wbDYveVdQVWtJQWtOdHZTL3lPN1VTUlZMUGJ0R1ZrM1FyZTZIY3FhY0NYekVqSU5jSmhHRVZnODNZOG4KTStZK2E5SjBsVW5IeXRNU0ZaRTg1aDg4T3NlUlMyUXdxam96VW8yajFEb3dtaFNTVXY5TmE1QWUyMnljY2lCawpFWlNxOGE0clNsd3F0aGFFTE5wZW9UTFVrNmlWb1VrSy9pTHZhTXZya2RqOXlKWTFPL2d2bGZOMmFpTlRTVC8yCmJkK1BBNFJCVG9HOXJYbjZ2TmtVV2RiTGliVT0KLS0tLS1FTkQgQ0VSVElGSUNBVEUtLS0tLQ=="
            }
        ]
    }
}
```
