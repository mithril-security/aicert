#!/bin/bash

set -e

# Create a Mithril OS disk
earthly -i -P +mithril-os --OS_CONFIG='config.yaml'

# Upload the OS disk to Azure and convert it into an OS image
./upload.sh

# Generate OS measurements
./scripts/generate_expected_measurements_files.py