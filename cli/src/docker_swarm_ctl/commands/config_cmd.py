"""Configuration commands"""

import click
from tabulate import tabulate

from ..utils import error_handler, print_output


@click.group()
def config():
    """Manage CLI configuration"""
    pass


@config.command()
@click.pass_context
def view(ctx):
    """View current configuration"""
    config = ctx.obj['config']
    
    if not config.contexts:
        click.echo("No contexts configured")
        return
    
    # Prepare table data
    table_data = []
    for name, context in config.contexts.items():
        current = '*' if name == config.current_context else ''
        authenticated = 'Yes' if context.token else 'No'
        table_data.append([
            current,
            name,
            context.api_url,
            context.username or '-',
            authenticated
        ])
    
    headers = ['CURRENT', 'NAME', 'API URL', 'USER', 'AUTH']
    click.echo(tabulate(table_data, headers=headers, tablefmt='simple'))


@config.command()
@click.argument('name')
@click.option('--api-url', required=True, help='API URL for the context')
@click.option('--username', help='Default username for this context')
@click.option('--verify-ssl/--no-verify-ssl', default=True, help='Verify SSL certificates')
@click.pass_context
@error_handler
def add_context(ctx, name: str, api_url: str, username: str, verify_ssl: bool):
    """Add a new context"""
    config_manager = ctx.obj['config_manager']
    
    config_manager.add_context(
        name=name,
        api_url=api_url,
        username=username,
        verify_ssl=verify_ssl
    )
    
    click.echo(f"Context '{name}' added successfully")
    
    # If it's the first context, it's automatically set as current
    config = config_manager.load()
    if config.current_context == name:
        click.echo(f"Switched to context '{name}'")


@config.command()
@click.argument('name')
@click.pass_context
@error_handler
def remove_context(ctx, name: str):
    """Remove a context"""
    config = ctx.obj['config']
    config_manager = ctx.obj['config_manager']
    
    if name not in config.contexts:
        click.echo(f"Context '{name}' not found", err=True)
        ctx.exit(1)
    
    # Confirm if it's the current context
    if config.current_context == name:
        if not click.confirm(f"'{name}' is the current context. Remove anyway?"):
            return
    
    config_manager.remove_context(name)
    click.echo(f"Context '{name}' removed")


@config.command()
@click.argument('name')
@click.pass_context
@error_handler
def use_context(ctx, name: str):
    """Switch to a different context"""
    config = ctx.obj['config']
    config_manager = ctx.obj['config_manager']
    
    if name not in config.contexts:
        click.echo(f"Context '{name}' not found", err=True)
        click.echo("\nAvailable contexts:")
        for ctx_name in config.contexts:
            click.echo(f"  - {ctx_name}")
        ctx.exit(1)
    
    if config_manager.use_context(name):
        click.echo(f"Switched to context '{name}'")
    else:
        click.echo(f"Failed to switch context", err=True)
        ctx.exit(1)


@config.command()
@click.pass_context
def current_context(ctx):
    """Display the current context"""
    config = ctx.obj['config']
    
    if not config.current_context:
        click.echo("No current context set")
        return
    
    context = config.contexts.get(config.current_context)
    if not context:
        click.echo(f"Current context '{config.current_context}' not found in config", err=True)
        return
    
    click.echo(f"Current context: {config.current_context}")
    click.echo(f"API URL: {context.api_url}")
    click.echo(f"Username: {context.username or '-'}")
    click.echo(f"Authenticated: {'Yes' if context.token else 'No'}")
    click.echo(f"Verify SSL: {context.verify_ssl}")