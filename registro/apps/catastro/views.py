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
    ColDocumentotipo, CrAutoreconocimientoetnicotipo, ColInteresadotipo,CrSexotipo,
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
    ResolucionSerializer, CrSexotipoSerializer
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
            "sexo_tipo": CrSexotipoSerializer(CrSexotipo.objects.all(), many=True).data,
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

    def create(self, request, *args, **kwargs):
        try:

            # Validar y crear el radicado
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            instance = self.perform_create(serializer)
            
            # Log de éxito
            logger.info(f"Radicado creado exitosamente.")
            
            # Serializar la respuesta
            response_serializer = RadicadoListSerializer(instance)
            return Response({
                "mensaje": "Se creó el radicado exitosamente",
                "data": response_serializer.data
            }, status=status.HTTP_201_CREATED)
            
        except ValidationError as e:
            # Log del error de validación
            logger.warning(f"Error de validación al crear radicado: {str(e)}")
            if 'numero_radicado' in e.detail and any("Ya existe un radicado con este número" in str(msg) for msg in e.detail['numero_radicado']):
                return Response(
                    {"error": "Ya existe un radicado con este número."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Simplificar otros errores de validación
            simplified_errors = {}
            for field, messages in e.detail.items():
                if isinstance(messages, list) and messages:
                    simplified_errors[field] = messages[0]
                else:
                    simplified_errors[field] = messages
            
            return Response(simplified_errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            # Log del error inesperado
            logger.error(f"Error inesperado al crear radicado: {str(e)}", exc_info=True)
            return Response(
                {"error": "Ocurrió un error al procesar la solicitud"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def perform_create(self, serializer):
        try:
            return serializer.save()
        except Exception as e:
            logger.error(f"Error al guardar el radicado: {str(e)}", exc_info=True)
            raise

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
            if 'numero_radicado' in e.detail and any("Ya existe un radicado con este número" in str(msg) for msg in e.detail['numero_radicado']):
                return Response(
                    {"error": "Ya existe un radicado con este número."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Simplificar otros errores de validación
            simplified_errors = {}
            for field, messages in e.detail.items():
                if isinstance(messages, list) and messages:
                    simplified_errors[field] = messages[0]
                else:
                    simplified_errors[field] = messages
            
            return Response(simplified_errors, status=status.HTTP_400_BAD_REQUEST)
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

    def create(self, request, *args, **kwargs):
        is_many = isinstance(request.data, list)
        data = request.data.copy()

        if is_many:
            for item in data:
                item.setdefault('estado_asignacion', 1)
        else:
            data.setdefault('estado_asignacion', 1)

        try:
            # Validar y crear la(s) asignación(es)
            serializer = self.get_serializer(data=data, many=is_many)
            serializer.is_valid(raise_exception=True)
            
            with transaction.atomic():
                instances = self.perform_create(serializer)

            # Serializar la respuesta
            response_serializer = RadicadoPredioAsignadoSerializer(instances, many=is_many)
            
            mensaje = "Se crearon las asignaciones exitosamente" if is_many else "Se creó la asignación exitosamente"

            return Response({
                "mensaje": mensaje,
                "data": response_serializer.data
            }, status=status.HTTP_201_CREATED)
            
        except ValidationError as e:
            logger.warning(f"Error de validación al crear asignación: {str(e)}")
            
            details = e.detail
            error_message = "Error de validación desconocido."

            if isinstance(details, list):
                first_error_item = next((item for item in details if item), None)
                if isinstance(first_error_item, dict):
                    if 'non_field_errors' in first_error_item:
                        error_message = first_error_item['non_field_errors'][0]
                    else:
                        first_error_list = next(iter(first_error_item.values()), [])
                        if first_error_list:
                            error_message = first_error_list[0]
                elif first_error_item:
                    error_message = str(first_error_item)
                
                return Response({"error": str(error_message)}, status=status.HTTP_400_BAD_REQUEST)

            elif isinstance(details, dict):
                if 'non_field_errors' in details:
                    return Response({"error": details['non_field_errors'][0]}, status=status.HTTP_400_BAD_REQUEST)
                
                simplified_errors = {}
                for field, messages in details.items():
                    simplified_errors[field] = messages[0] if isinstance(messages, list) and messages else messages
                
                first_error_message = next(iter(simplified_errors.values()), "Error de validación.")
                return Response({"error": first_error_message}, status=status.HTTP_400_BAD_REQUEST)
            
            return Response({"error": str(details)}, status=status.HTTP_400_BAD_REQUEST)
        except Radicado.DoesNotExist:
            return Response(
                {"error": "El radicado especificado no existe"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Predio.DoesNotExist:
            return Response(
                {"error": "El predio especificado no existe"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error inesperado al crear asignación(es): {str(e)}", exc_info=True)
            return Response(
                {"error": "Ocurrió un error al procesar la solicitud"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def perform_create(self, serializer):
        return serializer.save()

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
            if 'numero_radicado' in e.detail and any("Ya existe un radicado con este número" in str(msg) for msg in e.detail['numero_radicado']):
                return Response(
                    {"error": "Ya existe un radicado con este número."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Simplificar otros errores de validación
            simplified_errors = {}
            for field, messages in e.detail.items():
                if isinstance(messages, list) and messages:
                    simplified_errors[field] = messages[0]
                else:
                    simplified_errors[field] = messages
            
            return Response(simplified_errors, status=status.HTTP_400_BAD_REQUEST)
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
        
        if id_asignacion:
            queryset = queryset.filter(id=id_asignacion)

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
                errors = serializer.errors
                if 'non_field_errors' in errors and errors['non_field_errors']:
                    error_message = errors['non_field_errors'][0]
                else:
                    # Extraer el primer mensaje de error de cualquier campo
                    error_message = next((msg[0] for msg in errors.values() if msg), "Error de validación desconocido.")
                
                return Response({'error': error_message}, status=status.HTTP_400_BAD_REQUEST)

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
                        estado_procesado = EstadoAsignacion.objects.get(ilicode='Revision')
                        asignacion.estado_asignacion = estado_procesado
                        asignacion.save()
                        logger.info(f"Estado de asignación {asignacion.id} actualizado a 'Revision'")
                    except EstadoAsignacion.DoesNotExist:
                        logger.warning("Estado 'Revision' no encontrado en EstadoAsignacion")
                        # Si no existe el estado, la transacción continuará pero sin actualizar estado
                        pass

                    logger.info(f"TRANSACCIÓN COMPLETADA exitosamente para mutación {mutacion_tipo_base}")
                    
                    # SI LLEGAMOS AQUÍ, TODO FUE EXITOSO - LA TRANSACCIÓN SE COMMITEA AUTOMÁTICamente
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
                
                # Simplificar el mensaje de error si es una ValidationError
                if isinstance(transaction_error, ValidationError):
                    details = transaction_error.detail
                    error_message = "Error de validación."
                    if isinstance(details, dict):
                        # Tomar el primer error del diccionario
                        first_key = next(iter(details))
                        first_error_list = details[first_key]
                        error_message = f"Error en el campo '{first_key}': {first_error_list[0]}"
                    elif isinstance(details, list) and details:
                        error_message = str(details[0])
                    else:
                        error_message = str(details)
                    
                    return Response({'error': error_message}, status=status.HTTP_400_BAD_REQUEST)
                
                # Para otros errores, relanzar para que lo maneje el except general
                raise transaction_error

        except ValidationError as ve:
            # Simplificar cualquier error de validación que no se haya capturado antes
            raw_error_message = str(ve)
            if 'no tiene avalúos registrados' in raw_error_message:
                error_message = 'El predio no tiene avalúos registrados. Contacte al área técnica para registrar el avalúo base del predio antes de procesar la mutación.'
            else:
                details = ve.detail if hasattr(ve, 'detail') else raw_error_message
                if isinstance(details, list) and details:
                    error_message = str(details[0])
                elif isinstance(details, dict) and details:
                    first_error_list = next(iter(details.values()), [])
                    error_message = str(first_error_list[0]) if first_error_list else "Error de validación."
                else:
                    error_message = str(details)
            return Response({'error': error_message}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error(f"Error al procesar mutación: {str(e)}", exc_info=True)
            return Response({
                'error': 'Ocurrió un error interno al procesar la mutación. Por favor, contacte al soporte técnico.'
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
        if mutacion_tipo == 15:  # Mutacion_Primera_Clase
            return self._procesar_mutacion_primera(mutacion_data, instance_resolucion, asignacion)
        
        elif mutacion_tipo == 16:  # Mutacion_Tercera_Clase
            return self._procesar_mutacion_tercera(mutacion_data, instance_resolucion, asignacion)
        
        # elif mutacion_tipo == 'Mutacion_Segunda_Clase':
        #     return self._procesar_mutacion_segunda(mutacion_data, instance_resolucion)
        
        else:
            # Esta línea no debería ejecutarse nunca debido a la validación anterior
            raise ValidationError(f'Error interno: tipo de mutación {mutacion_tipo} marcado como soportado pero no implementado')

    def _procesar_mutacion_primera(self, mutacion_data, instance_resolucion, asignacion):
        """
        Procesa mutación de primera clase - Cambio de Propietario.
        
        TRANSACCIONALIDAD: Si este método falla, la transacción atómica
        del método padre revertirá automáticamente todos los cambios.
        No se requiere rollback manual.
        """
        incorporador = IncorporarMutacionPrimera()
        incorporador.incorporar_primera(
            mutacion=mutacion_data,
            instance_resolucion=instance_resolucion,
            asignacion=asignacion
        )
        
        return {
            'tipo': 15, # ID de Mutacion_Primera_Clase
            'descripcion': 'Cambio de propietario procesado exitosamente',
            'predios_procesados': len(mutacion_data.get('predios', [])),
            'resolucion': instance_resolucion.numero_resolucion
        }

    def _procesar_mutacion_tercera(self, mutacion_data, instance_resolucion, asignacion):
        """
        Procesa mutación de tercera clase - Incorporación Nueva.
        
        TRANSACCIONALIDAD: Si este método falla, la transacción atómica
        del método padre revertirá automáticamente todos los cambios.
        No se requiere rollback manual.
        """
        incorporador = IncorporarMutacionTercera()
        incorporador.incorporar_tercera(
            mutacion=mutacion_data,
            instance_resolucion=instance_resolucion,
            asignacion=asignacion
        )
        
        return {
            'tipo': 16, # ID de Mutacion_Tercera_Clase
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
    Vista de prueba para verificar que la transaccionalidad funciona correctamente.
    Simula una operación que falla intencionalmente para verificar rollback.
    """
    permission_classes = [IsControlAnalistaUser]
    authentication_classes = [CookieJWTAuthentication]
    
    def post(self, request):
        """
        Prueba de transaccionalidad:
        1. Crea registros en múltiples tablas
        2. Falla intencionalmente
        3. Verifica que todos los registros se reviertan
        """
        try:
            with transaction.atomic():
                logger.info("INICIANDO PRUEBA DE TRANSACCIONALIDAD")
                
                # Crear un TramiteCatastral de prueba
                tramite_test = TramiteCatastral.objects.create(
                    mutacion_id=1,  # Asumiendo que existe
                    numero_resolucion=f"TEST-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    fecha_resolucion=datetime.now().date(),
                    fecha_inscripcion=datetime.now().date(),
                    comienzo_vida_util_version=datetime.now().date(),
                    radicado="TEST-RADICADO",
                    radicado_asignado_id=1  # Asumiendo que existe
                )
                
                logger.info(f"PRUEBA: TramiteCatastral creado ID: {tramite_test.id}")
                
                # Simular error intencional
                if request.data.get('simular_error', True):
                    logger.info("PRUEBA: Simulando error para probar rollback...")
                    raise ValidationError("Error simulado para probar transaccionalidad")
                
                return Response({
                    'mensaje': 'Prueba completada sin errores',
                    'tramite_id': tramite_test.id
                })
                
        except Exception as e:
            logger.error(f"PRUEBA: Error capturado - {str(e)}")
            logger.error("PRUEBA: La transacción debería revertirse automáticamente")
            
            return Response({
                'mensaje': 'Prueba de transaccionalidad ejecutada',
                'error_simulado': str(e),
                'info': 'Si la transaccionalidad funciona, no debería haber registros residuales en la BD'
            }, status=status.HTTP_400_BAD_REQUEST)


class ConsultarEstadoMutacionView(APIView):
    """
    Vista para consultar el estado de procesamiento de una mutación.
    """
    permission_classes = [IsControlAnalistaUser]
    authentication_classes = [CookieJWTAuthentication]
    
    def get(self, request, asignacion_id):
        """
        Consulta el estado actual de una asignación/mutación.
        
        Args:
            asignacion_id (int): ID de la asignación a consultar
        """
        try:
            # Verificar que el usuario tenga acceso a esta asignación
            asignacion = RadicadoPredioAsignado.objects.select_related(
                'radicado', 'estado_asignacion', 'mutacion', 'predio', 'usuario_analista'
            ).get(id=asignacion_id)
            
            # Verificar permisos (solo admin o analista asignado)
            from registro.apps.users.models import Rol_predio
            is_admin = Rol_predio.objects.filter(
                user=request.user,
                rol__name='Admin',
                is_activate=True
            ).exists()
            
            if not is_admin and asignacion.usuario_analista != request.user:
                return Response({
                    'error': 'Sin permisos',
                    'detalle': 'No tienes permisos para consultar esta asignación'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Serializar datos
            serializer = RadicadoPredioAsignadoSerializer(asignacion)
            
            # Buscar trámites procesados relacionados
            tramites = TramiteCatastral.objects.filter(
                radicado_asignado=asignacion
            ).order_by('-id')
            
            tramites_data = []
            for tramite in tramites:
                tramites_data.append({
                    'tramite_id': tramite.id,
                    'numero_resolucion': tramite.numero_resolucion,
                    'fecha_resolucion': tramite.fecha_resolucion,
                    'mutacion': tramite.mutacion.ilicode if tramite.mutacion else None
                })
            
            return Response({
                'asignacion': serializer.data,
                'tramites_procesados': tramites_data,
                'total_tramites': len(tramites_data)
            }, status=status.HTTP_200_OK)
            
        except RadicadoPredioAsignado.DoesNotExist:
            return Response({
                'error': 'Asignación no encontrada',
                'detalle': f'No existe una asignación con ID {asignacion_id}'
            }, status=status.HTTP_404_NOT_FOUND)
            
        except Exception as e:
            logger.error(f"Error al consultar estado de mutación: {str(e)}", exc_info=True)
            return Response({
                'error': 'Error interno del servidor',
                'detalle': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class ProcesarGeometriaView(APIView):
    """
    Endpoint para subir y validar un archivo ZIP con geometrías (Shapefile).
    """
    permission_classes = [IsControlAnalistaUser]
    authentication_classes = [CookieJWTAuthentication]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        archivo_zip = request.FILES.get('file')

        if not archivo_zip:
            return Response({"error": "No se proporcionó el archivo 'file'."}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            helper = IncorporacionUnidadesHelper()
            features_dict = helper._procesar_geometria_zip(archivo_zip)
            
            # Construir la respuesta final FeatureCollection
            feature_collection = {
                "type": "FeatureCollection",
                "features": list(features_dict.values()) # Convertimos los valores del diccionario a una lista
            }

            return Response(feature_collection, status=status.HTTP_200_OK)

        except ValidationError as ve:
            return Response({'error': 'Error de validación de geometría', 'detalle': ve.detail}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error al procesar el archivo de geometría: {e}", exc_info=True)
            return Response({"error": "Error interno al procesar el archivo.", "detalle": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class FinalizarTramiteView(APIView):
    """
    Endpoint para finalizar un trámite catastral.
    Este proceso es el paso final después de que una mutación ha sido procesada y revisada.
    
    Acciones:
    1. Cambia el estado de la asignación del radicado a 'Finalizado'.
    2. Pasa el predio original (activo) a estado 'historico'.
    3. Activa el predio o predios que estaban en estado 'novedad'.
    Todo el proceso se ejecuta en una transacción atómica.
    """
    permission_classes = [IsCoordinadorOrAdminUser]
    authentication_classes = [CookieJWTAuthentication]

    def post(self, request, tramite_id, *args, **kwargs):
        try:
            with transaction.atomic():
                # 1. Obtener el trámite y sus relaciones críticas
                try:
                    tramite = TramiteCatastral.objects.select_related(
                        'radicado_asignado',
                        'radicado_asignado__predio',
                        'radicado_asignado__estado_asignacion'
                    ).get(id=tramite_id)
                except TramiteCatastral.DoesNotExist:
                    return Response({'error': f'Trámite con ID {tramite_id} no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

                asignacion = tramite.radicado_asignado
                predio_original = asignacion.predio

                # 2. Validar que el trámite no esté ya finalizado
                if asignacion.estado_asignacion.ilicode == 'Finalizado':
                    return Response({'error': 'Este trámite ya ha sido finalizado.'}, status=status.HTTP_400_BAD_REQUEST)

                # 3. Identificar el(los) predio(s) de novedad asociados al trámite
                # Se obtiene primero los IDs de los predios desde el historial, y se convierte a lista para evitar lazy evaluation
                predios_novedad_ids = list(Historial_predio.objects.filter(
                    predio_tramitecatastral__tramite_catastral=tramite,
                    predio__estado__ilicode='Novedad'
                ).values_list('predio__id', flat=True).distinct())

                # Luego se obtienen los objetos Predio completos
                predios_novedad = Predio.objects.filter(id__in=predios_novedad_ids)


                # 4. Validar que existan predios de novedad para activar
                if not predios_novedad.exists():
                    return Response({'error': 'No se encontraron predios en estado "novedad" asociados a este trámite.'}, status=status.HTTP_400_BAD_REQUEST)

                # 5. Obtener los objetos de estado necesarios
                try:
                    estado_activo = CrEstadotipo.objects.get(ilicode='Activo')
                    estado_historico = CrEstadotipo.objects.get(ilicode='Historico')
                    estado_finalizado = EstadoAsignacion.objects.get(ilicode='Finalizado')
                except (CrEstadotipo.DoesNotExist, EstadoAsignacion.DoesNotExist) as e:
                    logger.error(f"Error crítico de configuración: No se encontraron estados base: {e}")
                    return Response({'error': 'Error de configuración del servidor: Faltan estados (activo, historico, Finalizado).'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

                # 6. Ejecutar las actualizaciones de estado
                logger.info(f"Finalizando trámite {tramite_id}. Predio original: {predio_original.numero_predial_nacional}")
                
                current_datetime = datetime.now()

                # Pasar predio original a histórico y actualizar fin de vida útil
                predio_original.estado = estado_historico
                predio_original.fin_vida_util_version = current_datetime
                predio_original.save()
                logger.info(f"Predio {predio_original.numero_predial_nacional} pasado a estado 'historico'. Fin de vida útil: {current_datetime}")

                # Activar predios de novedad y actualizar comienzo de vida útil
                npns_activados = list(predios_novedad.values_list('numero_predial_nacional', flat=True))
                predios_novedad.update(estado=estado_activo, comienzo_vida_util_version=current_datetime)
                logger.info(f"Activados {len(npns_activados)} predios: {npns_activados}. Comienzo de vida útil: {current_datetime}")

                # Finalizar la asignación
                asignacion.estado_asignacion = estado_finalizado
                asignacion.save()
                logger.info(f"Asignación {asignacion.id} pasada a estado 'Finalizado'.")

                return Response({
                    'mensaje': 'Trámite finalizado exitosamente.',
                    'predio_historico': predio_original.id,
                    'predio_activado': predios_novedad_ids
                }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error al finalizar el trámite {tramite_id}: {e}", exc_info=True)
            return Response({'error': 'Ocurrió un error inesperado durante la finalización del trámite.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GenerarResolucionPDFView(APIView):
    """
    Vista para generar un PDF de resolución para un trámite catastral específico.
    """
    permission_classes = [IsAuthenticated] # O el permiso que consideres adecuado
    authentication_classes = [CookieJWTAuthentication]

    def get(self, request, tramite_id):
        try:
            # 1. Obtener el trámite catastral
            tramite = TramiteCatastral.objects.get(id=tramite_id)
        except TramiteCatastral.DoesNotExist:
            return Response(
                {'error': f'No se encontró un trámite con el ID {tramite_id}.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # 2. Serializar los datos usando el nuevo orquestador
        serializer = ResolucionSerializer(tramite)
        datos_resolucion = serializer.data

        # 3. Renderizar el template HTML con los datos
        html_string = render_to_string('catastro/resolucion_pdf.html', {'data': datos_resolucion})
        
        # 4. Generar el PDF usando WeasyPrint
        try:
            html = HTML(string=html_string)
            pdf = html.write_pdf()

            response = HttpResponse(pdf, content_type='application/pdf')
            response['Content-Disposition'] = f'inline; filename="resolucion_{tramite.numero_resolucion}.pdf"'
            
            return response
        except Exception as e:
            logger.error(f"Error generando PDF de resolución para trámite {tramite_id}: {e}", exc_info=True)
            return Response(
                {'error': 'Ocurrió un error al generar el PDF.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
