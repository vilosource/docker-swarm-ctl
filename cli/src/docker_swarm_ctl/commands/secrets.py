"""Secret management commands"""

import click

from ..utils import error_handler, require_auth


@click.group()
def secrets():
    """Manage Docker secrets"""
    pass


@secrets.command()
@click.option('--host', required=True, help='Swarm manager host ID')
@click.pass_context
@require_auth
@error_handler
def list(ctx, host: str):
    """List secrets"""
    click.echo(f"Listing secrets on host {host}")
    # Implementation would call client.list_secrets(host)