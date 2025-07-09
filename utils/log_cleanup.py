"""Log cleanup utilities for managing database log retention."""

from datetime import datetime, timedelta
from supabase import create_client, Client
from config import settings
from api.logger import get_logger, LogCategory
import time


class LogCleanupManager:
    """Manages cleanup of old logs from the database."""
    
    LAST_CLEANUP_KEY = 'last_log_cleanup'
    CLEANUP_INTERVAL_HOURS = 24  # Run cleanup once per day
    
    def __init__(self):
        self.config = settings
        self.logger = get_logger()
        self.supabase = create_client(settings.database.supabase_url, settings.database.supabase_key)
        
    def should_run_cleanup(self):
        """Check if cleanup should run based on last execution time."""
        try:
            # Check metadata table for last cleanup timestamp
            response = self.supabase.table('system_metadata').select('*').eq('key', self.LAST_CLEANUP_KEY).execute()
            
            if not response.data:
                # No record exists, should run cleanup
                return True
                
            last_cleanup_str = response.data[0].get('value')
            if not last_cleanup_str:
                return True
                
            last_cleanup = datetime.fromisoformat(last_cleanup_str)
            hours_since_cleanup = (datetime.utcnow() - last_cleanup).total_seconds() / 3600
            
            return hours_since_cleanup >= self.CLEANUP_INTERVAL_HOURS
            
        except Exception as e:
            self.logger.warning(LogCategory.SYSTEM, "cleanup_check_error", 
                              f"Error checking last cleanup time: {str(e)}")
            # On error, allow cleanup to run
            return True
    
    def update_last_cleanup_time(self):
        """Update the last cleanup timestamp in metadata."""
        try:
            current_time = datetime.utcnow().isoformat()
            
            # Try to update existing record
            response = self.supabase.table('system_metadata').upsert({
                'key': self.LAST_CLEANUP_KEY,
                'value': current_time,
                'updated_at': current_time
            }).execute()
            
        except Exception as e:
            self.logger.error(LogCategory.SYSTEM, "cleanup_timestamp_error", 
                            f"Failed to update cleanup timestamp: {str(e)}")
    
    def cleanup_old_logs(self):
        """Remove logs older than retention period."""
        if not self.should_run_cleanup():
            return
            
        try:
            start_time = time.time()
            retention_days = self.config.logging.database_logging['retention_days']
            
            # Calculate cutoff date
            cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
            
            self.logger.info(LogCategory.SYSTEM, "log_cleanup_start", 
                           f"Starting log cleanup for logs older than {retention_days} days")
            
            # Delete old logs using RPC function if available
            try:
                # Try to use the SQL function we defined
                response = self.supabase.rpc('cleanup_old_system_logs').execute()
                self.logger.info(LogCategory.SYSTEM, "log_cleanup_function", 
                               "Used SQL cleanup function")
            except:
                # Fallback to direct deletion
                response = self.supabase.table('system_logs').delete().lt('created_at', cutoff_date.isoformat()).execute()
                
            # Get count of remaining logs
            count_response = self.supabase.table('system_logs').select('count', count='exact').execute()
            remaining_logs = count_response.count if count_response else 'unknown'
            
            elapsed_time = time.time() - start_time
            
            self.logger.info(LogCategory.SYSTEM, "log_cleanup_complete", 
                           f"Log cleanup completed in {elapsed_time:.2f}s. Remaining logs: {remaining_logs}")
            
            # Update last cleanup time
            self.update_last_cleanup_time()
            
        except Exception as e:
            self.logger.error(LogCategory.SYSTEM, "log_cleanup_error", 
                            f"Failed to cleanup logs: {str(e)}")


def run_log_cleanup():
    """Convenience function to run log cleanup."""
    manager = LogCleanupManager()
    manager.cleanup_old_logs()