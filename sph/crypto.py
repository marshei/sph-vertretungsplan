import base64
import hashlib
import logging

from Cryptodome import Random
from Cryptodome.Cipher import AES
from Cryptodome.Cipher import PKCS1_v1_5 as Cipher_PKCS1_v1_5
from Cryptodome.PublicKey import RSA
from Cryptodome.Util.Padding import pad, unpad


def bytes_to_key(data, salt, output=48):
    # extended from https://gist.github.com/gsakkis/4546068
    assert len(salt) == 8, len(salt)
    data += salt
    key = hashlib.md5(data).digest()
    final_key = key
    while len(final_key) < output:
        key = hashlib.md5(key + data).digest()
        final_key += key
    return final_key[:output]


class AesCrypto:

    def __init__(self) -> None:
        super().__init__()
        self.BLOCK_SIZE = 16

    def encrypt(self, message, passphrase):
        salt = Random.new().read(8)
        key_iv = bytes_to_key(passphrase, salt, 32 + 16)
        key = key_iv[:32]
        iv = key_iv[32:]
        aes = AES.new(key, AES.MODE_CBC, iv)
        return base64.b64encode(b"Salted__" + salt + aes.encrypt(pad(message, self.BLOCK_SIZE)))

    def decrypt(self, encrypted, passphrase):
        encrypted = base64.b64decode(encrypted)
        assert encrypted[0:8] == b"Salted__"
        salt = encrypted[8:16]
        key_iv = bytes_to_key(passphrase, salt, 32 + 16)
        key = key_iv[:32]
        iv = key_iv[32:]
        aes = AES.new(key, AES.MODE_CBC, iv)
        return unpad(aes.decrypt(encrypted[16:]), self.BLOCK_SIZE)

    def cycle(self, message, passphrase):
        message = message.encode("utf-8")
        passphrase = passphrase.encode("utf-8")
        print("Original data:")
        print(message)

        encrypted = self.encrypt(message, passphrase)
        print("Encrypted data:")
        print(encrypted)

        decrypted = self.decrypt(encrypted, passphrase)
        print("Decrypted data:")
        print(decrypted)

        if decrypted != message:
            raise Exception("Failed to decrypt message!")

        print("")


class RsaCrypto:

    def __init__(self, public_key: str) -> None:
        self.public_key = RSA.importKey(public_key)
        self.key_length = self.public_key.size_in_bits() + 1
        self.default_length = self.key_length / 8
        # logging.debug("Length of public key: %d Bits -> Default data length: %d"
        #               % (self.key_length, self.default_length))
        self.cipher_rsa = Cipher_PKCS1_v1_5.new(self.public_key)

    def encrypt(self, message: bytes) -> bytes:
        # Encrypt the message with the public RSA key
        encrypted = base64.b64encode(self.cipher_rsa.encrypt(message))
        # logging.debug("Original Message : %s\nEncrypted Message: %s\n"
        #              % (message.decode("utf-8"), encrypted.decode("utf-8")))
        return encrypted

    def decrypt(self, message: bytes) -> bytes:
        ciphertext = base64.b64decode(message)
        length = len(ciphertext)
        offset = 0
        result = []
        while offset < length:
            remaining = length - offset
            if remaining > self.default_length:
                current_length = self.default_length
            else:
                current_length = remaining
            logging.debug("Current length: %d" % current_length)
            result.append(self.cipher_rsa.decrypt(ciphertext[offset: offset + current_length], b'DECRYPTION FAILED'))
            offset += current_length

        plaintext = b''.join(result)
        logging.debug("Encrypted Message: %s\nDecrypted Message: %s\n"
                      % (message.decode("utf-8"), plaintext.decode("utf-8")))
        return plaintext
