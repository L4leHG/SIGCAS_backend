from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.views import View
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError, APIException
from rest_framework.decorators import action
from rest_framework import serializers
from django.db.models import Q

from registro.apps.catastro import models
from registro.apps.catastro.models import (
    Predio, Radicado,
    ColDocumentotipo, ColInteresadotipo,
    #####***************************************************************DOMINIOS
    #GRUPO PREDIO
    CrPrediotipo, CrCondicionprediotipo, CrDestinacioneconomicatipo, CrEstadotipo,
    # INTERESADO
    ColDocumentotipo, CrAutoreconocimientoetnicotipo, ColInteresadotipo,
    # GRUPO FUENTE ADMINISTRATIVA
    ColFuenteadministrativatipo, ColEstadodisponibilidadtipo, EnteEmisortipo,
    # GRUPO UNIDAD CONSTRUCCIÓN
    CrUnidadconstrucciontipo, CrUsouconstipo, CrConstruccionplantatipo,
    #INDIVIDUALES
    ColUnidadadministrativabasicatipo,EstadoAsignacion,CrMutaciontipo, User
    #####***************************************************************
)
from .serializers import (
    PredioSerializer, 
    SerializerRadicado,
    #####DOMINIOS
    CrPrediotipoSerializer, CrCondicionprediotipoSerializer, CrDestinacioneconomicatipoSerializer, CrEstadotipoSerializer,
    ColDocumentotipoSerializer, CrAutoreconocimientoetnicotipoSerializer, ColInteresadotipoSerializer,
    ColFuenteadministrativatipoSerializer, ColEstadodisponibilidadtipoSerializer, EnteEmisortipoSerializer,
    CrUnidadconstrucciontipoSerializer, CrUsouconstipoSerializer, CrConstruccionplantatipoSerializer,
    ColUnidadadministrativabasicatipoSerializer,
    EstadoAsignacionSerializer, CrMutaciontipoSerializer, RadicadoListSerializer,
    RadicadoPredioAsignadoEditSerializer, UserSerializer, RadicadoPredioAsignadoSerializer
)

from registro.apps.catastro.models import RadicadoPredioAsignado
from registro.apps.utils.middleware.CookiesJWTAuthentication import CookieJWTAuthentication
from registro.apps.utils.permission.permission import IsConsultaAmindUser

import logging
import copy

logger = logging.getLogger(__name__)

    
# --- ********************************* VIEWS PARA PREDIO ********************************* ---
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

#### ********************************* VIEWS PARA DOMINIOS *********************************

# --- DOMINIOS DE PREDIO ---
class DominiosPredioView(APIView):
    def get(self, request):
        return Response({
            "tipo": CrPrediotipoSerializer(CrPrediotipo.objects.all(), many=True).data,
            "condicion": CrCondicionprediotipoSerializer(CrCondicionprediotipo.objects.all(), many=True).data,
            "destino_economico": CrDestinacioneconomicatipoSerializer(CrDestinacioneconomicatipo.objects.all(), many=True).data,
            "estado": CrEstadotipoSerializer(CrEstadotipo.objects.all(), many=True).data,
        })


# --- DOMINIOS DE INTERESADO ---
class DominiosInteresadoView(APIView):
    def get(self, request):
        return Response({
            "documento_tipo": ColDocumentotipoSerializer(ColDocumentotipo.objects.all(), many=True).data,
            "etnia": CrAutoreconocimientoetnicotipoSerializer(CrAutoreconocimientoetnicotipo.objects.all(), many=True).data,
            "tipo_interesado": ColInteresadotipoSerializer(ColInteresadotipo.objects.all(), many=True).data,
        })


# --- DOMINIOS DE FUENTE ADMINISTRATIVA ---
class DominiosFuenteAdministrativaView(APIView):
    def get(self, request):
        return Response({
            "fuente": ColFuenteadministrativatipoSerializer(ColFuenteadministrativatipo.objects.all(), many=True).data,
            "estado_disponibilidad": ColEstadodisponibilidadtipoSerializer(ColEstadodisponibilidadtipo.objects.all(), many=True).data,
            "ente_emisor": EnteEmisortipoSerializer(EnteEmisortipo.objects.all(), many=True).data,
        })


