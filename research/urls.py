from django.urls import path
from . import views

app_name = 'research'

urlpatterns = [
    # Account management — mounted at /account/ in main/urls.py
    path('', views.account_panel, name='account_panel'),
    path('settings/', views.account_settings, name='account_settings'),
    path('password/', views.change_password, name='change_password'),
    path('register/', views.user_registration, name='user_registration'),
    path('register/success/', views.registration_success, name='registration_success'),
]
