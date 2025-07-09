from rest_framework.serializers import ModelSerializer, ValidationError

from registro.apps.catastro.models import (
    CaracteristicasUnidadconstruccion, Unidadconstruccion, Historial_predio,
    CrUnidadconstrucciontipo, CrUsouconstipo, CrConstruccionplantatipo
)

class UnidadesSerializer(ModelSerializer):
    
    class Meta:
        model = CaracteristicasUnidadconstruccion
        fields = '__all__'
        depth = 1

class IncorporacionUnidadesSerializer():

    def get_unidades_actuales(self, instance_predio_actual):
        """
        Obtiene las unidades de un predio existente de forma eficiente.
        Retorna siempre una lista, que puede estar vacía.
        """
        if not instance_predio_actual:
            return []

        ids_unidades = Historial_predio.objects.filter(
            predio=instance_predio_actual,
            predio_unidadespacial__unidadconstruccion__isnull=False
        ).values_list('predio_unidadespacial__unidadconstruccion__caracteristicas_unidadconstruccion__id', flat=True).distinct()
        
        if not ids_unidades:
            return []

        # Se obtienen todas las características en una sola consulta para evitar N+1.
        unidades_caracteristicas = CaracteristicasUnidadconstruccion.objects.filter(id__in=ids_unidades)
        
        # Se prepara la lista de retorno con el formato esperado.
        return [
            {'instance_unidad': unidad, 'instance_titulo': None}
            for unidad in unidades_caracteristicas
        ]
    
    def incorporar_unidades(self, predio=None, instance_predio_actual=None, instance_predio_novedad=None, validar=False):
        """
        Orquesta la creación o copia de unidades de construcción.
        """
        npn = predio.get('npn')
        unidades_json = predio.get('unidades')
        
        if validar and not unidades_json:
            raise ValidationError(f'Para el predio {npn} las unidades son obligatorias.')
        
        if unidades_json:
            # Escenario 1: Se proporcionan nuevas unidades, se crean.
            return self.create_unidades(predio)
        
        # Escenario 2: No hay unidades nuevas, se copian de un predio anterior.
        predio_a_consultar = instance_predio_novedad.order_by('-id').first() if instance_predio_novedad else instance_predio_actual
        return self.get_unidades_actuales(predio_a_consultar)

    def create_unidades(self, list_json=None):
        """
        Crea las instancias de CaracteristicasUnidadconstruccion y sus geometrías.
        Optimizado para usar bulk_create en las geometrías.
        """
        if not list_json or list_json.get('eliminar_unidad') == 'SI' or not list_json.get('unidades'):
            return []

        npn = list_json.get('npn')
        unidades_creadas = []

        for unidad_data in list_json.get('unidades'):
            identificador = unidad_data.get('identificador')
            geometry_unidad = unidad_data.get('geometry_unidad')
            if not geometry_unidad:
                raise ValidationError(f'La unidad con identificador {identificador} del predio {npn} no contiene una geometría válida')

            # GET INSTANCIAS RELACIONADAS
            try:
                instance_CrUsouconstipo = CrUsouconstipo.objects.get(ilicode=unidad_data.get('uso'))
                instance_unidad_construccion_tipo = CrUnidadconstrucciontipo.objects.get(ilicode=unidad_data.get('unidadconstrucciontipo'))
            except (CrUsouconstipo.DoesNotExist, CrUnidadconstrucciontipo.DoesNotExist) as e:
                raise ValidationError(f"Error en datos de la unidad {identificador}: {e}")

            # PREPARAR Y VALIDAR DATOS DE CARACTERÍSTICAS
            dict_create_unidades = {
                'identificador': identificador,
                'total_plantas': unidad_data.get('total_plantas'),
                'anio_construccion': unidad_data.get('anio_construccion'),
                'avaluo_unidad': unidad_data.get('avaluo_unidad'),
                'area_construida': unidad_data.get('area_construida'),
                'estado_conservacion': unidad_data.get('estado_conservacion'),
                'puntaje': unidad_data.get('puntaje'),
                'unidad_construccion_tipo': instance_unidad_construccion_tipo,
                'uso': instance_CrUsouconstipo,
            }
            
            serializer = UnidadesSerializer(data=dict_create_unidades)
            serializer.is_valid(raise_exception=True)
            
            # CREAR CARACTERÍSTICA (NECESARIO PARA OBTENER ID)
            instance_unidad = CaracteristicasUnidadconstruccion.objects.create(**dict_create_unidades)
            
            # PREPARAR Y CREAR GEOMETRÍAS CON BULK_CREATE
            geometrias_a_crear = [
                Unidadconstruccion(unidad_construccion=instance_unidad, **geometria)
                for geometria in geometry_unidad
            ]
            if geometrias_a_crear:
                Unidadconstruccion.objects.bulk_create(geometrias_a_crear)

            # AÑADIR A LA LISTA DE RETORNO
            unidades_creadas.append({'instance_unidad': instance_unidad, 'instance_titulo': None})

        # VALIDACIONES DE NEGOCIO FINALES
        if not unidades_creadas:
            if list_json.get('uso') in ('Comercial','Cultural','Habitacional','Industrial','Institucional'):
                raise ValidationError(f"El uso {list_json.get('uso')} debe tener asociada mínimo una construcción.")
        
        return unidades_creadas