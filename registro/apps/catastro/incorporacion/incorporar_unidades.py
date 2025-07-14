from rest_framework.serializers import ModelSerializer, ValidationError
from django.contrib.gis.geos import GEOSGeometry, MultiPolygon, Polygon
import json
from datetime import datetime
from django.db import transaction
from django.contrib.gis.gdal import SpatialReference, CoordTransform
import zipfile
import io
import geopandas as gpd
from shapely.geometry import mapping
import pandas as pd
import tempfile
import os
import logging

from registro.apps.catastro.models import (
    CaracteristicasUnidadconstruccion, Unidadconstruccion, Historial_predio,
    CrUnidadconstrucciontipo, CrUsouconstipo, CrConstruccionplantatipo
)
from registro.apps.catastro.serializers import UnidadesSerializer

logger = logging.getLogger(__name__)

class IncorporacionUnidadesSerializer():

    def _procesar_geometria_zip(self, archivo_zip, npn_predio):
        """
        Procesa un archivo .zip que contiene un Shapefile.
        
        Extrae las geometrías y las devuelve en un diccionario
        de Features GeoJSON, con el 'identifica' de cada unidad como clave.
        """
        features = {}
        # Usar un directorio temporal para extraer los archivos de forma segura
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                with zipfile.ZipFile(io.BytesIO(archivo_zip.read()), 'r') as zf:
                    zf.extractall(tmpdir)
                
                # Buscar el archivo .shp en el directorio temporal
                shp_filepath = None
                for root, dirs, files in os.walk(tmpdir):
                    for file in files:
                        if file.lower().endswith('.shp'):
                            shp_filepath = os.path.join(root, file)
                            break
                    if shp_filepath:
                        break
                
                if not shp_filepath:
                    raise ValidationError("El archivo .zip no contiene un archivo .shp.")
                
                gdf = gpd.read_file(shp_filepath)

                # Convertir todas las columnas a minúsculas para estandarizar
                gdf.columns = [col.lower() for col in gdf.columns]

                # Validar CRS y columnas
                if not gdf.crs or gdf.crs.to_epsg() != 9377:
                    raise ValidationError(f"El CRS del Shapefile debe ser 9377, pero es {gdf.crs}.")
                
                columnas_requeridas = ['codigo', 'identifica']
                for col in columnas_requeridas:
                    if col not in gdf.columns:
                        raise ValidationError(f"El Shapefile debe contener la columna '{col}'.")

                for index, row in gdf.iterrows():
                    if str(row['codigo']) != str(npn_predio):
                        raise ValidationError(f"El 'codigo' {row['codigo']} en el Shapefile no coincide con el NPN del predio {npn_predio}.")
                    
                    identificador = str(row['identifica'])
                    
                    # Convertir todas las propiedades a un formato JSON serializable
                    properties = row.drop('geometry').to_dict()
                    for key, value in properties.items():
                        if isinstance(value, (datetime, pd.Timestamp)):
                            properties[key] = value.isoformat()
                        elif pd.isna(value):
                            properties[key] = None

                    feature = {
                        "type": "Feature",
                        "geometry": mapping(row['geometry']), # Convertir geometría a formato GeoJSON
                        "properties": properties
                    }
                    features[identificador] = feature

            except zipfile.BadZipFile:
                raise ValidationError("El archivo proporcionado no es un .zip válido.")
            except Exception as e:
                logger.error(f"Error detallado al procesar Shapefile: {e}", exc_info=True)
                raise ValidationError(f"Error al procesar el Shapefile: {e}")
            
        return features

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
        
        # Se busca la unidad de construccion completa (con geometría)
        unidades_completas = Unidadconstruccion.objects.filter(
            caracteristicas_unidadconstruccion__in=unidades_caracteristicas
        )
        return unidades_completas
    
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
        
        Maneja dos casos:
        1. Solo características (sin geometría): Duplica Unidadconstruccion existente
        2. Con geometría nueva: Crea nueva geometría y valida identificadores
        """
        if not list_json or list_json.get('eliminar_unidad') == 'SI' or not list_json.get('unidades'):
            return []

        npn = list_json.get('npn')
        unidades_creadas = []

        for unidad_data in list_json.get('unidades'):
            identificador = unidad_data.get('identificador')
            
            # La geometría ahora viene siempre en el mismo campo
            geometria_unidad = unidad_data.get('geometry_unidad')

            # GET INSTANCIAS RELACIONADAS
            uso_ilicode = unidad_data.get('uso')
            unidad_construccion_tipo_ilicode = unidad_data.get('unidadconstrucciontipo')
            try:
                CrUsouconstipo.objects.get(ilicode=uso_ilicode)
                CrUnidadconstrucciontipo.objects.get(ilicode=unidad_construccion_tipo_ilicode)
            except (CrUsouconstipo.DoesNotExist, CrUnidadconstrucciontipo.DoesNotExist) as e:
                raise ValidationError(f"Error en datos de la unidad {identificador}: {e}")

            # PREPARAR DATOS DE CARACTERÍSTICAS
            dict_create_unidades = {
                'identificador': identificador,
                'total_plantas': unidad_data.get('total_plantas'),
                'anio_construccion': unidad_data.get('anio_construccion'),
                'avaluo_unidad': unidad_data.get('avaluo_unidad'),
                'area_construida': unidad_data.get('area_construida'),
                'estado_conservacion': unidad_data.get('estado_conservacion'),
                'puntaje': unidad_data.get('puntaje'),
                'tipo_unidad_construccion': unidad_construccion_tipo_ilicode,
                'uso': uso_ilicode,
            }
            
            # VALIDAR DATOS DE CARACTERÍSTICAS
            serializer = UnidadesSerializer(data=dict_create_unidades)
            instance_caracteristicas_unidad = None
            if serializer.is_valid(raise_exception=True):
                instance_caracteristicas_unidad = serializer.save()

            # LÓGICA PARA MANEJAR GEOMETRÍA
            instance_unidad = None
            if geometria_unidad:
                # Si se proporciona geometría, se crea una nueva Unidadconstruccion
                
                # Origen: 9377 (viene del SHP/GeoJSON), Destino: 4326 (para el campo `geom`)
                srid_origen = 9377
                srid_destino = 4326

                # La geometria ya viene en formato GeoJSON (Feature)
                geometria_original = GEOSGeometry(json.dumps(geometria_unidad['geometry']), srid=srid_origen)

                transformacion = CoordTransform(SpatialReference(srid_origen), SpatialReference(srid_destino))
                geometria_transformada = geometria_original.transform(transformacion, clone=True)
                
                if isinstance(geometria_transformada, Polygon):
                    geometria_final = MultiPolygon(geometria_transformada)
                else:
                    geometria_final = geometria_transformada

                instance_tipo_planta = self._obtener_tipo_planta_por_defecto()
                
                instance_unidad = Unidadconstruccion.objects.create(
                    caracteristicas_unidadconstruccion=instance_caracteristicas_unidad,
                    geometria=geometria_final,
                    planta_ubicacion=unidad_data.get('planta_ubicacion'),
                    altura=unidad_data.get('altura'),
                    comienzo_vida_util=datetime.now().date(),
                    tipo_planta=instance_tipo_planta
                )
            
            # Si se creó la unidad, se añade a la lista
            if instance_unidad:
                unidades_creadas.append(instance_unidad)

        return unidades_creadas

    def _validar_identificadores_geometria(self, geometry_unidad, identificador_caracteristica, npn):
        """
        Valida que los identificadores del GeoJSON coincidan con los datos del proceso.
        
        Validaciones:
        1. Campo "CODIGO" debe coincidir con el NPN del predio
        2. Campo "IDENTIFICA" debe coincidir con el identificador de la unidad
        3. Campo "local_id" es opcional (solo para referencia interna)
        
        Args:
            geometry_unidad (list|dict): Lista de geometrías o FeatureCollection de GeoJSON
            identificador_caracteristica (str): Identificador de la característica
            npn (str): Número predial nacional del predio
        """
        # Normalizar el formato de entrada
        geometrias_a_validar = []
        
        if isinstance(geometry_unidad, dict):
            # Caso 1: FeatureCollection de GeoJSON estándar
            if geometry_unidad.get('type') == 'FeatureCollection':
                geometrias_a_validar = geometry_unidad.get('features', [])
            # Caso 2: Feature individual
            elif geometry_unidad.get('type') == 'Feature':
                geometrias_a_validar = [geometry_unidad]
            # Caso 3: Objeto con geometría directa
            else:
                geometrias_a_validar = [geometry_unidad]
        elif isinstance(geometry_unidad, list):
            # Caso 4: Array de geometrías
            geometrias_a_validar = geometry_unidad
        else:
            raise ValidationError(
                f"Formato de geometry_unidad no válido para la unidad {identificador_caracteristica} "
                f"del predio {npn}. Debe ser un FeatureCollection, Feature o array de geometrías."
            )
        
        if not geometrias_a_validar:
            raise ValidationError(
                f"No se encontraron geometrías para validar en la unidad {identificador_caracteristica} "
                f"del predio {npn}"
            )
        
        for geometria in geometrias_a_validar:
            # Extraer properties si viene en formato GeoJSON estándar
            properties = geometria.get('properties', {})
            
            # DEBUG: Ver qué campos están disponibles
            available_keys = list(properties.keys()) + list(geometria.keys())
            
            # VALIDACIÓN 1: Campo CODIGO debe coincidir con NPN
            # Buscar en properties primero, luego en el nivel raíz
            codigo_geo = None
            
            # Buscar CODIGO en properties (puede tener espacios)
            for key, value in properties.items():
                if str(key).strip().upper() == 'CODIGO':
                    codigo_geo = str(value).strip()
                    break
            
            # Si no se encontró en properties, buscar en nivel raíz
            if not codigo_geo:
                for key, value in geometria.items():
                    if str(key).strip().upper() == 'CODIGO':
                        codigo_geo = str(value).strip()
                        break
            
            if not codigo_geo:
                raise ValidationError(
                    f"La geometría de la unidad {identificador_caracteristica} del predio {npn} "
                    f"debe tener el campo 'CODIGO' en properties o en el nivel raíz. "
                    f"Campos disponibles: {available_keys}"
                )
            
            if codigo_geo != str(npn).strip():
                raise ValidationError(
                    f"El campo 'CODIGO' de la geometría '{codigo_geo}' no coincide con "
                    f"el NPN del predio '{npn}'"
                )
            
            # VALIDACIÓN 2: Campo IDENTIFICA debe coincidir con identificador de unidad
            # Buscar en properties primero, luego en el nivel raíz
            identifica_geo = None
            
            # Buscar IDENTIFICA en properties (puede tener espacios)
            for key, value in properties.items():
                if str(key).strip().upper() == 'IDENTIFICA':
                    identifica_geo = str(value).strip()
                    break
            
            # Si no se encontró en properties, buscar en nivel raíz
            if not identifica_geo:
                for key, value in geometria.items():
                    if str(key).strip().upper() == 'IDENTIFICA':
                        identifica_geo = str(value).strip()
                        break
            
            if not identifica_geo:
                raise ValidationError(
                    f"La geometría de la unidad {identificador_caracteristica} del predio {npn} "
                    f"debe tener el campo 'IDENTIFICA' en properties o en el nivel raíz. "
                    f"Campos disponibles: {available_keys}"
                )
            
            if identifica_geo != str(identificador_caracteristica).strip():
                raise ValidationError(
                    f"El campo 'IDENTIFICA' de la geometría '{identifica_geo}' no coincide con "
                    f"el identificador de la unidad '{identificador_caracteristica}' "
                    f"para el predio {npn}"
                )
            
            # VALIDACIÓN 3: Campo local_id (opcional para referencia interna)
            # Ya validamos IDENTIFICA, no necesitamos validar identificador adicional
            # Solo verificamos que tenga local_id si está presente
            local_id = properties.get('local_id') or geometria.get('local_id')
            if local_id and not isinstance(local_id, str):
                raise ValidationError(
                    f"El campo 'local_id' de la geometría debe ser un string válido "
                    f"para la unidad {identificador_caracteristica} del predio {npn}"
                )

    def _buscar_geometria_existente_por_identificador(self, identificador):
        """
        Busca geometría existente por identificador de la característica.
        
        Args:
            identificador (str): Identificador de la característica
            
        Returns:
            QuerySet: Geometrías existentes con ese identificador
        """
        return Unidadconstruccion.objects.filter(
            caracteristicas_unidadconstruccion__identificador=identificador
        ).first()

    def _duplicar_geometria_existente(self, geometria_existente, nueva_caracteristica):
        """
        Duplica geometría existente asociándola a la nueva característica.
        
        Args:
            geometria_existente (Unidadconstruccion): Geometría a duplicar
            nueva_caracteristica (CaracteristicasUnidadconstruccion): Nueva característica
        """
        
        # Obtener datos de la geometría existente
        geometria_data = {
            'geom': geometria_existente.geom,
            'local_id': geometria_existente.local_id,
            'altura': geometria_existente.altura,
            'comienzo_vida_util': geometria_existente.comienzo_vida_util or datetime.now().date(),
            'fin_vida_util': geometria_existente.fin_vida_util,
            'geometria': geometria_existente.geometria,
            'planta_ubicacion': geometria_existente.planta_ubicacion,
            'tipo_planta': geometria_existente.tipo_planta,
        }
        
        # Crear nueva geometría con la nueva característica
        nueva_geometria = Unidadconstruccion.objects.create(
            caracteristicas_unidadconstruccion=nueva_caracteristica,
            **geometria_data
        )
        
        return nueva_geometria

    def _convertir_a_multipolygon(self, geometry_data):
        """
        Convierte una geometría GeoJSON a un MultiPolygon de GeoDjango.
        
        Args:
            geometry_data (dict): Geometría en formato GeoJSON
            
        Returns:
            MultiPolygon: Objeto MultiPolygon de GeoDjango
        """
        try:
            # Convertir GeoJSON a objeto de geometría GEOS
            geom = GEOSGeometry(json.dumps(geometry_data))
            
            # Si ya es un MultiPolygon, devolver tal como está
            if geom.geom_type == 'MultiPolygon':
                return geom
            
            # Si es un Polygon, convertir a MultiPolygon
            elif geom.geom_type == 'Polygon':
                return MultiPolygon(geom)
            
            # Si es otro tipo de geometría, intentar convertir a MultiPolygon
            else:
                raise ValidationError(
                    f"Tipo de geometría no soportado: {geom.geom_type}. "
                    f"Se esperaba Polygon o MultiPolygon."
                )
                
        except Exception as e:
            raise ValidationError(
                f"Error al convertir geometría GeoJSON a MultiPolygon: {str(e)}"
            )

    def _obtener_tipo_planta_por_defecto(self):
        """
        Obtiene el tipo de planta por defecto (Piso) para las nuevas geometrías de unidades.
        
        Returns:
            CrConstruccionplantatipo: Instancia del tipo de planta por defecto
        """
        try:
            # Intentar obtener el tipo de planta "Piso" 
            return CrConstruccionplantatipo.objects.get(ilicode='Piso')
        except CrConstruccionplantatipo.DoesNotExist:
            # Si no existe "Piso", obtener el primer tipo de planta disponible
            primer_tipo = CrConstruccionplantatipo.objects.first()
            if primer_tipo:
                return primer_tipo
            else:
                # Si no hay ningún tipo de planta en la base de datos, lanzar error
                raise ValidationError(
                    "No se encontraron tipos de planta en la base de datos. "
                    "Se requiere al menos un tipo de planta para crear geometrías de unidades."
                )