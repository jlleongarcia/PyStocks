"""
Forms for user registration and account management
"""

from django import forms
from django.contrib.auth.models import User
from .models import UserRegistrationRequest


class UserRegistrationForm(forms.Form):
    """Form for user registration requests"""
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your username'
        }),
        help_text='Unique username for your account. Only letters, numbers and @/./+/-/_ allowed.'
    )
    
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email address'
        }),
        help_text='We will use this to contact you about your request.'
    )
    
    first_name = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your first name'
        })
    )
    
    last_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your last name'
        })
    )
    
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your password'
        }),
        help_text='Password must be at least 8 characters long and contain letters and numbers.'
    )
    
    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm your password'
        })
    )
    
    def clean_username(self):
        """Validate username uniqueness"""
        username = self.cleaned_data.get("username")
        
        # Check if username already exists
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("This username is already taken.")
        
        # Check if there's a pending request with this username
        if UserRegistrationRequest.objects.filter(username=username, status='pending').exists():
            raise forms.ValidationError("There is already a pending request with this username.")
        
        return username
    
    def clean_email(self):
        """Validate email uniqueness"""
        email = self.cleaned_data.get("email")
        
        # Check if email already exists
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already registered.")
        
        # Check if there's a pending request with this email
        if UserRegistrationRequest.objects.filter(email=email, status='pending').exists():
            raise forms.ValidationError("There is already a pending request with this email.")
        
        return email
    
    def clean_password1(self):
        """Validate password strength"""
        password = self.cleaned_data.get("password1")
        
        if len(password) < 8:
            raise forms.ValidationError("Password must be at least 8 characters long.")
        
        # Check for at least one letter and one number
        has_letter = any(char.isalpha() for char in password)
        has_number = any(char.isdigit() for char in password)
        
        if not has_letter:
            raise forms.ValidationError("Password must contain at least one letter.")
        
        if not has_number:
            raise forms.ValidationError("Password must contain at least one number.")
        
        return password
    
    def clean(self):
        """Validate password confirmation"""
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")
        
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match.")
        
        return cleaned_data
    
    def save(self):
        """Create a new registration request"""
        from django.contrib.auth.hashers import make_password
        
        # Create password hash
        password_hash = make_password(self.cleaned_data['password1'])
        
        # Create registration request
        request = UserRegistrationRequest.objects.create(
            username=self.cleaned_data['username'],
            email=self.cleaned_data['email'],
            first_name=self.cleaned_data['first_name'],
            last_name=self.cleaned_data['last_name'],
            password_hash=password_hash,
            status='pending'
        )
        
        return request


class AccountSettingsForm(forms.ModelForm):
    """Form for users to manage their account settings"""
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your first name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your last name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your email address'
            }),
        }
    
    def clean_email(self):
        """Validate email uniqueness (excluding current user)"""
        email = self.cleaned_data.get('email')
        
        # Check if another user already has this email
        existing_user = User.objects.filter(email=email).exclude(pk=self.instance.pk)
        if existing_user.exists():
            raise forms.ValidationError("This email is already in use by another user.")
        
        return email


class PasswordChangeForm(forms.Form):
    """Form for users to change their password"""
    current_password = forms.CharField(
        label='Current Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your current password'
        })
    )
    
    new_password1 = forms.CharField(
        label='New Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your new password'
        }),
        help_text='Password must be at least 8 characters long and contain letters and numbers.'
    )
    
    new_password2 = forms.CharField(
        label='Confirm New Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm your new password'
        })
    )
    
    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
    
    def clean_current_password(self):
        """Validate current password"""
        current_password = self.cleaned_data.get('current_password')
        
        if not self.user.check_password(current_password):
            raise forms.ValidationError("Current password is incorrect.")
        
        return current_password
    
    def clean_new_password1(self):
        """Validate new password strength"""
        password = self.cleaned_data.get("new_password1")
        
        if len(password) < 8:
            raise forms.ValidationError("Password must be at least 8 characters long.")
        
        # Check for at least one letter and one number
        has_letter = any(char.isalpha() for char in password)
        has_number = any(char.isdigit() for char in password)
        
        if not has_letter:
            raise forms.ValidationError("Password must contain at least one letter.")
        
        if not has_number:
            raise forms.ValidationError("Password must contain at least one number.")
        
        return password
    
    def clean(self):
        """Validate password confirmation"""
        cleaned_data = super().clean()
        new_password1 = cleaned_data.get("new_password1")
        new_password2 = cleaned_data.get("new_password2")
        
        if new_password1 and new_password2 and new_password1 != new_password2:
            raise forms.ValidationError("New passwords don't match.")
        
        return cleaned_data
    
    def save(self):
        """Change the user's password"""
        password = self.cleaned_data['new_password1']
        self.user.set_password(password)
        self.user.save()
        return self.user