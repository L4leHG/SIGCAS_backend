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


class IncorporarMutacionTercera(
        BaseSerializer,
        IncorporarInteresadoSerializer,
        PredioIncorporacionSerializer,
        IncorporarPredioUnidadespacial,
        IncorporacionUnidadesSerializer,
        IncorporacionTerrenoSerializer,
        IncorporacionGestionSerializer,
        IncorporacionHistorialPredioSerializer,
    ):

    def incorporar_tercera(self, mutacion=None, instance_resolucion=None, asignacion=None):
        """
        Procesa la mutación de tercera clase - Modificación de Predio Existente.
        
        Este tipo de mutación permite:
        - Modificar destinación económica del predio
        - Crear nuevas unidades constructivas
        - Eliminar todas las relaciones de unidades (booleano, no el registro físico)
        - Conservar terrenos e interesados existentes
        - Solo se puede realizar sobre predios existentes
        - Requiere radicado y analista asignado
        """
        # VALIDAR QUE TENGA PERMISOS (radicado y analista asignado)
        self.validar_permisos_mutacion(mutacion)
        
        # GENERAMOS LA MUTACION Y RESOLUCION
        self.get_resolucion(mutacion, instance_resolucion, 16)

        for predio in mutacion['predios']:
            # El NPN de origen se toma de la asignación para asegurar consistencia
            numero_predial_nacional = asignacion.predio.numero_predial_nacional if asignacion and asignacion.predio else predio.get('numero_predial_nacional')
            
            # >>> AÑADIR EL NPN AL DICCIONARIO DEL PREDIO <<<
            # Se asegura que el NPN del proceso esté disponible en las funciones subsecuentes.
            predio['npn'] = numero_predial_nacional

            # OBTENER INSTANCIAS DEL PREDIO
            instance_predio, instance_predio_actual = self.get_instance_predio_and_actual(numero_predial_nacional)
            
            # VALIDAR QUE EL PREDIO EXISTE (NO SE PERMITE INCORPORACION NUEVA)
            if instance_predio_actual is None:
                raise ValidationError(f'El predio {numero_predial_nacional} no existe. La mutación de tercera solo permite modificar predios existentes.')
            
            # MODIFICAR DESTINO ECONÓMICO SI SE PROPORCIONA
            if predio.get('destinacion_economica'):
                self.modificar_destino_economico_predio(predio, instance_predio)
            
            # ADICIONAR LA INSTANCIA EN RESOLUCION PREDIO
            self.data_resolucion_predio['predio'] = instance_predio
            self.data_resolucion_predio['nuevo'] = False  # Siempre es modificación
            
            # REUTILIZAR FUENTE ADMINISTRATIVA EXISTENTE
            self.reutilizar_fuente_administrativa_existente(instance_predio, instance_predio_actual)

            # INCORPORAR RESOLUCION PREDIO (PredioTramitecatastral)
            instance_resolucion_predio = self.create_resolucion_predio(self.data_resolucion_predio)
            
            # INCORPORAR AVALUOS - Copiar del predio actual
            self.incorporar_nuevos_avaluos(
                avaluos=predio.get('avaluos', []),
                instance_predio=instance_predio, 
                instance_tramitecatastral_predio=instance_resolucion_predio, 
                instance_predio_actual=instance_predio_actual
            )

            # PROCESAR MODIFICACIONES DE UNIDADES Y CONSERVAR ELEMENTOS EXISTENTES
            self.procesar_modificaciones_predio_existente(
                predio=predio,
                instance_predio=instance_predio,
                instance_predio_actual=instance_predio_actual,
                instance_resolucion_predio=instance_resolucion_predio
            )

    def validar_permisos_mutacion(self, mutacion):
        """
        Valida que la mutación tenga los permisos necesarios.
        
        Nota: Los permisos de radicado y analista ya se validan en 
        MutacionRadicadoValidationSerializer, por lo que no es necesario 
        validarlos nuevamente aquí.
        
        Args:
            mutacion (dict): Datos de la mutación
        """
        # Los permisos se validan en el serializer de entrada
        # No es necesario validar radicado y analista aquí
        pass

    def modificar_destino_economico_predio(self, predio, instance_predio):
        """
        Modifica el destino económico del predio.
        
        Args:
            predio (dict): Datos del predio con el nuevo destino económico
            instance_predio (Predio): Instancia del predio a modificar
        """
        nuevo_destino_id = predio.get('destinacion_economica')
        if nuevo_destino_id:
            try:
                from registro.apps.catastro.models import CrDestinacioneconomicatipo
                instancia_destinacion = CrDestinacioneconomicatipo.objects.get(t_id=nuevo_destino_id)
                instance_predio.destinacion_economica = instancia_destinacion
                instance_predio.save()
            except CrDestinacioneconomicatipo.DoesNotExist:
                raise ValidationError(f'El destino económico con ID {nuevo_destino_id} no existe.')

    def procesar_modificaciones_predio_existente(self, predio, instance_predio, instance_predio_actual, instance_resolucion_predio):
        """
        Procesa las modificaciones de un predio existente.
        
                 - Conserva terrenos e interesados existentes
         - Permite crear nuevas unidades
         - Permite eliminar TODAS las relaciones de unidades existentes (booleano)
         - Crea copias de las relaciones del predio actual
        
        Args:
            predio (dict): Datos del predio con las modificaciones
            instance_predio (Predio): Instancia del nuevo predio
            instance_predio_actual (Predio): Instancia del predio actual
            instance_resolucion_predio (PredioTramitecatastral): Resolución del predio
        """
        # Preparar datos para conservar elementos existentes
        predio_procesado = predio.copy()
        
        # CONSERVAR TERRENOS EXISTENTES (no se modifican en mutación tercera)
        predio_procesado['terrenos'] = None  # Indica que se conserven los existentes
        predio_procesado['geometry_terreno'] = None  # No se modifica geometría
        
        # CONSERVAR INTERESADOS EXISTENTES (no se modifican en mutación tercera)
        if 'interesados' not in predio_procesado or not predio_procesado.get('interesados'):
            predio_procesado['interesados'] = None  # Indica que se conserven los existentes
        
        # PROCESAR UNIDADES SEGÚN LO ENVIADO
        unidades_nuevas = predio.get('unidades', [])
        eliminar_unidades = predio.get('unidades_eliminar', False)
        
        # PROCESAR ELIMINACION DE RELACIONES DE UNIDADES (ANTES DE AGREGAR NUEVAS)
        if eliminar_unidades:
            # Para eliminar, simplemente pasamos una lista vacía.
            # La lógica subyacente no creará ninguna relación de unidad.
            predio_procesado['unidades'] = []
        elif unidades_nuevas:
            # Si se envían unidades nuevas, las agregamos para su procesamiento.
            predio_procesado['unidades'] = unidades_nuevas
        else:
            # Si no se especifican nuevas unidades ni se eliminan,
            # se conservan las existentes (se copian las relaciones).
            predio_procesado['unidades'] = None
        
        # Se agrega el tipo de mutación para que la lógica subyacente 
        # pueda identificarla y crear las copias de las relaciones del terreno.
        predio_procesado['mutacion'] = 'Tercera'
        
        # EJECUTAR PROCESO DE INCORPORACION CONSERVANDO ELEMENTOS EXISTENTES
        self.get_terrenos_unidades_alfa_historica(
            predio=predio_procesado, 
            instance_predio=instance_predio, 
            instance_predio_actual=instance_predio_actual, 
            instance_predio_novedad=None,
            instance_resolucion_predio=instance_resolucion_predio,
            validar_unidad=False,  # Las unidades son opcionales
            validar_interesados=False  # Los interesados se conservan del predio actual
        )

    def procesar_eliminacion_relaciones_unidades(self, instance_predio_actual):
        """
        Elimina TODAS las relaciones de unidades del predio actual, NO el registro físico de las unidades.
        
        Elimina:
        1. Las relaciones en PredioUnidadespacial
        2. Los registros en Historial_predio que tengan esas relaciones
        
        Las unidades constructivas permanecen intactas en la base de datos.
        
        Args:
            instance_predio_actual (Predio): Instancia del predio actual
        """
        from registro.apps.catastro.models import PredioUnidadespacial, Historial_predio
        
        # Obtener las relaciones de unidades constructivas del predio actual
        relaciones_unidades = PredioUnidadespacial.objects.filter(
            predio=instance_predio_actual,
            unidadconstruccion__isnull=False
        )
        
        # Eliminar registros en Historial_predio que tengan estas relaciones
        for relacion in relaciones_unidades:
            Historial_predio.objects.filter(
                predio_unidadespacial=relacion
            ).delete()
        
        # Eliminar las relaciones en PredioUnidadespacial
        unidades_eliminadas = relaciones_unidades.delete()
        
        return unidades_eliminadas

    def reutilizar_fuente_administrativa_existente(self, instance_predio, instance_predio_actual):
        """
        Reutiliza la fuente administrativa existente del predio actual.
        
        Args:
            instance_predio (Predio): Instancia del nuevo predio
            instance_predio_actual (Predio): Instancia del predio actual
        """
        from registro.apps.catastro.models import PredioFuenteadministrativa
        
        # Buscar la fuente administrativa existente del predio actual
        fuente_predio_actual = PredioFuenteadministrativa.objects.filter(
            predio=instance_predio_actual
        ).first()
        
        if fuente_predio_actual:
            # Crear nueva relación con la misma fuente administrativa
            self.create_Predio_fuenteadministrativa({
                'predio': instance_predio,
                'fuenteadministrativa': fuente_predio_actual.fuenteadministrativa
            })
