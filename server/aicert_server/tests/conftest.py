import pytest 
from fastapi import FastAPI
from typing import Generator, Any
from fastapi.testclient import TestClient

from aicert_server.main import app



def start_application():
    # app = FastAPI()
    return app


@pytest.fixture(scope="module")
def app() -> Generator[FastAPI, Any, None]:
    _app = start_application()
    yield _app

@pytest.fixture(scope="module")
def client(app: FastAPI) -> Generator[TestClient, Any, None]:

    with TestClient(app) as client:
        yield client


class ModelName:
    def __init__(self, name) -> None:
        self.name = name
    def __eq__(self, name) -> bool:
        return self.name == name

@pytest.fixture(scope="module")
def model_name():
    return ModelName("llama2")

class DatasetName: 
    def __init__(self, name) -> None:
        self.name = name
    def __eq__(self, name) -> bool:
        return self.name == name

@pytest.fixture(scope="module")
def dataset_name():
    return DatasetName("dataset/alpaca2")

