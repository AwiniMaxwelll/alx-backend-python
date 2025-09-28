import logging
import time
from datetime import datetime

from django.core.cache import cache
from django.http import JsonResponse

# Configure logger with more specific settings
logger = logging.getLogger('request_logging')
logger.setLevel(logging.INFO)
handler = logging.FileHandler('requests.log')
formatter = logging.Formatter('%(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# Basic configuration for logging to a file
logging.basicConfig(filename='requests.log', level=logging.INFO)

class RequestLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        user = request.user.email if request.user.is_authenticated else 'AnonymousUser'
        log_message = f"{datetime.now()} - User: {user} - Path: {request.path}"
        logging.info(log_message)

        response = self.get_response(request)

        return response


class RestrictAccessByTimeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check if the request is for chat-related paths
        if self.is_chat_request(request):
            current_hour = datetime.now().hour

            # Check if current time is outside allowed hours (6PM to 9PM = 18 to 21)
            if current_hour < 18 or current_hour >= 21:
                return JsonResponse(
                    {'error': 'Chat access is restricted. Available from 6:00 PM to 9:00 PM.'},
                    status=403
                )

        response = self.get_response(request)
        return response

    def is_chat_request(self, request):
        """
        Check if the request is related to chat functionality.
        Adjust paths based on your URL patterns.
        """
        chat_paths = ['/api/conversations/', '/api/messages/']
        return any(request.path.startswith(path) for path in chat_paths)


class OffensiveLanguageMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.max_messages = 5  # Maximum messages per time window
        self.time_window = 60  # Time window in seconds (1 minute)

    def __call__(self, request):
        # Check if it's a POST request to chat endpoints
        if request.method == 'POST' and self.is_chat_request(request):
            client_ip = self.get_client_ip(request)

            # Check rate limit for this IP
            if self.is_rate_limited(client_ip):
                return JsonResponse(
                    {'error': 'Rate limit exceeded. You can only send 5 messages per minute.'},
                    status=429
                )

        response = self.get_response(request)
        return response

    def get_client_ip(self, request):
        """Extract client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    def is_chat_request(self, request):
        """Check if the request is related to chat functionality."""
        chat_paths = ['/api/conversations/', '/api/messages/']
        return any(request.path.startswith(path) for path in chat_paths)

    def is_rate_limited(self, ip_address):
        """Check if IP has exceeded rate limit and update counter."""
        cache_key = f"rate_limit_{ip_address}"
        current_time = time.time()

        # Get existing data from cache
        rate_data = cache.get(cache_key, {'count': 0, 'window_start': current_time})

        # Check if we're still in the same time window
        if current_time - rate_data['window_start'] > self.time_window:
            # Reset counter for new time window
            rate_data = {'count': 1, 'window_start': current_time}
        else:
            # Increment counter in current window
            rate_data['count'] += 1

        # Update cache
        cache.set(cache_key, rate_data, timeout=self.time_window + 10)

        # Return True if rate limit exceeded
        return rate_data['count'] > self.max_messages


class RolepermissionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check if the request is for chat-related paths
        if self.is_chat_request(request):
            # Block unauthenticated users completely
            print(f"Request Object: {request}")
            print(f"Request User: {request.user}, Authenticated: {request.user.is_authenticated}")
            if not request.user.is_authenticated:
                return JsonResponse(
                    {'error': 'Authentication required. Please login to access chat.'},
                    status=401
                )

            # Check if authenticated user has required role permissions
            if not self.has_required_role(request.user):
                return JsonResponse(
                    {'error': 'Access denied. Admin or Host role required for chat access.'},
                    status=403
                )

        response = self.get_response(request)
        return response

    def is_chat_request(self, request):
        """Check if the request is related to chat functionality."""
        chat_paths = ['/api/conversations/', '/api/messages/']
        return any(request.path.startswith(path) for path in chat_paths)

    def has_required_role(self, user):
        """Check if user has admin or host role (not guest)."""
        from .models import User
        allowed_roles = [User.Role.ADMIN, User.Role.HOST]
        return user.role in allowed_roles