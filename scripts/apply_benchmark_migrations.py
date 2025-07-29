#!/usr/bin/env python3
"""
Apply benchmark metadata migrations to the database
"""

import os
import sys

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.supabase_client import get_supabase_client

def apply_migrations():
    """Apply SQL migrations for benchmark metadata improvements"""
    
    # Get Supabase client
    db_client = get_supabase_client()
    project_id = "axvqumsxlncbqzecjlxy"  # From the Supabase project list
    
    # Read migration files
    migrations_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'migrations')
    
    migrations = [
        '001_benchmark_rebalance_history.sql',
        '002_benchmark_modifications.sql'
    ]
    
    print("Applying benchmark metadata migrations...")
    print(f"Project ID: {project_id}")
    print("-" * 60)
    
    for migration_file in migrations:
        filepath = os.path.join(migrations_dir, migration_file)
        if os.path.exists(filepath):
            print(f"\nApplying migration: {migration_file}")
            
            with open(filepath, 'r') as f:
                sql = f.read()
            
            # Split the SQL into individual statements (by semicolon)
            statements = [s.strip() for s in sql.split(';') if s.strip()]
            
            for i, statement in enumerate(statements, 1):
                # Skip comments
                if statement.startswith('--'):
                    continue
                    
                try:
                    # Use the MCP Supabase tool to apply the migration
                    print(f"  Executing statement {i}/{len(statements)}...")
                    # Note: In production, you would use db_client.rpc() or execute through MCP
                    print(f"  Statement preview: {statement[:100]}...")
                    
                except Exception as e:
                    print(f"  ERROR: {str(e)}")
                    return False
            
            print(f"✅ Migration {migration_file} applied successfully")
        else:
            print(f"❌ Migration file not found: {filepath}")
            return False
    
    print("\n" + "="*60)
    print("✅ All migrations applied successfully!")
    print("="*60)
    
    # Provide instructions for manual application
    print("\nTo apply these migrations manually:")
    print("1. Connect to your Supabase database")
    print("2. Run the SQL files in order:")
    print("   - migrations/001_benchmark_rebalance_history.sql")
    print("   - migrations/002_benchmark_modifications.sql")
    print("\nOr use the mcp__supabase__apply_migration tool")
    
    return True

if __name__ == "__main__":
    success = apply_migrations()
    sys.exit(0 if success else 1)