from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializer.serializer import CustomTokenObtainPairSerializer
from rest_framework import views

#MODELS
from registro.apps.login.models import HistorialLogueo
from registro.apps.users.models import User, Rol_predio
from rest_framework.exceptions import NotFound

# PERMISSIONS
from ..utils.permission.permission import IsConsultaAmindUser, IsControlAmindUser, IsControlAnalistaUser, IsAnalistaControlAmindUser
from ..utils.middleware.CookiesJWTAuthentication import CookieJWTAuthentication

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            access_token = response.data['access']
            refresh_token = response.data['refresh']
            # Incluye información del usuario y roles
            user = response.data['user']
            instance_usuario = User.objects.get(email=user['email'])
            # Se crea el logueo cuando el registro es exitoso.
            HistorialLogueo.objects.create(usuario=instance_usuario, direccion_ip=request.META.get('REMOTE_ADDR'))
            user_info = {
                'username': user['username'],
                'roles': user['roles'],
                #'avatar_url': user['avatar_url']
            }
            response = Response(user_info)  # Crear una nueva respuesta con la información del usuario
            response.set_cookie('access_token', access_token, httponly=True, max_age=3600)
            response.set_cookie('refresh_token', refresh_token, httponly=True, max_age=3600)
        return response

class LogoutView(views.APIView):
    def post(self, request, *args, **kwargs):
        response = Response({"detail": "Logout successful"})
        response.delete_cookie('access_token')
        response.delete_cookie('refresh_token')
        return response

class VerifyAuthView(views.APIView):
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsConsultaAmindUser]

    def get(self, request, *args, **kwargs):
        """
        Verifica si el usuario está autenticado. Si el token en las cookies
        HttpOnly es válido, el usuario podrá acceder a esta vista.
        """
        return Response({"isAuthenticated": True})

class VerifyAuthCalidadView(views.APIView):
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsControlAmindUser]

    def get(self, request, *args, **kwargs):
        """
        Verifica si el usuario está autenticado. Si el token en las cookies
        HttpOnly es válido, el usuario podrá acceder a esta vista.
        """
        return Response({"isAuthenticated": True})

