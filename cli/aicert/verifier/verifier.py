import json

def verify(json_name: str):
    print(json_name)

def pprint(json_name: str):
    f = open(json_name)
    dictionary = json.load(f)
    print(dictionary)