from rest_framework import serializers
from registro.apps.catastro.models import (
    Predio, CaracteristicasUnidadconstruccion, Unidadconstruccion, 
    Terreno, PredioUnidadespacial, CrCondicionprediotipo, TerrenoZonas, Interesado,InteresadoPredio,
    EstructuraAvaluo, Radicado, RadicadoPredioAsignado, EstadoAsignacion, CrMutaciontipo, ColDocumentotipo, ColInteresadotipo
)
from rest_framework_gis.serializers import GeoFeatureModelSerializer

class CaracteristicasUnidadconstruccionSerializer(serializers.ModelSerializer):
    uso = serializers.SerializerMethodField()
    tipo_unidad_construccion = serializers.SerializerMethodField()

    class Meta:
        model = CaracteristicasUnidadconstruccion
        fields = [
            'identificador', 'tipo_unidad_construccion',
            'total_plantas', 'uso', 'anio_construccion',
            'area_construida', 'estado_conservacion', 
            'avaluo_unidad', 'puntaje'
        ]

    def get_uso(self, obj):
        if obj.uso:
            return obj.uso.ilicode
        return None

    def get_tipo_unidad_construccion(self, obj):
        if obj.tipo_unidad_construccion:
            return obj.tipo_unidad_construccion.ilicode
        return None

class UnidadConstruccionSerializer(GeoFeatureModelSerializer):
    caracteristicas_unidadconstruccion = CaracteristicasUnidadconstruccionSerializer()
    
    class Meta:
        model = Unidadconstruccion
        geo_field = "geom"
        fields = [
            'planta_ubicacion', 'altura', 'caracteristicas_unidadconstruccion'
          
        ]
    

    
class CaracteristicasUnidadconstruccionAlfaSerializer(serializers.ModelSerializer):
    class Meta:
        model = CaracteristicasUnidadconstruccion
        fields = ['identificador']


class TerrenoSerializer(GeoFeatureModelSerializer):
  
    class Meta:
        model = Terreno
        geo_field = "geom"
        fields = ['id']

class TerrenoAlfaSerializer(serializers.ModelSerializer):
    class Meta:
        model = TerrenoZonas
        fields = ['area_catastral_terreno','avaluo_terreno','zona_fisica','zona_geoeconomica']


class PredioUnidadespacialSerializer(serializers.ModelSerializer):
    terreno = TerrenoSerializer()
    unidadconstruccion = UnidadConstruccionSerializer()

    class Meta:
        model = PredioUnidadespacial
        fields = ['terreno', 'unidadconstruccion']

    

class InteresadoSerializer(serializers.ModelSerializer):
    tipo_documento = serializers.SerializerMethodField()
    sexo = serializers.SerializerMethodField()
    autoreconocimientoetnico = serializers.SerializerMethodField()
    tipo_interesado = serializers.SerializerMethodField()

    class Meta:
        model = Interesado
        fields = [
            'tipo_documento', 'primer_nombre', 'segundo_nombre',
            'primer_apellido', 'segundo_apellido', 'sexo',
            'autoreconocimientoetnico', 'autoreconocimientocampesino',
            'razon_social', 'nombre', 'tipo_interesado', 'numero_documento'
        ]

    def get_tipo_documento(self, obj):
        if obj.tipo_documento:
            return obj.tipo_documento.ilicode
        return None

    def get_sexo(self, obj):
        if obj.sexo:
            return obj.sexo.ilicode
        return None

    def get_autoreconocimientoetnico(self, obj):
        if obj.autoreconocimientoetnico:
            return obj.autoreconocimientoetnico.ilicode
        return None

    def get_tipo_interesado(self, obj):
        if obj.tipo_interesado:
            return obj.tipo_interesado.ilicode
        return None

class EstructuraAvaluoSerializer(serializers.ModelSerializer):
    class Meta:
        model = EstructuraAvaluo
        fields = [
            'fecha_avaluo', 'avaluo_catastral', 'vigencia'
        ]

