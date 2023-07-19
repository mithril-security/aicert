#!/usr/bin/env bash

set -ex


echo '[ -z "${POETRY_ACTIVE}" ] || source $(poetry env info --path)/bin/activate' >> ~/.zshrc