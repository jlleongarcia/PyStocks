"""
Custom adapters for django-allauth — requires manual approval for new accounts.
"""
from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.exceptions import ImmediateHttpResponse
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse
from .models import UserRegistrationRequest


class AccountAdapter(DefaultAccountAdapter):
    """Prevent direct user creation; accounts are created through the approval flow."""

    def save_user(self, request, user, form, commit=True):
        return user


class SocialAccountAdapter(DefaultSocialAccountAdapter):

    def is_open_for_signup(self, request, sociallogin):
        return True

    def pre_social_login(self, request, sociallogin):
        if sociallogin.is_existing:
            return

        email = sociallogin.account.extra_data.get('email')
        if not email:
            messages.error(request, 'Could not get email from your Google account.')
            raise ImmediateHttpResponse(redirect(reverse('account_login')))

        pending = UserRegistrationRequest.objects.filter(email=email, status='pending').first()
        if pending:
            messages.warning(request, f'A pending request for {email} already exists. We will contact you when approved.')
            raise ImmediateHttpResponse(redirect(reverse('research:registration_success')))

        rejected = UserRegistrationRequest.objects.filter(email=email, status='rejected').first()
        if rejected:
            messages.error(request, f'The request for {email} was previously rejected. Please contact the administrator.')
            raise ImmediateHttpResponse(redirect(reverse('account_login')))

    def save_user(self, request, sociallogin, form=None):
        email = sociallogin.account.extra_data.get('email')
        first_name = sociallogin.account.extra_data.get('given_name', '')
        last_name = sociallogin.account.extra_data.get('family_name', '')
        google_id = sociallogin.account.uid
        google_picture = sociallogin.account.extra_data.get('picture', '')

        username = self._generate_unique_username(email)

        registration_request = UserRegistrationRequest.objects.create(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            registration_type='google',
            google_id=google_id,
            google_picture=google_picture,
            status='pending',
        )

        self._notify_admin(request, registration_request)

        messages.success(
            request,
            f'Google registration request sent. We will contact you at {email} when approved.'
        )
        raise ImmediateHttpResponse(redirect(reverse('research:registration_success')))

    def _generate_unique_username(self, email):
        from django.contrib.auth.models import User
        base = email.split('@')[0]
        username = base
        counter = 1
        while (User.objects.filter(username=username).exists() or
               UserRegistrationRequest.objects.filter(username=username).exists()):
            username = f"{base}{counter}"
            counter += 1
        return username

    def _notify_admin(self, request, solicitud):
        try:
            from django.core.mail import send_mail
            from django.conf import settings
            from django.contrib.auth.models import User

            admin_user = User.objects.filter(is_superuser=True).first()
            admin_email = (
                admin_user.email if admin_user and admin_user.email
                else getattr(settings, 'ADMIN_EMAIL', '')
            )
            send_mail(
                subject=f'[Py-Stocks] New Google request — {solicitud.username}',
                message=(
                    f'New Google registration request.\n\n'
                    f'Username: {solicitud.username}\n'
                    f'Name: {solicitud.first_name} {solicitud.last_name}\n'
                    f'Email: {solicitud.email}\n'
                    f'Date: {solicitud.request_date.strftime("%m/%d/%Y %H:%M")}\n\n'
                    f'Admin: {request.build_absolute_uri("/admin/research/userregistrationrequest/")}'
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[admin_email],
                fail_silently=True,
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f'Admin notification error: {e}')
