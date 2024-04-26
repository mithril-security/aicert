from azure.identity import DefaultAzureCredential
from datetime import datetime, timedelta
from azure.storage.blob import BlobClient, generate_blob_sas, BlobSasPermissions

account_url = "https://axolotlfli.blob.core.windows.net"
default_credential = DefaultAzureCredential()



def get_blob_sas(account_name,account_key, container_name, blob_name):
    sas_blob = generate_blob_sas(account_name=account_name, 
                                container_name=container_name,
                                blob_name=blob_name,
                                account_key=account_key,
                                permission=BlobSasPermissions(read=True, write=True),
                                expiry=datetime.now() + timedelta(hours=1))
    return sas_blob


class ModelUploader:
    blob_service_client: BlobClient
    path_finetune_model: str
    sas_url: str

    def __init__(self, sas_url: str, finetune_model: str):
        self.sas_url = sas_url
        self.path_finetune_model = finetune_model
        self.blob_service_client = BlobClient.from_blob_url(sas_url)

    def upload_model(self):
        with open(self.path_finetune_model, 'rb') as data: 
            self.blob_service_client.upload_blob(data)
    
    def get_link(self):
        return "https://aicertstorage.blob.core.windows.net/aicertcontainer/finetuned-model.zip"
        

# blob_service_client = BlobServiceClient(account_url, credential=default_credential)
# # Create a unique name for the container
# container_name = str(uuid.uuid4())

# # Create the container
# container_client = blob_service_client.create_container(container_name)

# model_trained_path = "./workspace/finetuned-model.zip"
# model_trained_name = "finetuned-model.zip"
# blob_client = blob_service_client.get_blob_client(container=container_name, blob=model_trained_name)
# print("\nUploading to Azure Storage as blob:\n\t" + model_trained_name)

# with open(file=model_trained_path, mode="rb") as data:
#     blob_client.upload_blob(data)