"""Authentication commands"""

import click
import getpass
from typing import Optional

from ..client import APIError
from ..utils import error_handler


@click.group()
def auth():
    """Authentication commands"""
    pass


@auth.command()
@click.option('--username', '-u', prompt=True, help='Username')
@click.option('--password', '-p', help='Password (will prompt if not provided)')
@click.pass_context
@error_handler
def login(ctx, username: str, password: Optional[str]):
    """Login to Docker Swarm Control"""
    if not password:
        password = getpass.getpass('Password: ')
    
    config = ctx.obj['config']
    config_manager = ctx.obj['config_manager']
    
    # Get current context
    if not config.current_context:
        click.echo("Error: No context configured. Please run 'docker-swarm-ctl config add-context' first.", err=True)
        ctx.exit(1)
    
    context = config.contexts.get(config.current_context)
    if not context:
        click.echo(f"Error: Context '{config.current_context}' not found.", err=True)
        ctx.exit(1)
    
    # Create client without token for login
    from ..client import APIClient
    client = APIClient(context.api_url, verify_ssl=context.verify_ssl)
    
    try:
        # Login
        result = client.login(username, password)
        
        # Update context with username and token
        context.username = username
        context.token = result['access_token']
        
        # Save to config
        config_manager.save(config)
        
        # Update the client in context
        ctx.obj['client'] = client
        
        click.echo(f"Successfully logged in as {username}")
        click.echo(f"Context: {config.current_context} ({context.api_url})")
        
    except APIError as e:
        if e.status_code == 401:
            click.echo("Error: Invalid username or password", err=True)
        else:
            click.echo(f"Error: {e}", err=True)
        ctx.exit(1)


@auth.command()
@click.pass_context
@error_handler
def logout(ctx):
    """Logout from Docker Swarm Control"""
    config = ctx.obj['config']
    config_manager = ctx.obj['config_manager']
    client = ctx.obj['client']
    
    if not config.current_context:
        click.echo("Not logged in", err=True)
        return
    
    context = config.contexts.get(config.current_context)
    if not context or not context.token:
        click.echo("Not logged in", err=True)
        return
    
    # Call logout endpoint if client is available
    if client:
        try:
            client.logout()
        except:
            pass
    
    # Clear token from config
    context.token = None
    config_manager.save(config)
    
    click.echo(f"Successfully logged out from {config.current_context}")


@auth.command()
@click.pass_context
def whoami(ctx):
    """Display the current user"""
    config = ctx.obj['config']
    
    if not config.current_context:
        click.echo("Not logged in", err=True)
        ctx.exit(1)
    
    context = config.contexts.get(config.current_context)
    if not context or not context.username:
        click.echo("Not logged in", err=True)
        ctx.exit(1)
    
    click.echo(f"Current user: {context.username}")
    click.echo(f"Context: {config.current_context} ({context.api_url})")
    click.echo(f"Authenticated: {'Yes' if context.token else 'No'}")