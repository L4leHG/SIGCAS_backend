from rest_framework import serializers
from registro.apps.catastro.models import (
    Predio, CaracteristicasUnidadconstruccion, Unidadconstruccion, 
    Terreno, PredioUnidadespacial, CrCondicionprediotipo, TerrenoZonas, Interesado,InteresadoPredio,
    EstructuraAvaluo
)

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

class UnidadConstruccionSerializer(serializers.ModelSerializer):
    caracteristicas_unidadconstruccion = CaracteristicasUnidadconstruccionSerializer()

    class Meta:
        model = Unidadconstruccion
        fields = [
            'planta_ubicacion', 'altura', 'caracteristicas_unidadconstruccion',
            'geometria'
        ]
    
class CaracteristicasUnidadconstruccionAlfaSerializer(serializers.ModelSerializer):
    class Meta:
        model = CaracteristicasUnidadconstruccion
        fields = ['identificador']


class TerrenoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Terreno
        fields = ['geometria']

    
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

    class Meta:
        model = Predio
        fields = [
            'id', 'numero_predial_nacional', 'codigo_homologado',
            'departamento', 'municipio', 'matricula_inmobiliaria',
            'condicion_predio', 'destinacion_economica',
            'area_catastral_terreno', 'vigencia_actualizacion_catastral',
            'estado', 'tipo', 'direccion', 'tipo_predio',
            'terreno_geo', 'terreno_alfa', 'unidades_construccion_geo', 'interesado',
            'avaluo'
        ]

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
