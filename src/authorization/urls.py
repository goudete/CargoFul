from django.urls import path
from django.conf.urls import url
from . import views
from django.contrib.auth.views import (LoginView, LogoutView, PasswordResetView,
                                      PasswordResetDoneView, PasswordResetConfirmView, PasswordResetCompleteView)
from django.views.generic import TemplateView

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('accounts/login/', views.login_view, name='login'),
    path('login_success/', views.login_success, name='login_success'),
    path('logout/', views.logout_view, name='logout'),
    path('', views.home_view, name='home'),
    url(r'^activate/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
        views.activate, name='activate'),
    path('email_confirmed/',views.email_confirmed, name = "email_confirmed"),
    path('set_language_en', views.set_language_en, name='set_language_en'),
    path('set_language_es', views.set_language_es, name='set_language_es'),
    path('reset-password',PasswordResetView.as_view(template_name = "passwords/reset_password.html"), name = "reset_password"),
    path('reset-password/done',PasswordResetDoneView.as_view(template_name = "passwords/password_reset_done.html"), name = "password_reset_done"),
    path('reset-password/confirm/<uidb64>/<token>/',PasswordResetConfirmView.as_view(template_name="passwords/password_reset_confirm.html"), name = "password_reset_confirm"),
    path('reset-password/complete',PasswordResetCompleteView.as_view(template_name = "passwords/password_reset_complete.html"), name = "password_reset_complete"),
    path('test', TemplateView.as_view(template_name='emails/confirm_email/confirm_email_ES.html')),
    path('edit_profile/', views.editProfileView, name='edit_profile')
    ]
