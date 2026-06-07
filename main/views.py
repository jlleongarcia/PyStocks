from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse


def home(request):
    if request.user.is_authenticated:
        return redirect('portfolio:portfolio_list_view')
    return redirect('login')


@login_required
def password_change_required(request):
    if request.method == 'POST':
        old_password = request.POST.get('old_password')
        new_password1 = request.POST.get('new_password1')
        new_password2 = request.POST.get('new_password2')

        if not request.user.check_password(old_password):
            messages.error(request, 'Current password is incorrect.')
        elif new_password1 != new_password2:
            messages.error(request, 'New passwords do not match.')
        elif old_password == new_password1:
            messages.error(request, 'New password must be different from the current password.')
        elif len(new_password1) < 8:
            messages.error(request, 'New password must be at least 8 characters long.')
        else:
            request.user.set_password(new_password1)
            request.user.profile.force_password_change = False
            request.user.profile.password_changed_at = timezone.now()
            request.user.save()
            request.user.profile.save()
            update_session_auth_hash(request, request.user)
            messages.success(request, 'Password changed successfully.')
            return redirect('portfolio:portfolio_list_view')

    return render(request, 'password_change_required.html')


@api_view(['GET'])
def api_root(request, format=None):
    return Response({
        'message': 'Py-Stocks Portfolio Management API',
        'version': '2.0.0',
        'endpoints': {
            'portfolio': {
                'list': reverse('portfolio:portfolio-list', request=request, format=format),
                'transactions': reverse('portfolio:transaction-create', request=request, format=format),
                'dividends': reverse('portfolio:dividend-list', request=request, format=format),
            },
            'authentication': {
                'obtain_token': reverse('token_obtain_pair', request=request, format=format),
                'refresh_token': reverse('token_refresh', request=request, format=format),
            },
        },
    })
