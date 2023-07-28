# Requirements

Ubuntu 
```
sudo apt-get update
sudo apt-get install -y tpm2-tools
```

# Real 

`aicert verify`
`aicert new`

```shell
$ aicert build
[15:10:27] INFO     Launching the runner...                                         client.py:218
[15:13:40] INFO     Runner is ready.                                                client.py:220
           INFO     Submitting build request                                        client.py:249
[15:14:24] INFO     Attestation received                                            client.py:272
           INFO     Downloading output: helloworld                                  client.py:281
           INFO     Destoying runner                                                client.py:288
[15:16:53] INFO     Runner destroyed successfully                                   client.py:290
```

# Simulation

Set the following environment variable: 
`AICERT_SIMULATION_MODE=1`
