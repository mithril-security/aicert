import docker 
import os
import logging


class LogStreamer:
    """LogStreamer, register the stream outputed by a container

    
    """
    log_file: str = ""
    logger: logging.Logger

    def __init__(self, log_file: str) -> None:
        self.log_file = os.path.realpath(log_file)

    def __setup_logger(self):
        self.logger = logging.getLogger("log_outputs")
        self.logger.setLevel(logging.DEBUG)
        file_handler = logging.FileHandler(self.log_file)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

    def write_stream(self, container: docker.models.containers.Container):
        self.__setup_logger()
        for log in container.logs(stdout=True, stderr=False, stream=True):
            self.logger.info(f"{log}")

