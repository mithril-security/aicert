#!/bin/bash

set -e

## Load config
source upload_config.sh

upload_disk () {
    DISK_SIZE=`qemu-img info  --output json local/$1.raw | jq '."virtual-size"'`
    DISK_SIZE_K=$(((DISK_SIZE + 1023) / 1024))
    DISK_SIZE_M=$(((DISK_SIZE_K + 1023) / 1024))

    qemu-img resize -f raw local/$1.raw "${DISK_SIZE_M}M"
    qemu-img convert -q -f raw -o subformat=fixed,force_size -O vpc local/$1.raw local/$1.img.vhd

    DISK_NAME=$2

    DISK_SIZE=`qemu-img info --output json  local/$1.img.vhd | jq '."virtual-size"'`

    az disk create \
        -g $AZ_RESOURCE_GROUP \
        -n $DISK_NAME \
        -l $AZ_REGION \
        --os-type Linux \
        --upload-type Upload \
        --upload-size-bytes $DISK_SIZE \
        --sku StandardSSD_LRS \
        --security-type TrustedLaunch \
        --hyper-v-generation V2

    URL_ACCESS_SAS=`az disk grant-access -n $DISK_NAME -g $AZ_RESOURCE_GROUP --access-level Write --duration-in-seconds 86400 | jq -r '.accessSas'`
    azcopy copy --blob-type PageBlob "local/$1.img.vhd" "$URL_ACCESS_SAS"
    az disk revoke-access -n $DISK_NAME -g $AZ_RESOURCE_GROUP
}

## Create a resource group as defined in the upload config
az group create -l $AZ_REGION -n $AZ_RESOURCE_GROUP 

## Randomised ID to make disk and VM name unique for each run of this script 
ID=`openssl rand -hex 6`


## OS disk upload
OS_DISK_NAME="aicert-osdisk-$ID"
upload_disk "os_disk" $OS_DISK_NAME
echo "Uploaded OS disk"
echo "$OS_DISK_NAME"

## Create OS Image
DISK=$(az disk show -n $OS_DISK_NAME -g $AZ_RESOURCE_GROUP --query "id" | xargs )
IMAGEDEF="aicert_image"

az sig create --resource-group $AZ_RESOURCE_GROUP --gallery-name $GALLERY_NAME

az sig image-definition create \
    --resource-group $AZ_RESOURCE_GROUP --location $AZ_REGION --gallery-name $GALLERY_NAME \
    --gallery-image-definition $IMAGEDEF --publisher TrustedLaunchPublisher --offer TrustedLaunchOffer \
    --sku TrustedLaunchSku --os-type Linux --os-state Generalized \
    --hyper-v-generation V2 --features SecurityType=TrustedLaunch


az sig image-version create --resource-group $AZ_RESOURCE_GROUP \
    --gallery-name $GALLERY_NAME --gallery-image-definition $IMAGEDEF \
    --gallery-image-version 1.0.0 \
    --os-snapshot $DISK

az storage account create -n $STORAGE_ACCOUNT -g $AZ_RESOURCE_GROUP -l $AZ_REGION --sku Standard_LRS

az storage container create -n $STORAGE_CONTAINER --account-name $STORAGE_ACCOUNT

## Create terraform variables for resource group and gallery name
file="client/aicert/cli/deployment/deploy/terraform.tfvars"

echo -e "resource_group_name = \"$AZ_RESOURCE_GROUP\"\ngallery_name = \"$GALLERY_NAME\"\nstorage_account = \"$STORAGE_ACCOUNT\"\nstorage_container = \"$STORAGE_CONTAINER\"" > $file 