from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.views import View
from registro.apps.catastro import models
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated  # opcional
from rest_framework import status
from registro.apps.catastro.models import Predio
from registro.apps.catastro.serializers import PredioSerializer

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


class PredioDetalleAPIView(APIView):
    def get(self, request):
        numero_predial = request.query_params.get('numero_predial_nacional')
        if not numero_predial:
            return Response(
                {"error": "Debe proporcionar el parámetro 'numero_predial_nacional'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            predio = Predio.objects.get(numero_predial_nacional=numero_predial)
        except Predio.DoesNotExist:
            return Response(
                {"error": "No se encontró un predio con ese número predial."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = PredioSerializer(predio)
        return Response(serializer.data)