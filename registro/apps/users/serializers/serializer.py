#from django.contrib.auth.models import User
from ..models import User, Rol_predio, Rol
from rest_framework import serializers

class RolUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rol_predio
        fields = '__all__'


class UserRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('username', 'email', 'password','first_name','last_name')
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = User.objects.create_user(
            validated_data['username'],
            email=validated_data['email'],
            first_name = validated_data['first_name'],
            last_name = validated_data['last_name'],
            password=validated_data['password']
        )
        
        instance_rol = Rol.objects.get(id = 2)
        data_user = {
            'rol' : instance_rol,
            'user' : user
        }
        instance_rol_predio = Rol_predio(**data_user)
        instance_rol_predio.save()
        
        return user

    def validate_email(self, value):
        """ Verifica que el email sea único. """
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Un usuario con este email ya existe.")
        return value

class AvatarUploadSerializer(serializers.Serializer):
    avatar = serializers.ImageField()
    