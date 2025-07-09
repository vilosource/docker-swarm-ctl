"""Service management commands"""

import click

from ..utils import error_handler, require_auth


@click.group()
def services():
    """Manage swarm services"""
    pass


@services.command()
@click.option('--host', required=True, help='Swarm manager host ID')
@click.pass_context
@require_auth
@error_handler
def list(ctx, host: str):
    """List services"""
    click.echo(f"Listing services on host {host}")
    # Implementation would call client.list_services(host)


@services.command()
@click.option('--host', required=True, help='Swarm manager host ID')
@click.option('--name', required=True, help='Service name')
@click.option('--image', required=True, help='Container image')
@click.option('--replicas', type=int, default=1, help='Number of replicas')
@click.pass_context
@require_auth
@error_handler
def create(ctx, host: str, name: str, image: str, replicas: int):
    """Create a new service"""
    click.echo(f"Creating service '{name}' with image '{image}' on host {host}")
    # Implementation would call client.create_service(host, data)