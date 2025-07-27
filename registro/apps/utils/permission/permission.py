from rest_framework import permissions, exceptions
from django.utils.translation import gettext_lazy as _

#MODELS
from registro.apps.users.models import Rol_predio

# ESTA CLASE HABILITA SOLO AL ROLE DE ADMINISTRADOR Y EL DE CONSULTA
class IsControlAmindUser(permissions.BasePermission):
    """
    Allows access only to admin and consult users.
    """
    def has_permission(self, request, view):
        if request.user and request.user.is_active and request.user.is_verified:
            instance_rol_predio = Rol_predio.objects.filter(
                user=request.user, 
                rol__name__in=('Admin','Control_calidad'), 
                is_activate = True
            )
            if instance_rol_predio.exists():
                return True
        return False

class IsCoordinadorOrAdminUser(permissions.BasePermission):
    """
    Permite el acceso solo a usuarios con rol de Coordinador o Admin.
    """
    def has_permission(self, request, view):
        if request.user and request.user.is_active and request.user.is_verified:
            return Rol_predio.objects.filter(
                user=request.user,
                rol__name__in=('Admin', 'Coordinador'),
                is_activate=True
            ).exists()
        return False

# ESTA CLASE HABILITA SOLO AL ROLE DE ADMINISTRADOR Y EL DE CONSULTA
class IsControlAnalistaUser(permissions.BasePermission):
    """
    Permiso personalizado para permitir el acceso solo a usuarios con el rol de Analista de Control.
    """
    def has_permission(self, request, view):
        # Asegurarse de que el usuario esté autenticado
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Verificar si el usuario tiene el rol 'Control-Analista' (ID 2) o 'Admin' (ID 4) activo
        return Rol_predio.objects.filter(
            user=request.user,
            rol_id__in=[2, 4],  # IDs para 'Control-Analista' y 'Admin'
            is_activate=True
        ).exists()

# ESTA CLASE HABILITA SOLO AL ROLE DE ADMINISTRADOR Y EL DE CONSULTA
class IsAnalistaControlAmindUser(permissions.BasePermission):
    """
    Allows access only to admin and consult users.
    """
    def has_permission(self, request, view):
        if request.user and request.user.is_active and request.user.is_verified:
            instance_rol_predio = Rol_predio.objects.filter(
                user=request.user, 
                rol__name__in=('Admin','Analista','Control_calidad'), 
                is_activate = True
            )
            if instance_rol_predio.exists():
                return True
        return False

class IsConsultaAmindUser(permissions.BasePermission):
    """
    Allows access only to admin and consult users.
    """
    def has_permission(self, request, view):
        if request.user and request.user.is_active and request.user.is_verified:
            instance_rol_predio = Rol_predio.objects.filter(
                user=request.user, 
                rol__name__in=('Admin','Consulta'), 
                is_activate = True
            )
            if instance_rol_predio.exists():
                return True
        return False


# ESTA CLASE HABILITA SOLO AL ROLE DE ADMINISTRADOR Y EL DE DESCARGA
class IsDescargaAmindUser(permissions.BasePermission):
    """
    Allows access only to admin and download users.
    """
    def has_permission(self, request, view):
        if request.user and request.user.is_active and request.user.is_verified:
            instance_rol_predio = Rol_predio.objects.filter(
                user=request.user, 
                rol__name__in=('Admin','Descarga'),
                is_activate = True
            )
            if instance_rol_predio.exists():
                return True
        return False

class IsEdicionMutacionAmindUser(permissions.BasePermission):
    """
    Allows access only to admin and download users.
    """
    def has_permission(self, request, view):
        if request.user and request.user.is_active and request.user.is_verified:
            instance_rol_predio = Rol_predio.objects.filter(
                user=request.user, 
                rol__name__in=('Admin','EdicionMutacion'),
                is_activate = True
            )
            if instance_rol_predio.exists():
                return True
        return False

class IsRadicadoListViewUser(permissions.BasePermission):
    """
    Permite acceso a la lista de radicados basado en el rol del usuario:
    - Admin: puede ver todos los radicados
    - Analista: solo puede ver los radicados asignados a él
    """
    def has_permission(self, request, view):
        if request.user and request.user.is_active and request.user.is_verified:
            # Verificar si el usuario es admin
            instance_rol_predio = Rol_predio.objects.filter(
                user=request.user, 
                rol__name__in=('Admin',), 
                is_activate=True
            )
            if instance_rol_predio.exists():
                return True
            
            # Verificar si el usuario es analista
            instance_rol_predio = Rol_predio.objects.filter(
                user=request.user, 
                rol__name__in=('Analista',), 
                is_activate=True
            )
            if instance_rol_predio.exists():
                return True
                
        return False