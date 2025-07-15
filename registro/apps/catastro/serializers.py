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
    ColDocumentotipo,
    CrAutoreconocimientoetnicotipo,
    ColInteresadotipo,
    CrPrediotipo,
    CrCondicionprediotipo,
    CrDestinacioneconomicatipo,
    CrEstadotipo,
    ColUnidadadministrativabasicatipo,
    EstadoAsignacion,
    CrMutaciontipo,
    ColRelacionsuperficietipo,
    CrConstruccionplantatipo,
    User
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

class UnidadesSerializer(serializers.ModelSerializer):
    tipo_unidad_construccion = serializers.SlugRelatedField(
        queryset=CrUnidadconstrucciontipo.objects.all(),
        slug_field='ilicode'
    )
    uso = serializers.SlugRelatedField(
        queryset=CrUsouconstipo.objects.all(),
        slug_field='ilicode'
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
    tipo_interesado = serializers.SerializerMethodField()
    tipo_documento = serializers.SerializerMethodField()
    
    class Meta:
        model = Radicado
        fields = '__all__'


    def get_tipo_interesado(self, obj):
        if obj.tipo_interesado:
            return obj.tipo_interesado.ilicode
        return None
    
    def get_tipo_documento(self, obj):
        if obj.tipo_documento:
            return obj.tipo_documento.ilicode
        return None
    

        
class SerializerRadicado(serializers.Serializer):
    tipo_documento = serializers.CharField()
    tipo_interesado = serializers.CharField()
    numero_radicado = serializers.CharField()
    fecha_radicado = serializers.DateField()
    nombre_solicitante = serializers.CharField()
    numero_documento = serializers.CharField()
    oficio = serializers.CharField(allow_blank=True, required=False)

    def validate(self, data):
        tipo_documento = data.get('tipo_documento')
        tipo_interesado = data.get('tipo_interesado')
        numero_documento = data.get('numero_documento')
        numero_radicado = data.get('numero_radicado')

        # Validar existencia de ilicode en la base de datos
        try:
            doc = ColDocumentotipo.objects.get(ilicode=tipo_documento)
        except ColDocumentotipo.DoesNotExist:
            raise serializers.ValidationError({"tipo_documento": "Tipo de documento inválido (ilicode no encontrado)."})
 
        try:
            interesado = ColInteresadotipo.objects.get(ilicode=tipo_interesado)
        except ColInteresadotipo.DoesNotExist:
            raise serializers.ValidationError({"tipo_interesado": "Tipo de interesado inválido (ilicode no encontrado)."})

        # Validar número de radicado único solo si se está modificando
        instance = getattr(self, 'instance', None)
        if instance:
            # Si es una actualización, solo validar si el número de radicado está en los datos
            if 'numero_radicado' in data and numero_radicado != instance.numero_radicado:
                if Radicado.objects.filter(numero_radicado=numero_radicado).exclude(id=instance.id).exists():
                    raise serializers.ValidationError({"numero_radicado": "Ya existe un radicado con este número."})
        else:
            # Si es una creación, verificar que el número no exista
            if Radicado.objects.filter(numero_radicado=numero_radicado).exists():
                raise serializers.ValidationError({"numero_radicado": "Ya existe un radicado con este número."})

        # Validaciones usando ilicode directamente
        if tipo_interesado == "Persona_Natural":
            if tipo_documento == "NIT":
                raise serializers.ValidationError({
                    "tipo_documento": "Una Persona Natural no puede tener tipo de documento NIT."
                })
            elif tipo_documento == "Pasaporte":
                pass  # se permiten letras y números
            else:
                if not numero_documento.isdigit():
                    raise serializers.ValidationError({
                        "numero_documento": "Para Personas Naturales (excepto pasaporte), solo se permiten dígitos."
                    })

        elif tipo_interesado == "Persona_Juridica":
            if tipo_documento != "NIT":
                raise serializers.ValidationError({
                    "tipo_documento": "Una Persona Jurídica solo puede tener tipo de documento NIT."
                })
            if not re.fullmatch(r"[0-9\-]+", numero_documento):
                raise serializers.ValidationError({
                    "numero_documento": "Para Personas Jurídicas, solo se permiten números y guiones."
                })

        return data

    def create(self, validated_data):
        # Relacionar instancias reales por ilicode
        doc = ColDocumentotipo.objects.get(ilicode=validated_data['tipo_documento'])
        interesado = ColInteresadotipo.objects.get(ilicode=validated_data['tipo_interesado'])

        return Radicado.objects.create(
            tipo_documento=doc,
            tipo_interesado=interesado,
            numero_radicado=validated_data['numero_radicado'],
            fecha_radicado=validated_data['fecha_radicado'],
            nombre_solicitante=validated_data['nombre_solicitante'],
            numero_documento=validated_data['numero_documento'],
            oficio=validated_data.get('oficio', '')
        )
    
    def update(self, instance, validated_data):
         # Si se desea cambiar tipo_documento o tipo_interesado
        if 'tipo_documento' in validated_data:
            instance.tipo_documento = ColDocumentotipo.objects.get(ilicode=validated_data['tipo_documento'])
        if 'tipo_interesado' in validated_data:
            instance.tipo_interesado = ColInteresadotipo.objects.get(ilicode=validated_data['tipo_interesado'])
        
        instance.numero_radicado = validated_data.get('numero_radicado', instance.numero_radicado)
        instance.fecha_radicado = validated_data.get('fecha_radicado', instance.fecha_radicado)
        instance.nombre_solicitante = validated_data.get('nombre_solicitante', instance.nombre_solicitante)
        instance.numero_documento = validated_data.get('numero_documento', instance.numero_documento)
        instance.oficio = validated_data.get('oficio', instance.oficio)


        instance.save()
        return instance


#### ******************************SERIALIZER ASIGNAR RADICACION A PREDIO

class RadicadoPredioAsignadoSerializer(serializers.ModelSerializer):
    radicado_id= serializers.SerializerMethodField()
    numero_radicado = serializers.SerializerMethodField()
    predio_id = serializers.SerializerMethodField()
    numero_predial_nacional = serializers.SerializerMethodField()
    estado_asignacion = serializers.SerializerMethodField()
    mutacion = serializers.SerializerMethodField()
    usuario_analista = serializers.SerializerMethodField()
    usuario_coordinador = serializers.SerializerMethodField()

    class Meta:
        model = RadicadoPredioAsignado
        fields = [
            'id', 'radicado_id', 'numero_radicado', 'predio_id', 'numero_predial_nacional',
            'estado_asignacion', 'mutacion', 'usuario_analista',
            'usuario_coordinador'
        ]
    
    def get_radicado_id(self, obj):
        return obj.radicado.id if obj.radicado else None

    def get_numero_radicado(self, obj):
        return obj.radicado.numero_radicado if obj.radicado else None
    
    def get_predio_id(self, obj):
        return obj.predio.id if obj.predio else None
    
    def get_numero_predial_nacional(self, obj):
        return obj.predio.numero_predial_nacional if obj.predio else None

    def get_estado_asignacion(self, obj):
        return obj.estado_asignacion.ilicode if obj.estado_asignacion else None

    def get_mutacion(self, obj):
        return obj.mutacion.ilicode if obj.mutacion else None

    def get_usuario_analista(self, obj):
        if obj.usuario_analista:
            serializer = UserSerializer(obj.usuario_analista)
            return serializer.data['nombre_completo']
        return None

    def get_usuario_coordinador(self, obj):
        if obj.usuario_coordinador:
            serializer = UserSerializer(obj.usuario_coordinador)
            return serializer.data['nombre_completo']
        return None

class RadicadoPredioAsignadoEditSerializer(serializers.Serializer):
    numero_radicado = serializers.CharField()
    estado_asignacion = serializers.CharField(required=False, default="Pendiente")
    usuario_analista = serializers.CharField(required=False, allow_null=True)
    usuario_coordinador = serializers.CharField(required=False, allow_null=True)
    mutacion = serializers.CharField()
    numero_predial_nacional = serializers.CharField()

    def _get_user_full_name(self, full_name):
        if not full_name:
            return None
        
        try:
            # Buscar usuarios activos
            usuarios = User.objects.filter(is_active=True)
            
            # Usar el UserSerializer para obtener el nombre_completo de cada usuario
            for usuario in usuarios:
                serializer = UserSerializer(usuario)
                if serializer.data['nombre_completo'].lower() == full_name.lower():
                    return usuario
            
            return None
        except Exception as e:
            raise serializers.ValidationError(f"Error al buscar usuario: {str(e)}")

    def validate(self, data):
        # Validar que el radicado exista por número de radicado
        try:
            radicados = Radicado.objects.filter(numero_radicado=data['numero_radicado'])
            if not radicados.exists():
                raise serializers.ValidationError("El radicado no existe.")
            if radicados.count() > 1:
                raise serializers.ValidationError(
                    f"Existen múltiples radicados con el número {data['numero_radicado']}. Por favor, contacte al administrador."
                )
            radicado = radicados.first()
        except Exception as e:
            raise serializers.ValidationError(str(e))

        # Validar que el predio exista por NPN y esté en estado activo
        try:
            predio = Predio.objects.filter(
                numero_predial_nacional=data['numero_predial_nacional'],
                estado__ilicode='Activo'
            ).first()
            if not predio:
                raise serializers.ValidationError("El predio no existe o no está en estado activo.")
        except Exception as e:
            raise serializers.ValidationError(str(e))

        # Validar que el estado de asignación exista
        try:
            estado = EstadoAsignacion.objects.get(ilicode=data.get('estado_asignacion', 'Pendiente'))
        except EstadoAsignacion.DoesNotExist:
            raise serializers.ValidationError("El estado de asignación no existe.")

        # Validar que la mutación exista
        try:
            mutacion = CrMutaciontipo.objects.get(ilicode=data['mutacion'])
        except CrMutaciontipo.DoesNotExist:
            raise serializers.ValidationError("La mutación no existe.")

        # Validar y obtener usuarios si se proporcionan
        if data.get('usuario_analista'):
            usuario_analista = self._get_user_full_name(data['usuario_analista'])
            if not usuario_analista:
                raise serializers.ValidationError("No se encontró un usuario analista con ese nombre.")
            self.validated_analista = usuario_analista

        if data.get('usuario_coordinador'):
            usuario_coordinador = self._get_user_full_name(data['usuario_coordinador'])
            if not usuario_coordinador:
                raise serializers.ValidationError("No se encontró un usuario coordinador con ese nombre.")
            self.validated_coordinador = usuario_coordinador

        # Validar que no exista una asignación previa para este radicado y predio
        if not self.instance:  # Solo validar en creación
            if RadicadoPredioAsignado.objects.filter(
                radicado=radicado,
                predio=predio
            ).exists():
                raise serializers.ValidationError(
                    "Ya existe una asignación para este radicado y predio."
                )

        # Guardar el radicado y predio validados
        self.validated_radicado = radicado
        self.validated_predio = predio
        self.validated_estado = estado
        self.validated_mutacion = mutacion

        return data

    def create(self, validated_data):
        # Usar el radicado y predio ya validados
        radicado = self.validated_radicado
        predio = self.validated_predio
        estado = self.validated_estado
        mutacion = self.validated_mutacion
        
        # Usar los usuarios ya validados
        usuario_analista = getattr(self, 'validated_analista', None)
        usuario_coordinador = getattr(self, 'validated_coordinador', None)

        # Crear la asignación
        asignacion = RadicadoPredioAsignado.objects.create(
            radicado=radicado,
            predio=predio,
            estado_asignacion=estado,
            mutacion=mutacion,
            usuario_analista=usuario_analista,
            usuario_coordinador=usuario_coordinador
        )

        # Actualizar el estado de asignación del radicado
        radicado.asignado = True
        radicado.save()

        return asignacion
    
    def update(self, instance, validated_data):
        # Actualizar estado de asignación
        if 'estado_asignacion' in validated_data:
            instance.estado_asignacion = self.validated_estado

        # Actualizar mutación
        if 'mutacion' in validated_data:
            instance.mutacion = self.validated_mutacion

        # Actualizar usuarios
        if 'usuario_analista' in validated_data:
            instance.usuario_analista = getattr(self, 'validated_analista', None)
        
        if 'usuario_coordinador' in validated_data:
            instance.usuario_coordinador = getattr(self, 'validated_coordinador', None)

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
        estados_permitidos = ['Pendiente']  # Ajusta según tus estados
        if asignacion.estado_asignacion.ilicode not in estados_permitidos:
            raise serializers.ValidationError(
                f"No se puede procesar la mutación. Estado actual: {asignacion.estado_asignacion.ilicode}"
            )

        # Agregar instancias al contexto para uso posterior
        attrs['asignacion_instance'] = asignacion
        attrs['radicado_instance'] = asignacion.radicado
        attrs['mutacion_tipo'] = asignacion.mutacion.ilicode

        return attrs