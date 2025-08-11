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
from scripts.cleanup_nav_data import NavDataCleaner
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


# Custom template filter for formatting date strings
@app.template_filter('date')
def format_date(value, format='%Y-%m-%d %H:%M'):
    if isinstance(value, str):
        try:
            # Attempt to parse ISO format with potential timezone
            dt_object = datetime.fromisoformat(value.replace('Z', '+00:00'))
            return dt_object.strftime(format)
        except ValueError:
            return value  # Return original string if parsing fails
    return value


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


@app.route('/fee-management')
def fee_management():
    """Fee management page."""
    try:
        db = DatabaseManager()
        # Get all accrued fees
        accrued_fees = db._client.table('fee_tracking').select('*').eq('status', 'ACCRUED').execute().data
        # Get all withdrawal transactions
        withdrawals = db._client.table('processed_transactions').select('*').eq('type', 'WITHDRAWAL').execute().data

        for fee in accrued_fees:
            fee['potential_transactions'] = [tx for tx in withdrawals if tx['account_id'] == fee['account_id']]

        return render_template('admin/fee_management.html', accrued_fees=accrued_fees)
    except Exception as e:
        flash(f'Error loading fee management page: {str(e)}', 'error')
        return redirect(url_for('accounts'))


@app.route('/collect-fee', methods=['POST'])
def collect_fee():
    """Collect fee and update transaction type."""
    try:
        fee_id = request.form.get('fee_id')
        transaction_id = request.form.get('transaction_id')

        if not fee_id or not transaction_id:
            flash('Fee ID and Transaction ID are required.', 'error')
            return redirect(url_for('fee_management'))

        db = DatabaseManager()

        # Update fee_tracking table
        db._client.table('fee_tracking').update({
            'status': 'COLLECTED',
            'collection_tx_id': transaction_id,
            'collected_at': datetime.utcnow().isoformat()
        }).eq('id', fee_id).execute()

        # Update processed_transactions table
        db._client.table('processed_transactions').update({
            'type': 'FEE_WITHDRAWAL'
        }).eq('transaction_id', transaction_id).execute()

        flash('Fee collected successfully!', 'success')
        return redirect(url_for('fee_management'))
    except Exception as e:
        flash(f'Error collecting fee: {str(e)}', 'error')
        return redirect(url_for('fee_management'))


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


@app.route('/accounts/update-master-credentials/<account_id>', methods=['POST'])
def update_master_credentials(account_id):
    """Update master API credentials for a sub-account."""
    try:
        data = request.get_json()
        master_api_key = data.get('master_api_key')
        master_api_secret = data.get('master_api_secret')
        
        if not master_api_key or not master_api_secret:
            return jsonify({'success': False, 'error': 'Both API key and secret are required'}), 400
        
        # Update in database
        from utils.database_manager import get_supabase_client
        supabase = get_supabase_client()
        
        result = supabase.table('binance_accounts').update({
            'master_api_key': master_api_key,
            'master_api_secret': master_api_secret
        }).eq('id', account_id).execute()
        
        if result.data:
            return jsonify({
                'success': True, 
                'message': 'Master credentials updated successfully'
            })
        else:
            return jsonify({
                'success': False, 
                'error': 'Failed to update credentials'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False, 
            'error': str(e)
        }), 500


