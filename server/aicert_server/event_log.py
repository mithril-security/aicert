import hashlib
import json
from typing import Dict, Any, List, Tuple

from aicert_common.protocol import Resource, BuildRequest
from .tpm import quote, cert_chain, tpm_extend_pcr, PCR_FOR_MEASUREMENT


class EventLog:
    """
    >>> event_log = EventLog()
    >>> image = "python"
    >>> command = ("python3 main.py",)
    >>> artifact_pattern = "output.txt"
    >>> git_repo_url = "https://github.com/mithril-security/sample-test-repo.git"
    >>> event_start_build = {
    ...     "event_type": "start_build",
    ...     "image": image,
    ...     "command": command,
    ...     "artifact_pattern": artifact_pattern,
    ...     "git_repo_url": git_repo_url,
    ... }
    >>> event_log.append(event_start_build)
    """

    def __init__(self, simulation_mode: bool = False):
        self.__event_log = []
        self.__simulation_mode = simulation_mode

    def __append(self, event: Dict[str, Any]):
        event_json = json.dumps(event)
        if self.__simulation_mode:
            print(f"SIMULATION MODE: {event}")
        else:
            hash_event = hashlib.sha256(event_json.encode()).hexdigest()
            tpm_extend_pcr(PCR_FOR_MEASUREMENT, hash_event)
        self.__event_log.append(event_json)

    def build_request_event(self, build_request: BuildRequest) -> None:
        self.__append(
            {
                "event_type": "build_request",
                "content": {
                    "spec": {"build_request_proto": build_request.dict()},
                },
            }
        )

    def input_resource_event(self, resource: Resource, resource_hash: str) -> None:
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
        self.__append(
            {
                "event_type": "input_image",
                "content": {
                    "spec": {"image_name": input_image},
                    "resolved": {"id": input_image_id},
                },
            }
        )

    def outputs_event(self, outputs: List[Tuple[str, str]]) -> None:
        self.__append(
            {
                "event_type": "outputs",
                "content": [
                    {"spec": {"path": path}, "resolved": {"hash": hash}}
                    for path, hash in outputs
                ],
            }
        )

    def attest(self) -> Dict[str, Any]:
        return {
            "event_log": self.__event_log,
            "remote_attestation": {"quote": quote(), "cert_chain": cert_chain()}
            if not self.__simulation_mode
            else {"simulation_mode": True},
        }
