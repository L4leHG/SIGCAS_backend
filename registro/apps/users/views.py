import uuid
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers.serializer import UserRegistrationSerializer, AvatarUploadSerializer
from django.core.files.storage import default_storage

# PERMISSIONS
from ..utils.permission.permission import IsConsultaAmindUser
from ..utils.middleware.CookiesJWTAuthentication import CookieJWTAuthentication

# MODELS
from .models import User, Rol_predio

#SEND MAIL
from django.utils.http import urlsafe_base64_decode
from django.shortcuts import get_object_or_404
from django.utils.encoding import force_text
from django.contrib.auth.tokens import default_token_generator
from apps.utils.token.create_token import create_token_reset
from django.utils import timezone
from datetime import timedelta
from django.utils.html import strip_tags

#IMPORT TRANSACTIONS
from django.db import transaction

class RegisterUserAPIView(APIView):

    def text_content(self):
        bodyMail = {
            'subject':'Activacion de cuenta',
            'template': 'user/activate_account.html'
        }
        return bodyMail

    def post(self, request, *args, **kwargs):
        with transaction.atomic():
            serializer = UserRegistrationSerializer(data=request.data)
            if serializer.is_valid():
                user = serializer.save()
                bodyMail = self.text_content()
                create_token_reset(user, bodyMail, 'activate-account')
                return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ActivateAccountView(APIView):

    def eliminateUser(self, user):
        Rol_predio.objects.filter(user=user).delete()
        user.delete()
        user.delete()
    
    def activate_user(self, user):
        # SE ACTIVA EL USUARIO
        user.is_active = True
        user.is_verified = True
        user.save()
        
        # SE ACTIVA EL ROL
        instace_rol_predio = Rol_predio.objects.get(user=user)
        instace_rol_predio.is_activate = True
        instace_rol_predio.save()

    def post(self, request):
        uidb64 = request.data.get('uidb64', None)
        token = request.data.get('token', None)

        if uidb64 == None or  token == None:
            return Response({"error": "Activación inválida.", 'status':'failed'}, status=400)
        print(uidb64,token)
        try:
            uid = force_text(urlsafe_base64_decode(uidb64))
            user = get_object_or_404(User, pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist, AttributeError):
            user = None
        
        # Verificar si el token ha expirado
        if user.activation_token_created is not None:
            expiration_time = user.activation_token_created + timedelta(minutes=30)
            if timezone.now() > expiration_time:
                # El token ha expirado
                self.eliminateUser(user)
                return Response({"error": "El enlace de activación ha expirado."}, status=400)

        if user is not None and default_token_generator.check_token(user, token):
            self.activate_user(user)
            # Aquí puedes redireccionar a una página de confirmación o manejar como necesites
            return Response(True, status=200)
        else:
            # Manejar el error (usuario no encontrado o token inválido)
            return Response({"error": "Activación inválida.", 'status':'failed'}, status=400)

class VerificationAccountView(APIView):
    def post(self, request):
        uidb64 = request.data.get('uidb64')
        token = request.data.get('token')
        
        try:
            uid = force_text(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response({'error': 'El enlace de restablecimiento no es válido o ha expirado.'}, status=status.HTTP_400_BAD_REQUEST)
        # Verificar si el token ha expirado
        if user.activation_token_created is not None:
            expiration_time = user.activation_token_created + timedelta(minutes=2)
            if timezone.now() > expiration_time:
                return Response({"error": "El enlace de activación ha expirado."}, status=400)

        if user is not None and default_token_generator.check_token(user, token):
            return Response({'message': 'El token es válido.'}, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'El enlace de restablecimiento no es válido o ha expirado.'}, status=status.HTTP_400_BAD_REQUEST)



class PasswordResetRequestView(APIView):

    def text_content(self):
        bodyMail = {
            'subject':'Recuperacion de contraseña',
            'template': 'user/reset_password.html'
        }
        return bodyMail

    def post(self, request):
        email = request.data.get('email', None)
        user = User.objects.filter(email=email)
        if user.exists() == False:
            return Response(False)
        user = user.first()
        if user:
            bodyMail = self.text_content()
            create_token_reset(user, bodyMail, 'reset-password')

        return Response({'message': 'Si tu email está registrado, recibirás un enlace para restablecer tu contraseña.'}, status=status.HTTP_200_OK)


class PasswordResetConfirmView(APIView):
    def post(self, request):
        uidb64 = request.data.get('uidb64')
        token = request.data.get('token')
        new_password = request.data.get('password')
        try:
            # Decodificar uidb64 para obtener el ID del usuario
            uid = force_text(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response({'error': 'El enlace de restablecimiento no es válido o ha expirado.'})
        # Verificar si el token ha expirado
        if user.activation_token_created is not None:
            expiration_time = user.activation_token_created + timedelta(minutes=2)
            if timezone.now() > expiration_time:
                return Response({"error": "El enlace de activación ha expirado."})

        if user is not None and default_token_generator.check_token(user, token):
            user.set_password(new_password)
            user.save()
            return Response({'message': 'Tu contraseña ha sido restablecida con éxito.'}, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'El enlace de restablecimiento no es válido o ha expirado.'})
class TokenVerificationView(APIView):
    def post(self, request):
        uidb64 = request.data.get('uidb64')
        token = request.data.get('token')
        try:
            uid = force_text(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response({'error': 'El enlace de restablecimiento no es válido o ha expirado.'}, status=status.HTTP_400_BAD_REQUEST)
        # Verificar si el token ha expirado
        if user.activation_token_created is not None:
            expiration_time = user.activation_token_created + timedelta(minutes=2)
            if timezone.now() > expiration_time:
                return Response({"error": "El enlace de activación ha expirado."}, status=400)

        if user is not None and default_token_generator.check_token(user, token):
            return Response({'message': 'El token es válido.'}, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'El enlace de restablecimiento no es válido o ha expirado.'}, status=status.HTTP_400_BAD_REQUEST)


class VerificacionUsername(APIView):
    def post(self, request):
        username = request.data.get('username')
        instance_usuario = User.objects.filter(username = username)
        if instance_usuario.exists():
            data_message={
                'message':'El usuario ya existe.',
                'status':True,
                'user': None
            }
            return Response(data_message)
        return Response(False)

class AvatarUploadView(APIView):
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsConsultaAmindUser]
    
    def post(self, request):
        serializer = AvatarUploadSerializer(data=request.data)

        if serializer.is_valid():
            avatar = serializer.validated_data['avatar']
            user = request.user  # Asegúrate de tener un mecanismo de autenticación
            # Crear un nombre de archivo único
            unique_id = uuid.uuid4()
            extension = avatar.name.split('.')[-1]
            unique_file_name = f'avatars/{user.id}/{unique_id}.{extension}'
            # Guardar la imagen y actualizar el usuario
            file_path = default_storage.save(unique_file_name, avatar)
            user.avatar = file_path
            user.save()
            # Construir la URL absoluta del avatar
            avatar_url = request.build_absolute_uri(user.avatar.url)
            return Response({'avatar_url': avatar_url}, status=status.HTTP_200_OK)
        return Response(serializer.errors)

class ObtenerAvatarView(APIView):
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsConsultaAmindUser]
    def get(self, request):
        user = request.user
        if user.avatar and user.avatar.url:
            # Construir la URL absoluta del avatar
            avatar_url = request.build_absolute_uri(user.avatar.url)
            return Response({'avatar_url':avatar_url}, status=status.HTTP_200_OK)
        return Response(False)