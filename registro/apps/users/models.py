

# DJANGO
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator

from django.contrib.postgres.fields import ArrayField
from django.utils import timezone

# utilities
from registro.apps.utils.models import BaseModel


class Rol (BaseModel):
    name = models.CharField(max_length=150)
    def __str__(self):
        return self.name

class Permisos (BaseModel):
    name = models.CharField(max_length=50)
    def __str__(self):
        return self.name

# Utilities
class User(BaseModel, AbstractUser):
    
    email = models.EmailField(
        'direccion electronica',
        unique = True,
        error_messages= {
            'Unique':'El usuario con este email ya existe'
        }
    )

    phone_regex = RegexValidator(
        regex=r'\+?1?\d{9,15}$',
        message='El numero telefonico debe tener el formato: +999999999. Hasta 15 digitos permitido'
    )
    phone_number = models.CharField(max_length=17, blank=True)
    EMAIL_FIELD = "email"
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username",'first_name','last_name']

    is_client = models.BooleanField(
        'Status del usuario',
        default=True,
        help_text=(
            'Ayuda a identificar usuarios y realizar queries. '
        )
    )

    is_verified = models.BooleanField(
        'verificado',
        default=False,
        help_text = 'Configurado a verdadero cuando el usuario ha verificado su direccion de correo electronico'
    )

    activation_token_created = models.DateTimeField(null=True, blank=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)

    def __str__(self):
        """Regresa el nombre de usuario"""
        return self.username
    
    def get_short_name(self):
        return self.username

class Rol_predio(BaseModel):
    rol = models.ForeignKey(Rol, on_delete=models.RESTRICT)
    user = models.ForeignKey(User, on_delete=models.RESTRICT)
    is_activate = models.BooleanField(
        'Status del rp',
        default=False,
        help_text=(
            'Permite conocer que roles estan activos para cada usuario. '
        )
    )
    class Meta:
        ordering = ["id"]
        indexes = [
            models.Index(fields=['user']),
        ]

    def __str__(self):
        return f'{self.user},{self.rol}'

class SubidaDiaria(BaseModel):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    fecha = models.DateField(default=timezone.now)
    cantidad = models.IntegerField(default=0)