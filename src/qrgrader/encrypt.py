from cryptography.fernet import Fernet
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
import base64
import os
import argparse

def encrypt(message, password):
    salt = os.urandom(16)
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    fernet = Fernet(key)
    token = fernet.encrypt(message.encode())
    return base64.urlsafe_b64encode(salt + token).decode()

def decrypt(token_text, password):
    data = base64.urlsafe_b64decode(token_text.encode())
    salt, token = data[:16], data[16:]
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    fernet = Fernet(key)
    return fernet.decrypt(token).decode()

def main():
    # Argument parser to handle command line arguments

    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--file', help='File to encrypt', default='secret.txt')
    args = vars(parser.parse_args())




    with open(args['file'], 'r') as file:
        secret_message = file.read()
        passwd = input("Enter password for encryption: ")
        # Usage
        cipher_text = encrypt(secret_message, passwd)
        plain_text = decrypt(cipher_text, passwd)
        print(f"Cipher Text: {cipher_text}")
        print(f"Decrypted Text: {plain_text}")


if __name__ == '__main__':
    main()