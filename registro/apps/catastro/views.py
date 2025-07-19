from django.shortcuts import render
from django.http import HttpResponse, JsonResponse, Http404
from django.views import View
from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError, APIException
from rest_framework.decorators import action
from rest_framework import serializers
from rest_framework.parsers import MultiPartParser, JSONParser, FormParser
from django.db.models import Q
from django.template.loader import render_to_string
from weasyprint import HTML
from django.conf import settings
from datetime import datetime
import os
import json

from registro.apps.users.models import Rol_predio 
from registro.apps.catastro.models import (
    Predio, Radicado, TramiteCatastral,
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
    RadicadoPredioAsignadoEditSerializer, UserSerializer, RadicadoPredioAsignadoSerializer,
    ResolucionSerializer
)

from registro.apps.catastro.models import RadicadoPredioAsignado
from registro.apps.utils.middleware.CookiesJWTAuthentication import CookieJWTAuthentication
from registro.apps.utils.permission.permission import IsConsultaAmindUser, IsRadicadoListViewUser

import logging
import copy

# IMPORTS ADICIONALES PARA LA NUEVA VISTA
from registro.apps.catastro.mutacion.incorporacion_primera import IncorporarMutacionPrimera
from registro.apps.catastro.mutacion.incorporacion_tercera import IncorporarMutacionTercera
from registro.apps.catastro.serializers import MutacionRadicadoValidationSerializer
from registro.apps.utils.permission.permission import IsControlAnalistaUser, IsCoordinadorOrAdminUser
from registro.apps.catastro.utils_mutacion import (
    extraer_tipo_base_mutacion, 
    validar_coherencia_mutacion,
    es_tipo_mutacion_soportado
)
import traceback
from registro.apps.catastro.incorporacion.incorporar_unidades import IncorporacionUnidadesSerializer as IncorporacionUnidadesHelper
from registro.apps.catastro.models import Historial_predio

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

        # Cambiado a 'filter' para búsqueda parcial y devolver una lista
        predios = Predio.objects.filter(numero_predial_nacional__icontains=numero_predial)

        if not predios.exists():
            # Devolver una lista vacía si no hay resultados, en lugar de un error 404
            return Response([], status=status.HTTP_200_OK)

        serializer = PredioSerializer(predios, many=True)
        
        # Crear una lista de resultados simplificados
        response_data = []
        for predio_data in serializer.data:
            response_data.append({
                'id': predio_data.get('id'),
                'npn': predio_data.get('numero_predial_nacional'),
                'direccion': predio_data.get('direccion'),
                'area total': predio_data.get('area_catastral_terreno'),
                'orip_matricula': predio_data.get('orip_matricula'),
                'estado': predio_data.get('estado'),
                'nombre_interesado': predio_data.get('interesado')
            })
            
        return Response(response_data)
    

