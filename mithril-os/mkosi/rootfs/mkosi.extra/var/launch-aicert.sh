#!/bin/bash

set -e
set -x

# Directory containing .tar files with the docker images
tar_dir="/opt/container-images"

# Sanity check : Make sure the directory exists
if [ ! -d "$tar_dir" ]; then
  echo "Directory does not exist: $tar_dir"
  exit 1
fi

# Loop through .tar files in the directory
for tar_file in "$tar_dir"/*.tar; do
    echo "Loading Docker image from: $tar_file"
    docker load --input="$tar_file"
done

echo "Finished loading Docker images from $tar_dir"

docker compose -f /var/docker-compose.yml up
