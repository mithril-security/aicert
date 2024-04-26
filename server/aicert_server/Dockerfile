FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y tpm2-tools && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

WORKDIR /code

COPY . .
RUN pip install . && groupadd docker && usermod -aG docker root

WORKDIR /code/aicert_server
CMD ["python3", "main.py"]