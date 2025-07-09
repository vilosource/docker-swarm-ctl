"""Swarm management commands"""

import click
from typing import Optional

from ..client import APIError
from ..utils import error_handler, require_auth, print_output, format_timestamp


@click.group()
def swarm():
    """Manage Docker Swarm"""
    pass


@swarm.command()
@click.option('--host', required=True, help='Host ID')
@click.pass_context
@require_auth
@error_handler
def info(ctx, host: str):
    """Get swarm information"""
    client = ctx.obj['client']
    
    try:
        swarm_info = client.get_swarm_info(host)
        
        if ctx.obj['output_format'] in ['json', 'yaml']:
            print_output(ctx, swarm_info)
        else:
            # Display swarm information
            click.echo(f"Swarm ID: {swarm_info.get('ID', 'N/A')}")
            click.echo(f"Created: {format_timestamp(swarm_info.get('CreatedAt'))}")
            click.echo(f"Updated: {format_timestamp(swarm_info.get('UpdatedAt'))}")
            
            spec = swarm_info.get('Spec', {})
            click.echo(f"\nOrchestration:")
            click.echo(f"  Task History Retention: {spec.get('Orchestration', {}).get('TaskHistoryRetentionLimit', 'N/A')}")
            
            click.echo(f"\nRaft:")
            raft = spec.get('Raft', {})
            click.echo(f"  Snapshot Interval: {raft.get('SnapshotInterval', 'N/A')}")
            click.echo(f"  Keep Old Snapshots: {raft.get('KeepOldSnapshots', 'N/A')}")
            click.echo(f"  Log Entries for Slow Followers: {raft.get('LogEntriesForSlowFollowers', 'N/A')}")
            
            click.echo(f"\nDispatcher:")
            dispatcher = spec.get('Dispatcher', {})
            click.echo(f"  Heartbeat Period: {dispatcher.get('HeartbeatPeriod', 'N/A')}")
            
            click.echo(f"\nCA Config:")
            ca_config = spec.get('CAConfig', {})
            click.echo(f"  Node Cert Expiry: {ca_config.get('NodeCertExpiry', 'N/A')}")
            
            click.echo(f"\nEncryption Config:")
            encryption = spec.get('EncryptionConfig', {})
            click.echo(f"  Auto Lock Managers: {encryption.get('AutoLockManagers', False)}")
            
    except APIError as e:
        if e.status_code == 404:
            click.echo(f"Host '{host}' is not part of a swarm", err=True)
        elif e.status_code == 400:
            click.echo(f"Host '{host}' is not a swarm manager", err=True)
        else:
            click.echo(f"Error: {e}", err=True)
        ctx.exit(1)


@swarm.command()
@click.option('--host', required=True, help='Host ID to initialize as swarm manager')
@click.option('--advertise-addr', required=True, help='Advertised address (format: <ip|interface>[:port])')
@click.option('--listen-addr', default='0.0.0.0:2377', help='Listen address (format: <ip|interface>[:port])')
@click.option('--force-new-cluster', is_flag=True, help='Force create a new cluster from current state')
@click.option('--data-path-addr', help='Address or interface for data path traffic')
@click.pass_context
@require_auth
@error_handler
def init(ctx, host: str, advertise_addr: str, listen_addr: str, 
         force_new_cluster: bool, data_path_addr: Optional[str]):
    """Initialize a new swarm"""
    client = ctx.obj['client']
    
    data = {
        'advertise_addr': advertise_addr,
        'listen_addr': listen_addr,
        'force_new_cluster': force_new_cluster
    }
    
    if data_path_addr:
        data['data_path_addr'] = data_path_addr
    
    try:
        result = client.init_swarm(host, data)
        click.echo("Swarm initialized successfully")
        click.echo(f"Swarm ID: {result.get('ID', 'N/A')}")
        
        # Show join tokens
        click.echo("\nTo add a worker to this swarm, run the following command:")
        click.echo(f"  docker-swarm-ctl swarm join --host <host-id> --token <worker-token> --remote-addr {advertise_addr}")
        click.echo("\nTo add a manager to this swarm, run the following command:")
        click.echo(f"  docker-swarm-ctl swarm join --host <host-id> --token <manager-token> --remote-addr {advertise_addr}")
        click.echo("\nTo retrieve the join tokens, run:")
        click.echo(f"  docker-swarm-ctl swarm join-token --host {host} worker")
        click.echo(f"  docker-swarm-ctl swarm join-token --host {host} manager")
        
    except APIError as e:
        if e.status_code == 409:
            click.echo(f"Host '{host}' is already part of a swarm", err=True)
        else:
            click.echo(f"Error initializing swarm: {e}", err=True)
        ctx.exit(1)


