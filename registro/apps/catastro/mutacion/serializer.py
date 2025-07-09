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

    def crear_registros_historial_predio(self, instance_predio=None, interesado_predio=None, 
                                       instance_unidadespacial=None, instance_resolucion_predio=None):
        """
        Crea registros en Historial_predio de forma eficiente.
        
        Args:
            instance_predio: Instancia del predio
            interesado_predio: Lista de instancias InteresadoPredio
            instance_unidadespacial: Lista de instancias PredioUnidadespacial
            instance_resolucion_predio: Instancia de PredioTramitecatastral
        """
        registros_historial = []
        
        # Convertir a listas si no lo son
        interesados = interesado_predio if isinstance(interesado_predio, list) else [interesado_predio] if interesado_predio else []
        unidades = instance_unidadespacial if isinstance(instance_unidadespacial, list) else [instance_unidadespacial] if instance_unidadespacial else []
        
        # Crear registros para cada combinación de interesado y unidad espacial
        if interesados and unidades:
            for interesado in interesados:
                for unidad in unidades:
                    registros_historial.append(Historial_predio(
                        predio=instance_predio,
                        interesado_predio=interesado,
                        predio_unidadespacial=unidad,
                        predio_tramitecatastral=instance_resolucion_predio
                    ))
        elif interesados:
            # Solo interesados, sin unidades espaciales
            for interesado in interesados:
                registros_historial.append(Historial_predio(
                    predio=instance_predio,
                    interesado_predio=interesado,
                    predio_unidadespacial=None,
                    predio_tramitecatastral=instance_resolucion_predio
                ))
        elif unidades:
            # Solo unidades espaciales, sin interesados
            for unidad in unidades:
                registros_historial.append(Historial_predio(
                    predio=instance_predio,
                    interesado_predio=None,
                    predio_unidadespacial=unidad,
                    predio_tramitecatastral=instance_resolucion_predio
                ))
        else:
            # Registro mínimo solo con predio y trámite
            registros_historial.append(Historial_predio(
                predio=instance_predio,
                interesado_predio=None,
                predio_unidadespacial=None,
                predio_tramitecatastral=instance_resolucion_predio
            ))
        
        # Crear todos los registros de una sola vez
        if registros_historial:
            Historial_predio.objects.bulk_create(registros_historial)

    def get_terrenos_unidades_alfa_historica(self, 
            predio = None, 
            instance_predio = None, 
            instance_predio_actual = None, 
            instance_predio_novedad = None,
            instance_resolucion_predio=None,
            validar_unidad = False,
            validar_interesados = False,
      
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
        
        instance_unidades = self.incorporar_unidades(
            predio=predio, 
            instance_predio_actual=instance_predio_actual,
            instance_predio_novedad=instance_predio_novedad,
            validar=validar_unidad
        )
        
        #INCORPORAR ALFA CARTO
        data_unidadespacial = {
            'terrenos': instance_terrenos if terrenos else None,
            'unidades':instance_unidades if unidades else None, 
            'predio_novedad': instance_predio,
            'predio_novedad_dos': instance_predio_novedad,
            'predio_actual': instance_predio_actual,
            'npn': npn,
            'resolucion_predio': instance_resolucion_predio,
            'eliminar_unidad': eliminadas
        }
        instance_unidadespacial = self.create_Unidadespacial(data_unidadespacial)
        
        #INCORPORAR RESOLUCION HISTORICA
        # Crear registros en Historial_predio para cada combinación
        self.crear_registros_historial_predio(
            instance_predio=instance_predio,
            interesado_predio=interesado_predio,
            instance_unidadespacial=instance_unidadespacial,
            instance_resolucion_predio=instance_resolucion_predio
        )
            
