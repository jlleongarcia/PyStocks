"""
Custom adapters for django-allauth that require manual approval
"""

from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.exceptions import ImmediateHttpResponse
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse
from .models import UserRegistrationRequest


class AccountAdapter(DefaultAccountAdapter):
    """
    Adapter for regular accounts (manual form)
    Maintains existing behavior
    """
    
    def save_user(self, request, user, form, commit=True):
        """
        Override to prevent users from being created directly
        The user is created only when the request is approved
        """
        # Don't create the user directly, handle through UserRegistrationRequest
        return user


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Adapter for social accounts that requires manual approval
    """
    
    def is_open_for_signup(self, request, sociallogin):
        """
        Allow social registration process to create pending requests
        """
        return True
    
    def pre_social_login(self, request, sociallogin):
        """
        Executed before social login
        Check if user already exists or has pending request
        """
        # If user is already connected to a social account, continue
        if sociallogin.is_existing:
            return
        
        email = sociallogin.account.extra_data.get('email')
        if not email:
            messages.error(request, 'Could not get email from your Google account.')
            raise ImmediateHttpResponse(redirect(reverse('account_login')))
        
        # Check if there's already a pending request for this email
        existing_request = UserRegistrationRequest.objects.filter(
            email=email, 
            status='pending'
        ).first()
        
        if existing_request:
            messages.warning(
                request, 
                f'There is already a pending request for {email}. '
                'We will contact you when it is approved.'
            )
            raise ImmediateHttpResponse(redirect(reverse('research:registration_success')))
        
        # Check if there's already a rejected request
        rejected_request = UserRegistrationRequest.objects.filter(
            email=email, 
            status='rejected'
        ).first()
        
        if rejected_request:
            messages.error(
                request, 
                f'The request for {email} was previously rejected. '
                'Please contact the administrator.'
            )
            raise ImmediateHttpResponse(redirect(reverse('account_login')))
    
    def save_user(self, request, sociallogin, form=None):
        """
        Instead of creating the user directly, create a UserRegistrationRequest
        """
        # Get data from social login
        email = sociallogin.account.extra_data.get('email')
        first_name = sociallogin.account.extra_data.get('given_name', '')
        last_name = sociallogin.account.extra_data.get('family_name', '')
        google_id = sociallogin.account.uid
        google_picture = sociallogin.account.extra_data.get('picture', '')
        
        # Generate unique username based on email
        username = self._generate_unique_username(email)
        
        # Create pending registration request
        registration_request = UserRegistrationRequest.objects.create(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            registration_type='google',
            google_id=google_id,
            google_picture=google_picture,
            status='pending'
        )
        
        # Notify administrator
        self._notify_admin(request, registration_request)
        
        # Show message to user and redirect
        messages.success(
            request, 
            f'Google registration request sent! '
            f'Your request is pending approval. '
            f'We will contact you at {email} when it is processed.'
        )
        
        # Stop login process and redirect
        raise ImmediateHttpResponse(redirect(reverse('research:registration_success')))
    
    def _generate_unique_username(self, email):
        """Generate a unique username based on email"""
        from django.contrib.auth.models import User
        
        # Get base username from email
        base_username = email.split('@')[0]
        username = base_username
        counter = 1
        
        # Ensure uniqueness
        while (User.objects.filter(username=username).exists() or 
               UserRegistrationRequest.objects.filter(username=username).exists()):
            username = f"{base_username}{counter}"
            counter += 1
        
        return username
    
    def _notify_admin(self, request, solicitud):
        """Send notification to administrator about new Google request"""
        try:
            from django.core.mail import send_mail
            from django.conf import settings
            from django.contrib.auth.models import User
            import logging
            
            logger = logging.getLogger(__name__)
            
            # Get administrator email
            try:
                admin_user = User.objects.filter(is_superuser=True).first()
                admin_email = admin_user.email if admin_user and admin_user.email else settings.ADMIN_EMAIL
            except:
                admin_email = settings.ADMIN_EMAIL
            
            subject = f'[Py-Stocks] New Google request - {solicitud.username}'
            message = f"""
Hello Administrator,

A new Google registration request has been received for Py-Stocks.

Applicant details:
- Registration type: Google OAuth
- Generated username: {solicitud.username}
- Full name: {solicitud.first_name} {solicitud.last_name}
- Email: {solicitud.email}
- Google ID: {solicitud.google_id}
- Request date: {solicitud.request_date.strftime('%m/%d/%Y %H:%M')}

To review and approve/reject this request, access the admin panel:
{request.build_absolute_uri('/admin/research/userregistrationrequest/')}

Best regards,
Py-Stocks
            """
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[admin_email],
                fail_silently=False,
            )
            logger.info(f"Google notification email sent to admin {admin_email} for request {solicitud.username}")
            
        except Exception as e:
            # Log error but continue
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error sending Google notification email to admin: {e}")
            print(f"Error sending Google notification email to admin: {e}")