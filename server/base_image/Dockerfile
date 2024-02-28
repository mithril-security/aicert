FROM python:3.10.12-alpine3.18
RUN apk update && \
    apk add --no-cache git curl tar && \
    curl -sSL https://install.python-poetry.org | POETRY_VERSION=1.2.0 python3 -
ENV PATH=$PATH:/root/.local/bin
WORKDIR /mnt
