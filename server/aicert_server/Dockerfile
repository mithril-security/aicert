#FROM python:3.12 as requirements-stage
#
#WORKDIR /code
#
#RUN pip install poetry
#COPY ./pyproject.toml ./poetry.lock* /code/
#RUN poetry export -f requirements.txt --output requirements.txt

FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y tpm2-tools && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

WORKDIR /code

COPY . .
#COPY --from=requirements-stage /code/requirements.txt /code/requirements.txt
#RUN pip install --no-cache-dir -r /code/aicert_server/requirements.txt
RUN pip install . && groupadd docker && usermod -aG docker root
#COPY ./aicert_server /code/aicert_server

WORKDIR /code/aicert_server
CMD ["python3", "main.py"]