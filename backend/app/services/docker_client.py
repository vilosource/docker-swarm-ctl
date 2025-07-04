from typing import Optional, Dict, Any
import docker
from docker.client import DockerClient
from docker.errors import DockerException, APIError

from app.core.config import settings
from app.core.exceptions import DockerConnectionError, DockerOperationError


class DockerClientFactory:
    _client: Optional[DockerClient] = None
    
    @classmethod
    def get_client(cls) -> DockerClient:
        if cls._client is None:
            cls._client = cls._create_client()
        
        try:
            cls._client.ping()
        except (DockerException, APIError):
            cls._client = cls._create_client()
        
        return cls._client
    
    @classmethod
    def _create_client(cls) -> DockerClient:
        try:
            if settings.docker_host:
                kwargs = {
                    "base_url": settings.docker_host
                }
                
                if settings.docker_tls_verify and settings.docker_cert_path:
                    tls_config = docker.tls.TLSConfig(
                        client_cert=(
                            f"{settings.docker_cert_path}/cert.pem",
                            f"{settings.docker_cert_path}/key.pem"
                        ),
                        ca_cert=f"{settings.docker_cert_path}/ca.pem",
                        verify=True
                    )
                    kwargs["tls"] = tls_config
                
                client = docker.DockerClient(**kwargs)
            else:
                client = docker.from_env()
            
            client.ping()
            return client
            
        except DockerException as e:
            raise DockerConnectionError(f"Failed to connect to Docker daemon: {str(e)}")
    
    @classmethod
    def close(cls):
        if cls._client:
            cls._client.close()
            cls._client = None


def get_docker_client() -> DockerClient:
    return DockerClientFactory.get_client()


def handle_docker_errors(operation: str):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except APIError as e:
                raise DockerOperationError(operation, str(e))
            except DockerException as e:
                raise DockerOperationError(operation, str(e))
            except Exception as e:
                raise DockerOperationError(operation, f"Unexpected error: {str(e)}")
        return wrapper
    return decorator