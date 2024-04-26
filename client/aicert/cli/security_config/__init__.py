import importlib
import json

qemu_measurements = json.loads(
            importlib.resources.files(__package__)  # type: ignore
            .joinpath("measurements_qemu.json")
            .read_text()
        )
qemu_measurements = {
            int(k): v.lower()
            for k, v in qemu_measurements["measurements"].items()
        }

azure_measurements = json.loads(
            importlib.resources.files(__package__)  # type: ignore
            .joinpath("measurements_azure.json")
            .read_text()
        )
azure_measurements = {
            int(k): v.lower()
            for k, v in azure_measurements["measurements"].items()
        }

EXPECTED_OS_MEASUREMENTS = {
    "SIMULATION_QEMU": qemu_measurements,
    "AZURE_TRUSTED_LAUNCH": azure_measurements,
}

CONTAINER_MEASUREMENTS = json.loads(
            importlib.resources.files(__package__)  # type: ignore
            .joinpath("container_measurements.json")
            .read_text()
        )