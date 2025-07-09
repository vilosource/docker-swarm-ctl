"""Node management commands"""

import click
from typing import Optional

from ..client import APIError
from ..utils import error_handler, require_auth, print_output, format_timestamp, truncate_id


@click.group()
def nodes():
    """Manage swarm nodes"""
    pass


@nodes.command()
@click.option('--host', required=True, help='Swarm manager host ID')
@click.option('--filter', '-f', help='Filter nodes')
@click.pass_context
@require_auth
@error_handler
def list(ctx, host: str, filter: Optional[str]):
    """List swarm nodes"""
    client = ctx.obj['client']
    
    try:
        nodes_list = client.list_nodes(host)
        
        if ctx.obj['output_format'] in ['json', 'yaml']:
            print_output(ctx, nodes_list)
        else:
            # Format for table output
            headers = ['ID', 'HOSTNAME', 'STATUS', 'AVAILABILITY', 'MANAGER STATUS', 'ENGINE VERSION']
            fields = ['id', 'hostname', 'status', 'availability', 'manager_status', 'engine_version']
            
            formatted_nodes = []
            for node in nodes_list:
                formatted_node = {
                    'id': truncate_id(node.get('id', '')),
                    'hostname': node.get('hostname', '-'),
                    'status': node.get('status', '-'),
                    'availability': node.get('availability', '-'),
                    'manager_status': node.get('manager_status', '-'),
                    'engine_version': node.get('engine_version', '-')
                }
                formatted_nodes.append(formatted_node)
            
            print_output(ctx, formatted_nodes, headers=headers, fields=fields)
            
    except APIError as e:
        click.echo(f"Error listing nodes: {e}", err=True)
        ctx.exit(1)


@nodes.command()
@click.argument('node_id')
@click.option('--host', required=True, help='Swarm manager host ID')
@click.pass_context
@require_auth
@error_handler
def get(ctx, node_id: str, host: str):
    """Get details of a specific node"""
    client = ctx.obj['client']
    
    try:
        node = client.get_node(host, node_id)
        
        if ctx.obj['output_format'] in ['json', 'yaml']:
            print_output(ctx, node)
        else:
            # Display node details
            click.echo(f"ID: {node.get('id')}")
            click.echo(f"Hostname: {node.get('hostname')}")
            click.echo(f"Status: {node.get('status')}")
            click.echo(f"Availability: {node.get('availability')}")
            click.echo(f"Role: {node.get('role')}")
            click.echo(f"Manager Status: {node.get('manager_status', 'N/A')}")
            click.echo(f"Engine Version: {node.get('engine_version')}")
            
    except APIError as e:
        click.echo(f"Error getting node: {e}", err=True)
        ctx.exit(1)


@nodes.command()
@click.argument('node_id')
@click.option('--host', required=True, help='Swarm manager host ID')
@click.option('--availability', type=click.Choice(['active', 'pause', 'drain']), 
              help='Node availability')
@click.option('--role', type=click.Choice(['worker', 'manager']), help='Node role')
@click.option('--label-add', multiple=True, help='Add label (key=value)')
@click.option('--label-rm', multiple=True, help='Remove label')
@click.pass_context
@require_auth
@error_handler
def update(ctx, node_id: str, host: str, availability: Optional[str], 
          role: Optional[str], label_add: tuple, label_rm: tuple):
    """Update a node"""
    client = ctx.obj['client']
    
    # Build update data
    data = {}
    if availability:
        data['availability'] = availability
    if role:
        data['role'] = role
    
    # Handle labels
    labels_to_add = {}
    for label in label_add:
        if '=' in label:
            key, value = label.split('=', 1)
            labels_to_add[key] = value
    
    if labels_to_add or label_rm:
        data['labels'] = {
            'add': labels_to_add,
            'remove': list(label_rm)
        }
    
    if not data:
        click.echo("No updates specified", err=True)
        ctx.exit(1)
    
    try:
        node = client.update_node(host, node_id, data)
        click.echo(f"Node '{node_id}' updated successfully")
        
    except APIError as e:
        click.echo(f"Error updating node: {e}", err=True)
        ctx.exit(1)


@nodes.command()
@click.argument('node_id')
@click.option('--host', required=True, help='Swarm manager host ID')
@click.option('--force', is_flag=True, help='Force removal')
@click.pass_context
@require_auth
@error_handler
def rm(ctx, node_id: str, host: str, force: bool):
    """Remove a node from the swarm"""
    client = ctx.obj['client']
    
    if not force:
        if not click.confirm(f"Remove node '{node_id}' from swarm?"):
            click.echo("Operation cancelled")
            return
    
    try:
        client.delete_node(host, node_id)
        click.echo(f"Node '{node_id}' removed successfully")
        
    except APIError as e:
        click.echo(f"Error removing node: {e}", err=True)
        ctx.exit(1)