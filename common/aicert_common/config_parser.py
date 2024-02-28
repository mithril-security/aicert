import yaml 
import hashlib
from .protocol import Resource


class AxolotlConfig:
    """Axolotl yaml config file

    Methods : 
        - Verifies that the file uploaded is a valid Yaml file
        - Extracts the hashes of the model and dataset to be cloned

    """
    filename: str
    valid: bool = False

    __modelname: str
    __modelhash: str
    __datasetname: str
    __datasethash: str

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
        cls.__modelname, cls.__modelhash = cls.config.base_model.split("@")
    
    @classmethod
    def __extract_dataset(cls) -> None:
        """Extracts the dataset repo and the hash
        
        """
        cls.__datasetname, cls.__datasethash = cls.config.datasets.path("@")
    
    


