#!/usr/bin/env python3
"""
Simple configuration management script

Usage:
    python scripts/manage_config.py --list
    python scripts/manage_config.py --get scheduling.cron_interval_minutes
    python scripts/manage_config.py --set scheduling.cron_interval_minutes 30
    python scripts/manage_config.py --history
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings
from utils.database_manager import DatabaseManager


def list_configs(category=None):
    """List all runtime configurations."""
    try:
        db = DatabaseManager()
        query = db.supabase.table('runtime_config')\
            .select('key, value, description, category, updated_at')\
            .eq('is_active', True)\
            .order('category', desc=False)\
            .order('key', desc=False)
        
        if category:
            query = query.eq('category', category)
        
        response = query.execute()
        
        if not response.data:
            print("No runtime configurations found in database.")
            return
        
        # Group by category
        configs_by_category = {}
        for item in response.data:
            cat = item['category'] or 'uncategorized'
            if cat not in configs_by_category:
                configs_by_category[cat] = []
            configs_by_category[cat].append(item)
        
        # Display
        for cat, configs in configs_by_category.items():
            print(f"\n{cat.upper()}")
            print("-" * 80)
            for config in configs:
                value_str = json.dumps(config['value']) if isinstance(config['value'], dict) else str(config['value'])
                print(f"  {config['key']}: {value_str}")
                if config['description']:
                    print(f"    Description: {config['description']}")
                print(f"    Updated: {config['updated_at']}")
                print()
                
    except Exception as e:
        print(f"Error listing configurations: {e}")
        sys.exit(1)


def get_config(key, account_id=None):
    """Get a specific configuration value."""
    try:
        value = settings.get_dynamic(key, account_id=account_id)
        
        if value is None:
            print(f"Configuration '{key}' not found")
            sys.exit(1)
        
        # Get metadata
        db = DatabaseManager()
        response = db.supabase.table('runtime_config')\
            .select('*')\
            .eq('key', key)\
            .eq('is_active', True)\
            .execute()
        
        print(f"\nConfiguration: {key}")
        print("-" * 80)
        print(f"Value: {json.dumps(value) if isinstance(value, dict) else value}")
        
        if response.data:
            metadata = response.data[0]
            print(f"Description: {metadata.get('description', 'N/A')}")
            print(f"Category: {metadata.get('category', 'N/A')}")
            print(f"Updated: {metadata.get('updated_at', 'N/A')}")
            print(f"Updated By: {metadata.get('updated_by', 'N/A')}")
            print(f"Version: {metadata.get('version', 1)}")
            print(f"Source: Database")
        else:
            print(f"Source: Static configuration (settings.json)")
            
    except Exception as e:
        print(f"Error getting configuration: {e}")
        sys.exit(1)


def set_config(key, value, description=None, account_id=None):
    """Set a configuration value."""
    try:
        # Parse value if it looks like JSON
        if value.startswith('{') or value.startswith('['):
            parsed_value = json.loads(value)
        elif value.lower() == 'true':
            parsed_value = True
        elif value.lower() == 'false':
            parsed_value = False
        elif '.' in value and all(c.isdigit() or c == '.' for c in value):
            parsed_value = float(value)
        elif value.isdigit():
            parsed_value = int(value)
        else:
            parsed_value = value
        
        # Set the configuration
        success = settings.set_dynamic(
            key=key,
            value=parsed_value,
            account_id=account_id,
            description=description,
            updated_by='manage_config.py'
        )
        
        if success:
            print(f"\nSuccessfully updated configuration:")
            print(f"  Key: {key}")
            print(f"  Value: {json.dumps(parsed_value) if isinstance(parsed_value, dict) else parsed_value}")
            if description:
                print(f"  Description: {description}")
            if account_id:
                print(f"  Account ID: {account_id}")
        else:
            print(f"Failed to update configuration '{key}'")
            sys.exit(1)
            
    except json.JSONDecodeError as e:
        print(f"Invalid JSON value: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error setting configuration: {e}")
        sys.exit(1)


def show_history(key=None, limit=50):
    """Show configuration change history."""
    try:
        db = DatabaseManager()
        query = db.supabase.table('runtime_config_history')\
            .select('*')\
            .order('changed_at', desc=True)\
            .limit(limit)
        
        if key:
            query = query.eq('key', key)
        
        response = query.execute()
        
        if not response.data:
            print("No configuration history found.")
            return
        
        print(f"\nConfiguration History (last {limit} changes)")
        print("-" * 120)
        print(f"{'Timestamp':<20} {'Key':<40} {'Old Value':<20} {'New Value':<20} {'Changed By':<15}")
        print("-" * 120)
        
        for item in response.data:
            timestamp = item['changed_at'][:19]
            key_str = item['key'][:38] + '..' if len(item['key']) > 40 else item['key']
            old_val = str(item.get('old_value', 'N/A'))[:18] + '..' if len(str(item.get('old_value', 'N/A'))) > 20 else str(item.get('old_value', 'N/A'))
            new_val = str(item['new_value'])[:18] + '..' if len(str(item['new_value'])) > 20 else str(item['new_value'])
            changed_by = item['changed_by'][:13] + '..' if len(item['changed_by']) > 15 else item['changed_by']
            
            print(f"{timestamp:<20} {key_str:<40} {old_val:<20} {new_val:<20} {changed_by:<15}")
            
    except Exception as e:
        print(f"Error showing history: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description='Manage runtime configuration')
    
    # Commands
    parser.add_argument('--list', action='store_true', help='List all configurations')
    parser.add_argument('--get', metavar='KEY', help='Get a configuration value')
    parser.add_argument('--set', nargs=2, metavar=('KEY', 'VALUE'), help='Set a configuration value')
    parser.add_argument('--history', action='store_true', help='Show configuration history')
    
    # Options
    parser.add_argument('--category', help='Filter by category (for --list)')
    parser.add_argument('--description', help='Description for configuration change (for --set)')
    parser.add_argument('--account-id', help='Account ID for account-specific config')
    parser.add_argument('--limit', type=int, default=50, help='Limit for history (default: 50)')
    
    args = parser.parse_args()
    
    # Execute command
    if args.list:
        list_configs(category=args.category)
    elif args.get:
        get_config(args.get, account_id=args.account_id)
    elif args.set:
        key, value = args.set
        set_config(key, value, description=args.description, account_id=args.account_id)
    elif args.history:
        show_history(limit=args.limit)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()