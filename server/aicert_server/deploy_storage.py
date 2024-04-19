import os, uuid
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient

account_url = "https://axolotlfli.blob.core.windows.net"
default_credential = DefaultAzureCredential()

blob_service_client = BlobServiceClient(account_url, credential=default_credential)
# Create a unique name for the container
container_name = str(uuid.uuid4())

# Create the container
container_client = blob_service_client.create_container(container_name)

model_trained_path = "./workspace/finetuned-model.zip"
model_trained_name = "finetuned-model.zip"
blob_client = blob_service_client.get_blob_client(container=container_name, blob=model_trained_name)
print("\nUploading to Azure Storage as blob:\n\t" + model_trained_name)

with open(file=model_trained_path, mode="rb") as data:
    blob_client.upload_blob(data)