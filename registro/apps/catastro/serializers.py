from rest_framework import serializers
from registro.apps.catastro.models import (
    Predio, CaracteristicasUnidadconstruccion, Unidadconstruccion, 
    Terreno, PredioUnidadespacial, CrCondicionprediotipo, TerrenoZonas, Interesado,InteresadoPredio,
    EstructuraAvaluo, Radicado, RadicadoPredioAsignado, EstadoAsignacion, CrMutaciontipo, ColDocumentotipo, ColInteresadotipo,
 ######******************DOMINIOS
    CrUnidadconstrucciontipo,
    CrUsouconstipo,
    CrDerechotipo,
    ColFuenteadministrativatipo,
    ColEstadodisponibilidadtipo,
    EnteEmisortipo,
    CrAutoreconocimientoetnicotipo,
    CrPrediotipo,
    CrDestinacioneconomicatipo,
    CrEstadotipo,
    ColUnidadadministrativabasicatipo,
    ColRelacionsuperficietipo,
    CrConstruccionplantatipo,
    User,
    TramiteCatastral,
    Historial_predio
)
from registro.apps.users.models import Rol_predio
from rest_framework_gis.serializers import GeoFeatureModelSerializer
import re
import logging
from django.template.loader import render_to_string
from django.http import HttpResponse
from weasyprint import HTML
from datetime import datetime
from rest_framework.exceptions import ValidationError, APIException

logger = logging.getLogger(__name__)

class CaracteristicasUnidadconstruccionSerializer(serializers.ModelSerializer):
    uso = serializers.SlugRelatedField(
        queryset=CrUsouconstipo.objects.all(),
        slug_field='t_id'
    )
    tipo_unidad_construccion = serializers.SlugRelatedField(
        queryset=CrUnidadconstrucciontipo.objects.all(),
        slug_field='t_id'
    )

    class Meta:
        model = CaracteristicasUnidadconstruccion
        fields = [
            'identificador', 'tipo_unidad_construccion',
            'total_plantas', 'uso', 'anio_construccion',
            'area_construida', 'estado_conservacion', 
            'avaluo_unidad', 'puntaje'
        ]

