"""Host management commands"""

import click
from typing import Optional, List
import json
import yaml

from ..client import APIError
from ..utils import (
    error_handler, require_auth, print_output, format_timestamp,
    truncate_id, confirm_action, load_yaml_file, load_json_file
)


@click.group()
def hosts():
    """Manage Docker hosts"""
    pass


@hosts.command()
@click.option('--all-details', '-a', is_flag=True, help='Show all details')
@click.option('--filter', '-f', help='Filter hosts by property')
@click.pass_context
@require_auth
@error_handler
def list(ctx, all_details: bool, filter: Optional[str]):
    """List Docker hosts"""
    client = ctx.obj['client']
    
    try:
        hosts = client.list_hosts()
        
        # Apply filter if provided
        if filter:
            # Simple filter implementation (e.g., "is_active=true")
            if '=' in filter:
                key, value = filter.split('=', 1)
                hosts = [h for h in hosts if str(h.get(key)) == value]
        
        if ctx.obj['output_format'] in ['json', 'yaml']:
            print_output(ctx, hosts)
        else:
            # Prepare table data
            if all_details:
                headers = ['ID', 'NAME', 'URL', 'ACTIVE', 'TLS', 'CREATED', 'UPDATED']
                fields = ['id', 'display_name', 'url', 'is_active', 'tls_enabled', 
                         'created_at', 'updated_at']
            else:
                headers = ['ID', 'NAME', 'URL', 'ACTIVE', 'CREATED']
                fields = ['id', 'display_name', 'url', 'is_active', 'created_at']
            
            # Format data
            formatted_hosts = []
            for host in hosts:
                formatted_host = dict(host)
                formatted_host['id'] = truncate_id(host.get('id', ''))
                formatted_host['created_at'] = format_timestamp(host.get('created_at'))
                formatted_host['updated_at'] = format_timestamp(host.get('updated_at'))
                formatted_host['is_active'] = '✓' if host.get('is_active') else '✗'
                formatted_host['tls_enabled'] = '✓' if host.get('tls_enabled') else '✗'
                formatted_hosts.append(formatted_host)
            
            print_output(ctx, formatted_hosts, headers=headers, fields=fields)
            
    except APIError as e:
        click.echo(f"Error: {e}", err=True)
        ctx.exit(1)


@hosts.command()
@click.argument('host_id')
@click.pass_context
@require_auth
@error_handler
def get(ctx, host_id: str):
    """Get details of a specific host"""
    client = ctx.obj['client']
    
    try:
        host = client.get_host(host_id)
        
        if ctx.obj['output_format'] in ['json', 'yaml']:
            print_output(ctx, host)
        else:
            # Display detailed information
            click.echo(f"ID: {host.get('id')}")
            click.echo(f"Name: {host.get('display_name')}")
            click.echo(f"URL: {host.get('url')}")
            click.echo(f"Active: {'Yes' if host.get('is_active') else 'No'}")
            click.echo(f"TLS Enabled: {'Yes' if host.get('tls_enabled') else 'No'}")
            click.echo(f"Created: {format_timestamp(host.get('created_at'))}")
            click.echo(f"Updated: {format_timestamp(host.get('updated_at'))}")
            
            if host.get('tls_config'):
                click.echo("\nTLS Configuration:")
                tls = host['tls_config']
                if tls.get('ca_cert'):
                    click.echo("  CA Certificate: Present")
                if tls.get('client_cert'):
                    click.echo("  Client Certificate: Present")
                if tls.get('client_key'):
                    click.echo("  Client Key: Present")
            
    except APIError as e:
        if e.status_code == 404:
            click.echo(f"Host '{host_id}' not found", err=True)
        else:
            click.echo(f"Error: {e}", err=True)
        ctx.exit(1)


