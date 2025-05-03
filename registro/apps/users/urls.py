from django.urls import path
from .views import (RegisterUserAPIView, ActivateAccountView, 
                    PasswordResetConfirmView, PasswordResetRequestView, 
                    VerificacionUsername, TokenVerificationView, AvatarUploadView, ObtenerAvatarView)

urlpatterns = [
    path('register/', RegisterUserAPIView.as_view(), name='register_user'),
    path('activate/', ActivateAccountView.as_view(), name='activate-account'),
    path('password-reset/', PasswordResetRequestView.as_view(), name='password-reset'),
    path('password-reset-confirm/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
    path('validar-token/', TokenVerificationView.as_view(), name='validar-token'),
    path('verificar_usuario/', VerificacionUsername.as_view(), name='verificar_usuario'),
    path('update-avatar/', AvatarUploadView.as_view(), name='update-avatar'),
    path('obtener-avatar/', ObtenerAvatarView.as_view(), name='obtener-avatar'),
]