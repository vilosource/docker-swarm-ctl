"""Utility functions for the CLI"""

import json
import yaml
from datetime import datetime
from typing import Any, List, Dict, Optional
from tabulate import tabulate
import click


def format_timestamp(timestamp: Optional[str]) -> str:
    """Format a timestamp string to a human-readable format"""
    if not timestamp:
        return '-'
    
    try:
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        now = datetime.now(dt.tzinfo)
        delta = now - dt
        
        if delta.days > 0:
            return f"{delta.days}d ago"
        elif delta.seconds > 3600:
            return f"{delta.seconds // 3600}h ago"
        elif delta.seconds > 60:
            return f"{delta.seconds // 60}m ago"
        else:
            return "just now"
    except:
        return timestamp


def format_size(size_bytes: int) -> str:
    """Format bytes to human-readable size"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f}{unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f}PB"


def truncate_id(id_str: str, length: int = 12) -> str:
    """Truncate ID to specified length"""
    if not id_str:
        return '-'
    return id_str[:length]


class OutputFormatter:
    """Formats output in various formats"""
    
    def __init__(self, format_type: str = 'table'):
        self.format_type = format_type
    
    def format(self, data: Any, headers: Optional[List[str]] = None, 
               fields: Optional[List[str]] = None) -> str:
        """Format data based on format type"""
        if self.format_type == 'json':
            return self.format_json(data)
        elif self.format_type == 'yaml':
            return self.format_yaml(data)
        elif self.format_type == 'table':
            return self.format_table(data, headers, fields)
        elif self.format_type == 'wide':
            return self.format_wide(data, headers, fields)
        else:
            return str(data)
    
    def format_json(self, data: Any) -> str:
        """Format as JSON"""
        return json.dumps(data, indent=2, default=str)
    
    def format_yaml(self, data: Any) -> str:
        """Format as YAML"""
        return yaml.dump(data, default_flow_style=False, default_str=str)
    
    def format_table(self, data: Any, headers: Optional[List[str]] = None,
                    fields: Optional[List[str]] = None) -> str:
        """Format as table"""
        if not isinstance(data, list):
            data = [data]
        
        if not data:
            return "No resources found"
        
        # Extract data for table
        table_data = []
        for item in data:
            if fields:
                row = []
                for field in fields:
                    value = self._get_nested_value(item, field)
                    row.append(value)
                table_data.append(row)
            else:
                # Auto-detect fields from first item
                if isinstance(item, dict):
                    table_data.append(list(item.values()))
                else:
                    table_data.append([str(item)])
        
        # Use provided headers or auto-detect
        if not headers:
            if fields:
                headers = [f.split('.')[-1].upper() for f in fields]
            elif data and isinstance(data[0], dict):
                headers = [k.upper() for k in data[0].keys()]
            else:
                headers = ['VALUE']
        
        return tabulate(table_data, headers=headers, tablefmt='simple')
    
    def format_wide(self, data: Any, headers: Optional[List[str]] = None,
                   fields: Optional[List[str]] = None) -> str:
        """Format as wide table (includes more fields)"""
        # For wide format, we include more fields
        # This is typically handled by the specific command
        return self.format_table(data, headers, fields)
    
    def _get_nested_value(self, obj: Dict[str, Any], path: str) -> Any:
        """Get nested value from object using dot notation"""
        parts = path.split('.')
        value = obj
        
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part, '-')
            else:
                return '-'
        
        return value if value is not None else '-'


def output_formatter(ctx: click.Context) -> OutputFormatter:
    """Get output formatter from context"""
    format_type = ctx.obj.get('output_format', 'table')
    return OutputFormatter(format_type)


def print_output(ctx: click.Context, data: Any, headers: Optional[List[str]] = None,
                fields: Optional[List[str]] = None):
    """Print formatted output"""
    formatter = output_formatter(ctx)
    output = formatter.format(data, headers, fields)
    click.echo(output)


def confirm_action(message: str, default: bool = False) -> bool:
    """Ask for confirmation"""
    return click.confirm(message, default=default)


def error_handler(func):
    """Decorator to handle API errors"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            click.echo(f"Error: {str(e)}", err=True)
            ctx = click.get_current_context()
            ctx.exit(1)
    
    return wrapper


def require_auth(func):
    """Decorator to ensure authentication"""
    def wrapper(*args, **kwargs):
        ctx = click.get_current_context()
        client = ctx.obj.get('client')
        
        if not client or not client.token:
            click.echo("Error: Not authenticated. Please run 'docker-swarm-ctl login' first.", err=True)
            ctx.exit(1)
        
        return func(*args, **kwargs)
    
    return wrapper


def parse_labels(labels: List[str]) -> Dict[str, str]:
    """Parse label strings into dictionary"""
    result = {}
    for label in labels:
        if '=' in label:
            key, value = label.split('=', 1)
            result[key] = value
        else:
            result[label] = ''
    
    return result


def parse_key_value_pairs(pairs: List[str]) -> Dict[str, str]:
    """Parse key=value pairs into dictionary"""
    result = {}
    for pair in pairs:
        if '=' in pair:
            key, value = pair.split('=', 1)
            result[key] = value
    
    return result


def load_yaml_file(file_path: str) -> Any:
    """Load YAML file"""
    with open(file_path, 'r') as f:
        return yaml.safe_load(f)


def load_json_file(file_path: str) -> Any:
    """Load JSON file"""
    with open(file_path, 'r') as f:
        return json.load(f)