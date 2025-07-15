from registro.apps.catastro.models import (
    Historial_predio, PredioUnidadespacial, CrEstadotipo, Unidadconstruccion, Terreno
)
from django.db.models import QuerySet
from rest_framework.serializers import ValidationError

class IncorporarPredioUnidadespacial():
    
    def get_predio_para_filtrar(self, list_json, instance_predio_novedad):
        """
        Determina el único predio de "novedad" que se usará para la consulta.
        La regla es: tomar el predio de novedad que se proporcione, priorizando
        el que viene en el JSON.
        """
        predio_novedad = list_json.get('predio_novedad')

        # Si se proporcionó una novedad en el JSON, la procesamos.
        if predio_novedad:
            # Si es un QuerySet, tomamos el primer elemento si existe.
            if isinstance(predio_novedad, QuerySet):
                return predio_novedad.first() # .first() devuelve None si el queryset está vacío.
            # Si es un objeto, lo devolvemos directamente.
            return predio_novedad

        # Si no hay novedad en el JSON, usamos la que se pasa como argumento.
        return instance_predio_novedad
        
    def consultar_historial_predio(self, predio_para_filtrar, campo_isnull):
        """
        Dado un predio, realiza la consulta en Historial_predio filtrando por un campo no nulo.
        (por ejemplo: 'terreno' o 'unidadconstruccion').

        Devuelve el QuerySet resultante. Si no se proporciona un predio, retorna .none().
        """
        if predio_para_filtrar is None:
            return Historial_predio.objects.none()

        # Arma el filtro dinámico, por ejemplo:
        #   predio=predio_para_filtrar,
        #   predio_unidadespacial__terreno__isnull=False   (o)   predio_unidadespacial__unidadconstruccion__isnull=False
        filter_kwargs = {
            "predio": predio_para_filtrar,
            f"predio_unidadespacial__{campo_isnull}__isnull": False
        }
        return (
            Historial_predio.objects
            .filter(**filter_kwargs)
            .select_related('predio_unidadespacial')
        )

    def conservar_y_relacionar_geometria(self, instance_predio_novedad, instance_predio_actual):
        """
        Conserva la geometría (terreno y unidades) del predio actual y la relaciona
        con el nuevo predio (novedad) creando copias de sus relaciones en PredioUnidadespacial.
        """
        # 1. Obtener todas las relaciones espaciales del predio actual (terrenos y unidades)
        relaciones_actuales = PredioUnidadespacial.objects.filter(predio=instance_predio_actual)

        if not relaciones_actuales.exists():
            raise ValidationError(f"El predio activo {instance_predio_actual.numero_predial_nacional} no tiene unidades espaciales asociadas.")

        # 2. Preparar una lista de nuevas relaciones para crear
        nuevas_relaciones = []
        for relacion_actual in relaciones_actuales:
            nuevas_relaciones.append(
                PredioUnidadespacial(
                    predio=instance_predio_novedad,
                    terreno=relacion_actual.terreno,
                    unidadconstruccion=relacion_actual.unidadconstruccion,
                    local_id=relacion_actual.local_id
                )
            )
        
        # 3. Crear todas las nuevas relaciones en una sola transacción
        if nuevas_relaciones:
            PredioUnidadespacial.objects.bulk_create(nuevas_relaciones)
        
        # Devolver el predio novedad y las nuevas relaciones creadas
        unidades_creadas = list(PredioUnidadespacial.objects.filter(predio=instance_predio_novedad))
        return instance_predio_novedad, unidades_creadas

    def procesar_tipo_unidadespacial(self, list_json, tipo_dato, campo_modelo, otro_tipo_dato):
        """
        Procesa un tipo específico de unidad espacial (terreno o unidad de construcción),
        decidiendo si crear nuevas instancias, reutilizar existentes, o crear copias.
        """
        nuevas_instancias = []
        instancias_existentes = []
        instance_predio_novedad = list_json.get('predio_novedad')
        datos_json = list_json.get(tipo_dato)
        es_mutacion_tercera = list_json.get('es_mutacion_tercera', False)

        if datos_json:
            # Escenario 1: Hay datos nuevos en el JSON (ya sean unidades o terrenos).
            # Se crean las relaciones en PredioUnidadespacial.
            for instancia in datos_json:
                if tipo_dato == 'unidades':
                    nuevas_instancias.append(PredioUnidadespacial(
                        unidadconstruccion=instancia,
                        predio=instance_predio_novedad
                    ))
                elif tipo_dato == 'terrenos':
                    nuevas_instancias.append(PredioUnidadespacial(
                        terreno=instancia,
                        predio=instance_predio_novedad
                    ))
        else:
            # Escenario 2: No hay datos en el JSON. Se intenta copiar del predio actual (lógica de mutación tercera).
            predio_actual = list_json.get('predio_actual')
            if predio_actual and es_mutacion_tercera:
                filter_kwargs = {
                    'predio': predio_actual,
                    f'{campo_modelo}__isnull': False
                }
                qs_actuales = PredioUnidadespacial.objects.filter(**filter_kwargs)
                
                for relacion_actual in qs_actuales:
                    copia_data = {
                        'terreno': relacion_actual.terreno,
                        'unidadconstruccion': relacion_actual.unidadconstruccion,
                        'predio': instance_predio_novedad,
                        'local_id': relacion_actual.local_id
                    }
                    nuevas_instancias.append(PredioUnidadespacial(**copia_data))

        return nuevas_instancias, instancias_existentes

    def create_Unidadespacial(self, list_json=None):
        """
        Crea o reutiliza instancias de PredioUnidadespacial (terrenos y unidades).
        La creación de nuevas instancias se realiza de forma masiva y eficiente.
        """
        unidades_finales = []
        instancias_para_crear = []

        # 1. Procesar Unidades de Construcción (si no se eliminan todas)
        if list_json.get('eliminar_unidad') != 'SI':
            crear_unidad, copiar_unidad = self.procesar_tipo_unidadespacial(
                list_json, 'unidades', 'unidadconstruccion', 'terrenos'
            )
            instancias_para_crear.extend(crear_unidad)
            unidades_finales.extend(copiar_unidad)

        # 2. Procesar Terrenos
        crear_terreno, copiar_terreno = self.procesar_tipo_unidadespacial(
            list_json, 'terrenos', 'terreno', 'unidades'
        )
        instancias_para_crear.extend(crear_terreno)
        unidades_finales.extend(copiar_terreno)

        # 3. Crear todas las nuevas instancias de una sola vez con bulk_create
        if instancias_para_crear:
            instancias_creadas = PredioUnidadespacial.objects.bulk_create(instancias_para_crear)
            unidades_finales.extend(instancias_creadas)
            
        return unidades_finales

        