class PredioSerializer(serializers.ModelSerializer):
    terreno_geo = serializers.SerializerMethodField()
    unidades_construccion_geo = serializers.SerializerMethodField()
    terreno_alfa = serializers.SerializerMethodField()
    # unidades_construccion_alfa = serializers.SerializerMethodField()
    condicion_predio = serializers.SerializerMethodField()
    destinacion_economica = serializers.SerializerMethodField()
    estado = serializers.SerializerMethodField()
    tipo = serializers.SerializerMethodField()
    tipo_predio = serializers.SerializerMethodField()
    interesado = serializers.SerializerMethodField()
    avaluo = serializers.SerializerMethodField()
    area_catastral_terreno = serializers.SerializerMethodField()
    orip_matricula = serializers.SerializerMethodField()

    class Meta:
        model = Predio
        fields = [
            'id', 'numero_predial_nacional', 'codigo_homologado',
            'departamento', 'municipio', 'orip_matricula',
            'condicion_predio', 'destinacion_economica',
            'area_catastral_terreno', 'vigencia_actualizacion_catastral',
            'estado', 'tipo', 'direccion', 'tipo_predio',
            'terreno_geo', 'terreno_alfa', 'unidades_construccion_geo', 'interesado',
            'avaluo'
        ]

    def get_orip_matricula(self, obj):
        if obj.codigo_orip and obj.matricula_inmobiliaria:
            return f"{obj.codigo_orip}-{obj.matricula_inmobiliaria}"
        return None

    def get_area_catastral_terreno(self, obj):
        if obj.area_catastral_terreno is not None:
            return round(float(obj.area_catastral_terreno), 2)
        return None

    def get_avaluo(self, obj):
        instance = EstructuraAvaluo.objects.filter(predio=obj).order_by('-fecha_avaluo')
        if instance.exists():
            return EstructuraAvaluoSerializer(instance, many=True).data
        return None

    def get_terreno_geo(self, obj):
        instance= PredioUnidadespacial.objects.filter(predio=obj, terreno__isnull=False)
        if instance.exists():
            instance_terreno = [instance.terreno for instance in instance]
            return TerrenoSerializer(instance_terreno, many=True).data
        return None

    def get_terreno_alfa(self, obj):
        instance = PredioUnidadespacial.objects.filter(predio=obj, terreno__isnull=False)
        if instance.exists():
            instance_terreno = [instance.terreno for instance in instance]
            instance_terreno_alfa = TerrenoZonas.objects.filter(terreno__in=instance_terreno)
            return TerrenoAlfaSerializer(instance_terreno_alfa, many=True).data
        return []

    def get_unidades_construccion_geo(self, obj):
        instance= PredioUnidadespacial.objects.filter(predio=obj, unidadconstruccion__isnull=False)
        if instance.exists():
            instance_unidad = [instance.unidadconstruccion for instance in instance]
            return UnidadConstruccionSerializer(instance_unidad, many=True).data
        return None

    # def get_unidades_construccion_alfa(self, obj):
    #     instance = PredioUnidadespacial.objects.filter(predio=obj, unidadconstruccion__isnull=False)
    #     if instance.exists():
    #         instance_unidad = [instance.unidadconstruccion.caracteristicas_unidadconstruccion.id for instance in instance if instance.unidadconstruccion ]
    #         instance_unidades_construccion_alfa = CaracteristicasUnidadconstruccion.objects.filter(id__in=instance_unidad)
    #         return CaracteristicasUnidadconstruccionAlfaSerializer(instance_unidades_construccion_alfa, many=True).data
    #     return []
    def get_interesado(self, obj):
        instance = InteresadoPredio.objects.filter(predio=obj)
        if instance.exists():
            instance_interesado = [instance.interesado for instance in instance]
            return InteresadoSerializer(instance_interesado, many=True).data
        return None

    def get_condicion_predio(self, obj):
        if obj.condicion_predio:
            return obj.condicion_predio.ilicode
        return None

    def get_destinacion_economica(self, obj):
        if obj.destinacion_economica:
            return obj.destinacion_economica.ilicode
        return None

    def get_estado(self, obj):
        if obj.estado:
            return obj.estado.ilicode
        return None

    def get_tipo(self, obj):
        if obj.tipo:
            return obj.tipo.ilicode
        return None

    def get_tipo_predio(self, obj):
        if obj.tipo_predio:
            return obj.tipo_predio.ilicode
        return None

#### ******************************SERIALIZER PARA DOMINIOS

#### ******************************SERIALIZER PARA RADICACION 
class SerializerRadicado (serializers.Serializer):
    pass

