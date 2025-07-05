import base64
from typing import Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.core.config import settings
from app.core.exceptions import AppException


class EncryptionError(AppException):
    def __init__(self, message: str = "Encryption operation failed"):
        super().__init__(
            message=message,
            code="ENCRYPTION_ERROR",
            status_code=500
        )


class CredentialEncryption:
    """Service for encrypting and decrypting sensitive credential data"""
    
    def __init__(self, master_key: Optional[str] = None):
        """
        Initialize encryption service with master key
        
        Args:
            master_key: Master encryption key. If not provided, uses settings.secret_key
        """
        if not master_key:
            master_key = settings.secret_key
            
        if not master_key:
            raise EncryptionError("No master key provided for encryption")
        
        # Derive encryption key from master key using PBKDF2
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'docker-control-platform-salt',  # In production, use a random salt per deployment
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(master_key.encode()))
        self.cipher = Fernet(key)
    
    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a plaintext string
        
        Args:
            plaintext: The string to encrypt
            
        Returns:
            Base64-encoded encrypted string
            
        Raises:
            EncryptionError: If encryption fails
        """
        try:
            if not plaintext:
                return ""
            encrypted_bytes = self.cipher.encrypt(plaintext.encode())
            return encrypted_bytes.decode()
        except Exception as e:
            raise EncryptionError(f"Failed to encrypt data: {str(e)}")
    
    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt an encrypted string
        
        Args:
            ciphertext: Base64-encoded encrypted string
            
        Returns:
            Decrypted plaintext string
            
        Raises:
            EncryptionError: If decryption fails
        """
        try:
            if not ciphertext:
                return ""
            decrypted_bytes = self.cipher.decrypt(ciphertext.encode())
            return decrypted_bytes.decode()
        except Exception as e:
            raise EncryptionError(f"Failed to decrypt data: {str(e)}")
    
    def encrypt_dict(self, data: dict) -> dict:
        """
        Encrypt all string values in a dictionary
        
        Args:
            data: Dictionary with string values to encrypt
            
        Returns:
            Dictionary with encrypted values
        """
        encrypted_data = {}
        for key, value in data.items():
            if isinstance(value, str):
                encrypted_data[key] = self.encrypt(value)
            else:
                encrypted_data[key] = value
        return encrypted_data
    
    def decrypt_dict(self, data: dict) -> dict:
        """
        Decrypt all string values in a dictionary
        
        Args:
            data: Dictionary with encrypted string values
            
        Returns:
            Dictionary with decrypted values
        """
        decrypted_data = {}
        for key, value in data.items():
            if isinstance(value, str) and value:
                try:
                    decrypted_data[key] = self.decrypt(value)
                except EncryptionError:
                    # If decryption fails, assume it's not encrypted
                    decrypted_data[key] = value
            else:
                decrypted_data[key] = value
        return decrypted_data


# Global instance
_encryption_service: Optional[CredentialEncryption] = None


def get_encryption_service() -> CredentialEncryption:
    """Get or create the global encryption service instance"""
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = CredentialEncryption()
    return _encryption_service