@app.route('/accounts/create', methods=['GET', 'POST'])
def create_account():
    """Create new account."""
    from utils.database_manager import get_supabase_client
    supabase = get_supabase_client()
    
    if request.method == 'GET':
        # Get master accounts for dropdown
        try:
            master_accounts = supabase.table('binance_accounts').select('*').eq('is_sub_account', False).execute()
            print(f"DEBUG: Rendering create account form with {len(master_accounts.data or [])} master accounts")
            return render_template('admin/account_form.html', 
                                 account=None, 
                                 master_accounts=master_accounts.data or [])
        except Exception as e:
            print(f"ERROR in create_account GET: {str(e)}")
            import traceback
            traceback.print_exc()
            flash(f'Error loading form: {str(e)}', 'error')
            return redirect(url_for('accounts'))
    
    # POST - create account
    try:
        # Get form data
        account_name = request.form.get('account_name', '').strip()
        api_key = request.form.get('api_key', '').strip()
        api_secret = request.form.get('api_secret', '').strip()
        email = request.form.get('email', '').strip() or None
        is_sub_account = request.form.get('is_sub_account') == 'on'
        master_account_id = request.form.get('master_account_id') or None
        master_api_key = request.form.get('master_api_key', '').strip() or None
        master_api_secret = request.form.get('master_api_secret', '').strip() or None
        performance_fee_rate = float(request.form.get('performance_fee_rate', 0.5))
        
        # Validate required fields
        if not account_name or not api_key or not api_secret:
            flash('Account name, API key and API secret are required', 'error')
            return redirect(url_for('create_account'))
        
        # Check if account name already exists
        existing = supabase.table('binance_accounts').select('id').eq('account_name', account_name).execute()
        if existing.data:
            flash(f'Account name "{account_name}" already exists', 'error')
            return redirect(url_for('create_account'))
        
        # Create account data
        account_data = {
            'account_name': account_name,
            'api_key': api_key,
            'api_secret': api_secret,
            'email': email,
            'is_sub_account': is_sub_account,
            'performance_fee_rate': performance_fee_rate
        }
        
        # Add sub-account specific fields
        if is_sub_account:
            if master_account_id:
                account_data['master_account_id'] = master_account_id
            if master_api_key and master_api_secret:
                account_data['master_api_key'] = master_api_key
                account_data['master_api_secret'] = master_api_secret
        
        # Insert account
        result = supabase.table('binance_accounts').insert(account_data).execute()
        
        if result.data:
            flash(f'Account "{account_name}" created successfully', 'success')
            return redirect(url_for('accounts'))
        else:
            flash('Failed to create account', 'error')
            return redirect(url_for('create_account'))
            
    except Exception as e:
        flash(f'Error creating account: {str(e)}', 'error')
        return redirect(url_for('create_account'))


@app.route('/accounts/edit/<account_id>', methods=['GET', 'POST'])
def edit_account(account_id):
    """Edit existing account."""
    from utils.database_manager import get_supabase_client
    supabase = get_supabase_client()
    
    # Get account
    account_result = supabase.table('binance_accounts').select('*').eq('id', account_id).execute()
    if not account_result.data:
        flash('Account not found', 'error')
        return redirect(url_for('accounts'))
    
    account = account_result.data[0]
    
    if request.method == 'GET':
        # Get master accounts for dropdown
        master_accounts = supabase.table('binance_accounts').select('*').eq('is_sub_account', False).execute()
        
        # Test current account credentials (with error handling)
        validation_result = None
        try:
            from scripts.validate_account import test_account_settings
            is_valid, message = test_account_settings(account_id)
            validation_result = {
                'is_valid': is_valid,
                'message': message
            }
        except Exception as e:
            # If validation fails, log but continue showing the form
            print(f"Warning: Could not validate account {account_id}: {str(e)}")
        
        return render_template('admin/account_form.html', 
                             account=account, 
                             master_accounts=master_accounts.data or [],
                             validation_result=validation_result)
    
    # POST - update account
    try:
        # Get form data
        account_name = request.form.get('account_name', '').strip()
        api_key = request.form.get('api_key', '').strip()
        api_secret = request.form.get('api_secret', '').strip()
        email = request.form.get('email', '').strip() or None
        is_sub_account = request.form.get('is_sub_account') == 'on'
        master_account_id = request.form.get('master_account_id') or None
        master_api_key = request.form.get('master_api_key', '').strip() or None
        master_api_secret = request.form.get('master_api_secret', '').strip() or None
        performance_fee_rate = float(request.form.get('performance_fee_rate', 0.5))
        
        # Validate required fields
        if not account_name or not api_key or not api_secret:
            flash('Account name, API key and API secret are required', 'error')
            return redirect(url_for('edit_account', account_id=account_id))
        
        # Check if account name already exists (excluding current account)
        existing = supabase.table('binance_accounts').select('id').eq('account_name', account_name).neq('id', account_id).execute()
        if existing.data:
            flash(f'Account name "{account_name}" already exists', 'error')
            return redirect(url_for('edit_account', account_id=account_id))
        
        # Update account data
        update_data = {
            'account_name': account_name,
            'api_key': api_key,
            'api_secret': api_secret,
            'email': email,
            'is_sub_account': is_sub_account,
            'performance_fee_rate': performance_fee_rate
        }
        
        # Handle sub-account fields
        if is_sub_account:
            update_data['master_account_id'] = master_account_id
            update_data['master_api_key'] = master_api_key
            update_data['master_api_secret'] = master_api_secret
        else:
            # Clear sub-account fields if not a sub-account
            update_data['master_account_id'] = None
            update_data['master_api_key'] = None
            update_data['master_api_secret'] = None
        
        # Update account
        result = supabase.table('binance_accounts').update(update_data).eq('id', account_id).execute()
        
        if result.data:
            flash(f'Account "{account_name}" updated successfully', 'success')
            return redirect(url_for('accounts'))
        else:
            flash('Failed to update account', 'error')
            return redirect(url_for('edit_account', account_id=account_id))
            
    except Exception as e:
        flash(f'Error updating account: {str(e)}', 'error')
        return redirect(url_for('edit_account', account_id=account_id))




