from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.views import View
from registro.apps.catastro import models

# Create your views here.

class SaludoCatastroView(View):
    def get(self, request, *args, **kwargs):
        return HttpResponse("saludos desde catastro")

    
class PredioListView(View):
    def get(self, request):
        predios = models.Predio.objects.all().values(
        
            'numero_predial_nacional',
            'codigo_homologado',
            'direccion'
        )[:100]  # Limita a 100 resultados si es muy grande
        return JsonResponse(list(predios), safe=False)