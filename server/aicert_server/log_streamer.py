import docker 
import os
import logging
import json
import time

class LogStreamer:
    """LogStreamer, register the stream outputed by a container

    
    """
    log_file: str = ""
    logger: logging.Logger
    filehandler: logging.FileHandler

    def __init__(self, log_file: str) -> None:
        self.log_file = os.path.realpath(log_file)
        self.filehandler = logging.FileHandler(log_file)

    def __setup_logger(self):
        self.logger = logging.getLogger("log_outputs")
        self.logger.setLevel(logging.DEBUG)
        formatter=logging.Formatter('{"time":"%(asctime)s", "name": "%(name)s", "level": "%(levelname)s", "message": "%(message)s"}')
        # formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.filehandler.setFormatter(formatter)
        self.logger.addHandler(self.filehandler)

    def write_stream(self, container: docker.models.containers.Container):
        self.__setup_logger()
        for log in container.logs(stdout=True, stderr=False, stream=True):
            self.logger.info(f"{log}")

        self.logger.removeHandler(self.filehandler)
        self.filehandler.close()
