import pytest 
from fastapi import FastAPI
from fastapi.testclient import TestClient


def start_application():
    app = FastAPI()

    return app




class ModelName:
    def __init__(self, name) -> None:
        self.name = name
    def __eq__(self, name) -> bool:
        return self.name == name

@pytest.fixture
def model_name():
    return ModelName("llama2")

class DatasetName: 
    def __init__(self, name) -> None:
        self.name = name
    def __eq__(self, name) -> bool:
        return self.name == name

@pytest.fixture
def dataset_name():
    return DatasetName("dataset/alpaca2")

