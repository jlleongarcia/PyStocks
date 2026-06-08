"""
Research app views — account management only.
Stock data is handled internally via research.services.StockDataFetcher.
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages

from .models import UserRegistrationRequest
from .forms import UserRegistrationForm, AccountSettingsForm, PasswordChangeForm

import logging
logger = logging.getLogger(__name__)


def user_registration(request):
    """User registration — creates a pending request awaiting admin approval."""
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            solicitud = form.save()

            try:
                from django.core.mail import send_mail
                from django.conf import settings
                from django.contrib.auth.models import User

                admin_user = User.objects.filter(is_superuser=True).first()
                admin_email = (
                    admin_user.email
                    if admin_user and admin_user.email
                    else getattr(settings, 'ADMIN_EMAIL', '')
                )
                send_mail(
                    subject=f'[Market Mind] New registration request — {solicitud.username}',
                    message=(
                        f'New registration request.\n\n'
                        f'Username: {solicitud.username}\n'
                        f'Name: {solicitud.first_name} {solicitud.last_name}\n'
                        f'Email: {solicitud.email}\n'
                        f'Date: {solicitud.request_date.strftime("%m/%d/%Y %H:%M")}\n\n'
                        f'Admin panel: {request.build_absolute_uri("/admin/research/userregistrationrequest/")}'
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[admin_email],
                    fail_silently=True,
                )
            except Exception as e:
                logger.error(f'Error sending admin notification: {e}')

            messages.success(
                request,
                f'Registration request sent. We will contact you at {solicitud.email} when approved.'
            )
            return redirect('research:registration_success')
    else:
        form = UserRegistrationForm()

    return render(request, 'registration/registro.html', {'form': form})


def registration_success(request):
    return render(request, 'registration/registro_exitoso.html')


@login_required
def account_panel(request):
    return render(request, 'registration/account_panel.html', {'user': request.user})


@login_required
def account_settings(request):
    if request.method == 'POST':
        form = AccountSettingsForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Account settings updated.')
            return redirect('research:account_panel')
    else:
        form = AccountSettingsForm(instance=request.user)

    return render(request, 'registration/account_settings.html', {'form': form})


@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Password changed successfully.')
            return redirect('research:account_panel')
    else:
        form = PasswordChangeForm(request.user)

    return render(request, 'registration/change_password.html', {'form': form})