class PredioDetalleAPIView(APIView):
    def get(self, request):
        numero_predial = request.query_params.get('numero_predial_nacional')
        predio_id = request.query_params.get('predio_id')
        formato = request.query_params.get('formato', 'json')  # Por defecto retorna JSON

        # Búsqueda prioritaria por ID de predio si se proporciona
        if predio_id:
            try:
                predio = Predio.objects.get(id=predio_id)
                
                # Si se proporciona NPN, validar que coincida con el del predio encontrado
                if numero_predial and predio.numero_predial_nacional != numero_predial:
                    return Response(
                        {"error": f"El predio con ID {predio_id} no corresponde al número predial {numero_predial}."},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                serializer = PredioSerializer(predio)
                if formato.lower() == 'pdf':
                    try:
                        return serializer.generate_pdf(serializer.data, predio.numero_predial_nacional)
                    except Exception as e:
                        return Response({"error": "Ocurrió un error al generar el PDF"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
                return Response(serializer.data)
                
            except Predio.DoesNotExist:
                return Response({"error": f"No se encontró un predio con el ID {predio_id}."}, status=status.HTTP_404_NOT_FOUND)

        # Búsqueda por número predial nacional si no se proporciona ID
        if numero_predial:
            predios = Predio.objects.filter(numero_predial_nacional=numero_predial)

            if not predios.exists():
                return Response(
                    {"error": f"No se encontraron predios con el número predial {numero_predial}."},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Si se pide un PDF en una búsqueda por NPN sin ID, es ambiguo
            if formato.lower() == 'pdf':
                return Response(
                    {"error": "Para generar un PDF, debe proporcionar el 'predio_id' del registro específico."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Para JSON, serializamos todos los resultados encontrados
            serializer = PredioSerializer(predios, many=True)
            return Response(serializer.data)

        # Si no se proporciona ningún identificador
        return Response(
            {"error": "Debe proporcionar el 'numero_predial_nacional'."},
            status=status.HTTP_400_BAD_REQUEST
        )

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
        ).prefetch_related(
            'rol_predio_set__rol'  # Prefetch para optimizar la obtención de roles
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

    def get_serializer(self, *args, **kwargs):
        if isinstance(kwargs.get('data', {}), list):
            kwargs['many'] = True
        return super().get_serializer(*args, **kwargs)

    def create(self, request, *args, **kwargs):
        try:
            # Validar y crear el/los radicado(s)
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            instances = serializer.save()

            # Determinar si se crearon uno o varios para la respuesta
            is_many = isinstance(instances, list)
            
            # Log de éxito
            logger.info(f"Se crearon {len(instances) if is_many else 1} radicado(s) exitosamente.")
            
            # Serializar la respuesta
            response_serializer = RadicadoListSerializer(instances, many=is_many)
            mensaje = "Se crearon los radicados exitosamente" if is_many else "Se creó el radicado exitosamente"
            
            return Response({
                "mensaje": mensaje,
                "data": response_serializer.data
            }, status=status.HTTP_201_CREATED)
            
        except ValidationError as e:
            # Log del error de validación
            logger.warning(f"Error de validación al crear radicado: {str(e)}")
            return Response(
                {"error": "Error de validación", "detalles": e.detail},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            # Log del error inesperado
            logger.error(f"Error inesperado al crear radicado: {str(e)}", exc_info=True)
            return Response(
                {"error": "Ocurrió un error al procesar la solicitud"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def perform_create(self, serializer):
        return serializer.save()

class RadicadoUpdateView(generics.UpdateAPIView):
    queryset = Radicado.objects.all()
    serializer_class = SerializerRadicado
    permission_classes = [IsConsultaAmindUser]
    authentication_classes = [CookieJWTAuthentication]
    lookup_field = 'id'

    def get_object(self):
        try:
            return super().get_object()
        except Http404:
            raise ValidationError({
                "error": f"No se encontró el radicado con el ID {self.kwargs.get('id')}"
            })

    def update(self, request, *args, **kwargs):
        try:

            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            
            # Serializar la respuesta con el serializer de lectura
            response_serializer = RadicadoListSerializer(instance)
            return Response({
                "mensaje": "Se actualizó el radicado exitosamente",
                "data": response_serializer.data
            })
            
        except ValidationError as e:
            return Response(
                {"error": "Error de validación", "detalles": e.detail},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": "Ocurrió un error al procesar la solicitud"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def perform_update(self, serializer):
        try:
            serializer.save()
        except Exception as e:
            logger.error(f"Error al guardar la actualización del radicado: {str(e)}", exc_info=True)
            raise

class RadicadoListView(generics.ListAPIView):
    serializer_class = RadicadoListSerializer
    permission_classes = [IsRadicadoListViewUser]
    authentication_classes = [CookieJWTAuthentication]

    def get_queryset(self):
        try:
            queryset = Radicado.objects.all()

            # Verificar si el usuario es admin
            is_admin = Rol_predio.objects.filter(
                user=self.request.user,
                rol__name__in=('Admin',),
                is_activate=True
            ).exists()

            # Si no es admin, filtrar por radicados asignados al analista
            if not is_admin:
                queryset = queryset.filter(
                    radicadopredioasignado__usuario_analista=self.request.user
                ).distinct()

            numero_radicado = self.request.query_params.get('numero_radicado')
            npn = self.request.query_params.get('npn')

            if numero_radicado:
                queryset = queryset.filter(numero_radicado=numero_radicado)
                if not queryset.exists():
                    raise ValidationError({
                        f"No se encontró ningún radicado con el número {numero_radicado}"
                    })
            
            if npn:
                queryset_predio_estado = CrEstadotipo.objects.get(t_id = 105)
                queryset_predio = Predio.objects.get(numero_predial_nacional = npn, estado = queryset_predio_estado)
                queryset_asignacion = RadicadoPredioAsignado.objects.get(predio = queryset_predio)
                queryset = queryset.filter(id = queryset_asignacion.radicado.id)
                if not queryset.exists():
                    raise ValidationError({
                        f"No se encontró ningún radicado con el npn {npn}"
                    })

            return queryset
        except Exception as e:
            logger.error(f"Error al obtener queryset de radicados: {str(e)}", exc_info=True)
            raise

    def list(self, request, *args, **kwargs):
        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)
            
        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:

            return Response(
                {"Ocurrió un error al procesar la solicitud"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RadicadoDeleteView(generics.DestroyAPIView):
    queryset = Radicado.objects.all()
    serializer_class = RadicadoListSerializer
    permission_classes = [IsConsultaAmindUser]
    authentication_classes = [CookieJWTAuthentication]
    lookup_field = 'id'

    def get_object(self):
        try:
            return super().get_object()
        except Http404:
            raise ValidationError({
                "error": "No se encontró el radicado"
            })

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            
            # Verificar si el radicado tiene asignaciones
            if RadicadoPredioAsignado.objects.filter(radicado=instance).exists():
                return Response(
                    {"error": "No se puede eliminar el radicado porque tiene asignaciones asociadas"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Eliminar el radicado
            self.perform_destroy(instance)
            return Response(
                {"mensaje": "Se eliminó el radicado exitosamente"},
                status=status.HTTP_200_OK
            )
            
        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error al eliminar radicado: {str(e)}", exc_info=True)
            return Response(
                {"error": "Ocurrió un error al procesar la solicitud"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def perform_destroy(self, instance):
        try:
            instance.delete()
        except Exception as e:
            logger.error(f"Error al eliminar el radicado: {str(e)}", exc_info=True)
            raise

#### ********************************* VIEWS PARA ASIGNACION DE RADICADO A PREDIO *********************************

class RadicadoPredioAsignadoCreateView(generics.CreateAPIView):
    serializer_class = RadicadoPredioAsignadoEditSerializer
    permission_classes = [IsConsultaAmindUser]
    authentication_classes = [CookieJWTAuthentication]

    def get_serializer(self, *args, **kwargs):
        if isinstance(kwargs.get('data', {}), list):
            kwargs['many'] = True
        return super().get_serializer(*args, **kwargs)

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            instances = serializer.save()

            is_many = isinstance(request.data, list)
            response_serializer = RadicadoPredioAsignadoSerializer(instances, many=is_many)
            
            mensaje = "Se crearon las asignaciones exitosamente" if is_many else "Se creó la asignación exitosamente"

            return Response({
                "mensaje": mensaje,
                "data": response_serializer.data
            }, status=status.HTTP_201_CREATED)
            
        except ValidationError as e:
            return Response(
                {"error": "Error de validación", "detalles": e.detail},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error inesperado al crear asignación(es): {str(e)}", exc_info=True)
            return Response(
                {"error": "Ocurrió un error al procesar la solicitud"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class RadicadoPredioAsignadoUpdateView(generics.UpdateAPIView):
    queryset = RadicadoPredioAsignado.objects.all()
    serializer_class = RadicadoPredioAsignadoEditSerializer
    permission_classes = [IsConsultaAmindUser]
    authentication_classes = [CookieJWTAuthentication]
    lookup_field = 'id'

    def get_object(self):
        try:
            return super().get_object()
        except Http404:
            raise ValidationError({
                "error": f"No se encontró la asignación con el ID {self.kwargs.get('id')}"
            })

    def update(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            
            # Serializar la respuesta con el serializer de lectura
            response_serializer = RadicadoPredioAsignadoSerializer(instance)
            return Response({
                "mensaje": "Se actualizó la asignación exitosamente",
                "data": response_serializer.data
            })
        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error al actualizar asignación: {str(e)}")
            return Response(
                {"error": "Ocurrió un error al procesar la solicitud"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class RadicadoPredioAsignadoListView(generics.ListAPIView):
    serializer_class = RadicadoPredioAsignadoSerializer
    permission_classes = [IsConsultaAmindUser]
    authentication_classes = [CookieJWTAuthentication]

    def get_queryset(self):
        queryset = RadicadoPredioAsignado.objects.all()
        numero_radicado = self.request.query_params.get('numero_radicado')
        id_asignacion = self.request.query_params.get('id_asignacion')

        if numero_radicado:
            queryset = queryset.filter(radicado__numero_radicado=numero_radicado)
            if not queryset.exists():
                raise ValidationError({
                    "error": f"No se encontró ninguna asignación con el número de radicado {numero_radicado}"
                })
        
        if id_asignacion:
            queryset = queryset.filter(id= id_asignacion)
            if not queryset.exists():
                raise ValidationError({
                    "No se encontró la asignacion"
                })

        return queryset
    
    def list(self, request, *args, **kwargs):
        print(request.query_params.get('id_asignacion'),'identificador*')

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
        

class RadicadoPredioAsignadoDeleteView(generics.DestroyAPIView):
    queryset = RadicadoPredioAsignado.objects.all()
    serializer_class = RadicadoPredioAsignadoSerializer
    permission_classes = [IsConsultaAmindUser]
    authentication_classes = [CookieJWTAuthentication]
    lookup_field = 'id'

    def get_object(self):
        try:
            return super().get_object()
        except Http404:
            raise ValidationError({
                "error": f"No se encontró la asignación"
            })

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            
            # Obtener el radicado asociado antes de eliminar
            radicado = instance.radicado
            
            # Eliminar la asignación
            self.perform_destroy(instance)
            
            # Verificar si el radicado tiene otras asignaciones
            if not RadicadoPredioAsignado.objects.filter(radicado=radicado).exists():
                # Si no hay más asignaciones, actualizar el campo asignado del radicado
                radicado.asignado = False
                radicado.save()
            
            return Response({
                "mensaje": "Se eliminó la asignación exitosamente"
            }, status=status.HTTP_200_OK)
            
        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error al eliminar asignación: {str(e)}", exc_info=True)
            return Response(
                {"error": "Ocurrió un error al procesar la solicitud"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def perform_destroy(self, instance):
        try:
            instance.delete()
        except Exception as e:
            logger.error(f"Error al eliminar la asignación: {str(e)}", exc_info=True)
            raise

class ProcesarMutacionView(APIView):
    """
    Vista para procesar mutaciones catastrales.
    
    Valida que:
    - El radicado exista y esté asignado al analista
    - El usuario sea el analista asignado a la mutación
    - Procesa la mutación según su tipo específico
    
    Tipos de mutación soportados:
    - Primera: Cambio de propietario (conserva terrenos y unidades)
    - Tercera: Incorporación nueva (nuevos predios, terrenos y unidades)
    """
    permission_classes = [IsControlAnalistaUser]
    authentication_classes = [CookieJWTAuthentication]
    
    def post(self, request):
        """
        Procesa una mutación catastral.
        """
        try:
            # VALIDAR DATOS DE ENTRADA
            serializer = MutacionRadicadoValidationSerializer(
                data=request.data,
                context={'request': request}
            )
            
            if not serializer.is_valid():
                return Response({
                    'error': 'Datos de validación incorrectos',
                    'detalle': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

            # OBTENER DATOS VALIDADOS
            validated_data = serializer.validated_data
            asignacion = validated_data['asignacion_instance']
            radicado = validated_data['radicado_instance']
            mutacion_tipo = validated_data['mutacion_tipo']
            mutacion_data = validated_data['mutacion']

            # VERIFICAR COHERENCIA DEL TIPO DE MUTACIÓN
            mutacion_data_tipo = mutacion_data.get('tipo_mutacion', '')
            
            # Validar que el tipo completo coincida exactamente
            es_valido, mensaje_error = validar_coherencia_mutacion(mutacion_tipo, mutacion_data_tipo)
            if not es_valido:
                return Response({
                    'error': 'Inconsistencia en tipo de mutación',
                    'detalle': mensaje_error
                }, status=status.HTTP_400_BAD_REQUEST)

            # EXTRAER TIPO BASE PARA PROCESAMIENTO INTERNO
            mutacion_tipo_base = extraer_tipo_base_mutacion(mutacion_tipo)

            # PROCESAR LA MUTACIÓN DENTRO DE UNA TRANSACCIÓN ATÓMICA
            # Esto garantiza que TODA la operación se revierta si algo falla
            try:
                with transaction.atomic():
                    logger.info(f"INICIANDO TRANSACCIÓN para mutación {mutacion_tipo_base}")
                    
                    # PROCESAR LA MUTACIÓN SEGÚN SU TIPO
                    resultado = self._procesar_mutacion(
                        mutacion_tipo=mutacion_tipo_base,  # Usar tipo base para procesamiento
                        mutacion_data=mutacion_data,
                        asignacion=asignacion,
                        radicado=radicado
                    )

                    # ACTUALIZAR ESTADO DE LA ASIGNACIÓN A "REVISION"
                    # Esto también forma parte de la transacción atómica
                    try:
                        estado_procesado = EstadoAsignacion.objects.get(t_id=4) # Asumiendo que 4 es 'Revision'
                        asignacion.estado_asignacion = estado_procesado
                        asignacion.save()
                        logger.info(f"Estado de asignación {asignacion.id} actualizado a 'Revision'")
                    except EstadoAsignacion.DoesNotExist:
                        logger.warning("Estado 'Revision' no encontrado en EstadoAsignacion")
                        # Si no existe el estado, la transacción continuará pero sin actualizar estado
                        pass

                    logger.info(f"TRANSACCIÓN COMPLETADA exitosamente para mutación {mutacion_tipo_base}")
                    
                    # SI LLEGAMOS AQUÍ, TODO FUE EXITOSO - LA TRANSACCIÓN SE COMMITEA AUTOMÁTICAMENTE
                    return Response({
                        'success': True,
                        'mensaje': f'Mutación {mutacion_tipo_base} procesada exitosamente',
                        'radicado': radicado.numero_radicado,
                        'predio': asignacion.predio.numero_predial_nacional,
                        'resultado': resultado
                    }, status=status.HTTP_200_OK)
                    
            except Exception as transaction_error:
                logger.error(f"ERROR EN TRANSACCIÓN: {str(transaction_error)}")
                logger.error("TRANSACCIÓN REVERTIDA: Todos los cambios han sido deshechos automáticamente")
                # La transacción se revierte automáticamente al salir del bloque with
                raise transaction_error  # Re-lanzar para que sea manejado por el except general

        except ValidationError as ve:
            # Manejo específico para errores de avalúos
            error_message = str(ve)
            if 'no tiene avalúos registrados' in error_message:
                return Response({
                    'error': 'Datos faltantes en el predio',
                    'detalle': str(ve),
                    'solucion': 'Contacte al área técnica para registrar el avalúo base del predio antes de procesar la mutación.',
                    'tipo_error': 'avaluos_faltantes'
                }, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({
                    'error': 'Error de validación',
                    'detalle': str(ve),
                    'tipo_error': 'validacion'
                }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error(f"Error al procesar mutación: {str(e)}", exc_info=True)
            
            # Logging adicional para problemas de transaccionalidad
            logger.error("TRANSACCIÓN REVERTIDA: Todos los cambios han sido deshechos automáticamente")
            
            return Response({
                'error': 'Error interno del servidor',
                'detalle': str(e),
                'mensaje_tecnico': 'La transacción fue revertida automáticamente. No se guardaron cambios parciales.',
                'trace': traceback.format_exc() if settings.DEBUG else None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _procesar_mutacion(self, mutacion_tipo, mutacion_data, asignacion, radicado):
        """
        Procesa la mutación según su tipo específico.
        
        Args:
            mutacion_tipo (str): Tipo de mutación (Primera, Segunda, Tercera, etc.)
            mutacion_data (dict): Datos de la mutación
            asignacion (RadicadoPredioAsignado): Instancia de asignación
            radicado (Radicado): Instancia del radicado
            
        Returns:
            dict: Resultado del procesamiento
        """
        # CREAR INSTANCIA DE RESOLUCIÓN BÁSICA
        # Esta será usada por todas las mutaciones
        instance_resolucion = TramiteCatastral.objects.create(
            mutacion=asignacion.mutacion,
            numero_resolucion=f"RES-{radicado.numero_radicado}-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            fecha_resolucion=datetime.now().date(),
            fecha_inscripcion=datetime.now().date(),
            comienzo_vida_util_version=datetime.now().date(),
            radicado=radicado.numero_radicado,
            radicado_asignado=asignacion
        )
        logger.info(f"DEBUG: TramiteCatastral creado ID: {instance_resolucion.id}, Número: {instance_resolucion.numero_resolucion}")

        # VALIDAR QUE EL TIPO DE MUTACIÓN ESTÉ SOPORTADO
        if not es_tipo_mutacion_soportado(mutacion_tipo):
            raise ValidationError(f'Tipo de mutación no soportado: {mutacion_tipo}')
        
        # PROCESAR SEGÚN TIPO DE MUTACIÓN
        if mutacion_tipo == 15:  #  Mutacion_Primera_Clase
            return self._procesar_mutacion_primera(mutacion_data, instance_resolucion)
        
        elif mutacion_tipo == 16:  #  Mutacion_Tercera_Clase
            return self._procesar_mutacion_tercera(mutacion_data, instance_resolucion)
        
        else:
            # Esta línea no debería ejecutarse nunca debido a la validación anterior
            raise ValidationError(f'Error interno: tipo de mutación {mutacion_tipo} marcado como soportado pero no implementado')

    def _procesar_mutacion_primera(self, mutacion_data, instance_resolucion):
        """
        Procesa mutación de primera clase - Cambio de Propietario.
        
        TRANSACCIONALIDAD: Si este método falla, la transacción atómica
        del método padre revertirá automáticamente todos los cambios.
        No se requiere rollback manual.
        """
        incorporador = IncorporarMutacionPrimera()
        incorporador.incorporar_primera(
            mutacion=mutacion_data,
            instance_resolucion=instance_resolucion
        )
        
        return {
            'tipo': 1, # ID de Mutacion_Primera_Clase
            'descripcion': 'Cambio de propietario procesado exitosamente',
            'predios_procesados': len(mutacion_data.get('predios', [])),
            'resolucion': instance_resolucion.numero_resolucion
        }

    def _procesar_mutacion_tercera(self, mutacion_data, instance_resolucion):
        """
        Procesa mutación de tercera clase - Incorporación Nueva.
        
        TRANSACCIONALIDAD: Si este método falla, la transacción atómica
        del método padre revertirá automáticamente todos los cambios.
        No se requiere rollback manual.
        """
        incorporador = IncorporarMutacionTercera()
        incorporador.incorporar_tercera(
            mutacion=mutacion_data,
            instance_resolucion=instance_resolucion
        )
        
        return {
            'tipo': 3, # ID de Mutacion_Tercera_Clase
            'descripcion': 'Incorporación nueva procesada exitosamente',
            'predios_procesados': len(mutacion_data.get('predios', [])),
            'resolucion': instance_resolucion.numero_resolucion
        }

    # def _procesar_mutacion_segunda(self, mutacion_data, instance_resolucion):
    #     """Procesa mutación de segunda clase - Ejemplo para futuras implementaciones"""
    #     try:
    #         # Implementar cuando se tenga la clase IncorporarMutacionSegunda
    #         pass
    #     except Exception as e:
    #         instance_resolucion.delete()
    #         raise e


class VerificarTransaccionalidadView(APIView):
    """
    Vista de solo lectura para verificar si una mutación ya ha sido procesada
    en un trámite catastral.
    """
    permission_classes = [IsControlAnalistaUser]
    authentication_classes = [CookieJWTAuthentication]

    def get(self, request, asignacion_id):
        try:
            # Validar que la asignación exista
            asignacion = RadicadoPredioAsignado.objects.get(id=asignacion_id)
            
            # Verificar si existe un trámite asociado
            transaccionalidad_activa = TramiteCatastral.objects.filter(
                radicado_asignado=asignacion
            ).exists()
            
            return Response({
                'asignacion_id': asignacion_id,
                'transaccionalidad_activa': transaccionalidad_activa
            })
            
        except RadicadoPredioAsignado.DoesNotExist:
            return Response({
                'error': 'Asignación no encontrada'
            }, status=status.HTTP_404_NOT_FOUND)

class FinalizarTramiteView(APIView):
    permission_classes = [IsCoordinadorOrAdminUser]
    authentication_classes = [CookieJWTAuthentication]

    @transaction.atomic
    def post(self, request, tramite_id):
        try:
            tramite = TramiteCatastral.objects.get(id=tramite_id)
            asignacion = tramite.radicado_asignado

            # Validar que la asignación no esté ya finalizada
            if asignacion.estado_asignacion.t_id == 3:  #  t_id de 'Finalizado'
                return Response({
                    'error': 'Trámite ya finalizado',
                    'detalle': 'Esta asignación ya se encuentra en estado Finalizado.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Actualizar todos los predios en novedad a estado 'Activo'
            historial_predios_ids = Historial_predio.objects.filter(
                predio_tramitecatastral__tramite_catastral=tramite,
                predio__estado__t_id=106  # 106 es el t_id de 'Novedad'
            ).values_list('predio_id', flat=True)

            if historial_predios_ids:
                estado_activo = CrEstadotipo.objects.get(t_id=105)  # Asumiendo que 105 es 'Activo'
                Predio.objects.filter(id__in=historial_predios_ids).update(estado=estado_activo)

            # Actualizar el estado del predio original a 'Histórico'
            predio_original = asignacion.predio
            if predio_original:
                estado_historico = CrEstadotipo.objects.get(t_id=107)  #  107 es 'Historico'
                predio_original.estado = estado_historico
                predio_original.save()

            # Cambiar estado de la asignación a 'Finalizado'
            estado_finalizado = EstadoAsignacion.objects.get(t_id=3)  #  Estado 'Finalizado'
            asignacion.estado_asignacion = estado_finalizado
            asignacion.save()

            return Response({'mensaje': 'Trámite finalizado exitosamente'})

        except TramiteCatastral.DoesNotExist:
            return Response({'error': 'Trámite no encontrado'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error al finalizar el trámite {tramite_id}: {e}", exc_info=True)
            return Response({'error': 'Error interno del servidor'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class GenerarResolucionPDFView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [CookieJWTAuthentication]

    def get(self, request, tramite_id):
        try:
            tramite = TramiteCatastral.objects.get(id=tramite_id)
            serializer = ResolucionSerializer(tramite)
            
            # Aquí necesitarías una función para generar el PDF a partir de los datos serializados
            # Esta parte depende de tu implementación específica de `weasyprint` u otra librería
            # Ejemplo simplificado:
            # pdf_file = generar_pdf_con_weasyprint(serializer.data)
            # return HttpResponse(pdf_file, content_type='application/pdf')

            return Response(serializer.data) # Devolver JSON por ahora
        
        except TramiteCatastral.DoesNotExist:
            return Response({'error': 'Trámite no encontrado'}, status=status.HTTP_404_NOT_FOUND)