@app.route('/accounts/test-connection', methods=['POST'])
def test_connection():
    """Test API connection for an account."""
    try:
        data = request.get_json()
        api_key = data.get('api_key', '').strip()
        api_secret = data.get('api_secret', '').strip()
        is_sub_account = data.get('is_sub_account', False)
        master_api_key = data.get('master_api_key', '').strip()
        master_api_secret = data.get('master_api_secret', '').strip()
        email = data.get('email', '').strip()
        
        errors = []
        warnings = []
        
        # Test main API credentials
        if not api_key or not api_secret:
            errors.append('API key and secret are required')
        else:
            # Try to make a simple API call to test credentials
            import requests
            import time
            import hmac
            import hashlib
            from urllib.parse import urlencode
            
            def test_binance_api(key, secret):
                try:
                    base_url = 'https://api.binance.com'
                    endpoint = '/api/v3/account'
                    timestamp = int(time.time() * 1000)
                    params = {'timestamp': timestamp}
                    query_string = urlencode(params)
                    signature = hmac.new(
                        secret.encode('utf-8'),
                        query_string.encode('utf-8'),
                        hashlib.sha256
                    ).hexdigest()
                    params['signature'] = signature
                    
                    headers = {'X-MBX-APIKEY': key}
                    response = requests.get(
                        base_url + endpoint,
                        headers=headers,
                        params=params,
                        timeout=10
                    )
                    
                    if response.status_code == 200:
                        return True, 'Connection successful'
                    elif response.status_code == 401:
                        return False, 'Invalid API credentials'
                    elif response.status_code == 418:
                        return False, 'IP not whitelisted for this API key'
                    else:
                        return False, f'API error (code {response.status_code})'
                except Exception as e:
                    return False, f'Connection failed: {str(e)}'
            
            success, message = test_binance_api(api_key, api_secret)
            if not success:
                errors.append(f'Main API: {message}')
        
        # Test sub-account specific requirements
        if is_sub_account:
            if not email:
                warnings.append('Email is recommended for sub-account transfer detection')
            
            if master_api_key and master_api_secret:
                # Test master API credentials
                success, message = test_binance_api(master_api_key, master_api_secret)
                if not success:
                    errors.append(f'Master API: {message}')
            else:
                warnings.append('Master API credentials not provided - transfer detection will not work')
        
        if errors:
            return jsonify({
                'success': False,
                'errors': errors,
                'warnings': warnings
            })
        else:
            return jsonify({
                'success': True,
                'message': 'All tests passed successfully!',
                'warnings': warnings
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'errors': [f'Unexpected error: {str(e)}']
        }), 500


