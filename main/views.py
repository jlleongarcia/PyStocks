from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse


def home(request):
    """
    Home page - MarketMind landing page
    """
    return render(request, 'index.html')


@login_required
def password_change_required(request):
    """
    Force password change for users with temporary passwords
    """
    if request.method == 'POST':
        old_password = request.POST.get('old_password')
        new_password1 = request.POST.get('new_password1')
        new_password2 = request.POST.get('new_password2')
        
        # Validate old password
        if not request.user.check_password(old_password):
            messages.error(request, 'Current password is incorrect.')
        # Validate new passwords match
        elif new_password1 != new_password2:
            messages.error(request, 'New passwords do not match.')
        # Validate new password is different
        elif old_password == new_password1:
            messages.error(request, 'New password must be different from the current password.')
        # Validate password strength (minimum 8 characters)
        elif len(new_password1) < 8:
            messages.error(request, 'New password must be at least 8 characters long.')
        else:
            # Change password
            request.user.set_password(new_password1)
            request.user.profile.force_password_change = False
            request.user.profile.password_changed_at = timezone.now()
            request.user.save()
            request.user.profile.save()
            
            # Keep user logged in after password change
            update_session_auth_hash(request, request.user)
            
            messages.success(request, 'Your password has been successfully changed!')
            return redirect('home')
    
    return render(request, 'password_change_required.html')


@api_view(['GET'])
def api_root(request, format=None):
    """
    API Root - Welcome to MarketMind API
    """
    return Response({
        'message': 'Welcome to MarketMind - Stock Market Research & Portfolio Management API',
        'version': '1.0.0',
        'endpoints': {
            'admin': reverse('admin:index', request=request, format=format),
            'research': {
                'search_stocks': '/api/research/stocks/search/?q=AAPL',
                'stock_detail': '/api/research/stocks/{symbol}/',
                'stock_history': '/api/research/stocks/{symbol}/history/?period=1mo',
                'stock_metrics': '/api/research/stocks/{symbol}/metrics/',
            },
            'portfolio': {
                'list': reverse('portfolio:portfolio-list', request=request, format=format),
                'transactions': reverse('portfolio:transaction-create', request=request, format=format),
                'dividends': reverse('portfolio:dividend-list', request=request, format=format),
            },
            'authentication': {
                'obtain_token': reverse('token_obtain_pair', request=request, format=format),
                'refresh_token': reverse('token_refresh', request=request, format=format),
            }
        },
        'documentation': {
            'free_tier': 'Research endpoints are available without authentication',
            'premium_tier': 'Portfolio endpoints require JWT authentication',
        }
    })
