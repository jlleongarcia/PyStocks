from django.shortcuts import redirect
from django.urls import reverse
from django.contrib.auth.models import AnonymousUser


class ForcePasswordChangeMiddleware:
    """Middleware to force password change for users with temporary passwords"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        # Paths that should be accessible without password change
        allowed_paths = [
            reverse('password_change_required'),
            reverse('logout'),
            '/admin/logout/',
        ]
        
        # Check if user needs to change password
        if (not isinstance(request.user, AnonymousUser) and 
            request.user.is_authenticated and 
            hasattr(request.user, 'profile') and
            request.user.profile.force_password_change and
            request.path not in allowed_paths and
            not request.path.startswith('/static/') and
            not request.path.startswith('/media/')):
            
            return redirect('password_change_required')
        
        response = self.get_response(request)
        return response