@app.route('/accounts/delete/<account_id>', methods=['POST'])
def delete_account(account_id):
    """Delete account and all related data."""
    try:
        from utils.database_manager import get_supabase_client
        supabase = get_supabase_client()
        
        # Get account name for message
        account_result = supabase.table('binance_accounts').select('account_name').eq('id', account_id).execute()
        if not account_result.data:
            return jsonify({'success': False, 'error': 'Account not found'}), 404
        
        account_name = account_result.data[0]['account_name']
        
        # Delete related data in order
        tables_to_clean = [
            'processed_transactions',
            'nav_history',
            'benchmark_configs',
            'benchmark_modifications',
            'benchmark_rebalance_history',
            'account_processing_status',
            'fee_tracking'
        ]
        
        for table in tables_to_clean:
            supabase.table(table).delete().eq('account_id', account_id).execute()
        
        # Finally delete the account
        result = supabase.table('binance_accounts').delete().eq('id', account_id).execute()
        
        if result.data:
            return jsonify({
                'success': True,
                'message': f'Account "{account_name}" and all related data deleted successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to delete account'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/accounts/cleanup')
def cleanup_data():
    """Show data cleanup form."""
    try:
        # Get all accounts
        accounts = get_accounts()
        
        return render_template('admin/data_cleanup.html', 
                               accounts=accounts)
    except Exception as e:
        flash(f'Error loading cleanup page: {str(e)}', 'error')
        return redirect(url_for('accounts'))


@app.route('/accounts/cleanup/preview', methods=['POST'])
def preview_cleanup():
    """Preview what data would be deleted."""
    try:
        data = request.get_json()
        account_ids = data.get('account_ids', [])
        from_timestamp = datetime.fromisoformat(data['from_timestamp'].replace('Z', '+00:00'))
        to_timestamp = None
        if data.get('to_timestamp'):
            to_timestamp = datetime.fromisoformat(data['to_timestamp'].replace('Z', '+00:00'))
        
        if not account_ids:
            return jsonify({'success': False, 'error': 'No accounts selected'}), 400
        
        # Get preview
        cleaner = NavDataCleaner(dry_run=True)
        preview = cleaner.preview_cleanup(account_ids, from_timestamp, to_timestamp)
        
        # Get account names for display
        db = DatabaseManager()
        accounts = db._client.table('binance_accounts')\
            .select('id, account_name')\
            .in_('id', account_ids)\
            .execute()
        
        account_names = {a['id']: a['account_name'] for a in accounts.data}
        
        return jsonify({
            'success': True,
            'preview': preview,
            'account_names': account_names,
            'from_timestamp': from_timestamp.isoformat(),
            'to_timestamp': to_timestamp.isoformat() if to_timestamp else None
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/accounts/cleanup/execute', methods=['POST'])
def execute_cleanup():
    """Execute the data cleanup."""
    try:
        data = request.get_json()
        account_ids = data.get('account_ids', [])
        from_timestamp = datetime.fromisoformat(data['from_timestamp'].replace('Z', '+00:00'))
        to_timestamp = None
        if data.get('to_timestamp'):
            to_timestamp = datetime.fromisoformat(data['to_timestamp'].replace('Z', '+00:00'))
        reset_status = data.get('reset_processing_status', True)
        
        if not account_ids:
            return jsonify({'success': False, 'error': 'No accounts selected'}), 400
        
        # Execute cleanup
        cleaner = NavDataCleaner(dry_run=False)
        deleted_counts, errors = cleaner.cleanup_data(
            account_ids, 
            from_timestamp, 
            to_timestamp,
            reset_processing_status=reset_status
        )
        
        if errors:
            return jsonify({
                'success': False,
                'errors': errors,
                'deleted_counts': deleted_counts
            }), 500
        
        return jsonify({
            'success': True,
            'deleted_counts': deleted_counts,
            'message': 'Data cleanup completed successfully'
        })
        
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