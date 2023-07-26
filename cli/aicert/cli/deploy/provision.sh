#!/bin/bash

terraform output -raw tls_private_key > private_key.pem
chmod 600 private_key.pem
VM_IP="$(terraform output -raw public_ip_address)" envsubst < inventory.ini.tmpl > inventory.ini

openssl ecparam -genkey -name prime256v1 -out client.key
openssl req -new -key client.key -out client.csr -subj "/C=US/ST=California/L=San Francisco/O=My Company/CN=mydomain.com"
openssl x509 -req -days 365 -in client.csr -signkey client.key -out client.crt

ansible-playbook -i inventory.ini deploy.yml