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
        else:
            self._set_file_permissions(key_file)

        self.fernet = Fernet(self._load_key())

    def _generate_key(self):
        key = Fernet.generate_key()
        with open(self.key_file, 'wb') as key_file:
            key_file.write(key)
        self._set_file_permissions(self.key_file)

    def _load_key(self):
        with open(self.key_file, 'rb') as key_file:
            return key_file.read()

    def _set_file_permissions(self, file_path):
        os.chmod(file_path, 0o600)  # Read and write only for the owner

    def save_credentials(self, username, password):
        credentials = {
            "username": username,
            "password": password
        }

        encrypted_config = self.fernet.encrypt(json.dumps(credentials).encode())
        with open(self.config_file, 'wb') as file:
            file.write(encrypted_config)
        self._set_file_permissions(self.config_file)
        print("Credentials saved successfully.")

    def get_credentials(self):
        try:
            credentials = self.load_credentials()
            return credentials['username'], credentials['password']
        except FileNotFoundError:
            return self.prompt_and_save_credentials()

    def load_credentials(self):
        if not os.path.exists(self.config_file):
            raise FileNotFoundError("Credentials file not found.")

        with open(self.config_file, 'rb') as file:
            encrypted_config = file.read()
        decrypted_config = self.fernet.decrypt(encrypted_config)
        return json.loads(decrypted_config)

    def delete_credentials(self):
        if os.path.exists(self.config_file):
            os.remove(self.config_file)
            print("Credentials have been deleted.")
        else:
            print("No saved credentials found.")

    def prompt_and_save_credentials(self):
        username = input("Enter your username: ")
        password = getpass("Enter your password: ")
        save_choice = input("Do you want to save these credentials? (y/n): ").lower()
        if save_choice == 'y':
            self.save_credentials(username, password)
        return username, password

if __name__ == "__main__":
    store = CredentialStore()
    store.prompt_and_save_credentials()