class UnidadesSerializer(serializers.ModelSerializer):
    tipo_unidad_construccion = serializers.SlugRelatedField(
        queryset=CrUnidadconstrucciontipo.objects.all(),
        slug_field='t_id'
    )
    uso = serializers.SlugRelatedField(
        queryset=CrUsouconstipo.objects.all(),
        slug_field='t_id'
    )
    class Meta:
        model = CaracteristicasUnidadconstruccion
        fields = [
            'identificador',
            'total_plantas',
            'anio_construccion',
            'avaluo_unidad',
            'area_construida',
            'estado_conservacion',
            'puntaje',
            'tipo_unidad_construccion',
            'uso'
        ]

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
        fields = ['id','local_id']

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
    tipo_documento = serializers.SlugRelatedField(
        queryset=ColDocumentotipo.objects.all(),
        slug_field='t_id'
    )
    sexo = serializers.CharField(source='sexo.ilicode', read_only=True)
    autoreconocimientoetnico = serializers.SlugRelatedField(
        queryset=CrAutoreconocimientoetnicotipo.objects.all(),
        slug_field='t_id'
    )
    tipo_interesado = serializers.SlugRelatedField(
        queryset=ColInteresadotipo.objects.all(),
        slug_field='t_id'
    )

    class Meta:
        model = Interesado
        fields = [
            'tipo_documento', 'primer_nombre', 'segundo_nombre',
            'primer_apellido', 'segundo_apellido', 'sexo',
            'autoreconocimientoetnico', 'autoreconocimientocampesino',
            'razon_social', 'nombre', 'tipo_interesado', 'numero_documento'
        ]


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
    condicion_predio = serializers.SlugRelatedField(
        queryset=CrCondicionprediotipo.objects.all(),
        slug_field='t_id'
    )
    destinacion_economica = serializers.SlugRelatedField(
        queryset=CrDestinacioneconomicatipo.objects.all(),
        slug_field='t_id'
    )
    estado = serializers.SlugRelatedField(
        queryset=CrEstadotipo.objects.all(),
        slug_field='t_id'
    )
    tipo = serializers.CharField(source='tipo.ilicode', read_only=True)
    tipo_predio = serializers.SlugRelatedField(
        queryset=CrPrediotipo.objects.all(),
        slug_field='t_id'
    )
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

    def generate_pdf(self, data, numero_predial):
        """
        Genera un PDF con la información del predio.
        
        Args:
            data (dict): Datos serializados del predio
            numero_predial (str): Número predial del predio
            
        Returns:
            HttpResponse: Respuesta HTTP con el PDF generado
        """
        try:
            # Validar datos críticos
            if not data or not numero_predial:
                raise ValueError("Datos del predio o número predial no proporcionados")

            # Configuración del PDF
            pdf_options = {
                'page-size': 'A4',
                'margin-top': '2cm',
                'margin-right': '2cm',
                'margin-bottom': '2cm',
                'margin-left': '2cm',
                'encoding': 'UTF-8',
            }

            # Preparar metadatos
            metadata = {
                'title': f'Información del Predio {numero_predial}',
                'author': 'Sistema de Catastro',
                'creation_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            }

            # Organizar datos para el template
            template_data = {
                'predio': data,
                'fecha_generacion': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
                'metadata': metadata,
                'departamento': data.get('departamento'),
                'municipio': data.get('municipio'),
                'direccion': data.get('direccion'),
                'area_total': data.get('area_catastral_terreno'),
                'estado': data.get('estado'),
                'tipo_predio': data.get('tipo_predio'),
                'condicion': data.get('condicion_predio'),
                'destinacion': data.get('destinacion_economica'),
                'interesados': data.get('interesado', []),
                'avaluos': data.get('avaluo', []),
                'terrenos': data.get('terreno_geo', []),
                'construcciones': data.get('unidades_construccion_geo', [])
            }

            # Renderizar template
            html_string = render_to_string(
                'catastro/predio_pdf.html',
                template_data
            )

            # Generar PDF con configuración
            html = HTML(string=html_string)
            pdf = html.write_pdf(
                stylesheets=[],
                **pdf_options
            )

            # Crear respuesta HTTP
            response = HttpResponse(pdf, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="predio_{numero_predial}.pdf"'
            
            # Agregar metadatos a la respuesta
            response['X-PDF-Title'] = metadata['title']
            response['X-PDF-Author'] = metadata['author']
            response['X-PDF-Creation-Date'] = metadata['creation_date']

            return response

        except ValueError as ve:
            logger.error(f"Error de validación al generar PDF: {str(ve)}")
            raise ValidationError(str(ve))
        except Exception as e:
            logger.error(f"Error al generar PDF: {str(e)}", exc_info=True)
            raise APIException("Error al generar el PDF del predio")

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

    def get_interesado(self, obj):
        instance = InteresadoPredio.objects.filter(predio=obj)
        if instance.exists():
            instance_interesado = [instance.interesado for instance in instance]
            return InteresadoSerializer(instance_interesado, many=True).data
        return None


#### ******************************SERIALIZER PARA DOMINIOS

class CrUnidadconstrucciontipoSerializer(serializers.ModelSerializer):
    class Meta:
        model = CrUnidadconstrucciontipo
        fields = '__all__'

class CrUsouconstipoSerializer(serializers.ModelSerializer):
    class Meta:
        model = CrUsouconstipo
        fields = '__all__'

class CrDerechotipoSerializer(serializers.ModelSerializer):
    class Meta:
        model = CrDerechotipo
        fields = '__all__'

class ColFuenteadministrativatipoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ColFuenteadministrativatipo
        fields = '__all__'

class ColEstadodisponibilidadtipoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ColEstadodisponibilidadtipo
        fields = '__all__'

class EnteEmisortipoSerializer(serializers.ModelSerializer):
    class Meta:
        model = EnteEmisortipo
        fields = '__all__'

class ColDocumentotipoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ColDocumentotipo
        fields = '__all__'

class CrAutoreconocimientoetnicotipoSerializer(serializers.ModelSerializer):
    class Meta:
        model = CrAutoreconocimientoetnicotipo
        fields = '__all__'

class ColInteresadotipoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ColInteresadotipo
        fields = '__all__'

class CrPrediotipoSerializer(serializers.ModelSerializer):
    class Meta:
        model = CrPrediotipo
        fields = '__all__'

class CrCondicionprediotipoSerializer(serializers.ModelSerializer):
    class Meta:
        model = CrCondicionprediotipo
        fields = '__all__'

class CrDestinacioneconomicatipoSerializer(serializers.ModelSerializer):
    class Meta:
        model = CrDestinacioneconomicatipo
        fields = '__all__'

class CrEstadotipoSerializer(serializers.ModelSerializer):
    class Meta:
        model = CrEstadotipo
        fields = '__all__'

class ColUnidadadministrativabasicatipoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ColUnidadadministrativabasicatipo
        fields = '__all__'

class EstadoAsignacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = EstadoAsignacion
        fields = '__all__'

class CrMutaciontipoSerializer(serializers.ModelSerializer):
    class Meta:
        model = CrMutaciontipo
        fields = '__all__'

class ColRelacionsuperficietipoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ColRelacionsuperficietipo
        fields = '__all__'

class CrConstruccionplantatipoSerializer(serializers.ModelSerializer):
    class Meta:
        model = CrConstruccionplantatipo
        fields = '__all__'
        
class UserSerializer(serializers.ModelSerializer):
    nombre_completo = serializers.SerializerMethodField()
    rol = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email','nombre_completo', 'rol']

    def get_nombre_completo(self, obj):
        if obj.first_name and obj.last_name:
            return f"{obj.first_name} {obj.last_name}"
        return obj.username
    
    def get_rol(self, obj):
        # Usamos el prefetch_related que se hizo en la vista para eficiencia
        return [rol_predio.rol.name for rol_predio in obj.rol_predio_set.all() if rol_predio.rol]


#### ******************************SERIALIZER PARA RADICACION 

class RadicadoListSerializer(serializers.ModelSerializer):
    tipo_interesado = serializers.SlugRelatedField(
        queryset=ColInteresadotipo.objects.all(),
        slug_field='t_id'
    )
    tipo_documento = serializers.SlugRelatedField(
        queryset=ColDocumentotipo.objects.all(),
        slug_field='t_id'
    )
    
    class Meta:
        model = Radicado
        fields = '__all__'

        
class SerializerRadicado(serializers.Serializer):
    tipo_documento = serializers.IntegerField()
    tipo_interesado = serializers.IntegerField()
    numero_radicado = serializers.CharField()
    fecha_radicado = serializers.DateField()
    nombre_solicitante = serializers.CharField()
    numero_documento = serializers.CharField()
    oficio = serializers.BooleanField(required=False)

    class Meta:
        list_serializer_class = RadicadoListCreateSerializer

    def validate(self, data):
        # Validar tipo_documento por ID
        try:
            tipo_doc_id = data.get('tipo_documento')
            tipo_documento_instance = ColDocumentotipo.objects.get(t_id=tipo_doc_id)
            data['tipo_documento_instance'] = tipo_documento_instance
        except ColDocumentotipo.DoesNotExist:
            raise ValidationError({'tipo_documento': 'ID de tipo de documento inválido.'})

        # Validar tipo_interesado por ID
        try:
            tipo_interesado_id = data.get('tipo_interesado')
            tipo_interesado_instance = ColInteresadotipo.objects.get(t_id=tipo_interesado_id)
            data['tipo_interesado_instance'] = tipo_interesado_instance
        except ColInteresadotipo.DoesNotExist:
            raise ValidationError({'tipo_interesado': 'ID de tipo de interesado inválido.'})

        # --- VALIDACIONES DE NEGOCIO RESTAURADAS ---
        numero_radicado = data.get('numero_radicado')
        numero_documento = data.get('numero_documento')

        # Validar número de radicado único
        instance = getattr(self, 'instance', None)
        query = Radicado.objects.filter(numero_radicado=numero_radicado)
        if instance:
            query = query.exclude(id=instance.id)
        if query.exists():
            raise ValidationError({"numero_radicado": "Ya existe un radicado con este número."})

        # Validaciones de consistencia entre tipo de interesado y tipo de documento
        # Asumiendo IDs: Persona_Natural=1, Persona_Juridica=2, NIT=3, Pasaporte=4
        if tipo_interesado_instance.t_id == 6: # Persona_Natural
            if tipo_documento_instance.t_id == 302: # NIT
                raise ValidationError({
                    "tipo_documento": "Una Persona Natural no puede tener tipo de documento NIT."
                })
            # Permitir letras y números para Pasaporte, solo dígitos para los demás
            if tipo_documento_instance.t_id != 303 and not numero_documento.isdigit(): # Pasaporte
                raise ValidationError({
                    "numero_documento": "Para Personas Naturales (excepto pasaporte), el documento solo debe contener números."
                })

        elif tipo_interesado_instance.t_id == 7: # Persona_Juridica
            if tipo_documento_instance.t_id != 302: # NIT
                raise ValidationError({
                    "tipo_documento": "Una Persona Jurídica solo puede tener tipo de documento NIT."
                })
            # Validar formato de NIT (números y guion opcional)
            if not re.fullmatch(r"[0-9\-]+", numero_documento):
                 raise ValidationError({
                     "numero_documento": "Para Personas Jurídicas, el NIT solo debe contener números y un guion."
                 })

        return data

    def create(self, validated_data):
        try:
            radicado_obj = Radicado.objects.create(
                numero_radicado=validated_data['numero_radicado'],
                fecha_radicado=validated_data['fecha_radicado'],
                nombre_solicitante=validated_data['nombre_solicitante'],
                numero_documento=validated_data['numero_documento'],
                oficio=validated_data.get('oficio', False),
                tipo_documento=validated_data['tipo_documento_instance'],
                tipo_interesado=validated_data['tipo_interesado_instance']
            )
            return radicado_obj
        except Exception as e:
            raise APIException(f"Error al crear el radicado: {str(e)}")

    def update(self, instance, validated_data):
        instance.numero_radicado = validated_data.get('numero_radicado', instance.numero_radicado)
        instance.fecha_radicado = validated_data.get('fecha_radicado', instance.fecha_radicado)
        instance.nombre_solicitante = validated_data.get('nombre_solicitante', instance.nombre_solicitante)
        instance.numero_documento = validated_data.get('numero_documento', instance.numero_documento)
        instance.oficio = validated_data.get('oficio', instance.oficio)
        
        # Actualizar relaciones si se proporcionaron IDs
        if 'tipo_documento_instance' in validated_data:
            instance.tipo_documento = validated_data['tipo_documento_instance']
        if 'tipo_interesado_instance' in validated_data:
            instance.tipo_interesado = validated_data['tipo_interesado_instance']
            
        instance.save()
        return instance


#### ******************************SERIALIZER ASIGNAR RADICACION A PREDIO

class RadicadoPredioAsignadoSerializer(serializers.ModelSerializer):
    radicado_id= serializers.SerializerMethodField()
    numero_radicado = serializers.SerializerMethodField()
    predio_id = serializers.SerializerMethodField()
    numero_predial_nacional = serializers.SerializerMethodField()
    estado_asignacion = serializers.SlugRelatedField(
        queryset=EstadoAsignacion.objects.all(),
        slug_field='t_id'
    )
    mutacion = serializers.SlugRelatedField(
        queryset=CrMutaciontipo.objects.all(),
        slug_field='t_id'
    )
    usuario_analista = serializers.SerializerMethodField()
    usuario_coordinador = serializers.SerializerMethodField()
    tramite_catastral_id = serializers.SerializerMethodField()

    class Meta:
        model = RadicadoPredioAsignado
        fields = [
            'id', 'radicado_id', 'numero_radicado', 'predio_id', 'numero_predial_nacional',
            'estado_asignacion', 'mutacion', 'usuario_analista',
            'usuario_coordinador', 'tramite_catastral_id'
        ]
    
    def get_radicado_id(self, obj):
        return obj.radicado.id if obj.radicado else None

    def get_numero_radicado(self, obj):
        return obj.radicado.numero_radicado if obj.radicado else None
    
    def get_predio_id(self, obj):
        return obj.predio.id if obj.predio else None
    
    def get_numero_predial_nacional(self, obj):
        return obj.predio.numero_predial_nacional if obj.predio else None

    def get_usuario_analista(self, obj):
        if obj.usuario_analista:
            serializer = UserSerializer(obj.usuario_analista)
            return serializer.data['nombre_completo']
        return None

    def get_usuario_coordinador(self, obj):
        if obj.usuario_coordinador:
            return f"{obj.usuario_coordinador.first_name} {obj.usuario_coordinador.last_name}"
        return None

    def get_tramite_catastral_id(self, obj):
        """
        Obtiene el ID del trámite catastral más reciente asociado a esta asignación.
        """
        tramite = TramiteCatastral.objects.filter(radicado_asignado=obj).order_by('-id').first()
        if tramite:
            return tramite.id
        return None

class RadicadoPredioAsignadoListCreateSerializer(serializers.ListSerializer):
    def create(self, validated_data):
        asignaciones = [self.child.create(item) for item in validated_data]
        return asignaciones

class RadicadoPredioAsignadoEditSerializer(serializers.Serializer):
    numero_radicado = serializers.CharField()
    estado_asignacion = serializers.IntegerField()
    usuario_analista = serializers.IntegerField(required=False, allow_null=True)
    usuario_coordinador = serializers.IntegerField(required=False, allow_null=True)
    mutacion = serializers.IntegerField()
    numero_predial_nacional = serializers.CharField()

    class Meta:
        list_serializer_class = RadicadoPredioAsignadoListCreateSerializer

    def _get_user_by_id(self, user_id):
        if not user_id:
            return None
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None

    def validate(self, data):
        # Validar radicado
        try:
            radicado_instance = Radicado.objects.get(numero_radicado=data['numero_radicado'])
            data['radicado_instance'] = radicado_instance
        except Radicado.DoesNotExist:
            raise ValidationError({'numero_radicado': f"El radicado '{data['numero_radicado']}' no existe."})

        # Validar estado de asignación
        try:
            estado_id = data['estado_asignacion']
            estado_asignacion_instance = EstadoAsignacion.objects.get(t_id=estado_id)
            data['estado_asignacion_instance'] = estado_asignacion_instance
        except EstadoAsignacion.DoesNotExist:
            raise ValidationError({'estado_asignacion': f"El estado de asignación con ID '{estado_id}' no es válido."})

        # Validar usuarios por ID
        usuario_analista_id = data.get('usuario_analista')
        usuario_coordinador_id = data.get('usuario_coordinador')
        
        analista_instance = self._get_user_by_id(usuario_analista_id)
        coordinador_instance = self._get_user_by_id(usuario_coordinador_id)

        if usuario_analista_id and not analista_instance:
            raise ValidationError({'usuario_analista': f"El usuario analista con ID '{usuario_analista_id}' no existe."})
        
        if usuario_coordinador_id and not coordinador_instance:
            raise ValidationError({'usuario_coordinador': f"El usuario coordinador con ID '{usuario_coordinador_id}' no existe."})

        data['usuario_analista_instance'] = analista_instance
        data['usuario_coordinador_instance'] = coordinador_instance

        # Validar mutación por ID
        try:
            mutacion_id = data['mutacion']
            mutacion_instance = CrMutaciontipo.objects.get(t_id=mutacion_id)
            data['mutacion_instance'] = mutacion_instance
        except CrMutaciontipo.DoesNotExist:
            raise ValidationError({'mutacion': f"El tipo de mutación con ID '{mutacion_id}' no es válido."})
        except KeyError:
            raise ValidationError({'mutacion': 'El campo mutación es obligatorio.'})

        # Validar predio
        try:
            predio_instance = Predio.objects.get(numero_predial_nacional=data['numero_predial_nacional'])
            data['predio_instance'] = predio_instance
        except Predio.DoesNotExist:
            raise ValidationError({'numero_predial_nacional': f"El predio '{data['numero_predial_nacional']}' no existe."})

        return data

    def create(self, validated_data):
        radicado_instance = validated_data['radicado_instance']
        predio_instance = validated_data['predio_instance']

        # Verificar si ya existe una asignación para este radicado y predio
        if RadicadoPredioAsignado.objects.filter(radicado=radicado_instance, predio=predio_instance).exists():
            raise ValidationError(f"El predio {predio_instance.numero_predial_nacional} ya está asignado al radicado {radicado_instance.numero_radicado}.")

        asignacion = RadicadoPredioAsignado.objects.create(
            radicado=radicado_instance,
            estado_asignacion=validated_data['estado_asignacion_instance'],
            usuario_analista=validated_data['usuario_analista_instance'],
            usuario_coordinador=validated_data['usuario_coordinador_instance'],
            mutacion=validated_data['mutacion_instance'],
            predio=predio_instance
        )
        return asignacion

    def update(self, instance, validated_data):
        # Actualizar estado de asignación
        if 'estado_asignacion_instance' in validated_data:
            instance.estado_asignacion = validated_data['estado_asignacion_instance']

        # Actualizar usuarios
        if 'usuario_analista' in validated_data:
            instance.usuario_analista = validated_data.get('usuario_analista_instance')

        if 'usuario_coordinador' in validated_data:
            instance.usuario_coordinador = validated_data.get('usuario_coordinador_instance')

        # Actualizar mutación
        if 'mutacion_instance' in validated_data:
            instance.mutacion = validated_data['mutacion_instance']

        instance.save()
        return instance

class MutacionRadicadoValidationSerializer(serializers.Serializer):
    """
    Serializer para validar radicado y asignación antes de procesar mutaciones.
    Valida que:
    - El radicado exista
    - La asignación exista
    - El usuario que hace la petición sea el analista asignado
    - El estado de asignación permita la operación
    """
    radicado_id = serializers.IntegerField(
        help_text="ID del radicado"
    )
    asignacion_id = serializers.IntegerField(
        help_text="ID de la asignación del radicado al predio"
    )
    mutacion = serializers.JSONField(
        help_text="Datos de la mutación a procesar"
    )

    def validate_radicado_id(self, value):
        """Valida que el radicado exista"""
        try:
            radicado = Radicado.objects.get(id=value)
            return value
        except Radicado.DoesNotExist:
            raise serializers.ValidationError(f"No existe un radicado con ID {value}")

    def validate_asignacion_id(self, value):
        """Valida que la asignación exista"""
        try:
            asignacion = RadicadoPredioAsignado.objects.get(id=value)
            return value
        except RadicadoPredioAsignado.DoesNotExist:
            raise serializers.ValidationError(f"No existe una asignación con ID {value}")

    def validate(self, attrs):
        """Validación cruzada entre radicado, asignación y usuario"""
        radicado_id = attrs.get('radicado_id')
        asignacion_id = attrs.get('asignacion_id')
        
        # Obtener la asignación
        try:
            asignacion = RadicadoPredioAsignado.objects.select_related(
                'radicado', 'estado_asignacion', 'mutacion', 'predio', 'usuario_analista'
            ).get(id=asignacion_id)
        except RadicadoPredioAsignado.DoesNotExist:
            raise serializers.ValidationError("La asignación especificada no existe")

        # Validar que la asignación corresponde al radicado
        if asignacion.radicado.id != radicado_id:
            raise serializers.ValidationError(
                f"La asignación {asignacion_id} no corresponde al radicado {radicado_id}"
            )

        # Validar que el usuario actual sea el analista asignado
        request = self.context.get('request')
        if request and request.user:
            if not asignacion.usuario_analista:
                raise serializers.ValidationError(
                    "Esta asignación no tiene un analista asignado"
                )
            
            if asignacion.usuario_analista.id != request.user.id:
                raise serializers.ValidationError(
                    "No tienes permisos para procesar esta asignación. "
                    "Solo el analista asignado puede procesar la mutación."
                )

        # Validar estado de asignación (opcional - puedes ajustar según tu lógica)
        # Asumiendo que el t_id de 'Pendiente' es 1
        estados_permitidos_ids = [1] 
        if asignacion.estado_asignacion.t_id not in estados_permitidos_ids:
            raise serializers.ValidationError(
            )

        # Agregar instancias al contexto para uso posterior
        attrs['asignacion_instance'] = asignacion
        attrs['radicado_instance'] = asignacion.radicado
        attrs['mutacion_tipo'] = asignacion.mutacion.t_id

        return attrs


class ResolucionPredioDataSerializer(serializers.ModelSerializer):
    """Serializer para la información específica de un predio en la resolución."""
    avaluo = EstructuraAvaluoSerializer(many=True, source='estructuraavaluo_set')
    interesado = serializers.SerializerMethodField()
    destinacion_economica = serializers.IntegerField(source='destinacion_economica.t_id', read_only=True)
    matricula_inmobiliaria = serializers.SerializerMethodField()
    
    class Meta:
        model = Predio
        fields = [
            'numero_predial_nacional',
            'direccion',
            'matricula_inmobiliaria',
            'destinacion_economica',
            'avaluo',
            'interesado'
        ]
        
    def get_matricula_inmobiliaria(self, obj):
        if obj.codigo_orip and obj.matricula_inmobiliaria:
            return f"{obj.codigo_orip}-{obj.matricula_inmobiliaria}"
        return "N/A"
    
    def get_interesado(self, obj):
        # El modelo Predio no tiene una relación directa 'interesadopredio_set'
        # La relación está en InteresadoPredio.
        interesados_predio = InteresadoPredio.objects.filter(predio=obj)
        interesados = [ip.interesado for ip in interesados_predio]
        return InteresadoSerializer(interesados, many=True).data

class ResolucionSerializer(serializers.ModelSerializer):
    """
    Serializer para orquestar los datos necesarios para el PDF de la resolución.
    """
    predio_cancelado = serializers.SerializerMethodField()
    predios_inscritos = serializers.SerializerMethodField()
    
    class Meta:
        model = TramiteCatastral
        fields = [
            'numero_resolucion',
            'fecha_resolucion',
            'predio_cancelado',
            'predios_inscritos'
        ]
        
    def get_predio_cancelado(self, obj):
        """Obtiene y serializa la información del predio original (el que se cancela)."""
        if not obj.radicado_asignado or not obj.radicado_asignado.predio:
            return None
        predio_original = obj.radicado_asignado.predio
        return ResolucionPredioDataSerializer(predio_original).data

    def get_predios_inscritos(self, obj):
        """Obtiene y serializa la información de los nuevos predios (los que se inscriben)."""
        historial_entries = Historial_predio.objects.filter(
            predio_tramitecatastral__tramite_catastral=obj
        ).select_related('predio')
        
        predios_novedad_ids = historial_entries.values_list('predio_id', flat=True).distinct()
        predios_novedad = Predio.objects.filter(id__in=predios_novedad_ids)
        
        return ResolucionPredioDataSerializer(predios_novedad, many=True).data