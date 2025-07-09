"""API client for communicating with the backend"""

import requests
from typing import Dict, Any, Optional, List
from urllib.parse import urljoin
import json


class APIError(Exception):
    """API error exception"""
    def __init__(self, message: str, status_code: int = None, details: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.details = details


class APIClient:
    """Client for Docker Swarm Control API"""
    
    def __init__(self, base_url: str, token: Optional[str] = None, verify_ssl: bool = True):
        self.base_url = base_url.rstrip('/')
        self.token = token
        self.verify_ssl = verify_ssl
        self.session = requests.Session()
        
        if token:
            self.session.headers['Authorization'] = f'Bearer {token}'
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make an HTTP request to the API"""
        url = urljoin(self.base_url + '/', endpoint.lstrip('/'))
        
        # Handle params for GET requests
        params = kwargs.pop('params', {})
        # Remove None values from params
        params = {k: v for k, v in params.items() if v is not None}
        
        try:
            response = self.session.request(
                method, 
                url, 
                params=params,
                verify=self.verify_ssl,
                **kwargs
            )
            response.raise_for_status()
            return response
        except requests.exceptions.HTTPError as e:
            # Extract error details from response
            try:
                error_data = e.response.json()
                message = error_data.get('detail', str(e))
            except:
                message = str(e)
            
            raise APIError(message, e.response.status_code, e.response.text)
        except requests.exceptions.RequestException as e:
            raise APIError(f"Request failed: {str(e)}")
    
    def get(self, endpoint: str, **params) -> Any:
        """Make a GET request"""
        response = self._make_request('GET', endpoint, params=params)
        return response.json() if response.text else None
    
    def post(self, endpoint: str, data: Any = None, **params) -> Any:
        """Make a POST request"""
        kwargs = {'params': params}
        if data is not None:
            kwargs['json'] = data
        
        response = self._make_request('POST', endpoint, **kwargs)
        return response.json() if response.text else None
    
    def put(self, endpoint: str, data: Any = None, **params) -> Any:
        """Make a PUT request"""
        kwargs = {'params': params}
        if data is not None:
            kwargs['json'] = data
        
        response = self._make_request('PUT', endpoint, **kwargs)
        return response.json() if response.text else None
    
    def delete(self, endpoint: str, **params) -> Any:
        """Make a DELETE request"""
        response = self._make_request('DELETE', endpoint, params=params)
        return response.json() if response.text else None
    
    def patch(self, endpoint: str, data: Any = None, **params) -> Any:
        """Make a PATCH request"""
        kwargs = {'params': params}
        if data is not None:
            kwargs['json'] = data
        
        response = self._make_request('PATCH', endpoint, **kwargs)
        return response.json() if response.text else None
    
    # Authentication methods
    def login(self, username: str, password: str) -> Dict[str, str]:
        """Login and get access token"""
        response = self.session.post(
            urljoin(self.base_url + '/', 'auth/login'),
            data={'username': username, 'password': password},
            verify=self.verify_ssl
        )
        response.raise_for_status()
        
        data = response.json()
        self.token = data['access_token']
        self.session.headers['Authorization'] = f'Bearer {self.token}'
        
        return data
    
    def logout(self):
        """Logout and clear token"""
        try:
            self.post('auth/logout')
        except:
            pass
        
        self.token = None
        self.session.headers.pop('Authorization', None)
    
    def refresh_token(self, refresh_token: str) -> Dict[str, str]:
        """Refresh access token"""
        response = self.session.post(
            urljoin(self.base_url + '/', 'auth/refresh'),
            json={'refresh_token': refresh_token},
            verify=self.verify_ssl
        )
        response.raise_for_status()
        
        data = response.json()
        self.token = data['access_token']
        self.session.headers['Authorization'] = f'Bearer {self.token}'
        
        return data
    
    # Host management
    def list_hosts(self) -> List[Dict[str, Any]]:
        """List all Docker hosts"""
        data = self.get('hosts/')
        return data.get('items', [])
    
    def get_host(self, host_id: str) -> Dict[str, Any]:
        """Get a specific host"""
        return self.get(f'hosts/{host_id}')
    
    def create_host(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new host"""
        return self.post('hosts/', data)
    
    def update_host(self, host_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a host"""
        return self.put(f'hosts/{host_id}', data)
    
    def delete_host(self, host_id: str):
        """Delete a host"""
        return self.delete(f'hosts/{host_id}')
    
    # Swarm operations
    def get_swarm_info(self, host_id: str) -> Dict[str, Any]:
        """Get swarm information"""
        return self.get('swarm/', host_id=host_id)
    
    def init_swarm(self, host_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Initialize swarm on a host"""
        return self.post('swarm/init', data, host_id=host_id)
    
    def join_swarm(self, host_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Join a host to swarm"""
        return self.post('swarm/join', data, host_id=host_id)
    
    def leave_swarm(self, host_id: str, force: bool = False) -> Dict[str, Any]:
        """Leave swarm"""
        return self.post('swarm/leave', {'force': force}, host_id=host_id)
    
    def update_swarm(self, host_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update swarm configuration"""
        return self.put('swarm/', data, host_id=host_id)
    
    # Node operations
    def list_nodes(self, host_id: str) -> List[Dict[str, Any]]:
        """List swarm nodes"""
        data = self.get('nodes', host_id=host_id)
        return data.get('nodes', [])
    
    def get_node(self, host_id: str, node_id: str) -> Dict[str, Any]:
        """Get node details"""
        return self.get(f'nodes/{node_id}', host_id=host_id)
    
    def update_node(self, host_id: str, node_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update node"""
        return self.put(f'nodes/{node_id}', data, host_id=host_id)
    
    def delete_node(self, host_id: str, node_id: str):
        """Remove node from swarm"""
        return self.delete(f'nodes/{node_id}', host_id=host_id)
    
    # Service operations
    def list_services(self, host_id: str) -> List[Dict[str, Any]]:
        """List swarm services"""
        data = self.get('services', host_id=host_id)
        return data.get('services', [])
    
    def get_service(self, host_id: str, service_id: str) -> Dict[str, Any]:
        """Get service details"""
        return self.get(f'services/{service_id}', host_id=host_id)
    
    def create_service(self, host_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new service"""
        return self.post('services', data, host_id=host_id)
    
    def update_service(self, host_id: str, service_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update service"""
        return self.put(f'services/{service_id}', data, host_id=host_id)
    
    def scale_service(self, host_id: str, service_id: str, replicas: int, version: int) -> Dict[str, Any]:
        """Scale service"""
        return self.put(f'services/{service_id}/scale', 
                       {'replicas': replicas, 'version': version}, 
                       host_id=host_id)
    
    def delete_service(self, host_id: str, service_id: str):
        """Delete service"""
        return self.delete(f'services/{service_id}', host_id=host_id)
    
    def get_service_logs(self, host_id: str, service_id: str, **params) -> str:
        """Get service logs"""
        return self.get(f'services/{service_id}/logs', host_id=host_id, **params)
    
    def get_service_tasks(self, host_id: str, service_id: str) -> List[Dict[str, Any]]:
        """Get service tasks"""
        data = self.get(f'services/{service_id}/tasks', host_id=host_id)
        return data.get('tasks', [])
    
    # Secret operations
    def list_secrets(self, host_id: str) -> List[Dict[str, Any]]:
        """List secrets"""
        data = self.get('secrets', host_id=host_id)
        return data.get('secrets', [])
    
    def get_secret(self, host_id: str, secret_id: str) -> Dict[str, Any]:
        """Get secret details"""
        return self.get(f'secrets/{secret_id}', host_id=host_id)
    
    def create_secret(self, host_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new secret"""
        return self.post('secrets', data, host_id=host_id)
    
    def delete_secret(self, host_id: str, secret_id: str):
        """Delete secret"""
        return self.delete(f'secrets/{secret_id}', host_id=host_id)
    
    # Config operations
    def list_configs(self, host_id: str) -> List[Dict[str, Any]]:
        """List configs"""
        data = self.get('configs', host_id=host_id)
        return data.get('configs', [])
    
    def get_config(self, host_id: str, config_id: str) -> Dict[str, Any]:
        """Get config details"""
        return self.get(f'configs/{config_id}', host_id=host_id)
    
    def create_config(self, host_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new config"""
        return self.post('configs', data, host_id=host_id)
    
    def delete_config(self, host_id: str, config_id: str):
        """Delete config"""
        return self.delete(f'configs/{config_id}', host_id=host_id)
    
    # Container operations
    def list_containers(self, host_id: str, **params) -> List[Dict[str, Any]]:
        """List containers"""
        data = self.get('containers/', host_id=host_id, **params)
        return data.get('containers', [])
    
    def get_container(self, host_id: str, container_id: str) -> Dict[str, Any]:
        """Get container details"""
        return self.get(f'containers/{container_id}', host_id=host_id)
    
    def start_container(self, host_id: str, container_id: str):
        """Start a container"""
        return self.post(f'containers/{container_id}/start', host_id=host_id)
    
    def stop_container(self, host_id: str, container_id: str):
        """Stop a container"""
        return self.post(f'containers/{container_id}/stop', host_id=host_id)
    
    def restart_container(self, host_id: str, container_id: str):
        """Restart a container"""
        return self.post(f'containers/{container_id}/restart', host_id=host_id)
    
    def delete_container(self, host_id: str, container_id: str, force: bool = False):
        """Delete a container"""
        return self.delete(f'containers/{container_id}', host_id=host_id, force=force)
    
    def get_container_logs(self, host_id: str, container_id: str, **params) -> str:
        """Get container logs"""
        return self.get(f'containers/{container_id}/logs', host_id=host_id, **params)