# --- DOMINIOS DE UNIDAD DE CONSTRUCCIÓN ---
class DominiosUnidadConstruccionView(APIView):
    def get(self, request):
        return Response({
            "unidad_tipo": CrUnidadconstrucciontipoSerializer(CrUnidadconstrucciontipo.objects.all(), many=True).data,
            "uso_construccion": CrUsouconstipoSerializer(CrUsouconstipo.objects.all(), many=True).data,
            "planta_tipo": CrConstruccionplantatipoSerializer(CrConstruccionplantatipo.objects.all(), many=True).data,
        })


# --- DOMINIO: Unidad Administrativa Básica ---
class UnidadAdministrativaBasicaTipoView(APIView):
    def get(self, request):
        data = ColUnidadadministrativabasicatipoSerializer(ColUnidadadministrativabasicatipo.objects.all(), many=True).data
        return Response(data)


# --- DOMINIO: Estado de Asignación ---
class EstadoAsignacionView(APIView):
    def get(self, request):
        data = EstadoAsignacionSerializer(EstadoAsignacion.objects.all(), many=True).data
        return Response(data)


# --- DOMINIO: Tipo de Mutación ---
class MutacionTipoView(APIView):
    def get(self, request):
        data = CrMutaciontipoSerializer(CrMutaciontipo.objects.all(), many=True).data
        return Response(data)
    
# --- DOMINIO: Usuario ---
class UserListView(generics.ListAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsConsultaAmindUser]
    authentication_classes = [CookieJWTAuthentication]

    def get_queryset(self):
        # Solo obtenemos los campos necesarios para el desplegable
        queryset = User.objects.filter(
            is_active=True
        ).only(
            'id', 
            'username', 
            'first_name', 
            'last_name', 
            'email'
        ).order_by('first_name', 'last_name')

        # Filtro opcional por nombre o apellido
        search = self.request.query_params.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(username__icontains=search)
            )

        return queryset

    def list(self, request, *args, **kwargs):
        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            return Response({
                'results': serializer.data,
                'count': queryset.count()
            })
        except Exception as e:
            return Response(
                {"error": "Ocurrió un error al procesar la solicitud"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    

    
#### ********************************* VIEWS PARA RADICACION *********************************

class RadicadoView(generics.CreateAPIView):
    serializer_class = SerializerRadicado
    permission_classes = [IsConsultaAmindUser]
    authentication_classes = [CookieJWTAuthentication]

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except serializers.ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {"error": "Ocurrió un error al procesar la solicitud"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def perform_create(self, serializer):
        print("Usuario autenticado:", self.request.user.email)
        serializer.save()

    
class RadicadoUpdateView(generics.UpdateAPIView):
    queryset = Radicado.objects.all()
    serializer_class = SerializerRadicado
    permission_classes = [IsConsultaAmindUser]
    authentication_classes = [CookieJWTAuthentication]
    lookup_field = 'id'  # o 'pk' si prefieres  

class RadicadoListView(generics.ListAPIView):
    serializer_class = RadicadoListSerializer
    permission_classes = [IsConsultaAmindUser]
    authentication_classes = [CookieJWTAuthentication]

    def get_queryset(self):
        queryset = Radicado.objects.all()
        numero_radicado = self.request.query_params.get('numero_radicado')
        # estado = self.request.query_params.get('estado')

        if numero_radicado:
            queryset = queryset.filter(numero_radicado=numero_radicado)
            if not queryset.exists():
                raise ValidationError({
                    "error": f"No se encontró ningún radicado con el número {numero_radicado}"
                })

        return queryset

    def list(self, request, *args, **kwargs):
        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)
        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(
                {"error": "Ocurrió un error al procesar la solicitud"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
#### ********************************* VIEWS PARA ASIGNACION DE RADICADO A PREDIO *********************************

class RadicadoPredioAsignadoCreateView(generics.CreateAPIView):
    serializer_class = RadicadoPredioAsignadoEditSerializer
    permission_classes = [IsConsultaAmindUser]
    authentication_classes = [CookieJWTAuthentication]

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            instance = self.perform_create(serializer)
            response_serializer = RadicadoPredioAsignadoSerializer(instance)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error al crear asignación: {str(e)}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def perform_create(self, serializer):
        return serializer.save()

class RadicadoPredioAsignadoUpdateView(generics.UpdateAPIView):
    queryset = RadicadoPredioAsignado.objects.all()
    serializer_class = RadicadoPredioAsignadoEditSerializer
    permission_classes = [IsConsultaAmindUser]
    authentication_classes = [CookieJWTAuthentication]
    lookup_field = 'id'  # o 'pk' si prefieres  
