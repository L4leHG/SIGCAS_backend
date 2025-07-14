from rest_framework.serializers import ValidationError

from copy import copy
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from datetime import datetime

# MODELS 
from registro.apps.catastro.models import (
    
    InteresadoPredio, Predio, PredioUnidadespacial, Terreno, CaracteristicasUnidadconstruccion, EstructuraAvaluo,
    TramiteCatastral, PredioTramitecatastral, Historial_predio, 
    CrMutaciontipo, CrEstadotipo, 
    )
class BaseSerializer():

    def __init__(self):
        """
        Inicializa los atributos de la instancia para evitar el estado compartido entre diferentes usos del serializador.
        """
        self.predio_novedad = []
        self.nuevo_predio = []
        self.data_resolucion_predio = {
            'predio': None, 
            'tramite_catastral': None,
            'radicado_asignado': None
        }

    def validate_resolucion(self, predio):
        numero_resolucion = predio.get('resolucion_repone')
        vigencia_repone = predio.get('vigencia_repone')
        try:
            # CONSULTAMOS LA REOSLUCION POR FECHA, NUMERO DE RESOLUCION Y QUE LA FECHA DE VIDA INICIO NO SEA NULA
            # CORREGIDO: 'fecha_vida_inicio__isnull' a 'comienzo_vida_util_version__isnull'
            instace_resolucion = TramiteCatastral.objects.get(
                numero_resolucion=numero_resolucion, 
                fecha_resolucion__year=vigencia_repone, 
                comienzo_vida_util_version__isnull=False
            )
        except ObjectDoesNotExist:
            # SI LA RESOLUCION NO EXISTE ENVIA EL MENSAJE
            raise ValidationError(f"La resolución con el número {numero_resolucion} y vigencia {vigencia_repone} no existe o está en novedad.")
        except MultipleObjectsReturned:
            # SI SE REGRESAN MULTIPLES RESULTADOS SE ENVIA EL MENSAJE DE ERROR
            raise ValidationError(f"La resolución {numero_resolucion} tiene más de un registro con la misma vigencia.")
        
        return instace_resolucion

    def get_resolucion(self,mutacion = None, instance_resolucion = None, mutacion_id = None):
        """
        Configura los datos de resolución usando la información ya disponible.
        
        Args:
            mutacion: Datos de la mutación del request (no se usa para búsquedas)
            instance_resolucion: Instancia de TramiteCatastral ya creada
            mutacion_id: ID legacy (no se usa)
        """
        # Usar la instancia de TramiteCatastral que ya está creada
        if not instance_resolucion:
            raise ValidationError("Se requiere una instancia de TramiteCatastral válida")
            
        self.data_resolucion_predio['tramite_catastral'] = instance_resolucion
        self.data_resolucion_predio['radicado_asignado'] = instance_resolucion.radicado_asignado

    def crear_registros_historial_predio(self, instance_predio, interesado_predio, 
                                        instance_unidadespacial, instance_resolucion_predio,
                                        es_mutacion_tercera=False):
        """
        Crea los registros en la tabla Historial_predio, asociando el predio con sus
        interesados y unidades espaciales (terrenos, unidades constructivas).
        """
        # Preparar los datos base para crear los registros históricos
        data_resolucion_historica = {
            'predio': instance_predio,
            'interesado_predio': interesado_predio,
            'predio_unidadespacial': instance_unidadespacial,
            'predio_tramitecatastral': instance_resolucion_predio,
            'es_mutacion_tercera': es_mutacion_tercera
        }

        # Llamar al método que crea los registros en la tabla Historial_predio
        self.create_resolucion_historica(data_resolucion_historica)
        
    def get_terrenos_unidades_alfa_historica(self, 
            predio = None, 
            instance_predio = None, 
            instance_predio_actual = None, 
            instance_predio_novedad = None,
            instance_resolucion_predio=None,
            validar_unidad=False,
            validar_interesados=True,
            archivo_geometria=None
        ):
        
        npn = predio.get('npn')
        terrenos = predio.get('terrenos')
        unidades = predio.get('unidades')
        eliminadas = predio.get('eliminar_unidad')
        mutacion = predio.get('mutacion')

        instance_terreno_geo = self.incorporar_terreno_geo(predio, instance_predio, instance_predio_actual)
        #INCORPORANDO INTERESADO
        interesado_predio = self.incorporar_interesados(
            predio=predio, 
            instance_predio=instance_predio, 
            instance_predio_actual=instance_predio_actual, 
            validar=validar_interesados
        )
        

        # INCORPORAR TERRENOS
        instance_terrenos = self.incorporar_terrenos(predio, instance_predio, instance_predio_actual, instance_predio_novedad,instance_terreno_geo)
        
        #***********************************************************************************************************************************UNIDADES
        
        instance_unidades = self.incorporar_unidades(
            predio,
            instance_predio_actual,
            instance_predio_novedad,
            validar_unidad,
            archivo_geometria
        )
        
        #***********************************************************************************************************************************UNIDADESPACIAL
        data_unidadespacial = {
            'terrenos': instance_terrenos if terrenos else None,
            'unidades':instance_unidades if unidades else None, 
            'predio_novedad': instance_predio,
            'predio_novedad_dos': instance_predio_novedad,
            'predio_actual': instance_predio_actual,
            'npn': npn,
            'resolucion_predio': instance_resolucion_predio,
            'eliminar_unidad': eliminadas,
            'es_mutacion_tercera': mutacion and 'Tercera' in str(mutacion)
        }
        instance_unidadespacial = self.create_Unidadespacial(data_unidadespacial)
        
        #INCORPORAR RESOLUCION HISTORICA
        # Crear registros en Historial_predio para cada combinación
        self.crear_registros_historial_predio(
            instance_predio=instance_predio,
            interesado_predio=interesado_predio,
            instance_unidadespacial=instance_unidadespacial,
            instance_resolucion_predio=instance_resolucion_predio,
            es_mutacion_tercera=data_unidadespacial.get('es_mutacion_tercera', False)
        )
            
