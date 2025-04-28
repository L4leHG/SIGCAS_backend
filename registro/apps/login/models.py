from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager


# Create your models here.


class CustomAccountManager(BaseUserManager):

    def create_superuser(self, email, name, password, **other_fields):

        other_fields.setdefault('is_superuser', True)
        other_fields.setdefault('is_active', True)
        other_fields.setdefault('rol', UsuarioRol.objects.get(id=6))

        if other_fields.get('is_superuser') is not True:
            raise ValueError(
                'Superuser must be assigned to is_superuser=True.')

        return self.create_user(email, name, password, **other_fields)

    def create_user(self, email, name, password, **other_fields):

        if not email:
            raise ValueError(_('You must provide an email address'))

        email = self.normalize_email(email)
        user = self.model(email=email, 
                          name=name, **other_fields)
        user.set_password(password)
        user.save()
        return user




class Usuarios(AbstractBaseUser, PermissionsMixin):
    nombre = models.CharField(max_length=100, blank=True)
    email = models.EmailField(('email address'), unique=True)
    rol = models.ForeignKey('UsuarioRol', on_delete=models.RESTRICT)
    is_active = models.BooleanField(default=True)
    is_superuser = models.BooleanField(default=False)

    groups = models.ManyToManyField(
        'auth.Group',
        related_name='usuarios_groups',   # <--- aquí cambiamos el nombre inverso
        blank=True,
        help_text=('The groups this user belongs to.'),
        related_query_name='user',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='usuarios_user_permissions',   # <--- aquí también
        blank=True,
        help_text=('Specific permissions for this user.'),
        related_query_name='user',
    )

    objects = CustomAccountManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']

    class Meta:
        ordering = ["id"]
        db_table = 'usuarios'
        indexes = [
            models.Index(fields=['rol', 'id']),
        ]

    def __str__(self):
        return self.email

class UsuarioRol(models.Model):
    t_id = models.AutoField(primary_key=True)
    ilicode = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'usuario_rol'
        ordering = ["ilicode"]

    def __str__(self):
        return self.ilicode

