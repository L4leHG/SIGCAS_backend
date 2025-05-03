"""user models admin"""

#django
import imp
from django.contrib import  admin
from django.contrib.auth.admin import UserAdmin

# models
from registro.apps.users.models import User, Rol_predio

class CustomUserAdmin(UserAdmin):
    """User model admin"""

    list_display = ('email','username','first_name','last_name','is_staff','is_client')
    list_filter = ('is_client','is_staff','created','modified')

admin.site.register(User,CustomUserAdmin)
admin.site.register(Rol_predio)