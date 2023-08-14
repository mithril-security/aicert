# Requirements
Terraform 

```
wget -O- https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt update && sudo apt install terraform
```


Azure CLI and login

```
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
az login
az account set --subscription "Microsoft Azure Sponsorship" 
```

# Run control plane

```
poetry run uvicorn control_plane.main:app --host 127.0.0.1 --port 8082
```