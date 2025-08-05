# ⚙️ Configuration Guide

This guide explains how to configure the Binance Portfolio Monitor.

## Environment Variables (.env)

The `.env` file is used to store sensitive information, such as API keys and database credentials. This file should never be committed to version control.

### Required Variables

*   `SUPABASE_URL`: The URL of your Supabase project.
*   `SUPABASE_ANON_KEY`: The anonymous key for your Supabase project.

### Optional Variables

*   `SUPABASE_SERVICE_ROLE_KEY`: The service role key for your Supabase project (for enhanced security).
*   `DEMO_MODE`: Set to `true` to run the application in demo mode with mock data.
*   `LOG_LEVEL`: The logging level (e.g., `DEBUG`, `INFO`, `WARNING`, `ERROR`).
*   `WEBHOOK_URL`: The URL for sending notifications.
*   `NOTIFICATION_ENABLED`: Set to `true` to enable notifications.

## Main Configuration (config/settings.json)

The `config/settings.json` file contains the main configuration for the application. It is divided into several sections:

*   **database**: Database connection settings.
*   **scheduling**: Cron job and daemon scheduling settings.
*   **financial**: Financial parameters, such as benchmark allocation and rebalancing frequency.
*   **api**: Binance API settings.
*   **dashboard**: Web dashboard settings.
*   **logging**: Logging configuration.
*   **file_system**: File system paths.
*   **notifications**: Notification settings.
*   **security**: Security settings, such as CORS origins and API rate limiting.
*   **runtime**: Runtime settings, such as the Python version and environment.
*   **chart_configuration**: Chart.js configuration.
*   **data_processing**: Data processing settings.
*   **monitoring**: Health check and performance monitoring settings.
*   **fee_management**: Fee management settings.
*   **development**: Development settings.

## Environment-Specific Configuration

You can override the default settings in `config/settings.json` for different environments by creating a JSON file in the `config/environments/` directory. The name of the file should correspond to the environment name (e.g., `production.json`, `development.json`, `test.json`).

The application will automatically load the configuration for the current environment, which is determined by the `runtime.environment` setting in `config/settings.json` or by the `ENVIRONMENT` environment variable.

