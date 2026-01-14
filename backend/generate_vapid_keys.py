
import base64
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

def generate_vapid_keys():
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_key = private_key.public_key()

    # Private Key (Base64 URL Safe)
    private_val = private_key.private_numbers().private_value
    private_bytes = private_val.to_bytes(32, byteorder='big')
    private_b64 = base64.urlsafe_b64encode(private_bytes).decode('utf-8').rstrip('=')

    # Public Key (Uncompressed Point -> Base64 URL Safe)
    public_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint
    )
    public_b64 = base64.urlsafe_b64encode(public_bytes).decode('utf-8').rstrip('=')

    print("VAPID_PRIVATE_KEY=" + private_b64)
    print("VAPID_PUBLIC_KEY=" + public_b64)
    print("VAPID_CLAIM_EMAIL=mailto:your-email@example.com")

if __name__ == "__main__":
    generate_vapid_keys()
