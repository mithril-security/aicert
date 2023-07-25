# Requirements 


The server requires access to /dev/tpmrm0, so 
for testing at least you'll need to run `sudo chmod 0666 /dev/tpmrm0`


Install git-lfs

curl -s https://packagecloud.io/install/repositories/github/git-lfs/script.deb.sh | sudo bash
sudo apt-get install git-lfs
git lfs install

<!-- ```
sudo apt-get update
sudo apt-get install libtss2-dev
``` -->

# Dependencies needed for tpm2-pytss 

```
sudo apt-get update
sudo apt-get install -y tpm2-tools
```



```
cd server
poetry shell && poetry install
```

Run test

```
pytest server/main.py
```

```
# In server/server
uvicorn main:app
```


# Datascientist

# Requirements

Install terraform

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

Other requirements

```
apt-get install gettext-base
pipx install --include-deps ansible
```


```
$ terraform init

Initializing the backend...

Initializing provider plugins...
- Finding hashicorp/azurerm versions matching "~> 3.0.2"...
- Installing hashicorp/azurerm v3.0.2...
- Installed hashicorp/azurerm v3.0.2 (signed by HashiCorp)

Terraform has created a lock file .terraform.lock.hcl to record the provider
selections it made above. Include this file in your version control repository
so that Terraform can guarantee to make the same selections by default when
you run "terraform init" in the future.

Terraform has been successfully initialized!

You may now begin working with Terraform. Try running "terraform plan" to see
any changes that are required for your infrastructure. All Terraform commands
should now work.

If you ever set or change modules or backend configuration for Terraform,
rerun this command to reinitialize your working directory. If you forget, other
commands will detect it and remind you to do so if necessary.
```

# Create and initialize VM
```
terraform apply

terraform output -raw tls_private_key > private_key.pem
chmod 600 private_key.pem
VM_IP="$(terraform output -raw public_ip_address)" envsubst < inventory.ini.tmpl > inventory.ini

openssl ecparam -genkey -name prime256v1 -out client.key
openssl req -new -key client.key -out client.csr -subj "/C=US/ST=California/L=San Francisco/O=My Company/CN=mydomain.com"
openssl x509 -req -days 365 -in client.csr -signkey client.key -out client.crt

ansible-playbook -i inventory.ini deploy.yml
```

# Run the workflow
```
curl  --cert client.crt --key client.key \
      --cacert tls_ca.crt \
      --resolve aicert_worker:443:$(terraform output -raw public_ip_address) \
    https://aicert_worker/
```


# Finalization (destroy VM)
```
terraform destroy
```

<!-- ssh -i private_key.pem azureuser@$(terraform output -raw public_ip_address) -->


<!-- uvicorn main:app --host 127.0.0.1 --port 8080 --workers 4 -->





<!-- GitHub Copilot: If you prefer to use elliptic curve cryptography instead of RSA, you can generate an EC private key and certificate with OpenSSL using the following steps:

1. Generate an EC private key:

   ```
   openssl ecparam -genkey -name prime256v1 -out client.key
   ```

   This will generate an EC private key using the `secp256r1` curve.

2. Create a certificate signing request (CSR) for the client:

   ```
   openssl req -new -key client.key -out client.csr -subj "/C=US/ST=California/L=San Francisco/O=My Company/CN=mydomain.com"
   ```

   You will be prompted to enter information about the client, such as its name and organization.

3. Generate a self-signed certificate for the client using the CSR:

   ```
   openssl x509 -req -days 365 -in client.csr -signkey client.key -out client.crt
   ```

   This will create a self-signed certificate for the client that is valid for 365 days.

You can then use the `client.key` and `client.crt` files as the client's private key and certificate, respectively.
 -->
