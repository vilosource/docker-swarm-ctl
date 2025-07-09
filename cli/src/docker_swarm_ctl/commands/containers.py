"""Container management commands"""

import click

from ..utils import error_handler, require_auth


@click.group()
def containers():
    """Manage containers"""
    pass


@containers.command()
@click.option('--host', required=True, help='Docker host ID')
@click.option('--all', '-a', is_flag=True, help='Show all containers')
@click.pass_context
@require_auth
@error_handler
def list(ctx, host: str, all: bool):
    """List containers"""
    click.echo(f"Listing containers on host {host}")
    # Implementation would call client.list_containers(host, all=all)


@containers.command()
@click.argument('container_id')
@click.option('--host', required=True, help='Docker host ID')
@click.option('--follow', '-f', is_flag=True, help='Follow log output')
@click.pass_context
@require_auth
@error_handler
def logs(ctx, container_id: str, host: str, follow: bool):
    """Get container logs"""
    click.echo(f"Getting logs for container {container_id} on host {host}")
    # Implementation would call client.get_container_logs(host, container_id, follow=follow)