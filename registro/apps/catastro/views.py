from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.views import View
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError, APIException
from rest_framework.decorators import action

from registro.apps.catastro import models
from registro.apps.catastro.models import (
    Predio, Radicado, RadicadoPredioAsignado, 
    EstadoAsignacion, CrMutaciontipo, 
    ColDocumentotipo, ColInteresadotipo
)
from .serializers import (
    PredioSerializer, RadicadoSerializer, 
    RadicadoPredioAsignadoSerializer, 
    SerializerRadicado
)
from registro.apps.utils.middleware.CookiesJWTAuthentication import CookieJWTAuthentication
from registro.apps.utils.permission.permission import IsConsultaAmindUser

import logging
import copy

logger = logging.getLogger(__name__)

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
    

class PredioPreView(APIView):
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

        # Creamos una instancia del serializer con los campos específicos
        serializer = PredioSerializer(predio)
        # Filtramos los campos que queremos en la respuesta
        data = {
            'id':serializer.data.get('id'),
            'npn': serializer.data.get('numero_predial_nacional'),
            'direccion': serializer.data.get('direccion'),
            'area total': serializer.data.get('area_catastral_terreno'),
            'orip_matricula':serializer.data.get('orip_matricula'),
            'estado': serializer.data.get('estado'),

        }
        return Response(data)
    

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


#### ******************************VIEWS PARA RADICACION 

class RadicadoView(generics.CreateAPIView):
    serializer_class = SerializerRadicado
    permission_classes = [IsConsultaAmindUser]
    authentication_classes = [CookieJWTAuthentication]

    def create (self, request): 
        request_user=copy.copy(request.data)
        print(request.user.email)
        tipo_documento_user = request_user.get('tipo_documento')
        tipo_interesado_user = request_user.get('tipo_interesado')
        numero_radicado_user = request_user.get('numero_radicado')
        fecha_radicado_user = request_user.get('fecha_radicado')
        nombre_solicitante_user = request_user.get('nombre_solicitante')
        numero_documento_user = request_user.get ('numero_documento')
        oficio_user = request_user.get ('oficio')

        instance_tipo_documento= ColDocumentotipo.objects.get(ilicode = tipo_documento_user)
        instance_tipo_interesado = ColInteresadotipo.objects.get(ilicode = tipo_interesado_user)


        # request_user['tipo_interesado'] = instance_tipo_interesado

       
        Radicado.objects.create( 
            tipo_documento = instance_tipo_documento,
            tipo_interesado = instance_tipo_interesado,
            numero_radicado=numero_radicado_user, 
            fecha_radicado = fecha_radicado_user,
            nombre_solicitante = nombre_solicitante_user,
            numero_documento = numero_documento_user,
            oficio = oficio_user
              )
        
        return Response({
            'data':tipo_documento_user
        })
    

    
      

