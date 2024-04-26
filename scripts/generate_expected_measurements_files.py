#!/usr/bin/env python3.11

from compute_expected_pcr4 import compute_golden_pcr4, Target
import json

# PCR0, PCR1, PCR2, PCR3 are related to the firmware and are therefore target specific
# PCR4 must be as precomputed. PCR4 measures the entire UKI and ensures that we execute 
# the expected OS

# systemd-stub measurements
# PCR12 : Overridden kernel command line, credentials, foo.efi.extra.d/*.addon.efi
# We don't use any of those features (and those features can be used to bypass security)
# --> MUST be a sequence of 00s 
# PCR13: System Extensions
# --> MUST be a sequence of 00s

# On Azure PCR[1], PCR[2], PCR[3]:
# Only one event measured in the PCR EV_SEPARATOR 
# whose hash is stardized to be df3f619804a92fdb4057192dc43dd748ea778adc52bc498ce80524c014b81119
# --> Starting with 00s in PCR TPM_Extend(EV_SEPARATOR) = "3d458cfe55cc03ea1f443f1562beec8df51c75e14a9fcf9a7234a13f198e7969"
golden_pcr4_azure = compute_golden_pcr4("local/os_disk.raw",target= Target.AZURE_TRUSTED_LAUNCH)

golden_measurements_azure = {
    'measurements':
        {
            0: "4847edbe7ffb070581e1da6d4f03f8019fd46b86cf97f2079cc400c62a662e0a",
            1: "3d458cfe55cc03ea1f443f1562beec8df51c75e14a9fcf9a7234a13f198e7969",
            2: "3d458cfe55cc03ea1f443f1562beec8df51c75e14a9fcf9a7234a13f198e7969",
            3: "3d458cfe55cc03ea1f443f1562beec8df51c75e14a9fcf9a7234a13f198e7969",
            4: golden_pcr4_azure.hex(),
            12: "0000000000000000000000000000000000000000000000000000000000000000",
            13: "0000000000000000000000000000000000000000000000000000000000000000"
        }
}

with open("client/aicert/cli/security_config/measurements_azure.json", 'w') as json_file:
    json.dump(golden_measurements_azure, json_file, indent=4)

golden_pcr4_qemu = compute_golden_pcr4("local/os_disk.raw",target= Target.QEMU)

golden_measurements_qemu = {
    'measurements':
        {
            0: "7a3aef1f264580a9951faf514b342effc88393d33250c82672cc9e61fe8bd45c",
            1: "e770a9ec2d9b42e102170f18622f2b2416b3ca2120f99745889345d059c07152",
            2: "3410b9935d57037330b3c0865afaa89ce8efb59e84548029bb8685f5d33839d2",
            3: "3d458cfe55cc03ea1f443f1562beec8df51c75e14a9fcf9a7234a13f198e7969",
            4: golden_pcr4_qemu.hex(),
            12: "0000000000000000000000000000000000000000000000000000000000000000",
            13: "0000000000000000000000000000000000000000000000000000000000000000"
        }
}

with open("client/aicert/cli/security_config/measurements_qemu.json", 'w') as json_file:
    json.dump(golden_measurements_qemu, json_file, indent=4)

with open("client/aicert/cli/security_config/container_measurements.json", 'w') as json_file:
    file = open("local/container_ids.json")
    container_ids = json.load(file)
    json.dump(container_ids, json_file, indent=4)
