"""Config management commands"""

import click

from ..utils import error_handler, require_auth


@click.group()
def configs():
    """Manage Docker configs"""
    pass


@configs.command()
@click.option('--host', required=True, help='Swarm manager host ID')
@click.pass_context
@require_auth
@error_handler
def list(ctx, host: str):
    """List configs"""
    click.echo(f"Listing configs on host {host}")
    # Implementation would call client.list_configs(host)