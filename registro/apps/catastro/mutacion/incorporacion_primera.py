from registro.apps.catastro.mutacion.serializer import BaseSerializer

# FUNCIONES DE INCORPORACION 
from registro.apps.catastro.incorporacion.incorporar_predio_unidadespacial import IncorporarPredioUnidadespacial
from registro.apps.catastro.incorporacion.incorporar_interesado import IncorporarInteresadoSerializer
from registro.apps.catastro.incorporacion.incorporar_predio import PredioIncorporacionSerializer
from registro.apps.catastro.incorporacion.incorporar_historial_predio import IncorporacionHistorialPredioSerializer
from registro.apps.catastro.incorporacion.incorporar_gestion import IncorporacionGestionSerializer
from registro.apps.catastro.incorporacion.incorporar_terreno import IncorporacionTerrenoSerializer
from registro.apps.catastro.incorporacion.incorporar_unidades import IncorporacionUnidadesSerializer

from rest_framework.serializers import ValidationError
from registro.apps.catastro.models import Terreno, FuenteAdministrativa, PredioFuenteadministrativa
from datetime import datetime


class IncorporarMutacionPrimera(
        BaseSerializer,
        IncorporarInteresadoSerializer,
        PredioIncorporacionSerializer,
        IncorporarPredioUnidadespacial,
        IncorporacionUnidadesSerializer,
        IncorporacionTerrenoSerializer,
        IncorporacionGestionSerializer,
        IncorporacionHistorialPredioSerializer,
    ):

    def get_fecha_inscripcion_desde_fuente_administrativa(self, predio, instance_predio_actual=None):
        """
        Obtiene la fecha de inscripción catastral desde la fuente administrativa.
        
        Proceso:
        1. Si hay información de fuente administrativa nueva, crearla/buscarla
        2. Si no hay nueva, buscar la fuente administrativa existente del predio actual
        3. Retorna la fecha_documento_fuente para usar como fecha_inscripcion
        
        Args:
            predio (dict): Datos del predio con posible información de fuente administrativa
            instance_predio_actual (Predio): Instancia del predio actual para buscar fuente existente
            
        Returns:
            date: Fecha de inscripción catastral o None si no se encuentra
        """
        npn = predio.get('npn')
        
        # Prioridad 1: Si hay información de fuente administrativa nueva en el predio
        if predio.get('fuente_administrativa'):
            try:
                fuente_data = predio.get('fuente_administrativa')
                instancia_fuente_admin = self.create_fuenteadministrativa(fuente_data)
                
                if instancia_fuente_admin and instancia_fuente_admin.fecha_documento_fuente:
                    return instancia_fuente_admin.fecha_documento_fuente
                    
            except Exception as e:
                # Si hay error al crear la fuente, continuar con el siguiente método
                pass
        
        # Prioridad 2: Buscar la fuente administrativa existente del predio actual
        if instance_predio_actual:
            try:
                # Buscar la fuente administrativa más reciente relacionada con el predio actual
                relacion_fuente = PredioFuenteadministrativa.objects.filter(
                    predio=instance_predio_actual
                ).select_related('fuenteadministrativa').order_by('-id').first()
                
                if relacion_fuente and relacion_fuente.fuenteadministrativa.fecha_documento_fuente:
                    return relacion_fuente.fuenteadministrativa.fecha_documento_fuente
                    
            except Exception as e:
                # Si hay error al buscar la fuente existente, continuar
                pass
        
        # Si no se encuentra ninguna fecha, retornar None
        return None

    def incorporar_primera(self, mutacion=None, instance_resolucion=None, asignacion=None):
        """
        Procesa la mutación de primera clase - Cambio de Propietario.
        
        Este tipo de mutación:
        - Permite actualizar o incorporar nuevos propietarios
        - Conserva los terrenos y unidades existentes del predio
        - Permite modificar la fuente administrativa
        - Requiere interesados obligatorios
        """
        # GENERAMOS LA MUTACION Y RESOLUCION
        self.get_resolucion(mutacion, instance_resolucion, 15)

        for predio in mutacion['predios']:
            # El NPN de origen se toma de la asignación para asegurar consistencia
            npn = asignacion.predio.numero_predial_nacional if asignacion and asignacion.predio else predio.get('npn')
            
            # OBTENER INSTANCIAS DEL PREDIO
            instance_predio, instance_predio_actual = self.get_instance_predio_and_actual(npn)
            
            # ADICIONAR LA INSTANCIA EN RESOLUCION PREDIO
            self.data_resolucion_predio['predio'] = instance_predio

            # GESTIONAR FUENTE ADMINISTRATIVA
            fuente_administrativa = predio.get('fuente_administrativa')
            
            if fuente_administrativa and not self.es_fuente_administrativa_vacia(fuente_administrativa):
                # CASO 1: Se proporciona fuente administrativa nueva con datos válidos
                instancia_fuente_admin = self.create_fuenteadministrativa(fuente_administrativa)
                if instancia_fuente_admin:
                    # CREAR RELACION PREDIO-FUENTE ADMINISTRATIVA
                    self.create_Predio_fuenteadministrativa({
                        'predio': instance_predio,
                        'fuenteadministrativa': instancia_fuente_admin
                    })
            else:
                # CASO 2: No se proporciona fuente administrativa o está vacía - reutilizar la existente
                self.reutilizar_fuente_administrativa_existente(instance_predio, instance_predio_actual)

            # INCORPORAR RESOLUCION PREDIO (PredioTramitecatastral)
            instance_resolucion_predio = self.create_resolucion_predio(self.data_resolucion_predio)
            
            # INCORPORAR AVALUOS - Copiar del predio actual
            self.incorporar_nuevos_avaluos(
                avaluos=None,  # No hay avalúos nuevos
                instance_predio=instance_predio, 
                instance_tramitecatastral_predio=instance_resolucion_predio, 
                instance_predio_actual=instance_predio_actual
            )

            # VALIDAR QUE EXISTAN INTERESADOS PARA CAMBIO DE PROPIETARIO
            if not predio.get('interesados'):
                raise ValidationError(f'No se registraron propietarios para el predio {npn}. Los interesados son obligatorios para cambio de propietario.')
            
            # --- LÓGICA DE INCORPORACIÓN EXPLÍCITA PARA MUTACIÓN PRIMERA ---

            # 1. CONSERVAR Y RELACIONAR GEOMETRÍA (TERRENO Y UNIDADES)
            instance_predio, unidades_espaciales_creadas = self.conservar_y_relacionar_geometria(instance_predio, instance_predio_actual)

            # 2. INCORPORAR INTERESADOS (NUEVOS PROPIETARIOS)
            interesados_predio_creados = self.incorporar_interesados(
                predio=predio,
                instance_predio=instance_predio
            )

            # 3. CREAR REGISTRO EN HISTORIAL DEL PREDIO
            self.crear_registros_historial_predio(
                instance_predio=instance_predio,
                interesado_predio=interesados_predio_creados,
                instance_unidadespacial=unidades_espaciales_creadas,
                instance_resolucion_predio=instance_resolucion_predio,
                es_mutacion_tercera=False
            )

            # La llamada genérica get_terrenos_unidades_alfa_historica se reemplaza por las 3 llamadas explícitas de arriba.
