import yaml 
from aicert_common.protocol import Resource
import sys


class AxolotlConfig:
    """Axolotl yaml config file

    Methods : 
        - Verifies that the file uploaded is a valid Yaml file
        - Extracts the hashes of the model and dataset to be cloned

    """
    filename: str
    valid: bool = False

    __modelname: str = ""
    __modelhash: str = ""
    __datasetname: str = ""
    __datasethash: str = ""

    model_resource : Resource
    dataset_resource : Resource

    config: dict

    @classmethod
    def __verify_config_file(cls, yaml_config: str) -> bool:
        """Verifies yaml configuration and inserts into file

        
        """
        try:
            cls.config = yaml.safe_load(yaml_config)
            return True
        except:
            print(f"Error")
            return False
        
    @classmethod 
    def __extract_model(cls) -> None: 
        """Extracts the model repo and the hash 

        
        """
        cls.__modelname, cls.__modelhash = cls.config['base_model'].split("@")
    
    @classmethod
    def __extract_dataset(cls) -> None:
        """Extracts the dataset repo and the hash
        
        """

        cls.__datasetname, cls.__datasethash = cls.config['datasets'][0]['path'].split("@")
    
    @classmethod 
    def initialize(cls, config_file: str):
        cls.__verify_config_file(config_file)
        AxolotlConfig.__extract_model()
        AxolotlConfig.__extract_dataset()

    @classmethod
    def parse(cls, resource_path) -> None:
        """Setup resources ModelResource & datasetResource
            Setup the axolotl configuration and changing the model name
            and the dataset path 

            Returns the Axolotl configuration to be saved in workspace for 
            usage 
        """
        cls.model_resource = {
            'resource_type':'model', 
            'repo' : cls.__modelname,
            'hash' : cls.__modelhash,
            'path' : str(resource_path)
        }
        
        cls.dataset_resource = {
            'resource_type' : "dataset",
            'repo' : cls.__datasetname,
            'hash' : cls.__datasethash,
            'path' : str(resource_path)
        }
    

        cls.config['base_model'] = cls.__modelname
        cls.config['datasets'][0]['path'] = cls.__datasetname



