#!/usr/bin/env python3
"""
Apply runtime configuration migrations
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.database_manager import DatabaseManager

def apply_migrations():
    """Apply runtime configuration migrations."""
    print("Applying Runtime Configuration Migrations")
    print("=" * 50)
    
    db = DatabaseManager()
    
    # Read migration files
    migrations = [
        'migrations/add_runtime_configuration_tables.sql',
        'migrations/populate_runtime_config.sql'
    ]
    
    for migration_file in migrations:
        print(f"\nApplying {migration_file}...")
        try:
            with open(migration_file, 'r') as f:
                sql = f.read()
                
            # Split by semicolon and execute each statement
            statements = [s.strip() for s in sql.split(';') if s.strip()]
            
            for i, statement in enumerate(statements):
                if statement:
                    try:
                        # Use raw SQL execution
                        db._client.rpc('exec_sql', {'query': statement + ';'}).execute()
                        print(f"  ✓ Statement {i+1}/{len(statements)} executed")
                    except Exception as e:
                        if 'already exists' in str(e):
                            print(f"  ⚠ Statement {i+1} skipped (already exists)")
                        else:
                            print(f"  ✗ Statement {i+1} failed: {e}")
                            
            print(f"✓ {migration_file} completed")
            
        except Exception as e:
            print(f"✗ Failed to apply {migration_file}: {e}")
            print("\nYou may need to run the migrations manually:")
            print(f"psql $DATABASE_URL < {migration_file}")
            return False
    
    print("\n" + "=" * 50)
    print("✅ Migrations completed!")
    return True

if __name__ == '__main__':
    apply_migrations()