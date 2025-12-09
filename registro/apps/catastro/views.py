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
    Predio, Radicado, TramiteCatastral, PredioTramitecatastral,
    ColDocumentotipo, ColInteresadotipo, Interesado, InteresadoPredio, Terreno, Unidadconstruccion, EstructuraAvaluo,
    PredioUnidadespacial,
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
# Importar las clases de incorporación granular
from registro.apps.catastro.incorporacion.incorporar_interesado import IncorporarInteresadoSerializer
from registro.apps.catastro.incorporacion.incorporar_gestion import IncorporacionGestionSerializer 

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

            # Ordenar de forma descendente por ID (más recientes primero)
            return queryset.order_by('-id')
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
                {"error": f"Error inesperado: {str(e)}"},
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
                {"error": f"Error inesperado: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class RadicadoPredioAsignadoListView(generics.ListAPIView):
    """
    Lista las asignaciones de radicados a predios con filtrado por rol y búsqueda.

    - Autenticación: Requiere que el usuario esté autenticado.
    - Roles Privilegiados (IDs: 1, 3, 4): Ven todas las asignaciones.
    - Otros Roles: Ven solo las asignaciones donde son el analista.
    - Búsqueda: Permite filtrar por el inicio del 'numero_radicado'.
    - Orden: Descendente por ID de asignación.
    """
    serializer_class = RadicadoPredioAsignadoSerializer
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        
        # 5. Optimización y Rendimiento (N+1)
        base_queryset = RadicadoPredioAsignado.objects.select_related(
            'radicado', 'predio', 'estado_asignacion', 'mutacion',
            'usuario_analista', 'usuario_coordinador'
        ).prefetch_related(
            'usuario_analista__rol_predio_set__rol',
            'usuario_coordinador__rol_predio_set__rol'
        )

        # 3. Lógica de Filtrado por Roles
        privileged_roles_ids = {1, 3, 4}
        user_roles_ids = set(user.rol_predio_set.filter(is_activate=True).values_list('rol__id', flat=True))
        
        is_privileged = not user_roles_ids.isdisjoint(privileged_roles_ids)

        if is_privileged:
            # CASO A (Usuario Privilegiado): Acceso total
            queryset = base_queryset
        else:
            # CASO B (Usuario No Privilegiado): Filtrar por analista
            queryset = base_queryset.filter(usuario_analista=user)
            
        # 4. Funcionalidad de Búsqueda
        numero_radicado = self.request.query_params.get('numero_radicado')
        if numero_radicado:
            queryset = queryset.filter(radicado__numero_radicado__startswith=numero_radicado)

        # 6. Ordenamiento
        return queryset.order_by('-id')

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
    parser_classes = [JSONParser]  # Asegurar que la vista procese JSON
    
    def post(self, request):
        """
        Procesa una mutación catastral.
        """
        # --- INICIO BLOQUE DE DEPURACIÓN ---
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"--- DEBUG: INICIO DE SOLICITUD A ProcesarMutacionView ---")
        logger.debug(f"Cabeceras de la solicitud: {request.headers}")
        logger.debug(f"Content-Type detectado por DRF: {request.content_type}")
        logger.debug(f"Cuerpo de la solicitud (raw): {request.body}")
        logger.debug(f"Datos de la solicitud (después de parsear): {request.data}")
        logger.debug(f"--- DEBUG: FIN DE BLOQUE DE DEPURACIÓN ---")
        
        try:
            # VALIDAR DATOS DE ENTRADA
            serializer = MutacionRadicadoValidationSerializer(
                data=request.data,
                context={'request': request}
            )
            
            if not serializer.is_valid():
                # Formatear errores para que sean más claros
                simplified_errors = {
                    field: messages[0] for field, messages in serializer.errors.items()
                }
                return Response({
                    'detalle': simplified_errors
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
            'resolucion': instance_resolucion.numero_resolucion,
            'tramite_id': instance_resolucion.id
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
            'resolucion': instance_resolucion.numero_resolucion,
            'tramite_id': instance_resolucion.id
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

    def post(self, request, asignacion_id, *args, **kwargs):
        finalizar = request.data.get('finalizar')
        if finalizar is None:
            return Response({'error': 'El parámetro booleano "finalizar" es requerido en el cuerpo de la solicitud.'}, status=status.HTTP_400_BAD_REQUEST)
        if not isinstance(finalizar, bool):
            return Response({'error': 'El parámetro "finalizar" debe ser un valor booleano (true o false).'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                # 1. Obtener la asignación y sus relaciones críticas
                try:
                    asignacion = RadicadoPredioAsignado.objects.select_related(
                        'predio',
                        'estado_asignacion'
                    ).get(id=asignacion_id)
                except RadicadoPredioAsignado.DoesNotExist:
                    return Response({'error': f'Asignación con ID {asignacion_id} no encontrada.'}, status=status.HTTP_404_NOT_FOUND)

                # Obtener el trámite a través de la asignación
                try:
                    tramite = TramiteCatastral.objects.get(radicado_asignado=asignacion)
                except TramiteCatastral.DoesNotExist:
                    return Response({'error': f'No se encontró un trámite catastral asociado a la asignación {asignacion_id}.'}, status=status.HTTP_404_NOT_FOUND)

                
                # 2. Validar estados
                if asignacion.estado_asignacion.ilicode == 'Finalizado':
                    return Response({'error': 'Este trámite ya ha sido finalizado.'}, status=status.HTTP_400_BAD_REQUEST)
                
                if asignacion.estado_asignacion.ilicode != 'Revision':
                    return Response({'error': f'La acción no es válida. El trámite está en estado "{asignacion.estado_asignacion.ilicode}", se esperaba "Revisión".'}, status=status.HTTP_400_BAD_REQUEST)
                
                # --- Lógica de bifurcación ---
                if finalizar:
                    # CASO: FINALIZAR EL TRÁMITE (OK)
                    predios_novedad_ids = list(Historial_predio.objects.filter(
                        predio_tramitecatastral__tramite_catastral=tramite,
                        predio__estado__ilicode='Novedad'
                    ).values_list('predio__id', flat=True).distinct())
                    
                    if not predios_novedad_ids:
                        return Response({'error': 'No se encontraron predios en estado "novedad" asociados a este trámite para finalizar.'}, status=status.HTTP_400_BAD_REQUEST)

                    predios_novedad = Predio.objects.filter(id__in=predios_novedad_ids)
                    predio_original = asignacion.predio

                    try:
                        estado_activo = CrEstadotipo.objects.get(ilicode='Activo')
                        estado_historico = CrEstadotipo.objects.get(ilicode='Historico')
                        estado_finalizado = EstadoAsignacion.objects.get(ilicode='Finalizado')
                    except (CrEstadotipo.DoesNotExist, EstadoAsignacion.DoesNotExist) as e:
                        logger.error(f"Error crítico de configuración: No se encontraron estados base: {e}")
                        return Response({'error': 'Error de configuración del servidor: Faltan estados (Activo, Historico, Finalizado).'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

                    logger.info(f"Finalizando trámite asociado a la asignación {asignacion_id}. Predio original: {predio_original.numero_predial_nacional}")
                    
                    current_datetime = datetime.now()

                    predio_original.estado = estado_historico
                    predio_original.fin_vida_util_version = current_datetime
                    predio_original.save()
                    logger.info(f"Predio {predio_original.numero_predial_nacional} pasado a estado 'historico'. Fin de vida útil: {current_datetime}")

                    npns_activados = list(predios_novedad.values_list('numero_predial_nacional', flat=True))
                    predios_novedad.update(estado=estado_activo, comienzo_vida_util_version=current_datetime)
                    logger.info(f"Activados {len(npns_activados)} predios: {npns_activados}. Comienzo de vida útil: {current_datetime}")

                    asignacion.estado_asignacion = estado_finalizado
                    asignacion.save()
                    logger.info(f"Asignación {asignacion.id} pasada a estado 'Finalizado'.")

                    return Response({
                        'mensaje': 'Trámite finalizado exitosamente.',
                        'predio_historico': predio_original.id,
                        'predios_activados': predios_novedad_ids
                    }, status=status.HTTP_200_OK)

                else:
                    # CASO: DEVOLVER A CORRECCIÓN (NO OK)
                    try:
                        estado_en_proceso = EstadoAsignacion.objects.get(ilicode='En proceso')
                    except EstadoAsignacion.DoesNotExist:
                        logger.error("Error crítico de configuración: No se encontró el estado 'En proceso'.")
                        return Response({'error': 'Error de configuración del servidor: Falta el estado "En proceso".'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                    
                    asignacion.estado_asignacion = estado_en_proceso
                    asignacion.save()
                    logger.info(f"Asignación {asignacion.id} pasada a estado 'En proceso' para corrección.")
                    
                    return Response({
                        'mensaje': 'El trámite ha sido devuelto para corrección.',
                        'nuevo_estado': 'En proceso'
                    }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error al procesar la finalización de la asignación {asignacion_id}: {e}", exc_info=True)
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

class EnviarARevisionView(APIView):
    """
    Endpoint para que un analista envíe un trámite corregido de vuelta a revisión.
    
    Acciones:
    1.  Verifica que el usuario sea el analista asignado (o un admin).
    2.  Valida que el estado actual de la asignación sea 'En proceso'.
    3.  Cambia el estado de la asignación a 'Revisión'.
    """
    permission_classes = [IsControlAnalistaUser] # Permiso para analistas
    authentication_classes = [CookieJWTAuthentication]

    def post(self, request, asignacion_id, *args, **kwargs):
        try:
            with transaction.atomic():
                # 1. Obtener la asignación directamente
                try:
                    asignacion = RadicadoPredioAsignado.objects.select_related(
                        'estado_asignacion', 'usuario_analista'
                    ).get(id=asignacion_id)
                except RadicadoPredioAsignado.DoesNotExist:
                    return Response({'error': f'Asignación con ID {asignacion_id} no encontrada.'}, status=status.HTTP_404_NOT_FOUND)

                # 2. Validar que el usuario sea el analista asignado
                user_roles = [rp.rol.name.lower() for rp in request.user.rol_predio_set.all() if rp.rol]
                is_admin = 'admin' in user_roles

                if not is_admin and asignacion.usuario_analista != request.user:
                    return Response({'error': 'No tienes permiso para modificar este trámite. Solo el analista asignado puede hacerlo.'}, status=status.HTTP_403_FORBIDDEN)

                # 3. Validar que el estado actual sea 'En proceso'
                if asignacion.estado_asignacion.ilicode != 'En proceso':
                    return Response({
                        'error': f'La acción no es válida. El trámite está en estado "{asignacion.estado_asignacion.ilicode}", se esperaba "En proceso".'
                    }, status=status.HTTP_400_BAD_REQUEST)

                # 4. Obtener el estado 'Revisión'
                try:
                    estado_revision = EstadoAsignacion.objects.get(ilicode='Revision')
                except EstadoAsignacion.DoesNotExist:
                    logger.error("Error crítico de configuración: No se encontró el estado 'Revision'.")
                    return Response({'error': 'Error de configuración del servidor: Falta el estado "Revision".'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

                # 5. Cambiar el estado
                asignacion.estado_asignacion = estado_revision
                asignacion.save()
                logger.info(f"Asignación {asignacion.id} pasada a estado 'Revisión' por el usuario {request.user.username}.")

                return Response({
                    'mensaje': 'El trámite ha sido enviado a revisión exitosamente.',
                    'nuevo_estado': 'Revisión'
                }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error al enviar a revisión la asignación {asignacion_id}: {e}", exc_info=True)
            return Response({'error': 'Ocurrió un error inesperado al procesar la solicitud.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ActualizarMutacionView(APIView):
    """
    Endpoint para actualizar una mutación en estado 'En proceso' de forma granular.
    - Preserva el ID del TramiteCatastral y de los Predios 'Novedad'.
    - Actualiza componentes individuales (interesados, terrenos, etc.) solo si se 
      proporcionan en la solicitud, mediante una estrategia de "borrar y recrear" 
      para esos componentes específicos.
    """
    permission_classes = [IsControlAnalistaUser]
    authentication_classes = [CookieJWTAuthentication]
    parser_classes = [JSONParser]

    def put(self, request, *args, **kwargs):
        tramite_id = request.data.get('tramite_id')
        if not tramite_id:
            return Response({'error': 'El cuerpo de la solicitud debe contener "tramite_id".'}, status=status.HTTP_400_BAD_REQUEST)

        mutacion_data = request.data.get('mutacion')
        if not mutacion_data:
            return Response({'error': 'El cuerpo de la solicitud debe contener la clave "mutacion".'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                # 1. Obtener y validar el trámite
                tramite, asignacion, error_response = self._validar_tramite_y_permisos(request, tramite_id)
                if error_response:
                    return error_response

                # 2. Procesar cada predio en la solicitud de mutación
                predios_data = mutacion_data.get('predios', [])
                if not predios_data:
                    raise ValidationError("La mutación no contiene la lista de 'predios' a actualizar.")

                for predio_data in predios_data:
                    # Obtener predio_id del request
                    predio_id = predio_data.get('predio_id')
                    if not predio_id:
                        raise ValidationError("Cada predio en la solicitud debe contener 'predio_id'.")
                    
                    try:
                        # Obtener el predio directamente por ID
                        predio_a_actualizar = Predio.objects.get(id=predio_id)
                    except Predio.DoesNotExist:
                        raise ValidationError(f"El predio con ID '{predio_id}' no existe.")
                    
                    # Validar que el predio pertenece a este trámite y está en estado 'Novedad'
                    predio_tramite = PredioTramitecatastral.objects.filter(
                        predio=predio_a_actualizar,
                        tramite_catastral=tramite
                    ).first()
                    
                    if not predio_tramite:
                        raise ValidationError(
                            f"El predio con ID '{predio_id}' no está asociado al trámite {tramite_id}."
                        )
                    
                    if predio_a_actualizar.estado.ilicode != 'Novedad':
                        raise ValidationError(
                            f"El predio con ID '{predio_id}' no está en estado 'Novedad'. "
                            f"Estado actual: '{predio_a_actualizar.estado.ilicode}'"
                        )
                    
                    # 3. Actualización granular por componente
                    self._actualizar_componentes_del_predio(predio_a_actualizar, predio_data, tramite)

                return Response({
                    'mensaje': 'La mutación ha sido actualizada exitosamente con las correcciones.',
                    'tramite_id': tramite.id
                }, status=status.HTTP_200_OK)

        except ValidationError as ve:
            return Response({'error': 'Error de validación', 'detalle': ve.detail}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error al actualizar la mutación para el trámite {tramite_id}: {e}", exc_info=True)
            return Response({'error': 'Ocurrió un error inesperado al actualizar la mutación.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _validar_tramite_y_permisos(self, request, tramite_id):
        """Obtiene el trámite y valida el estado y los permisos del usuario."""
        try:
            tramite = TramiteCatastral.objects.select_related(
                'radicado_asignado__estado_asignacion',
                'radicado_asignado__usuario_analista'
            ).get(id=tramite_id)
        except TramiteCatastral.DoesNotExist:
            return None, None, Response({'error': f'Trámite con ID {tramite_id} no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        asignacion = tramite.radicado_asignado
        user_roles = [rp.rol.name.lower() for rp in request.user.rol_predio_set.all() if rp.rol]
        is_admin = 'admin' in user_roles

        if not is_admin and asignacion.usuario_analista != request.user:
            return None, None, Response({'error': 'No tienes permiso para modificar este trámite.'}, status=status.HTTP_403_FORBIDDEN)
        
        if asignacion.estado_asignacion.ilicode != 'En proceso':
            return None, None, Response({'error': f'La acción no es válida. El trámite está en estado "{asignacion.estado_asignacion.ilicode}", se esperaba "En proceso".'}, status=status.HTTP_400_BAD_REQUEST)
        
        return tramite, asignacion, None

    def _actualizar_componentes_del_predio(self, predio, predio_data, tramite):
        """Orquesta la actualización granular de los componentes de un predio."""
        
        # NOTA: Para M1 no se actualizan datos básicos del predio (direccion, condicion_predio, destinacion_economica)
        # Solo se actualizan interesados y fuente administrativa

        # Actualizar interesados (si se proporcionan)
        if 'interesados' in predio_data:
            self._actualizar_interesados(predio, predio_data['interesados'], tramite)
        
        # Actualizar fuente administrativa (si se proporciona)
        if 'fuente_administrativa' in predio_data:
            self._actualizar_fuente_administrativa(predio, predio_data['fuente_administrativa'], tramite)

        # Actualizar terrenos (si se proporcionan)
        if 'terrenos' in predio_data:
            # Eliminar los terrenos y unidades espaciales asociadas al predio
            Terreno.objects.filter(prediounidadespacial__predio=predio).delete()
            # La recreación requiere la lógica completa de `IncorporarMutacionTercera` o similar.
            # Esta parte es compleja y se simplifica aquí.
            # Idealmente, llamar a un método específico:
            # incorporador = IncorporarMutacionTercera()
            # incorporador.incorporar_terrenos(predio, predio_data['terrenos'], tramite)
            logger.info(f"Lógica de actualización de terrenos para predio {predio.id} debe ser implementada.")

        # Actualizar unidades de construcción (si se proporcionan)
        if 'unidades' in predio_data:
            Unidadconstruccion.objects.filter(prediounidadespacial__predio=predio).delete()
            # incorporador.incorporar_unidades(...)
            logger.info(f"Lógica de actualización de unidades para predio {predio.id} debe ser implementada.")
            
        # Actualizar avalúos (si se proporcionan)
        if 'avaluo' in predio_data:
            EstructuraAvaluo.objects.filter(predio=predio).delete()
            # incorporador.incorporar_avaluo(...)
            logger.info(f"Lógica de actualización de avalúos para predio {predio.id} debe ser implementada.")

    def _actualizar_interesados(self, predio, interesados_data, tramite):
        """
        Actualiza los interesados del predio según las reglas de negocio:
        - Si el request tiene solo 1 interesado: el predio conserva solo ese interesado
        - Si el request tiene múltiples interesados: se conservan los que corresponden y se agregan los nuevos
        - Si un interesado corresponde a uno existente:
          * Si no está asociado a otro predio → se actualiza su información
          * Si está asociado a otro predio → se crea un nuevo registro y se asocia al predio del trámite,
            eliminando la relación antigua (si no tiene historial)
        """
        from registro.apps.catastro.serializers import InteresadoSerializer as InteresadoModelSerializer
        
        # Obtener las relaciones actuales de interesados con este predio
        relaciones_actuales = InteresadoPredio.objects.filter(predio=predio).select_related('interesado')
        # Mapear relaciones actuales por identificador único (tipo_documento_id + numero_documento)
        relaciones_por_identificador = {}
        for rel in relaciones_actuales:
            interesado = rel.interesado
            identificador = (
                interesado.tipo_documento_id,
                interesado.numero_documento or '',
            )
            relaciones_por_identificador[identificador] = rel
        
        # IDs de interesados que se mantendrán en el predio
        nuevos_interesados_ids = set()
        relaciones_a_eliminar_por_reemplazo = []
        
        for interesado_data in interesados_data:
            # Asignar valor por defecto para 'autoreconocimientoetnico' si no se proporciona
            if 'autoreconocimientoetnico' not in interesado_data or not interesado_data.get('autoreconocimientoetnico'):
                interesado_data['autoreconocimientoetnico'] = 335  # ID para "No aplica"
            
            # Validar datos del interesado
            serializer_interesado = InteresadoModelSerializer(data=interesado_data)
            serializer_interesado.is_valid(raise_exception=True)
            validated_data = serializer_interesado.validated_data
            
            # Construir campos de búsqueda
            tipo_documento = validated_data.get('tipo_documento')
            numero_documento = validated_data.get('numero_documento')
            tipo_interesado_obj = validated_data.get('tipo_interesado')
            
            search_fields = {
                'tipo_documento': tipo_documento,
                'numero_documento': numero_documento,
            }
            
            defaults = {
                'tipo_documento': tipo_documento,
                'numero_documento': numero_documento,
                'primer_nombre': validated_data.get('primer_nombre'),
                'segundo_nombre': validated_data.get('segundo_nombre'),
                'primer_apellido': validated_data.get('primer_apellido'),
                'segundo_apellido': validated_data.get('segundo_apellido'),
                'razon_social': validated_data.get('razon_social'),
                'sexo': validated_data.get('sexo'),
                'tipo_interesado': tipo_interesado_obj,
                'autoreconocimientoetnico': validated_data.get('autoreconocimientoetnico'),
            }
            
            # Ajustar campos de búsqueda según tipo de interesado
            if tipo_interesado_obj and tipo_interesado_obj.t_id == 6:  # Persona Natural
                search_fields.update({
                    'primer_nombre': defaults.get('primer_nombre'),
                    'segundo_nombre': defaults.get('segundo_nombre'),
                    'primer_apellido': defaults.get('primer_apellido'),
                    'segundo_apellido': defaults.get('segundo_apellido'),
                })
            elif tipo_interesado_obj:  # Persona Jurídica
                search_fields['razon_social'] = defaults.get('razon_social')
            
            # Construir nombre completo
            nombre_completo = f"{defaults.get('primer_nombre', '')} {defaults.get('segundo_nombre', '')} {defaults.get('primer_apellido', '')} {defaults.get('segundo_apellido', '')}".strip()
            if not nombre_completo:
                nombre_completo = defaults.get('razon_social')
            defaults['nombre'] = nombre_completo
            
            # Identificar si este interesado corresponde a uno existente en el predio
            # Se identifica por tipo_documento + numero_documento
            tipo_doc_id = tipo_documento.id if hasattr(tipo_documento, 'id') else tipo_documento
            identificador_request = (
                tipo_doc_id,
                numero_documento or '',
            )
            
            relacion_existente_en_predio = relaciones_por_identificador.get(identificador_request)
            
            # Buscar si el interesado ya existe en la base de datos
            try:
                interesado_existente = Interesado.objects.get(**search_fields)
                
                # Verificar si el interesado está asociado a otros predios (además de este)
                otras_relaciones = InteresadoPredio.objects.filter(
                    interesado=interesado_existente
                ).exclude(predio=predio)
                
                if otras_relaciones.exists():
                    # El interesado está asociado a otro predio: crear un nuevo registro
                    interesado_nuevo = Interesado.objects.create(**defaults)
                    # Crear relación con el nuevo interesado
                    relacion_nueva = InteresadoPredio.objects.create(
                        interesado=interesado_nuevo,
                        predio=predio
                    )
                    nuevos_interesados_ids.add(interesado_nuevo.id)
                    
                    # Si había una relación antigua en este predio con el mismo identificador, marcarla para eliminación
                    if relacion_existente_en_predio:
                        relaciones_a_eliminar_por_reemplazo.append(relacion_existente_en_predio)
                else:
                    # El interesado no está asociado a otro predio: actualizar su información
                    for key, value in defaults.items():
                        setattr(interesado_existente, key, value)
                    interesado_existente.save()
                    # Crear o mantener la relación
                    relacion, created = InteresadoPredio.objects.get_or_create(
                        interesado=interesado_existente,
                        predio=predio
                    )
                    nuevos_interesados_ids.add(interesado_existente.id)
                    
            except Interesado.DoesNotExist:
                # El interesado no existe: crear uno nuevo
                interesado_nuevo = Interesado.objects.create(**defaults)
                relacion_nueva = InteresadoPredio.objects.create(
                    interesado=interesado_nuevo,
                    predio=predio
                )
                nuevos_interesados_ids.add(interesado_nuevo.id)
                
                # Si había una relación antigua en este predio con el mismo identificador, marcarla para eliminación
                if relacion_existente_en_predio:
                    relaciones_a_eliminar_por_reemplazo.append(relacion_existente_en_predio)
        
        # Eliminar relaciones que fueron reemplazadas (si no tienen historial)
        if relaciones_a_eliminar_por_reemplazo:
            relaciones_reemplazo_ids = [rel.id for rel in relaciones_a_eliminar_por_reemplazo]
            relaciones_reemplazo_con_historial = Historial_predio.objects.filter(
                interesado_predio_id__in=relaciones_reemplazo_ids
            ).values_list('interesado_predio_id', flat=True).distinct()
            
            relaciones_reemplazo_sin_historial = [
                rel for rel in relaciones_a_eliminar_por_reemplazo 
                if rel.id not in relaciones_reemplazo_con_historial
            ]
            if relaciones_reemplazo_sin_historial:
                InteresadoPredio.objects.filter(
                    id__in=[rel.id for rel in relaciones_reemplazo_sin_historial]
                ).delete()
        
        # Refrescar las relaciones actuales para obtener el estado más reciente
        # (después de haber creado/actualizado las nuevas relaciones)
        relaciones_actuales_refrescadas = InteresadoPredio.objects.filter(predio=predio)
        
        # Eliminar relaciones con interesados que ya no están en la lista del request
        relaciones_a_eliminar = relaciones_actuales_refrescadas.exclude(interesado_id__in=nuevos_interesados_ids)
        
        # Excluir las relaciones que ya fueron procesadas en el reemplazo
        relaciones_reemplazo_ids = [rel.id for rel in relaciones_a_eliminar_por_reemplazo]
        relaciones_a_eliminar = relaciones_a_eliminar.exclude(id__in=relaciones_reemplazo_ids)
        
        # Log para debugging
        logger.info(
            f"Predio {predio.id}: Nuevos interesados IDs: {nuevos_interesados_ids}, "
            f"Relaciones a eliminar: {list(relaciones_a_eliminar.values_list('id', flat=True))}"
        )
        
        # Obtener el PredioTramitecatastral para eliminar el historial del predio en novedad
        predio_tramite = PredioTramitecatastral.objects.filter(
            predio=predio,
            tramite_catastral=tramite
        ).first()
        
        # Eliminar relaciones que ya no están en el request
        if relaciones_a_eliminar.exists():
            for relacion in relaciones_a_eliminar:
                interesado = relacion.interesado
                relacion_id = relacion.id
                
                # 1. Eliminar el historial del predio en novedad para esta relación
                if predio_tramite:
                    historial_a_eliminar = Historial_predio.objects.filter(
                        predio=predio,
                        interesado_predio=relacion,
                        predio_tramitecatastral=predio_tramite
                    )
                    if historial_a_eliminar.exists():
                        historial_a_eliminar.delete()
                        logger.info(
                            f"Se eliminó el historial del predio {predio.id} para la relación "
                            f"InteresadoPredio {relacion_id}"
                        )
                
                # 2. Verificar si el interesado está asociado a otros predios (ANTES de eliminar)
                otras_relaciones = InteresadoPredio.objects.filter(
                    interesado=interesado
                ).exclude(predio=predio)
                
                # 3. Verificar si hay historial en otros trámites que referencie este interesado (ANTES de eliminar)
                # Buscar todas las relaciones InteresadoPredio de este interesado para verificar historial
                todas_las_relaciones_interesado = InteresadoPredio.objects.filter(interesado=interesado)
                historial_otros_tramites = Historial_predio.objects.filter(
                    interesado_predio__in=todas_las_relaciones_interesado
                ).exclude(predio=predio)
                
                # 4. Eliminar la relación InteresadoPredio
                relacion.delete()
                logger.info(
                    f"Se eliminó la relación InteresadoPredio {relacion_id} del predio {predio.id}"
                )
                
                # 5. Si el interesado NO está asociado a otro predio y NO tiene historial en otros trámites,
                # eliminar también el registro Interesado
                if not otras_relaciones.exists() and not historial_otros_tramites.exists():
                    interesado_id = interesado.id
                    interesado.delete()
                    logger.info(
                        f"Se eliminó el registro Interesado {interesado_id} porque no está "
                        f"asociado a otros predios ni tiene historial en otros trámites"
                    )
                elif otras_relaciones.exists():
                    logger.info(
                        f"Se mantuvo el registro Interesado {interesado.id} porque está "
                        f"asociado a otros predios"
                    )
                elif historial_otros_tramites.exists():
                    logger.info(
                        f"Se mantuvo el registro Interesado {interesado.id} porque tiene "
                        f"historial en otros trámites"
                    )
        
        # Crear registros en Historial_predio para los interesados actualizados/creados
        self._crear_historial_interesados(predio, tramite)
    
    def _crear_historial_interesados(self, predio, tramite):
        """
        Actualiza los registros en Historial_predio para los interesados del predio.
        - Conserva los registros existentes de predio_unidadespacial (sin modificar)
        - Elimina los registros de historial de interesados que ya no existen
        - Crea solo nuevos registros para los nuevos interesados que no tienen historial
        
        IMPORTANTE: Los registros de historial deben ser SEPARADOS:
        - Un registro para cada interesado_predio (con predio_unidadespacial=None)
        - Un registro para cada predio_unidadespacial (con interesado_predio=None)
        NO se pueden combinar ambos en un mismo registro.
        """
        # Obtener el PredioTramitecatastral asociado al predio y trámite
        predio_tramite = PredioTramitecatastral.objects.filter(
            predio=predio,
            tramite_catastral=tramite
        ).first()
        
        if not predio_tramite:
            logger.warning(
                f"No se encontró PredioTramitecatastral para predio {predio.id} y trámite {tramite.id}. "
                f"No se crearán registros de historial."
            )
            return
        
        # Obtener las relaciones actuales de InteresadoPredio del predio (después de la actualización)
        relaciones_interesados_actuales = InteresadoPredio.objects.filter(predio=predio)
        
        # Obtener los registros de historial existentes para este predio y trámite
        historial_existente = Historial_predio.objects.filter(
            predio=predio,
            predio_tramitecatastral=predio_tramite
        )
        
        # Separar registros existentes: los de unidades espaciales (que se conservan) y los de interesados
        historial_unidades_existentes = historial_existente.filter(
            predio_unidadespacial__isnull=False,
            interesado_predio__isnull=True
        )
        
        historial_interesados_existentes = historial_existente.filter(
            interesado_predio__isnull=False,
            predio_unidadespacial__isnull=True
        )
        
        # Obtener los IDs de interesados que ya tienen historial
        interesados_con_historial = historial_interesados_existentes.values_list(
            'interesado_predio_id', flat=True
        ).distinct()
        
        # Identificar relaciones de interesados que ya no existen (se eliminaron)
        relaciones_interesados_actuales_ids = set(relaciones_interesados_actuales.values_list('id', flat=True))
        relaciones_eliminadas = historial_interesados_existentes.exclude(
            interesado_predio_id__in=relaciones_interesados_actuales_ids
        )
        
        # Eliminar registros de historial de interesados que ya no existen
        if relaciones_eliminadas.exists():
            relaciones_eliminadas.delete()
            logger.info(
                f"Se eliminaron {relaciones_eliminadas.count()} registros de historial "
                f"de interesados que ya no existen para el predio {predio.id}"
            )
        
        # Crear registros de historial solo para los nuevos interesados (que no tienen historial)
        nuevos_registros_historial = []
        
        for interesado_predio in relaciones_interesados_actuales:
            # Solo crear historial si este interesado_predio no tiene historial existente
            if interesado_predio.id not in interesados_con_historial:
                nuevos_registros_historial.append(
                    Historial_predio(
                        predio=predio,
                        interesado_predio=interesado_predio,
                        predio_unidadespacial=None,  # IMPORTANTE: separado, no combinado
                        predio_tramitecatastral=predio_tramite
                    )
                )
        
        # Crear los nuevos registros de historial
        if nuevos_registros_historial:
            Historial_predio.objects.bulk_create(nuevos_registros_historial)
            logger.info(
                f"Se crearon {len(nuevos_registros_historial)} nuevos registros en Historial_predio "
                f"para interesados del predio {predio.id} y trámite {tramite.id}"
            )
        
        # Log de resumen
        logger.info(
            f"Historial actualizado para predio {predio.id}: "
            f"Conservados {historial_unidades_existentes.count()} registros de unidades espaciales, "
            f"Conservados {historial_interesados_existentes.filter(interesado_predio_id__in=relaciones_interesados_actuales_ids).count()} registros de interesados existentes, "
            f"Creados {len(nuevos_registros_historial)} nuevos registros de interesados"
        )
    
    def _actualizar_fuente_administrativa(self, predio, fuente_data, tramite):
        """
        Actualiza la fuente administrativa del predio.
        Si ya existe una relación, la elimina y crea una nueva.
        """
        from registro.apps.catastro.models import PredioFuenteadministrativa
        
        # Validar que la fuente no esté vacía
        interesado_helper = IncorporarInteresadoSerializer()
        if interesado_helper.es_fuente_administrativa_vacia(fuente_data):
            logger.warning(f"Se omitió la fuente administrativa para el predio {predio.id} porque está vacía.")
            return
        
        # Eliminar relaciones existentes de fuente administrativa con este predio
        PredioFuenteadministrativa.objects.filter(predio=predio).delete()
        
        # Crear nueva fuente administrativa
        instancia_fuente = interesado_helper.create_fuenteadministrativa(fuente_data)
        if instancia_fuente:
            # Crear relación predio-fuente administrativa
            interesado_helper.create_Predio_fuenteadministrativa({
                'predio': predio,
                'fuenteadministrativa': instancia_fuente
            })

class PredioDetalleTramiteAPIView(APIView):
    """
    Vista para visualizar la información de un predio con una lógica de estado específica para trámites.
    - Si el predio tiene una asignación en estado 'Pendiente', muestra el predio activo.
    - Si la asignación está en 'Revision' o 'En proceso', muestra el/los predio(s) 'Novedad' asociados.
    - En cualquier otro caso, o si no hay asignación, muestra el predio activo.
    """
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        numero_predial = request.query_params.get('numero_predial_nacional')
        if not numero_predial:
            return Response(
                {"error": "Debe proporcionar el parámetro 'numero_predial_nacional'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Siempre partimos del predio activo (estado__t_id=105)
            predio_activo = Predio.objects.get(numero_predial_nacional=numero_predial, estado__t_id=105)
        except Predio.DoesNotExist:
            return Response(
                {"error": f"No se encontró un predio 'Activo' con el número predial {numero_predial}."},
                status=status.HTTP_404_NOT_FOUND
            )
        except Predio.MultipleObjectsReturned:
             return Response(
                {"error": f"Error de integridad: Existe más de un predio 'Activo' con el NPN {numero_predial}. Por favor, contacte al administrador."},
                status=status.HTTP_409_CONFLICT
            )

        # Buscar la asignación más reciente para este predio que no esté finalizada
        asignacion = RadicadoPredioAsignado.objects.filter(
            predio=predio_activo
        ).exclude(estado_asignacion__t_id=3).order_by('-id').first()


        if not asignacion:
            # Si no hay asignación, mostrar el predio activo
            serializer = PredioSerializer(predio_activo)
            return Response(serializer.data)

        estado_asignacion_id = asignacion.estado_asignacion.t_id

        # Estado 'Revision' (t_id=2) o 'En proceso' (t_id=4)
        if estado_asignacion_id in [2, 4]:
            try:
                # Buscar el trámite asociado a la asignación
                tramite = TramiteCatastral.objects.get(radicado_asignado=asignacion)
                
                # Buscar los predios 'Novedad' (estado__t_id=106) a través del historial
                predios_novedad_ids = Historial_predio.objects.filter(
                    predio_tramitecatastral__tramite_catastral=tramite
                ).values_list('predio_id', flat=True).distinct()
                
                predios_novedad = Predio.objects.filter(
                    id__in=predios_novedad_ids,
                    estado__t_id=106
                )

                if predios_novedad.exists():
                    # Si se encuentran predios novedad, se serializan y se devuelven
                    serializer = PredioSerializer(predios_novedad, many=True)
                    return Response(serializer.data)
                else:
                    # Caso de borde: el trámite está en revisión/en proceso pero no hay predios novedad.
                    serializer = PredioSerializer(predio_activo)
                    data = serializer.data
                    data['advertencia'] = f"El trámite está en estado '{asignacion.estado_asignacion.ilicode}', pero no se encontraron predios 'Novedad' asociados. Mostrando predio activo."
                    return Response(data, status=status.HTTP_200_OK)

            except TramiteCatastral.DoesNotExist:
                # No se ha iniciado el trámite formalmente, mostrar predio activo
                serializer = PredioSerializer(predio_activo)
                data = serializer.data
                data['advertencia'] = f"La asignación está en estado '{asignacion.estado_asignacion.ilicode}', pero aún no se ha creado un trámite catastral. Mostrando predio activo."
                return Response(data)

        # Para 'Pendiente' (t_id=1) o cualquier otro estado, mostrar el predio activo
        serializer = PredioSerializer(predio_activo)
        return Response(serializer.data)
