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

    def _procesar_geometria_zip(self, archivo_zip):
        """
        Procesa un archivo .zip que contiene un Shapefile.
        
        Extrae las geometrías y las devuelve en una lista de Features GeoJSON.
        Permite múltiples features con el mismo identificador, ya que pueden
        representar diferentes polígonos de la misma unidad.
        """
        features = []
        # Usar un directorio temporal para extraer los archivos de forma segura
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                with zipfile.ZipFile(io.BytesIO(archivo_zip.read()), 'r') as zf:
                    # VALIDACIÓN DE ARCHIVOS ESENCIALES
                    filenames = [f.filename.lower() for f in zf.infolist()]
                    has_shp = any(fname.endswith('.shp') for fname in filenames)
                    has_shx = any(fname.endswith('.shx') for fname in filenames)
                    has_dbf = any(fname.endswith('.dbf') for fname in filenames)

                    if not (has_shp and has_shx and has_dbf):
                        raise ValidationError(
                            "El archivo .zip debe contener al menos un archivo .shp, .shx y .dbf."
                        )

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

                # Validar CRS de origen (debe ser 9377)
                if not gdf.crs or gdf.crs.to_epsg() != 9377:
                    raise ValidationError(f"El CRS del Shapefile debe ser 9377, pero es {gdf.crs}.")
                
                # Transformar a WGS 84 (4326) para la salida GeoJSON estándar
                gdf_4326 = gdf.to_crs(epsg=4326)

                columnas_requeridas = ['codigo', 'identifica']
                for col in columnas_requeridas:
                    if col not in gdf.columns:
                        raise ValidationError(f"El Shapefile debe contener la columna '{col}'.")

                # Iterar sobre el GeoDataFrame transformado
                for index, row in gdf_4326.iterrows():
                    # Convertir todas las propiedades a un formato JSON serializable
                    properties = row.drop('geometry').to_dict()
                    for key, value in properties.items():
                        if isinstance(value, (datetime, pd.Timestamp)):
                            properties[key] = value.isoformat()
                        elif pd.isna(value):
                            properties[key] = None

                    feature = {
                        "type": "Feature",
                        "geometry": mapping(row['geometry']), # Usar la geometría ya transformada a 4326
                        "properties": properties
                    }
                    # Agregar todas las features a la lista, permitiendo duplicados de identificador
                    features.append(feature)

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
    
    def get_geometria_from_data(self, geometria_data):
        """
        Extrae un objeto GEOSGeometry de varios formatos de entrada (FeatureCollection, Feature, dict).
        Además, detecta el SRID basado en los valores de las coordenadas.
        """
        try:
            if not geometria_data:
                return None

            geometry = None
            # Si es una FeatureCollection, tomamos la geometría de la primera 'feature'
            if geometria_data.get('type') == 'FeatureCollection':
                if not geometria_data.get('features'):
                    logger.warning("FeatureCollection de geometría está vacía.")
                    return None
                geometry = geometria_data['features'][0]['geometry']
            # Si es una Feature, tomamos su 'geometry'
            elif geometria_data.get('type') == 'Feature':
                geometry = geometria_data['geometry']
            # Si ya es un objeto de geometría
            else:
                geometry = geometria_data
            
            if not geometry or not geometry.get('coordinates'):
                logger.warning("No se encontraron coordenadas en los datos de geometría.")
                return None

            # Heurística para determinar el SRID basado en los valores de las coordenadas
            coords = geometry.get('coordinates', [])

            def flatten(coords_list):
                for item in coords_list:
                    if isinstance(item, (list, tuple)):
                        yield from flatten(item)
                    elif item is not None:
                        yield item
            
            all_coords = list(flatten(coords))
            
            # Si alguna coordenada está fuera del rango de WGS84 (-180 a 180), asumimos que es un sistema proyectado.
            if any(abs(c) > 180 for c in all_coords):
                logger.debug("Geometría con coordenadas proyectadas detectada. Asumiendo MAGNA-SIRGAS (9377).")
                srid = 9377
            else:
                logger.debug("Geometría parece estar en WGS84 (4326).")
                srid = 4326

            geometry_obj = GEOSGeometry(json.dumps(geometry), srid=srid)
            return geometry_obj
        
        except (KeyError, IndexError, TypeError, ValueError) as e:
            logger.error(f"Error al procesar la geometría: {e}")
            return None

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
        Crea las instancias de CaracteristicasUnidadconstruccion y sus geometrías
        a partir de una lista de características y un FeatureCollection de geometrías,
        asociándolas por el campo 'identificador'.
        
        Lógica:
        - Si hay múltiples polígonos con el mismo 'codigo' e 'identifica', comparten
          la misma CaracteristicasUnidadconstruccion pero se crean múltiples registros
          en Unidadconstruccion (uno por cada polígono).
        - Si hay polígonos con el mismo 'codigo' pero diferente 'identifica', cada uno
          tiene su propia CaracteristicasUnidadconstruccion.
        """
        if not list_json or not list_json.get('unidades'):
            return []

        # VALIDACIÓN: Los identificadores de las unidades deben ser únicos.
        caracteristicas_unidades = list_json.get('unidades', [])
        geometria_data = list_json.get('geometry_unidad')

        identificadores = [unidad.get('identificador') for unidad in caracteristicas_unidades]
        if len(identificadores) != len(set(identificadores)):
            raise ValidationError("Se encontraron identificadores de unidad duplicados. Cada unidad debe tener un identificador único.")
        
        if not geometria_data or not geometria_data.get('features'):
            raise ValidationError("Se requiere el campo 'geometry_unidad' con un FeatureCollection válido.")

        npn = list_json.get('npn')
        
        # Crear un mapa de geometrías agrupadas por (codigo, identifica)
        # Clave: (codigo, identifica) -> Lista de features
        mapa_geometrias_por_grupo = {}
        for feature in geometria_data['features']:
            props = feature.get('properties', {})
            codigo_geo = props.get('codigo')
            identificador_geo = props.get('identifica')
            
            if codigo_geo and identificador_geo:
                # Validar que el código coincida con el NPN del proceso
                if str(codigo_geo).strip() != str(npn).strip():
                    raise ValidationError(
                        f"El número predial de la geometría ('{str(codigo_geo).strip()}') "
                        f"no coincide con el del proceso ('{str(npn).strip()}')."
                    )
                
                # Clave compuesta: (codigo, identifica)
                grupo_key = (str(codigo_geo).strip(), str(identificador_geo))
                
                if grupo_key not in mapa_geometrias_por_grupo:
                    mapa_geometrias_por_grupo[grupo_key] = []
                mapa_geometrias_por_grupo[grupo_key].append(feature)

        # Crear un mapa de características por identificador para acceso rápido
        mapa_caracteristicas = {}
        for unidad_data in caracteristicas_unidades:
            identificador = str(unidad_data.get('identificador'))
            mapa_caracteristicas[identificador] = unidad_data

        unidades_creadas = []

        # Procesar cada grupo de geometrías (mismo codigo + mismo identifica)
        for (codigo_grupo, identificador_grupo), geometrias_features in mapa_geometrias_por_grupo.items():
            # Buscar los datos de características para este identificador
            unidad_data = mapa_caracteristicas.get(identificador_grupo)
            if not unidad_data:
                raise ValidationError(f"No se encontraron datos de características para el identificador '{identificador_grupo}' en 'geometry_unidad'.")

            # PREPARAR DATOS DE CARACTERÍSTICAS DIRECTAMENTE PARA EL SERIALIZER
            dict_create_unidades = {
                'identificador': identificador_grupo,
                'total_plantas': unidad_data.get('total_plantas'),
                'anio_construccion': unidad_data.get('anio_construccion'),
                'avaluo_unidad': unidad_data.get('avaluo_unidad'),
                'area_construida': unidad_data.get('area_construida'),
                'estado_conservacion': unidad_data.get('estado_conservacion'),
                'puntaje': unidad_data.get('puntaje'),
                'unidadconstrucciontipo': unidad_data.get('unidadconstrucciontipo'),
                'uso': unidad_data.get('uso'),
            }
            
            # VALIDAR Y CREAR UNA SOLA CaracteristicasUnidadconstruccion PARA ESTE GRUPO
            serializer = UnidadesSerializer(data=dict_create_unidades)
            instance_caracteristicas_unidad = None
            try:
                if serializer.is_valid(raise_exception=True):
                    instance_caracteristicas_unidad = serializer.save()
            except ValidationError as e:
                error_detail = e.detail
                error_message = "Error de validación en la unidad."
                if isinstance(error_detail, dict) and error_detail:
                    first_key = next(iter(error_detail))
                    first_error = error_detail[first_key][0]
                    if "does not exist" in first_error:
                        error_message = f"El ID proporcionado para '{first_key}' en la unidad '{identificador_grupo}' no es válido."
                    else:
                        error_message = f"Error en el campo '{first_key}' de la unidad '{identificador_grupo}': {first_error}"
                raise ValidationError(error_message)

            # CREAR MÚLTIPLES REGISTROS DE Unidadconstruccion, UNO POR CADA GEOMETRÍA
            # Todos compartirán la misma CaracteristicasUnidadconstruccion
            instance_tipo_planta = self._obtener_tipo_planta_por_defecto()
            
            for geometria_feature in geometrias_features:
                # LÓGICA PARA MANEJAR GEOMETRÍA
                geom_input = self.get_geometria_from_data(geometria_feature.get('geometry'))

                if not geom_input:
                    logger.warning(f"No se pudo obtener la geometría para la unidad '{identificador_grupo}', saltando esta geometría...")
                    continue
                
                # Asegurarnos de tener ambas geometrías: WGS84 (4326) y MAGNA (9377)
                if geom_input.srid == 4326:
                    geom_wgs84 = geom_input
                    transform_to_magna = CoordTransform(SpatialReference(4326), SpatialReference(9377))
                    geom_magna = geom_wgs84.transform(transform_to_magna, clone=True)
                elif geom_input.srid == 9377:
                    geom_magna = geom_input
                    transform_to_wgs84 = CoordTransform(SpatialReference(9377), SpatialReference(4326))
                    geom_wgs84 = geom_magna.transform(transform_to_wgs84, clone=True)
                else:
                    logger.error(f"SRID no reconocido ({geom_input.srid}) en la geometría de entrada para la unidad '{identificador_grupo}'. Saltando esta geometría.")
                    continue

                # Aseguramos que ambas geometrías sean MultiPolygon
                final_geom_wgs84 = MultiPolygon(geom_wgs84) if isinstance(geom_wgs84, Polygon) else geom_wgs84
                final_geom_magna = MultiPolygon(geom_magna) if isinstance(geom_magna, Polygon) else geom_magna

                # Crear un registro de Unidadconstruccion para cada geometría
                instance_unidad = Unidadconstruccion.objects.create(
                    caracteristicas_unidadconstruccion=instance_caracteristicas_unidad,
                    geom=final_geom_wgs84,
                    geometria=final_geom_magna,
                    planta_ubicacion=unidad_data.get('planta_ubicacion'),
                    altura=unidad_data.get('altura'),
                    comienzo_vida_util=datetime.now().date(),
                    tipo_planta=instance_tipo_planta
                )
                
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