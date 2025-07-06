#!/usr/bin/env python3
"""
Script to add lab Docker hosts to the database
"""
import sys
import os
# Add backend directory to path since we're now in lab/
backend_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backend')
sys.path.append(backend_path)

from app.db.session import SessionLocal
from app.models.docker_host import DockerHost, HostCredential, UserHostPermission
from app.models.user import User
from app.core.security import get_password_hash
from app.services.encryption import CredentialEncryption
from sqlalchemy.orm import Session
import json
from datetime import datetime

def add_lab_host(db: Session, hostname: str, ip_address: str = None):
    """Add a lab host to the database"""
    
    # Check if host already exists
    existing_host = db.query(DockerHost).filter(DockerHost.name == hostname).first()
    if existing_host:
        print(f"Host {hostname} already exists, updating...")
        host = existing_host
    else:
        host = DockerHost(
            name=hostname,
            display_name=f"Docker Lab - {hostname.split('.')[0]}",
            host=ip_address if ip_address else hostname,
            port=2375,
            connection_type="tcp",
            host_type="standalone",
            is_active=True,
            is_default=False,
            metadata={
                "environment": "lab",
                "network": "192.168.100.0/24",
                "interface": "eth0",
                "ip_address": ip_address,
                "added_by_script": True,
                "added_at": datetime.utcnow().isoformat()
            }
        )
        db.add(host)
        db.flush()
        print(f"Added host: {hostname} (IP: {ip_address})")
    
    # Update connection URL and host
    if ip_address:
        host.host = ip_address
        host.connection_url = f"tcp://{ip_address}:2375"
    else:
        host.connection_url = f"tcp://{hostname}:2375"
    
    # Get admin user to grant initial permissions
    admin_user = db.query(User).filter(User.email == "admin@example.com").first()
    if admin_user:
        # Check if permission already exists
        existing_perm = db.query(UserHostPermission).filter(
            UserHostPermission.user_id == admin_user.id,
            UserHostPermission.host_id == host.id
        ).first()
        
        if not existing_perm:
            permission = UserHostPermission(
                user_id=admin_user.id,
                host_id=host.id,
                can_view=True,
                can_manage_containers=True,
                can_manage_images=True,
                can_manage_volumes=True,
                can_manage_networks=True,
                can_execute=True,
                can_manage_system=True
            )
            db.add(permission)
            print(f"Granted admin permissions to {admin_user.email} for {hostname}")
    
    db.commit()
    return host

def main():
    """Main function"""
    db = SessionLocal()
    
    try:
        # Add all lab hosts with their eth0 IP addresses
        lab_hosts = [
            ("docker-1.lab.viloforge.com", "192.168.100.11"),
            ("docker-2.lab.viloforge.com", "192.168.100.12"),
            ("docker-3.lab.viloforge.com", "192.168.100.13"),
            ("docker-4.lab.viloforge.com", "192.168.100.14"),
        ]
        
        for hostname, ip in lab_hosts:
            add_lab_host(db, hostname, ip)
        
        # List all hosts
        print("\nAll Docker hosts in database:")
        hosts = db.query(DockerHost).all()
        for host in hosts:
            print(f"  - {host.name} ({host.connection_type}://{host.host}:{host.port}) - Active: {host.is_active}")
            
    finally:
        db.close()

if __name__ == "__main__":
    main()