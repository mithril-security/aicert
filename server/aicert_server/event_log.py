import hashlib
import json
from typing import Dict, Any, List, Tuple

from aicert_common.protocol import Resource, Build
from .tpm import quote, cert_chain, tpm_extend_pcr, PCR_FOR_MEASUREMENT


class EventLog:
    """Measured data in a structured format

    The event log functions as a chain of TPM-backed hashes.
    Every time an event is added, the backing PCR is "extended"
    with the new event. In practice this means that the TPM stores
    the hash of the previous PCR value and of new event data in the PCR.
    
    Args:
        simulation_mode (bool): if set to True, the TPM is not used at all
    """

    def __init__(self, simulation_mode: bool = False):
        self.__event_log = []
        self.__simulation_mode = simulation_mode

    def __append(self, event: Dict[str, Any]):
        """Private method: add an event to the event log, properly handling PCR extension
        
        Args:
            event (Dict[str, Any]): the structured event data
        """
        event_json = json.dumps(event)
        if self.__simulation_mode:
            print(f"SIMULATION MODE: {event}")
        else:
            hash_event = hashlib.sha256(event_json.encode()).hexdigest()
            tpm_extend_pcr(PCR_FOR_MEASUREMENT, hash_event)
        self.__event_log.append(event_json)

    def build_request_event(self, build_request: Build) -> None:
        """Add a build request event to the event log
        
        This event is used when the server receives a request.
        The content of the request is included in the event log.

        Args:
            build_requets (Build): build request (see aicert-common's protocol)
        """
        self.__append(
            {
                "event_type": "build_request",
                "content": {
                    "spec": {"build_request_proto": build_request.dict()},
                },
            }
        )

    def input_resource_event(self, resource: Resource, resource_hash: str) -> None:
        """Add an input resource event to the event log
        
        This event is used when the server has downloaded data that should be measured.
        The hash of the downloaded data is included in the event log.

        Args:
            resource (Resource): resource specs (see aicert-common's protocol)
            resource_hash (str): hash of the resource's downloaded data
        """
        self.__append(
            {
                "event_type": "input_resource",
                "content": {
                    "spec": {"resource_proto": resource.dict()},
                    "resolved": {"hash": resource_hash},
                },
            }
        )

    def input_image_event(self, input_image: str, input_image_id: str) -> None:
        """Add an input image event to the event log
        
        This event is used when the server has downloaded a docker image that should be measured.
        The identifier of the image is included in the event log.

        Args:
            input_image (str): name of the image
            input_image_id (str): id of the image
        """
        self.__append(
            {
                "event_type": "input_image",
                "content": {
                    "spec": {"image_name": input_image},
                    "resolved": {"id": input_image_id},
                },
            }
        )

    def configuration_event(self, configuration_file, configuration_file_hash) -> None: 
        """Add a configuration event to the event log
        
        This event is used to register the configuration file and its content. 
        We take into account the measurement of the configuration file so that it will serve
        as proof that axolotl was ran with the configuration file stated. 

        Args:
            configuration_file : Content of the configuration_file
            configuration_file_hash : Checksum of the configuration file content.
        """
        self.__append(
            {
                "event_type": "axolotl_configuration", 
                "content": {
                    "spec":  {"config_file": configuration_file},
                    "resolved": {"hash": configuration_file_hash},
                }
            }
        )

    def outputs_event(self, outputs: List[Tuple[str, str]]) -> None:
        """Add an outputs event to the event log
        
        This event is used after the build has completed, when the outputs must be measured.
        The hash of the outputs are included in the event log.

        Args:
            outputs (List[Tuple[str, str]]): list of output file names and corresponding hashes
        """
        self.__append(
            {
                "event_type": "outputs",
                "content": [
                    {"spec": {"path": path}, "resolved": {"hash": hash}}
                    for path, hash in outputs
                ],
            }
        )

    #def finetune(self, axolotl_config_filename, axolotl_config_hash, finetuning_image, image_hash) -> None:
    #    """Add a finetune event to the event log
    #    """
    #    self.__append(
    #        {
    #            "event_type": "finetuning",
    #            "content": [
    #                {
    #                    "spec": {"axolotl_config": axolotl_config_filename},
    #                    "resolved": {"hash": axolotl_config_hash}
    #                },
    #                {
    #                    "spec": {"image": finetuning_image},
    #                    "resolved": {"hash": image_hash}
    #                }
    #            ]
    #        }
    #    )

    def attest(self, ca_cert="") -> Dict[str, Any]:
        """Return the full event log, the TPM quote and the certificate chain in the same dict

        The TPM quote contains all the PCR values (including the one backing the event log).
        It is signed by the TPM key which can be verified through the cloud-provider certificate chain.

        In simulation mode, only the event log is return along with a special simulation_mode key.
        """
        return {
            "ca_cert": ca_cert,
            "event_log": self.__event_log,
            "remote_attestation": {"quote": quote(), "cert_chain": cert_chain()}
            if not self.__simulation_mode
            else {"simulation_mode": True},
        }