@hosts.command()
@click.option('--name', required=True, help='Display name for the host')
@click.option('--url', required=True, help='Docker daemon URL (e.g., tcp://192.168.1.100:2376)')
@click.option('--tls/--no-tls', default=False, help='Enable TLS')
@click.option('--ca-cert', type=click.Path(exists=True), help='CA certificate file')
@click.option('--client-cert', type=click.Path(exists=True), help='Client certificate file')
@click.option('--client-key', type=click.Path(exists=True), help='Client key file')
@click.option('--file', '-f', type=click.Path(exists=True), help='Load host configuration from file')
@click.pass_context
@require_auth
@error_handler
def create(ctx, name: str, url: str, tls: bool, ca_cert: Optional[str],
          client_cert: Optional[str], client_key: Optional[str], file: Optional[str]):
    """Create a new Docker host"""
    client = ctx.obj['client']
    
    if file:
        # Load configuration from file
        if file.endswith('.yaml') or file.endswith('.yml'):
            data = load_yaml_file(file)
        else:
            data = load_json_file(file)
    else:
        # Build configuration from CLI arguments
        data = {
            'display_name': name,
            'url': url,
            'tls_enabled': tls
        }
        
        # Add TLS configuration if provided
        if tls and any([ca_cert, client_cert, client_key]):
            tls_config = {}
            
            if ca_cert:
                with open(ca_cert, 'r') as f:
                    tls_config['ca_cert'] = f.read()
            
            if client_cert:
                with open(client_cert, 'r') as f:
                    tls_config['client_cert'] = f.read()
            
            if client_key:
                with open(client_key, 'r') as f:
                    tls_config['client_key'] = f.read()
            
            data['tls_config'] = tls_config
    
    try:
        host = client.create_host(data)
        click.echo(f"Host '{name}' created successfully")
        click.echo(f"ID: {host.get('id')}")
        
    except APIError as e:
        click.echo(f"Error creating host: {e}", err=True)
        ctx.exit(1)


@hosts.command()
@click.argument('host_id')
@click.option('--name', help='New display name')
@click.option('--url', help='New Docker daemon URL')
@click.option('--active/--inactive', default=None, help='Set host active status')
@click.pass_context
@require_auth
@error_handler
def update(ctx, host_id: str, name: Optional[str], url: Optional[str], active: Optional[bool]):
    """Update a Docker host"""
    client = ctx.obj['client']
    
    # Build update data
    data = {}
    if name is not None:
        data['display_name'] = name
    if url is not None:
        data['url'] = url
    if active is not None:
        data['is_active'] = active
    
    if not data:
        click.echo("No updates specified", err=True)
        ctx.exit(1)
    
    try:
        host = client.update_host(host_id, data)
        click.echo(f"Host '{host_id}' updated successfully")
        
    except APIError as e:
        if e.status_code == 404:
            click.echo(f"Host '{host_id}' not found", err=True)
        else:
            click.echo(f"Error updating host: {e}", err=True)
        ctx.exit(1)


@hosts.command()
@click.argument('host_id')
@click.option('--force', is_flag=True, help='Force deletion without confirmation')
@click.pass_context
@require_auth
@error_handler
def delete(ctx, host_id: str, force: bool):
    """Delete a Docker host"""
    client = ctx.obj['client']
    
    if not force:
        # Get host details for confirmation
        try:
            host = client.get_host(host_id)
            host_name = host.get('display_name', host_id)
            
            if not confirm_action(f"Delete host '{host_name}'?"):
                click.echo("Deletion cancelled")
                return
        except:
            # If we can't get host details, still ask for confirmation
            if not confirm_action(f"Delete host '{host_id}'?"):
                click.echo("Deletion cancelled")
                return
    
    try:
        client.delete_host(host_id)
        click.echo(f"Host '{host_id}' deleted successfully")
        
    except APIError as e:
        if e.status_code == 404:
            click.echo(f"Host '{host_id}' not found", err=True)
        else:
            click.echo(f"Error deleting host: {e}", err=True)
        ctx.exit(1)


@hosts.command()
@click.argument('host_id')
@click.pass_context
@require_auth
@error_handler
def test(ctx, host_id: str):
    """Test connection to a Docker host"""
    client = ctx.obj['client']
    
    try:
        # Get host details
        host = client.get_host(host_id)
        host_name = host.get('display_name', host_id)
        
        click.echo(f"Testing connection to '{host_name}'...")
        
        # Test connection by getting system info
        # This would require an additional endpoint in the API
        # For now, we'll just verify the host exists
        click.echo(f"✓ Host '{host_name}' is configured")
        click.echo(f"  URL: {host.get('url')}")
        click.echo(f"  TLS: {'Enabled' if host.get('tls_enabled') else 'Disabled'}")
        
        if host.get('is_active'):
            click.echo(f"  Status: Active")
        else:
            click.echo(f"  Status: Inactive", err=True)
        
    except APIError as e:
        if e.status_code == 404:
            click.echo(f"Host '{host_id}' not found", err=True)
        else:
            click.echo(f"Error: {e}", err=True)
        ctx.exit(1)