# Serializer para Radicado
class RadicadoSerializer(serializers.ModelSerializer):
    tipo_documento = serializers.SerializerMethodField()
    tipo_interesado = serializers.SerializerMethodField()
    radicado_asignado = serializers.SerializerMethodField()

    class Meta:
        model = Radicado
        fields = ['id', 'numero_radicado', 'fecha_radicado', 'asignado',
                 'oficio', 'nombre_solicitante', 'tipo_interesado_info',
                 'numero_documento', 'tipo_documento_info', 'radicado_asignado']
        read_only_fields = ('id',)

    def get_tipo_documento(self, obj):
        if obj.tipo_documento:
            return {
                'id': obj.tipo_documento.t_id,
                'ilicode': obj.tipo_documento.ilicode,
                'description': obj.tipo_documento.description
            }
        return None

    def get_tipo_interesado(self, obj):
        if obj.tipo_interesado:
            return {
                'id': obj.tipo_interesado.t_id,
                'ilicode': obj.tipo_interesado.ilicode,
                'description': obj.tipo_interesado.description
            }
        return None

    def get_radicado_asignado(self, obj):
        asignaciones = obj.radicadopredioasignado_set.all()
        if asignaciones.exists():
            return RadicadoPredioAsignadoSerializer(asignaciones, many=True).data
        return None

    def validate_numero_radicado(self, value):
        if Radicado.objects.filter(numero_radicado=value).exists():
            raise serializers.ValidationError(
                "Ya existe un radicado con este número"
            )
        return value

    def validate(self, data):
        if data.get('tipo_documento') and not data.get('numero_documento'):
            raise serializers.ValidationError(
                "Si se especifica el tipo de documento, debe proporcionar el número de documento"
            )
        return data

# Serializer para RadicadoPredioAsignado
class RadicadoPredioAsignadoSerializer(serializers.ModelSerializer):
    estado_asignacion = serializers.SerializerMethodField()
    mutacion = serializers.SerializerMethodField()
    usuario_analista = serializers.SerializerMethodField()
    usuario_coordinador = serializers.SerializerMethodField()
    predioo = serializers.SerializerMethodField()

    class Meta:
        model = RadicadoPredioAsignado
        fields = ['id', 'radicado', 'estado_asignacion_info', 'usuario_analista_info',
                 'usuario_coordinador_info', 'mutacion_info', 'predio_info']
        read_only_fields = ('id',)

    def get_estado_asignacion(self, obj):
        if obj.estado_asignacion:
            return {
                'id': obj.estado_asignacion.t_id,
                'ilicode': obj.estado_asignacion.ilicode,
                'description': obj.estado_asignacion.description
            }
        return None

    def get_mutacion(self, obj):
        if obj.mutacion:
            return {
                'id': obj.mutacion.t_id,
                'ilicode': obj.mutacion.ilicode,
                'description': obj.mutacion.description
            }
        return None

    def get_usuario_analista(self, obj):
        if obj.usuario_analista:
            return {
                'id': obj.usuario_analista.id,
                'username': obj.usuario_analista.username,
                'first_name': obj.usuario_analista.first_name,
                'last_name': obj.usuario_analista.last_name
            }
        return None

    def get_usuario_coordinador(self, obj):
        if obj.usuario_coordinador:
            return {
                'id': obj.usuario_coordinador.id,
                'username': obj.usuario_coordinador.username,
                'first_name': obj.usuario_coordinador.first_name,
                'last_name': obj.usuario_coordinador.last_name
            }
        return None

    def get_predio(self, obj):
        if obj.predio:
            return {
                'id': obj.predio.id,
                'numero_predial_nacional': obj.predio.numero_predial_nacional,
                'codigo_homologado': obj.predio.codigo_homologado,
                'direccion': obj.predio.direccion
            }
        return None

    def validate(self, data):
        # Validar que el usuario analista pertenece al grupo correcto
        if data.get('usuario_analista'):
            if not data['usuario_analista'].groups.filter(name='Analista').exists():
                raise serializers.ValidationError(
                    "El usuario asignado debe ser un analista"
                )
        
        # Validar que el usuario coordinador pertenece al grupo correcto
        if data.get('usuario_coordinador'):
            if not data['usuario_coordinador'].groups.filter(name='Coordinador').exists():
                raise serializers.ValidationError(
                    "El usuario asignado debe ser un coordinador"
                )

        # Validar que el radicado no esté ya asignado
        if RadicadoPredioAsignado.objects.filter(
            radicado=data.get('radicado'),
            predio=data.get('predio')
        ).exists():
            raise serializers.ValidationError(
                "Este predio ya está asignado a este radicado"
            )
                
        return data