from registro.apps.catastro.models import (
    Historial_predio, PredioUnidadespacial, CrEstadotipo
)
from django.db.models import QuerySet

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

    def procesar_tipo_unidadespacial(self, list_json, tipo_dato, campo_modelo, otro_tipo_dato):
        """
        Helper que procesa un tipo de unidad espacial (terreno o unidad).
        Devuelve dos listas: una de instancias nuevas para crear y otra de instancias existentes para reutilizar.
        """
        nuevas_instancias = []
        instancias_existentes = []
        instance_predio_novedad = list_json.get('predio_novedad')
        datos_json = list_json.get(tipo_dato)

        if datos_json:
            # Escenario 1: Hay datos nuevos en el JSON. Preparamos instancias para bulk_create.
            for dato in datos_json:
                data_unidadespacial = {
                    'terreno': None,
                    'unidadconstruccion': None,
                    'predio': instance_predio_novedad,
                }
                instance_key = f'instance_{campo_modelo}'
                data_unidadespacial[campo_modelo] = dato.get(instance_key)
                nuevas_instancias.append(PredioUnidadespacial(**data_unidadespacial))

        else:
            # Escenario 2: No hay datos en el JSON. Intentamos copiar de un predio anterior.
            predio_para_filtrar = self.get_predio_para_filtrar(list_json, instance_predio_novedad)
            qs_historicas = self.consultar_historial_predio(predio_para_filtrar, campo_modelo)

            if qs_historicas.exists():
                for hist in qs_historicas:
                    instancias_existentes.append(hist.predio_unidadespacial)
            else:
                predio_actual = list_json.get('predio_actual')
                if predio_actual:
                    filter_kwargs = {
                        'predio': predio_actual,
                        f'predio_unidadespacial__{campo_modelo}__isnull': False
                    }
                    qs_actuales = Historial_predio.objects.filter(**filter_kwargs)
                    
                    if list_json.get(otro_tipo_dato):
                        for hist in qs_actuales:
                            copia = hist.predio_unidadespacial
                            copia.id = None
                            copia.predio = instance_predio_novedad
                            nuevas_instancias.append(copia)
                    else:
                        for hist in qs_actuales:
                            instancias_existentes.append(hist.predio_unidadespacial)

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

        