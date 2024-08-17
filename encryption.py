import base64


def load_secret():
    with open('secret', 'r') as file:
        return file.read().strip()


def encrypt_number(number):
    secret = load_secret()
    number_bytes = str(number).encode('utf-8')

    secret_bytes = secret.encode('utf-8')
    encrypted_bytes = bytearray()

    for i in range(len(number_bytes)):
        encrypted_bytes.append(number_bytes[i] ^ secret_bytes[i % len(secret_bytes)])

    # URL-safe Base64 encode the encrypted bytes
    encrypted = base64.urlsafe_b64encode(encrypted_bytes).rstrip(b'=')

    return encrypted.decode('utf-8')


def decrypt_number(encrypted):
    secret = load_secret()
    encrypted_bytes = base64.urlsafe_b64decode(encrypted + '==')

    secret_bytes = secret.encode('utf-8')
    decrypted_bytes = bytearray()

    for i in range(len(encrypted_bytes)):
        decrypted_bytes.append(encrypted_bytes[i] ^ secret_bytes[i % len(secret_bytes)])

    return int(decrypted_bytes.decode('utf-8'))


def main():
    secret = load_secret()

    # Example number to encrypt
    number = 1234567890

    encrypted = encrypt_number(number)
    print(f"Encrypted: {encrypted}")

    decrypted = decrypt_number(encrypted)
    print(f"Decrypted: {decrypted}")


if __name__ == "__main__":
    main()
