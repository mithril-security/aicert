FROM python:3.10.12-alpine3.18
RUN apk update && \
    apk add --no-cache git curl tar git-lfs && \
    curl -sSL https://install.python-poetry.org | POETRY_VERSION=1.2.0 python3 -
RUN pip install huggingface_hub
ENV PATH=$PATH:/root/.local/bin

WORKDIR /mnt
