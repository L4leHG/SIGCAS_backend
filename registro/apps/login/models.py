from django.db import models
from registro.apps.users.models import User
from django.utils import timezone

from registro.apps.utils.models import BaseModel

class HistorialLogueo(BaseModel):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    fecha_hora = models.DateTimeField(default=timezone.now)
    direccion_ip = models.GenericIPAddressField(null=True, blank=True)

    def __str__(self):
        return f"{self.usuario.username} se logueó el {self.fecha_hora}"