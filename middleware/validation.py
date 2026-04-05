"""Input validation middleware for security."""
import logging
from flask import Flask, request

logger = logging.getLogger(__name__)


class InputValidationMiddleware:
    """
    Input validation middleware for verifying and sanitizing user input.
    Prevents security vulnerabilities like path traversal.
    """

    def __init__(self, app: Flask):
        self.app = app
        self.init_app(app)

    def init_app(self, app: Flask):
        """Initialize the middleware with the Flask app."""
        app.before_request(self.validate_request)

    def validate_request(self):
        """Validate each incoming request."""
        # Skip static files
        if request.path.startswith('/static'):
            return

        # Validate Content-Type for POST/PUT/PATCH
        if request.method in ['POST', 'PUT', 'PATCH']:
            content_type = request.content_type or ''
            if request.path.startswith('/upload') and 'multipart/form-data' not in content_type:
                logger.warning(f'Invalid content type for upload: {content_type}')

        # Validate User-Agent header length
        user_agent = request.headers.get('User-Agent', '')
        if len(user_agent) > 500:
            logger.warning(f'Suspiciously long User-Agent: {len(user_agent)} chars')

        # Check for path traversal attempts
        if '../' in request.path or '%2e%2e' in request.path.lower():
            logger.error(f'Path traversal attempt detected: {request.path}')
            return 'Invalid request', 400
