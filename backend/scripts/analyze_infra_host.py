import asyncio
import sys
from pathlib import Path
import json
from datetime import datetime

sys.path.append(str(Path(__file__).parent.parent))

from app.db.session import AsyncSessionLocal
from app.models.docker_host import DockerHost, HostCredential, HostConnectionStats
from app.models.user import User
from app.services.docker_service import DockerServiceFactory
from app.services.docker_connection_manager import DockerConnectionManager
from app.services.host_service import HostService
from app.core.config import settings
from app.services.encryption import CredentialEncryption
from sqlalchemy import select, or_
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


async def analyze_infra_host():
    """Analyze the infra-dsm-1.prod.optiscangroup.com host configuration"""
    async with AsyncSessionLocal() as session:
        # Search for the host by name or display name
        result = await session.execute(
            select(DockerHost).where(
                or_(
                    DockerHost.name == "infra-dsm-1.prod.optiscangroup.com",
                    DockerHost.display_name == "Infra Docker Swarm",
                    DockerHost.host_url.contains("infra-dsm-1.prod.optiscangroup.com")
                )
            )
        )
        host = result.scalar_one_or_none()
        
        if not host:
            print("❌ Host 'infra-dsm-1.prod.optiscangroup.com' not found in database")
            print("\nSearching all hosts for reference...")
            result = await session.execute(select(DockerHost))
            all_hosts = result.scalars().all()
            print(f"\nFound {len(all_hosts)} hosts in database:")
            for h in all_hosts:
                print(f"  - {h.name} (Display: {h.display_name}, URL: {h.host_url})")
            return
        
        print("=" * 80)
        print("HOST CONFIGURATION ANALYSIS")
        print("=" * 80)
        print(f"Host ID: {host.id}")
        print(f"Name: {host.name}")
        print(f"Display Name: {host.display_name}")
        print(f"Description: {host.description}")
        print(f"Host Type: {host.host_type}")
        print(f"Connection Type: {host.connection_type}")
        print(f"Host URL: {host.host_url}")
        print(f"Status: {host.status}")
        print(f"Is Active: {host.is_active}")
        print(f"Is Default: {host.is_default}")
        print(f"Last Health Check: {host.last_health_check}")
        print(f"Created At: {host.created_at}")
        print(f"Updated At: {host.updated_at}")
        
        # Swarm Information
        print("\nSWARM INFORMATION:")
        print(f"Swarm ID: {host.swarm_id}")
        print(f"Cluster Name: {host.cluster_name}")
        print(f"Is Leader: {host.is_leader}")
        
        # Get credentials
        result = await session.execute(
            select(HostCredential).where(HostCredential.host_id == host.id)
        )
        credentials = result.scalars().all()
        
        print("\nCREDENTIALS:")
        if not credentials:
            print("  ❌ No credentials found for this host")
        else:
            encryption_service = CredentialEncryption(settings.SECRET_KEY)
            for cred in credentials:
                print(f"  - Type: {cred.credential_type}")
                print(f"    Created: {cred.created_at}")
                print(f"    Updated: {cred.updated_at}")
                if cred.credential_metadata:
                    print(f"    Metadata: {json.dumps(cred.credential_metadata, indent=4)}")
                
                # Try to decrypt value (be careful with sensitive data)
                if cred.credential_type in ["ssh_user", "ssh_known_hosts"]:
                    try:
                        decrypted = encryption_service.decrypt(cred.encrypted_value)
                        if cred.credential_type == "ssh_user":
                            print(f"    SSH User: {decrypted}")
                        elif cred.credential_type == "ssh_known_hosts":
                            print(f"    Known Hosts: {decrypted[:100]}..." if len(decrypted) > 100 else f"    Known Hosts: {decrypted}")
                    except Exception as e:
                        print(f"    ⚠️  Failed to decrypt: {str(e)}")
                elif cred.credential_type in ["ssh_private_key", "ssh_password"]:
                    print(f"    [Sensitive credential - not displaying]")
        
        # Get connection stats
        result = await session.execute(
            select(HostConnectionStats).where(HostConnectionStats.host_id == host.id).order_by(HostConnectionStats.measured_at.desc()).limit(5)
        )
        stats = result.scalars().all()
        
        print("\nCONNECTION STATS (Recent):")
        if not stats:
            print("  No connection stats found")
        else:
            for stat in stats:
                print(f"  - Measured: {stat.measured_at}")
                print(f"    Active Connections: {stat.active_connections}")
                print(f"    Total Connections: {stat.total_connections}")
                print(f"    Failed Connections: {stat.failed_connections}")
                print(f"    Avg Response Time: {stat.avg_response_time_ms}ms")
                if stat.last_error:
                    print(f"    Last Error: {stat.last_error}")
                    print(f"    Last Error At: {stat.last_error_at}")
        
        # Test current connection
        print("\nTESTING CONNECTION:")
        print("=" * 80)
        
        try:
            # Get admin user for testing
            result = await session.execute(
                select(User).where(User.role == "admin").limit(1)
            )
            admin_user = result.scalar_one_or_none()
            
            if not admin_user:
                print("❌ No admin user found for testing")
                return
            
            # Test using DockerServiceFactory
            print(f"\nTesting with DockerServiceFactory...")
            try:
                service = await DockerServiceFactory.create_service(host.id, admin_user.id, session)
                info = await service.get_system_info()
                print("✅ Connection successful via DockerServiceFactory!")
                print(f"   Docker Version: {info.get('ServerVersion', 'N/A')}")
                print(f"   API Version: {info.get('ApiVersion', 'N/A')}")
            except Exception as e:
                print(f"❌ DockerServiceFactory failed: {str(e)}")
                logger.exception("DockerServiceFactory error:")
            
            # Test using ConnectionManager
            print(f"\nTesting with DockerConnectionManager...")
            try:
                conn_manager = DockerConnectionManager()
                client = await conn_manager.get_client(host.id, admin_user.id, session)
                
                # Try to get version info
                version_info = await asyncio.to_thread(client.version)
                print("✅ Connection successful via ConnectionManager!")
                print(f"   Version Info: {json.dumps(version_info, indent=2)}")
            except Exception as e:
                print(f"❌ ConnectionManager failed: {str(e)}")
                logger.exception("ConnectionManager error:")
            
            # Test SSH connection directly if it's SSH type
            if host.connection_type == "ssh":
                print(f"\nTesting SSH connection directly...")
                try:
                    from app.services.ssh_docker_connection import SSHDockerConnection
                    
                    # Get SSH credentials
                    ssh_creds = {}
                    for cred in credentials:
                        if cred.credential_type in ["ssh_user", "ssh_private_key", "ssh_password", "ssh_private_key_passphrase", "ssh_known_hosts"]:
                            try:
                                decrypted = encryption_service.decrypt(cred.encrypted_value)
                                ssh_creds[cred.credential_type] = decrypted
                            except:
                                pass
                    
                    print(f"  SSH Credentials found: {list(ssh_creds.keys())}")
                    
                    if "ssh_user" in ssh_creds:
                        print(f"  SSH User: {ssh_creds['ssh_user']}")
                        print(f"  SSH Host URL: {host.host_url}")
                        
                        # Parse the host URL
                        if host.host_url.startswith("ssh://"):
                            import re
                            match = re.match(r'ssh://([^:]+)(?::(\d+))?', host.host_url)
                            if match:
                                ssh_host = match.group(1)
                                ssh_port = int(match.group(2)) if match.group(2) else 22
                                print(f"  Parsed SSH Host: {ssh_host}")
                                print(f"  Parsed SSH Port: {ssh_port}")
                                
                                # Try to establish SSH connection
                                ssh_conn = SSHDockerConnection(
                                    host=ssh_host,
                                    port=ssh_port,
                                    username=ssh_creds.get("ssh_user"),
                                    private_key=ssh_creds.get("ssh_private_key"),
                                    password=ssh_creds.get("ssh_password"),
                                    passphrase=ssh_creds.get("ssh_private_key_passphrase"),
                                    known_hosts=ssh_creds.get("ssh_known_hosts")
                                )
                                
                                client = ssh_conn.get_client()
                                version = client.version()
                                print("✅ Direct SSH connection successful!")
                                print(f"   Docker Version: {version}")
                except Exception as e:
                    print(f"❌ Direct SSH test failed: {str(e)}")
                    logger.exception("Direct SSH error:")
            
        except Exception as e:
            print(f"❌ Connection test failed: {str(e)}")
            logger.exception("Connection test error:")
        
        print("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(analyze_infra_host())