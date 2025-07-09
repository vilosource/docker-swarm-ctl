"""Main CLI entry point"""

import click
import sys
from pathlib import Path

from .config import Config, ConfigManager
from .client import APIClient
from .commands import auth, config_cmd, hosts, swarm, nodes, services, secrets, configs, containers
from .utils import output_formatter


@click.group()
@click.option('--config', '-c', type=click.Path(), 
              default=str(Path.home() / '.docker-swarm-ctl' / 'config.yaml'),
              help='Config file location')
@click.option('--context', help='Override current context')
@click.option('--output', '-o', type=click.Choice(['table', 'json', 'yaml', 'wide']), 
              default='table', help='Output format')
@click.pass_context
def cli(ctx, config, context, output):
    """Docker Swarm Control - kubectl-like CLI for Docker Swarm"""
    # Initialize config
    config_manager = ConfigManager(config)
    cfg = config_manager.load()
    
    # Override context if specified
    if context:
        cfg.current_context = context
    
    # Initialize API client
    if cfg.current_context and cfg.current_context in cfg.contexts:
        context_cfg = cfg.contexts[cfg.current_context]
        client = APIClient(
            base_url=context_cfg.api_url,
            token=context_cfg.token
        )
    else:
        client = None
    
    # Store in context
    ctx.obj = {
        'config': cfg,
        'config_manager': config_manager,
        'client': client,
        'output_format': output
    }


# Add command groups
cli.add_command(auth.auth)
cli.add_command(config_cmd.config)
cli.add_command(hosts.hosts)
cli.add_command(swarm.swarm)
cli.add_command(nodes.nodes)
cli.add_command(services.services)
cli.add_command(secrets.secrets)
cli.add_command(configs.configs)
cli.add_command(containers.containers)


# Add top-level get/create/delete commands for kubectl-like syntax
@cli.command()
@click.argument('resource_type')
@click.argument('resource_name', required=False)
@click.option('--host', help='Host ID for swarm resources')
@click.option('--selector', '-l', help='Label selector')
@click.option('--filter', '-f', help='Filter resources')
@click.option('--watch', '-w', is_flag=True, help='Watch for changes')
@click.option('--all-namespaces', '-A', is_flag=True, help='List resources from all hosts')
@click.pass_context
def get(ctx, resource_type, resource_name, host, selector, filter, watch, all_namespaces):
    """Get one or many resources"""
    # Map resource types to commands
    resource_map = {
        'host': 'hosts',
        'hosts': 'hosts',
        'node': 'nodes',
        'nodes': 'nodes',
        'service': 'services',
        'services': 'services',
        'svc': 'services',
        'secret': 'secrets',
        'secrets': 'secrets',
        'config': 'configs',
        'configs': 'configs',
        'container': 'containers',
        'containers': 'containers',
    }
    
    mapped_resource = resource_map.get(resource_type.lower())
    if not mapped_resource:
        click.echo(f"Unknown resource type: {resource_type}", err=True)
        sys.exit(1)
    
    # Construct command
    cmd_parts = [mapped_resource, 'list']
    if resource_name:
        cmd_parts = [mapped_resource, 'get', resource_name]
    
    # Add options
    args = []
    if host:
        args.extend(['--host', host])
    if selector:
        args.extend(['--selector', selector])
    if filter:
        args.extend(['--filter', filter])
    if watch:
        args.append('--watch')
    if all_namespaces:
        args.append('--all-hosts')
    
    # Invoke the command
    cmd = cli
    for part in cmd_parts:
        cmd = cmd.commands.get(part) or cmd.get_command(ctx, part)
    
    ctx.invoke(cmd, *args)


@cli.command()
@click.argument('resource_type')
@click.option('--host', help='Host ID for swarm resources')
@click.option('--file', '-f', type=click.Path(exists=True), help='Resource definition file')
@click.pass_context
def create(ctx, resource_type, host, file):
    """Create a resource from a file or stdin"""
    # Map resource types to commands
    resource_map = {
        'host': 'hosts',
        'service': 'services',
        'svc': 'services',
        'secret': 'secrets',
        'config': 'configs',
    }
    
    mapped_resource = resource_map.get(resource_type.lower())
    if not mapped_resource:
        click.echo(f"Cannot create resource type: {resource_type}", err=True)
        sys.exit(1)
    
    # Construct command
    cmd_parts = [mapped_resource, 'create']
    
    # Add options
    args = []
    if host:
        args.extend(['--host', host])
    if file:
        args.extend(['--file', file])
    
    # Invoke the command
    cmd = cli
    for part in cmd_parts:
        cmd = cmd.commands.get(part) or cmd.get_command(ctx, part)
    
    ctx.invoke(cmd, *args)


@cli.command()
@click.argument('resource_type')
@click.argument('resource_name')
@click.option('--host', help='Host ID for swarm resources')
@click.option('--force', is_flag=True, help='Force deletion')
@click.pass_context
def delete(ctx, resource_type, resource_name, host, force):
    """Delete a resource"""
    # Map resource types to commands
    resource_map = {
        'host': 'hosts',
        'service': 'services',
        'svc': 'services',
        'secret': 'secrets',
        'config': 'configs',
        'container': 'containers',
    }
    
    mapped_resource = resource_map.get(resource_type.lower())
    if not mapped_resource:
        click.echo(f"Cannot delete resource type: {resource_type}", err=True)
        sys.exit(1)
    
    # Construct command
    cmd_parts = [mapped_resource, 'delete', resource_name]
    
    # Add options
    args = []
    if host:
        args.extend(['--host', host])
    if force:
        args.append('--force')
    
    # Invoke the command
    cmd = cli
    for part in cmd_parts:
        cmd = cmd.commands.get(part) or cmd.get_command(ctx, part)
    
    ctx.invoke(cmd, *args)


@cli.command()
@click.argument('service_name')
@click.option('--host', required=True, help='Host ID')
@click.option('--replicas', type=int, required=True, help='Number of replicas')
@click.pass_context
def scale(ctx, service_name, host, replicas):
    """Scale a service to a specified number of replicas"""
    # Invoke services scale command
    services_cmd = cli.commands.get('services')
    scale_cmd = services_cmd.commands.get('scale')
    ctx.invoke(scale_cmd, service_id=service_name, host=host, replicas=replicas)


@cli.command()
@click.argument('container_id')
@click.option('--host', required=True, help='Host ID')
@click.option('--follow', '-f', is_flag=True, help='Follow log output')
@click.option('--tail', type=int, default=100, help='Number of lines to show from the end')
@click.option('--timestamps', '-t', is_flag=True, help='Show timestamps')
@click.pass_context
def logs(ctx, container_id, host, follow, tail, timestamps):
    """Print the logs for a container"""
    # Invoke containers logs command
    containers_cmd = cli.commands.get('containers')
    logs_cmd = containers_cmd.commands.get('logs')
    ctx.invoke(logs_cmd, container_id=container_id, host=host, 
               follow=follow, tail=tail, timestamps=timestamps)


@cli.command()
@click.argument('container_id')
@click.option('--host', required=True, help='Host ID')
@click.argument('command', nargs=-1, required=True)
@click.pass_context
def exec(ctx, container_id, host, command):
    """Execute a command in a running container"""
    # Invoke containers exec command
    containers_cmd = cli.commands.get('containers')
    exec_cmd = containers_cmd.commands.get('exec')
    ctx.invoke(exec_cmd, container_id=container_id, host=host, command=command)


if __name__ == '__main__':
    cli()