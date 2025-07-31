#!/usr/bin/env python3
"""
Web Admin for Runtime Configuration

Simple web interface for managing runtime configuration without authentication.
"""

import json
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_cors import CORS
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings
from config.runtime_config import get_runtime_config
from scripts.reset_account_data import get_accounts, reset_account_data
from utils.database_manager import DatabaseManager

app = Flask(__name__, 
            template_folder='../templates',
            static_folder='../static')
app.secret_key = os.urandom(24)  # For flash messages
CORS(app, origins=['*'])

# Categories for grouping
CATEGORIES = [
    'scheduling',
    'financial', 
    'fee_management',
    'api',
    'data_processing',
    'monitoring',
    'logging',
    'chart_configuration',
    'development'
]

# Configuration metadata
CONFIG_METADATA = {
    # Deprecated/unused configs
    'financial.performance_alert_thresholds': {
        'status': 'deprecated',
        'reason': 'Not implemented - alert functionality not built',
        'alternative': None
    },
    'scheduling.daemon_interval_seconds': {
        'status': 'deprecated', 
        'reason': 'Replaced by scheduling.cron_interval_minutes',
        'alternative': 'scheduling.cron_interval_minutes'
    },
    'financial.rebalance_frequency': {
        'status': 'deprecated',
        'reason': 'Rebalancing uses rebalance_day/hour in benchmark_configs table',
        'alternative': 'benchmark_configs table'
    },
    
    # Active configs with special handling
    'scheduling.cron_interval_minutes': {
        'status': 'active',
        'requires_restart': 'run_forever.py',
        'options': [5, 10, 15, 30, 60]
    },
    'fee_management.calculation_schedule': {
        'status': 'active',
        'options': ['monthly', 'daily', 'hourly']
    },
    'fee_management.calculation_day': {
        'status': 'active',
        'range': [1, 28]
    },
    'fee_management.calculation_hour': {
        'status': 'active',
        'range': [0, 23]
    }
}


@app.route('/')
def index():
    """Main page - list all configurations."""
    try:
        runtime_config = get_runtime_config()
        db = DatabaseManager()
        
        # Get all runtime configs from database
        response = db._client.table('runtime_config')\
            .select('*')\
            .eq('is_active', True)\
            .order('category', desc=False)\
            .order('key', desc=False)\
            .execute()
        
        # Group by category
        configs_by_category = {}
        deprecated_configs = []
        
        for item in response.data:
            cat = item['category'] or 'uncategorized'
            
            # Add current value (might differ from database due to cache)
            item['current_value'] = runtime_config.get(item['key'], use_cache=True)
            
            # Add metadata
            metadata = CONFIG_METADATA.get(item['key'], {})
            item['metadata'] = metadata
            
            # Separate deprecated configs
            if metadata.get('status') == 'deprecated':
                deprecated_configs.append(item)
            else:
                if cat not in configs_by_category:
                    configs_by_category[cat] = []
                configs_by_category[cat].append(item)
        
        # Get cache info
        cache_ttl = runtime_config.cache.ttl_seconds
        
        return render_template('admin/config_list.html',
                             configs_by_category=configs_by_category,
                             deprecated_configs=deprecated_configs,
                             categories=CATEGORIES,
                             cache_ttl=cache_ttl)
        
    except Exception as e:
        flash(f'Error loading configurations: {str(e)}', 'error')
        return render_template('admin/config_list.html', 
                             configs_by_category={}, 
                             deprecated_configs=[],
                             categories=CATEGORIES)


@app.route('/edit/<path:key>')
def edit_config(key):
    """Edit configuration page."""
    try:
        runtime_config = get_runtime_config()
        db = DatabaseManager()
        
        # Get current value and metadata
        current_value = runtime_config.get(key)
        
        # Get metadata from database
        response = db._client.table('runtime_config')\
            .select('*')\
            .eq('key', key)\
            .eq('is_active', True)\
            .execute()
        
        if response.data:
            config = response.data[0]
            config['current_value'] = current_value
        else:
            # Not in database, must be from static config
            config = {
                'key': key,
                'value': current_value,
                'current_value': current_value,
                'description': 'Static configuration from settings.json',
                'category': key.split('.')[0] if '.' in key else 'general',
                'source': 'static'
            }
        
        # Determine value type for input
        if isinstance(current_value, bool):
            value_type = 'boolean'
        elif isinstance(current_value, (int, float)):
            value_type = 'number'
        elif isinstance(current_value, dict):
            value_type = 'json'
        else:
            value_type = 'text'
        
        # Add metadata
        config['metadata'] = CONFIG_METADATA.get(key, {})
        
        return render_template('admin/config_edit.html',
                             config=config,
                             value_type=value_type,
                             value_json=json.dumps(current_value, indent=2) if isinstance(current_value, dict) else None)
        
    except Exception as e:
        flash(f'Error loading configuration: {str(e)}', 'error')
        return redirect(url_for('index'))