@swarm.command()
@click.option('--host', required=True, help='Host ID to join to swarm')
@click.option('--token', required=True, help='Join token')
@click.option('--remote-addr', required=True, multiple=True, help='Manager addresses')
@click.option('--advertise-addr', help='Advertised address')
@click.option('--listen-addr', default='0.0.0.0:2377', help='Listen address')
@click.option('--data-path-addr', help='Address for data path traffic')
@click.pass_context
@require_auth
@error_handler
def join(ctx, host: str, token: str, remote_addr: tuple, 
         advertise_addr: Optional[str], listen_addr: str, 
         data_path_addr: Optional[str]):
    """Join a host to an existing swarm"""
    client = ctx.obj['client']
    
    data = {
        'join_token': token,
        'remote_addrs': list(remote_addr),
        'listen_addr': listen_addr
    }
    
    if advertise_addr:
        data['advertise_addr'] = advertise_addr
    if data_path_addr:
        data['data_path_addr'] = data_path_addr
    
    try:
        client.join_swarm(host, data)
        click.echo(f"Host successfully joined the swarm")
        
    except APIError as e:
        if e.status_code == 409:
            click.echo(f"Host '{host}' is already part of a swarm", err=True)
        else:
            click.echo(f"Error joining swarm: {e}", err=True)
        ctx.exit(1)


@swarm.command()
@click.option('--host', required=True, help='Host ID')
@click.option('--force', is_flag=True, help='Force leave even if node is a manager')
@click.pass_context
@require_auth
@error_handler
def leave(ctx, host: str, force: bool):
    """Leave the swarm"""
    client = ctx.obj['client']
    
    if not force:
        if not click.confirm("Are you sure you want to leave the swarm?"):
            click.echo("Operation cancelled")
            return
    
    try:
        client.leave_swarm(host, force)
        click.echo("Successfully left the swarm")
        
    except APIError as e:
        if e.status_code == 404:
            click.echo(f"Host '{host}' is not part of a swarm", err=True)
        else:
            click.echo(f"Error leaving swarm: {e}", err=True)
        ctx.exit(1)


@swarm.command()
@click.option('--host', required=True, help='Host ID')
@click.option('--rotate-worker-token', is_flag=True, help='Rotate the worker join token')
@click.option('--rotate-manager-token', is_flag=True, help='Rotate the manager join token')
@click.option('--rotate-manager-unlock-key', is_flag=True, help='Rotate the manager unlock key')
@click.pass_context
@require_auth
@error_handler
def update(ctx, host: str, rotate_worker_token: bool, 
          rotate_manager_token: bool, rotate_manager_unlock_key: bool):
    """Update swarm configuration"""
    client = ctx.obj['client']
    
    if not any([rotate_worker_token, rotate_manager_token, rotate_manager_unlock_key]):
        click.echo("No update options specified", err=True)
        ctx.exit(1)
    
    data = {
        'rotate_worker_token': rotate_worker_token,
        'rotate_manager_token': rotate_manager_token,
        'rotate_manager_unlock_key': rotate_manager_unlock_key
    }
    
    try:
        result = client.update_swarm(host, data)
        click.echo("Swarm configuration updated successfully")
        
        if rotate_worker_token:
            click.echo("Worker token rotated")
        if rotate_manager_token:
            click.echo("Manager token rotated")
        if rotate_manager_unlock_key:
            click.echo("Manager unlock key rotated")
        
    except APIError as e:
        if e.status_code == 404:
            click.echo(f"Host '{host}' is not part of a swarm", err=True)
        elif e.status_code == 400:
            click.echo(f"Host '{host}' is not a swarm manager", err=True)
        else:
            click.echo(f"Error updating swarm: {e}", err=True)
        ctx.exit(1)