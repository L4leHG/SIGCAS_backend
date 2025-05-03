from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.exceptions import AuthenticationFailed

from registro.apps.users.models import Rol_predio

# class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
#     def validate(self, attrs):
#         data_message={
#             'message':'Logueo exitoso',
#             'status':True,
#             'rol':None,
#             'user': None
#         }
#         try:
#             # Intenta validar y obtener el token como usualmente lo harías
#             user = super().validate(attrs)
#             roles = Rol_predio.objects.filter(user=self.user)
#             # Añade los campos adicionales que deseas incluir en la respuesta del token
#             user['username'] = self.user.username
#             user['email'] = self.user.email
#             user['rol'] = [rol.id for rol in roles]
#             data_message['user'] = user
#             # Otros campos adicionales...
#             return data_message
#         except AuthenticationFailed:
#             # Aquí puedes personalizar el mensaje de error
#             data_message['message']='No se puede loguear. Usuario y contraseña incorrecto'
#             data_message['status']=False
#             raise AuthenticationFailed(data_message)

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Añadir información adicional al token aquí si es necesario
        # token['username'] = user.username
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        user = self.user
        instance_roles = Rol_predio.objects.filter(user=user)
        
        # Obtener la URL absoluta del avatar
        # current_site = get_current_site(request)
        # domain = current_site.domain
        request = self.context['request']
        #avatar_url = request.build_absolute_uri(user.avatar.url) if user.avatar else ''

        # Añade los campos adicionales que deseas incluir en la respuesta del token
        data['user'] = {
            "username": self.user.username,
            "email": self.user.email,
            "roles": [rol.rol.name for rol in instance_roles],
        }

        return data