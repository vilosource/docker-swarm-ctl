"""
SSH Docker Monkey Patch

This module patches docker-py's SSH implementation to disable host key checking
and properly handle SSH authentication.
"""

import paramiko
from docker.transport import SSHHTTPAdapter


# Store the original _create_paramiko_client method
_original_create_paramiko_client = SSHHTTPAdapter._create_paramiko_client


def _patched_create_paramiko_client(self, base_url):
    """
    Patched version that disables host key checking and handles SSH keys properly.
    """
    import logging
    import os
    
    logger = logging.getLogger("docker_control_platform")
    logger.info(f"SSH Patch: Creating paramiko client for {base_url}")
    
    # Call the original method first
    _original_create_paramiko_client(self, base_url)
    
    # Now patch the SSH client to disable host key checking
    if hasattr(self, 'ssh_client'):
        logger.info("SSH Patch: Applying AutoAddPolicy to ssh_client")
        self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # Also patch the SSH params to disable host key checking
        if hasattr(self, 'ssh_params'):
            logger.info(f"SSH Patch: Original ssh_params: {self.ssh_params}")
            
            # Force disable host key checking in params
            self.ssh_params['look_for_keys'] = False
            self.ssh_params['allow_agent'] = False
            
            # Check for SSH key in environment
            ssh_key_path = os.environ.get('SSH_KEY_PATH')
            if ssh_key_path and os.path.exists(ssh_key_path):
                self.ssh_params['key_filename'] = ssh_key_path
                logger.info(f"SSH Patch: Using key file {ssh_key_path}")
            
            logger.info(f"SSH Patch: Updated ssh_params: {self.ssh_params}")
        
        logger.info("SSH Patch: Applied successfully")
    else:
        logger.warning("SSH Patch: No ssh_client found to patch")


def apply_ssh_docker_patch():
    """Apply the monkey patch to docker-py's SSH adapter."""
    import logging
    logger = logging.getLogger("docker_control_platform")
    
    logger.info("Applying SSH Docker patch...")
    SSHHTTPAdapter._create_paramiko_client = _patched_create_paramiko_client
    logger.info("SSH Docker patch applied successfully")
    
    # Verify the patch was applied
    if SSHHTTPAdapter._create_paramiko_client == _patched_create_paramiko_client:
        logger.info("SSH patch verification: SUCCESS")
    else:
        logger.error("SSH patch verification: FAILED")


def remove_ssh_docker_patch():
    """Remove the monkey patch."""
    SSHHTTPAdapter._create_paramiko_client = _original_create_paramiko_client