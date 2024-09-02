from cryptography.fernet import Fernet
import json
import os
from getpass import getpass

class CredentialStore:
    def __init__(self, config_file='config.json', key_file='secret.key'):
        self.config_file = config_file
        self.key_file = key_file

        if not os.path.exists(key_file):
            self._generate_key()

        self.fernet = Fernet(self._load_key())

    def _generate_key(self):
        key = Fernet.generate_key()
        with open(self.key_file, 'wb') as key_file:
            key_file.write(key)

    def _load_key(self):
        with open(self.key_file, 'rb') as key_file:
            return key_file.read()

    def save_credentials(self):
        username = input("Enter your username: ")
        password = getpass("Enter your password: ")

        credentials = {
            "username": username,
            "password": password
        }

        encrypted_config = self.fernet.encrypt(json.dumps(credentials).encode())
        with open(self.config_file, 'wb') as file:
            file.write(encrypted_config)
        print("Credentials saved successfully.")

    def load_credentials(self):
        with open(self.config_file, 'rb') as file:
            encrypted_config = file.read()
        decrypted_config = self.fernet.decrypt(encrypted_config)
        return json.loads(decrypted_config)

# Usage example (run this once to set up your credentials)
if __name__ == "__main__":
    store = CredentialStore()
    store.save_credentials()
