def handler(request, response):
    """Simple health check endpoint for Vercel."""
    response.status_code = 200
    return {
        "status": "healthy",
        "version": "v3-2025-07-13-14:10",
        "message": "MinimalSettings fix deployed"
    }