from rest_framework.serializers import ModelSerializer, ValidationError
from datetime import datetime

# MODELS 
from registro.apps.catastro.models import (
    TramiteCatastral, 
    PredioTramitecatastral
)


class ResolucionModelSerializer(ModelSerializer):
    class Meta:
        model = TramiteCatastral
        fields = '__all__'
        depth = 1


class IncorporacionGestionSerializer:
    """
    Clase para manejar la gestión de incorporaciones catastrales,
    incluyendo resoluciones y trámites de predios.
    """

    def asignar_fecha_inscripcion_catastral(self, predio=None, data_prediotramitecatastral=None, validar=False):
        """
        Asigna la fecha de inscripción catastral procesando diferentes formatos de fecha.
        
        Args:
            predio (dict): Datos del predio con posible fecha_inscripcion
            data_prediotramitecatastral (dict): Diccionario donde se asignará la fecha procesada
            validar (bool): Si True, valida que la fecha sea obligatoria
            
        Returns:
            bool: True si se asignó una fecha, False si no había fecha
            
        Raises:
            ValidationError: Si la validación falla o el formato de fecha es incorrecto
        """
        if not predio or not data_prediotramitecatastral:
            raise ValidationError('Los parámetros predio y data_prediotramitecatastral son obligatorios.')

        if validar and not predio.get('fecha_inscripcion'):
            raise ValidationError('La fecha de inscripción es obligatoria.')

        fecha_str = predio.get('fecha_inscripcion')
        if not fecha_str:
            return False

        npn = predio.get('numero_predial_nacional')
        
        try:
            # Solo acepta formato YYYY-MM-DD (ISO estándar)
            fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
            data_prediotramitecatastral['fecha_inscripcion'] = fecha
            return True
        except ValueError:
            raise ValidationError(
                f'La fecha de inscripción "{fecha_str}" no está en el formato correcto '
                f'para el NPN {npn}. Formato requerido: YYYY-MM-DD (ejemplo: 2024-12-25)'
            )

    def create_resolucion(self, data_resolucion=None):
        """
        Crea una nueva resolución (TramiteCatastral).
        
        Args:
            data_resolucion (dict): Datos para crear la resolución
            
        Returns:
            TramiteCatastral: Instancia creada
            
        Raises:
            ValidationError: Si los datos no son válidos
        """
        if not data_resolucion:
            raise ValidationError('Los datos de la resolución son obligatorios.')
        
        serializer = ResolucionModelSerializer(data=data_resolucion)
        serializer.is_valid(raise_exception=True)
        
        # Usar los datos validados del serializer
        instance_resolucion = serializer.save()
        return instance_resolucion

    def create_resolucion_predio(self, data_predio_tramite=None):
        """
        Crea una relación entre predio y trámite catastral.
        
        Args:
            data_predio_tramite (dict): Datos para crear la relación predio-trámite
            
        Returns:
            PredioTramitecatastral: Instancia creada
            
        Raises:
            ValidationError: Si los datos son inválidos
        """
        if not data_predio_tramite:
            raise ValidationError('Los datos del predio-trámite son obligatorios.')
        
        try:
            instance_resolucion_predio = PredioTramitecatastral(**data_predio_tramite)
            instance_resolucion_predio.full_clean()  # Validar antes de guardar
            instance_resolucion_predio.save()
            return instance_resolucion_predio
        except Exception as e:
            raise ValidationError(f'Error al crear la relación predio-trámite: {str(e)}')

    def create_fuenteadministrativa(self, data_fuente=None):
        """
        Crea una nueva fuente administrativa.
        
        Args:
            data_fuente (dict): Datos para crear la fuente administrativa
            
        Returns:
            ColFuenteadministrativa: Instancia creada
            
        Raises:
            ValidationError: Si los datos no son válidos o los dominios no existen
        """
        if not data_fuente:
            raise ValidationError('Los datos de la fuente administrativa son obligatorios.')
        
        # Lógica para crear la fuente administrativa
        try:
            # Corregido: buscar dominios por t_id en lugar de ilicode
            tipo_id = data_fuente.get('tipo')
            ente_emisor_id = data_fuente.get('ente_emisor')
            estado_disponibilidad_id = data_fuente.get('estado_disponibilidad')
            
            instancia_tipo = ColFuenteadministrativatipo.objects.get(t_id=tipo_id)
            instancia_ente_emisor = EnteEmisortipo.objects.get(t_id=ente_emisor_id)
            instancia_estado_disponibilidad = ColEstadodisponibilidadtipo.objects.get(t_id=estado_disponibilidad_id)

            data_to_create = {
                'tipo': instancia_tipo.pk,
                'ente_emisor': instancia_ente_emisor.pk,
                'estado_disponibilidad': instancia_estado_disponibilidad.pk,
                'oficina_origen': data_fuente.get('oficina_origen'),
                'fecha_documento_fuente': data_fuente.get('fecha_documento_fuente'),
                'numero_documento': data_fuente.get('numero_documento')
            }
            
            serializer = FuenteAdministrativaSerializer(data=data_to_create)
            if serializer.is_valid(raise_exception=True):
                return serializer.save()
                
        except (ColFuenteadministrativatipo.DoesNotExist, EnteEmisortipo.DoesNotExist, ColEstadodisponibilidadtipo.DoesNotExist) as e:
            raise ValidationError(f"Error en los datos de la fuente administrativa: ID de dominio no válido. Detalles: {e}")
        except Exception as e:
            raise ValidationError(f"Error al crear la fuente administrativa: {str(e)}")

    def create_Predio_fuenteadministrativa(self, data):
        """
        Crea la relación entre un predio y una fuente administrativa.
        
        Args:
            data (dict): Datos para crear la relación predio-fuente administrativa
            
        Returns:
            PredioFuenteadministrativa: Instancia creada
            
        Raises:
            ValidationError: Si los datos son inválidos
        """
        if not data:
            raise ValidationError('Los datos del predio-fuente administrativa son obligatorios.')
        
        try:
            instance_predio_fuente = PredioFuenteadministrativa(**data)
            instance_predio_fuente.full_clean()  # Validar antes de guardar
            instance_predio_fuente.save()
            return instance_predio_fuente
        except Exception as e:
            raise ValidationError(f'Error al crear la relación predio-fuente administrativa: {str(e)}')