@app.route('/save/<path:key>', methods=['POST'])
def save_config(key):
    """Save configuration value."""
    try:
        value_type = request.form.get('value_type')
        value_str = request.form.get('value')
        description = request.form.get('description', '')
        
        # Parse value based on type
        if value_type == 'boolean':
            value = value_str.lower() == 'true'
        elif value_type == 'number':
            value = float(value_str) if '.' in value_str else int(value_str)
        elif value_type == 'json':
            value = json.loads(value_str)
        else:
            value = value_str
        
        # Save to database
        success = settings.set_dynamic(
            key=key,
            value=value,
            description=description or f'Updated via web admin',
            updated_by='web_admin'
        )
        
        if success:
            flash(f'Successfully updated {key}', 'success')
        else:
            flash(f'Failed to update {key}', 'error')
            
    except json.JSONDecodeError:
        flash('Invalid JSON format', 'error')
    except Exception as e:
        flash(f'Error saving configuration: {str(e)}', 'error')
    
    return redirect(url_for('index'))


@app.route('/history')
def history():
    """Configuration change history."""
    try:
        runtime_config = get_runtime_config()
        history_data = runtime_config.get_history(limit=100)
        
        return render_template('admin/config_history.html',
                             history=history_data)
        
    except Exception as e:
        flash(f'Error loading history: {str(e)}', 'error')
        return render_template('admin/config_history.html', history=[])


@app.route('/refresh-cache', methods=['POST'])
def refresh_cache():
    """Clear configuration cache."""
    try:
        runtime_config = get_runtime_config()
        runtime_config.cache.invalidate()
        flash('Cache cleared successfully. New values will be loaded from database.', 'success')
    except Exception as e:
        flash(f'Error clearing cache: {str(e)}', 'error')
    
    return redirect(url_for('index'))


@app.route('/api/validate', methods=['POST'])
def validate_value():
    """Validate configuration value (AJAX endpoint)."""
    try:
        data = request.get_json()
        key = data.get('key')
        value = data.get('value')
        value_type = data.get('type')
        
        errors = []
        
        # Type-specific validation
        if value_type == 'json':
            try:
                json.loads(value)
            except:
                errors.append('Invalid JSON format')
        
        # Key-specific validation
        if key.endswith('_minutes') or key.endswith('_seconds') or key.endswith('_hours'):
            try:
                num_val = float(value)
                if num_val < 0:
                    errors.append('Value must be positive')
            except:
                errors.append('Value must be a number')
        
        if key.endswith('_rate') or key.endswith('percentage'):
            try:
                num_val = float(value)
                if num_val < 0 or num_val > 1:
                    errors.append('Rate must be between 0 and 1')
            except:
                errors.append('Value must be a number')
        
        if key == 'fee_management.calculation_schedule' and value not in ['monthly', 'daily', 'hourly']:
            errors.append('Schedule must be monthly, daily, or hourly')
        
        return jsonify({
            'valid': len(errors) == 0,
            'errors': errors
        })
        
    except Exception as e:
        return jsonify({
            'valid': False,
            'errors': [str(e)]
        })


@app.route('/accounts')
def accounts():
    """Account management page."""
    try:
        accounts_list = get_accounts()
        return render_template('admin/accounts.html', accounts=accounts_list)
    except Exception as e:
        flash(f'Error loading accounts: {str(e)}', 'error')
        return redirect(url_for('index'))


@app.route('/accounts/reset/<account_id>', methods=['POST'])
def reset_account(account_id):
    """Reset account data."""
    try:
        # Get account name for display
        accounts_list = get_accounts()
        account = next((acc for acc in accounts_list if acc['id'] == account_id), None)
        
        if not account:
            return jsonify({'success': False, 'error': 'Account not found'}), 404
        
        # Reset the account (skip confirmation since it's from web UI)
        success = reset_account_data(account_id, account['account_name'], skip_confirmation=True)
        
        if success:
            return jsonify({
                'success': True, 
                'message': f"Account '{account['account_name']}' has been reset successfully"
            })
        else:
            return jsonify({
                'success': False, 
                'error': 'Failed to reset account'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False, 
            'error': str(e)
        }), 500


@app.errorhandler(404)
def not_found(e):
    return render_template('admin/base.html', content='Page not found'), 404


@app.errorhandler(500)
def server_error(e):
    return render_template('admin/base.html', content='Internal server error'), 500


if __name__ == '__main__':
    port = int(os.environ.get('CONFIG_ADMIN_PORT', 8002))
    debug = settings.raw_config.get('development', {}).get('debug_mode', False)
    
    print(f"Starting Config Admin on http://localhost:{port}")
    print("No authentication required - for local use only")
    
    app.run(host='0.0.0.0', port=port, debug=debug)