import base64
import hashlib
import json
import subprocess
import tempfile
from OpenSSL import crypto
import requests
import yaml

from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.x509 import load_der_x509_certificate

req = requests.get("http://crl.microsoft.com/pkiinfra/certs/AMERoot_ameroot.crt")
req.raise_for_status()
ROOT_CERT_DER = req.content


class AttestationError(Exception):
    """This exception is raised when the attestation is invalid (enclave
    settings mismatching, debug mode unallowed...).

    Used as base exception for all other sub exceptions on the attestation
    validation
    """

    pass


def verify_ak_cert(cert_chain: list[bytes]) -> bytes:
    """
    Verify the certificate chain of the attestation key.
    Parameters:
        cert_chain: list of certificates in DER format
    Returns:
        AK certificate in DER format
    Raises:
        AttestationError: if the certificate chain is invalid
    """

    # Load certificate to be verified : attestation key certificate
    ak_cert = crypto.load_certificate(crypto.FILETYPE_ASN1, cert_chain[0])

    # Verify the certificate's chain
    store = crypto.X509Store()

    # Create the CA cert object from PEM string, and store into X509Store
    _rootca_cert = crypto.load_certificate(crypto.FILETYPE_ASN1, ROOT_CERT_DER)  # type: ignore
    store.add_cert(_rootca_cert)

    chain = [
        crypto.load_certificate(crypto.FILETYPE_ASN1, _cert_der)
        for _cert_der in cert_chain[1:-1]
    ]

    store_ctx = crypto.X509StoreContext(store, ak_cert, chain=chain)

    try:
        # if the cert is invalid, it will raise a X509StoreContextError
        store_ctx.verify_certificate()
    except crypto.X509StoreContextError:
        raise AttestationError("Invalid AK certificate")

    return cert_chain[0]


def check_quote(quote, pub_key_pem):
    """
    Check quote using tpm2_checkquote command.
    Parameters:
         quote: dictionary with keys 'message', 'signature', and 'pcr'
         pub_key_pem: public key in PEM format (string)
    Returns:
    Raises:


    """
    with tempfile.NamedTemporaryFile() as quote_msg_file, tempfile.NamedTemporaryFile() as quote_sig_file, tempfile.NamedTemporaryFile() as quote_pcr_file, tempfile.NamedTemporaryFile() as ak_pub_key_file:
        quote_msg_file.write(quote["message"])
        quote_msg_file.flush()

        quote_sig_file.write(quote["signature"])
        quote_sig_file.flush()

        quote_pcr_file.write(quote["pcr"])
        quote_pcr_file.flush()

        ak_pub_key_file.write(pub_key_pem)
        ak_pub_key_file.flush()

        tpm2_checkquote = subprocess.run(
            [
                "tpm2_checkquote",
                "--public",
                ak_pub_key_file.name,
                "--message",
                quote_msg_file.name,
                "--pcr",
                quote_pcr_file.name,
                "--signature",
                quote_sig_file.name,
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        return yaml.load(tpm2_checkquote.stdout, Loader=yaml.BaseLoader)



with open('sample_build_response.json') as f:
   build_response = json.load(f)

def decode_b64_encoding(x):
    return base64.b64decode(x["base64"])


build_response["remote_attestation"]["cert_chain"] = [
    decode_b64_encoding(cert_b64_encoded)
    for cert_b64_encoded in build_response["remote_attestation"]["cert_chain"]
]

ak_cert = verify_ak_cert(cert_chain=build_response["remote_attestation"]["cert_chain"])
ak_cert_ = load_der_x509_certificate(ak_cert)
ak_pub_key = ak_cert_.public_key()
ak_pub_key_pem = ak_pub_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo,
)

build_response["remote_attestation"]["quote"] = {
    k: decode_b64_encoding(v)
    for k, v in build_response["remote_attestation"]["quote"].items()
}
att_document = check_quote(
    build_response["remote_attestation"]["quote"], ak_pub_key_pem
)
# print(att_document)


# We should check the PCR to make sure the system has booted properly
# This is an example ... the real thing will depend on the system.
assert (
    att_document["pcrs"]["sha256"]["0"]
    == "0xD0D725F21BA5D701952888BCBC598E6DCEF9AFF4D1E03BB3606EB75368BAB351"
)
assert (
    att_document["pcrs"]["sha256"]["1"]
    == "0xFE72566C7F411900F7FA1B512DAC0627A4CAC8C0CB702F38919AD8C415CA47FC"
)
assert (
    att_document["pcrs"]["sha256"]["2"]
    == "0x3D458CFE55CC03EA1F443F1562BEEC8DF51C75E14A9FCF9A7234A13F198E7969"
)
assert (
    att_document["pcrs"]["sha256"]["3"]
    == "0x3D458CFE55CC03EA1F443F1562BEEC8DF51C75E14A9FCF9A7234A13F198E7969"
)
assert (
    att_document["pcrs"]["sha256"]["4"]
    == "0x1F0105624AB37B9AF59DA6618A406860E33EF6F42A38DDAF6ABFAB8F23802755"
)
assert (
    att_document["pcrs"]["sha256"]["5"]
    == "0xD36183A4CE9F539D686160695040237DA50E4AD80600607F84EFF41CF394DCD8"
)


def check_event_log(
    input_event_log,
    pcr_end,
    initial_pcr="0000000000000000000000000000000000000000000000000000000000000000",
):
    # Starting from the expected initial PCR state
    # We replay the event extending the PCR
    # At the end we get the expected PCR value 
    initial_pcr = bytes.fromhex(initial_pcr)
    current_pcr = initial_pcr
    for e in input_event_log:
        hash_event = hashlib.sha256(e.encode()).digest()
        current_pcr = hashlib.sha256(current_pcr + hash_event).digest()

    print("PCR in quote :", pcr_end)
    print("Expected PCR based on event log and initial PCR", current_pcr.hex())
    # Both PCR MUST match, else something sketchy is going on!
    assert pcr_end == current_pcr.hex()

    # Now we can return the parsed event log
    event_log = [json.loads(e) for e in input_event_log]

    return event_log


# To make test easier we use the PCR 16 since it is resettable `tpm2_pcrreset 16`
# But because it is resettable it MUST NOT be used in practice.
# An unused PCR that cannot be reset (SRTM) MUST be used instead
# PCR 14 or 15 should do it
print(
    check_event_log(
        build_response["event_log"],
        att_document["pcrs"]["sha256"]["16"].lower().removeprefix("0x"),
    )
)
