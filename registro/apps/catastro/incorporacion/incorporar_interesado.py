from rest_framework.serializers import ModelSerializer
from re import compile
from datetime import date, datetime

from registro.apps.catastro.models import (Predio, Interesado, 
InteresadoPredio, CrEstadotipo, FuenteAdministrativa,
CrMutaciontipo, TramiteCatastral, PredioTramitecatastral,
PredioFuenteadministrativa, EnteEmisortipo, ColEstadodisponibilidadtipo, ColFuenteadministrativatipo, ColDocumentotipo, ColInteresadotipo,
CrSexotipo, Historial_predio, CrAutoreconocimientoetnicotipo
) 
from registro.apps.catastro.serializers import InteresadoSerializer as InteresadoModelSerializer

from rest_framework.serializers import ValidationError


class FuenteAdministrativaSerializer(ModelSerializer):
    
    class Meta:
        model = FuenteAdministrativa
        fields = '__all__'
        depth = 1

class InteresadoSerializer(ModelSerializer):
    
    class Meta:
        model = Interesado
        fields = '__all__'
        depth = 1

class InteresadoPredioSerializer(ModelSerializer):
    
    class Meta:
        model = InteresadoPredio
        fields = '__all__'
        depth = 1

class IncorporarInteresadoSerializer():

    def validar_caracteres_especiales_nombre(self, cadena):
        # Definimos una expresión regular que busca caracteres no alfabéticos o numéricos
        patron = compile(r'[^a-zA-ZñÑáéíóúÁÉÍÓÚ\t ]')
        # Usamos re.search para buscar coincidencias en la cadena
        if patron.search(str(cadena)):
            return True  # Si se encuentra un carácter extraño, devolvemos False
        
        return False

    def validar_caracteres_especiales_razon_social(self, cadena):
        # Definimos una expresión regular que busca caracteres no alfabéticos o numéricos
        if cadena:
            patron = compile(r'[^0-9a-zA-ZñÑáéíóúÁÉÍÓÚ\t\s\-.&()]')
            # Usamos re.search para buscar coincidencias en la cadena
            if patron.search(str(cadena)):
                return True  # Si se encuentra un carácter extraño, devolvemos False
            return False
        return False
    def validar_caracteres_especiales_nit(self, cadena):
        # Definimos una expresión regular que busca caracteres no alfabéticos o numéricos
        if cadena:
            patron = compile(r'[^0-9\-]')
            # Usamos re.search para buscar coincidencias en la cadena
            if patron.search(str(cadena)):
                return True  # Si se encuentra un carácter extraño, devolvemos False
        return False
    
    def validar_caracteres_especiales_cedula(self, cadena):
        # Definimos una expresión regular que busca caracteres no alfabéticos o numéricos
        if cadena:
            patron = compile(r'[^0-9]')
            # Usamos re.search para buscar coincidencias en la cadena
            if patron.search(str(cadena)):
                return True  # Si se encuentra un carácter extraño, devolvemos False
        return False
    
    def validar_caracteres_especiales_pasaporte(self, cadena):
        # Definimos una expresión regular que busca caracteres no alfabéticos o numéricos
        if cadena:
            patron = compile(r'[^A-Z0-9]')
            # Usamos re.search para buscar coincidencias en la cadena
            if patron.search(str(cadena)):
                return True  # Si se encuentra un carácter extraño, devolvemos False
        return False
    
    def validar_solo_numero(self, cadena):
        # Definimos una expresión regular que busca caracteres no alfabéticos o numéricos
        #patron = re.compile(r'[^a-zA-Z1-9ñÑ\-]')
        if cadena:
            patron = compile(r'[^1-9|1\d]')
            #patron = compile(r'[^[2-9]|1\d|[12]\d{0,1}|30]')
            #patron = re.compile(r'\bfoo\b')
            # Usamos re.search para buscar coincidencias en la cadena
            if patron.search(str(cadena)):
                return True  # Si se encuentra un carácter extraño, devolvemos False
        return False

    def create_resolucion_predio(self, list_json):
        """
        Crea una instancia de PredioTramitecatastral con los datos proporcionados.
        
        Args:
            list_json (dict): Diccionario con las claves:
                - predio: Instancia del predio
                - tramite_catastral: Instancia del TramiteCatastral 
                - radicado_asignado: Instancia del RadicadoPredioAsignado
        
        Returns:
            PredioTramitecatastral: Instancia creada
        """
        # Validar que se proporcionen los datos necesarios
        if not list_json.get('predio'):
            raise ValidationError("Se requiere una instancia de predio")
        
        if not list_json.get('tramite_catastral'):
            raise ValidationError("Se requiere una instancia de tramite_catastral")
        
        if not list_json.get('radicado_asignado'):
            raise ValidationError("Se requiere una instancia de radicado_asignado")
        
        # Crear la instancia con los datos proporcionados
        instancia_resolucion_predio = PredioTramitecatastral(
            predio=list_json['predio'],
            tramite_catastral=list_json['tramite_catastral'],
            radicado_asignado=list_json['radicado_asignado']
        )
        instancia_resolucion_predio.save()
        print(f"DEBUG: PredioTramitecatastral creado ID: {instancia_resolucion_predio.id}")
        
        return instancia_resolucion_predio
    
    
    def create_Predio_fuenteadministrativa(self, validate_data):
        """
        Crea una relación entre un predio y una fuente administrativa.
        
        Args:
            validate_data (dict): Diccionario con 'predio' y 'fuenteadministrativa'
            
        Returns:
            PredioFuenteadministrativa: Instancia creada
        """
        instancia_fteadmin_predio = PredioFuenteadministrativa(**validate_data)
        instancia_fteadmin_predio.save()

        return instancia_fteadmin_predio

    def reutilizar_fuente_administrativa_existente(self, instance_predio, instance_predio_actual):
        """
        Reutiliza la fuente administrativa del predio actual (activo) para el nuevo predio (novedad).
        
        Este método busca la fuente administrativa más reciente asociada al predio actual
        y crea una nueva relación PredioFuenteadministrativa con el nuevo predio.
        
        Es útil para procesos de mutación donde se requiere mantener la misma fuente
        administrativa pero asociarla a un nuevo predio en estado de novedad.
        
        Args:
            instance_predio (Predio): Instancia del nuevo predio (novedad)
            instance_predio_actual (Predio): Instancia del predio actual (activo)
            
        Returns:
            PredioFuenteadministrativa: Instancia creada o None si no se pudo crear
        """
        if not instance_predio_actual:
            return None
            
        try:
            # Buscar la fuente administrativa más reciente relacionada con el predio actual
            relacion_fuente_actual = PredioFuenteadministrativa.objects.filter(
                predio=instance_predio_actual
            ).select_related('fuenteadministrativa').order_by('-id').first()
            
            if relacion_fuente_actual and relacion_fuente_actual.fuenteadministrativa:
                # Crear nueva relación con la misma fuente administrativa
                nueva_relacion = self.create_Predio_fuenteadministrativa({
                    'predio': instance_predio,
                    'fuenteadministrativa': relacion_fuente_actual.fuenteadministrativa
                })
                return nueva_relacion
                
        except Exception as e:
            # Si hay error al reutilizar la fuente existente, retornar None
            # El proceso puede continuar sin fuente administrativa en algunos casos
            pass
        
        return None

    def es_fuente_administrativa_vacia(self, fuente_administrativa):
        """
        Verifica si la fuente administrativa está vacía o no tiene datos válidos.
        
        Casos considerados como vacíos:
        - None
        - Diccionario vacío {}
        - Diccionario con todos los campos vacíos o None
        
        Args:
            fuente_administrativa (dict|None): Datos de la fuente administrativa
            
        Returns:
            bool: True si está vacía, False si tiene datos válidos
        """
        # Caso 1: None o falsy
        if not fuente_administrativa:
            return True
        
        # Caso 2: Diccionario vacío
        if not fuente_administrativa or len(fuente_administrativa) == 0:
            return True
            
        # Caso 3: Diccionario con campos pero todos vacíos
        campos_obligatorios = ['oficina_origen', 'fecha_documento_fuente', 'numero_documento', 
                               'ente_emisor', 'estado_disponibilidad', 'tipo']
        
        # Verificar si todos los campos obligatorios están vacíos
        for campo in campos_obligatorios:
            valor = fuente_administrativa.get(campo)
            if valor and str(valor).strip():  # Si tiene valor y no es solo espacios
                return False
        
        return True
    
    def create_fuenteadministrativa(self, validate_data):
        fuente_admin= validate_data

        if fuente_admin:
            oficina_origen= fuente_admin.get('oficina_origen')
            # ciudad_origen= fuente_admin.get('ciudad_origen')
            fecha_documento= fuente_admin.get('fecha_documento_fuente')  # Corregido: usar el nombre correcto del campo
            numero_documento= fuente_admin.get('numero_documento')
            ente_emisor= fuente_admin.get('ente_emisor')
            estado_disponibilidad= fuente_admin.get('estado_disponibilidad')
            tipo= fuente_admin.get('tipo')

            if  self.validar_solo_numero(oficina_origen):
                raise ValidationError('La oficina de origen no puede contener caracteres especiales')
            
            #Validar ente emisor
            try:
                instancia_ente_emisor = EnteEmisortipo.objects.get(t_id = ente_emisor)
            except EnteEmisortipo.DoesNotExist:
                raise ValidationError('El ente emisor no existe')
            
            #Validar estado disponibilidad
            try:
                instancia_estado_disponibilidad = ColEstadodisponibilidadtipo.objects.get(t_id = estado_disponibilidad)
            except ColEstadodisponibilidadtipo.DoesNotExist:
                raise ValidationError('El estado de disponibilidad no existe')
            
            #Validar tipo
            try:
                instancia_tipo = ColFuenteadministrativatipo.objects.get(t_id = tipo)
            except ColFuenteadministrativatipo.DoesNotExist:
                raise ValidationError('El tipo de fuente administrativa no existe')
            
            #Validar y convertir fecha documento
            if fecha_documento:
                # Si viene como string, convertirla a date
                if isinstance(fecha_documento, str):
                    try:
                        fecha_documento = datetime.strptime(fecha_documento, '%Y-%m-%d').date()
                    except ValueError:
                        raise ValidationError('La fecha de documento debe tener formato YYYY-MM-DD')
                elif not isinstance(fecha_documento, date):
                    raise ValidationError('La fecha de documento debe ser una fecha válida')

            data_fuente_admin = {
                'oficina_origen': oficina_origen,
                'fecha_documento_fuente': fecha_documento,            
                'numero_documento': numero_documento,
                'ente_emisor': instancia_ente_emisor,
                'estado_disponibilidad': instancia_estado_disponibilidad,
                'tipo': instancia_tipo,

            }

            serializer = FuenteAdministrativaSerializer(data = data_fuente_admin)
            serializer.is_valid(raise_exception=True)

            instancia_fuente_admin, created = FuenteAdministrativa.objects.get_or_create(
                **data_fuente_admin)
            
            return instancia_fuente_admin
        else:
            return None
    
    
    def create_interesado_predio(self, list_json=None):
        interesado= list_json.get('interesado')
        predio= list_json.get('predio')

        #validar interesado
        if interesado is None:
            raise ValidationError('No se ha enviado el interesado')
        
        #validar predio
        if predio is None:
            raise ValidationError('No se ha enviado el predio')
        
        instancia_interesado_predio = InteresadoPredio(
            interesado=interesado,
            predio=predio
        )
        instancia_interesado_predio.save()
        return instancia_interesado_predio

    def create_interesado(self, validate_data = None, instancia_predio = None, instancia_resolucion_predio = None):
        interesado = validate_data
        numero_documento_interesado = interesado.get('numero_documento')

        #VALIDAR CARACTERES ESPECIALES EN EL NOMBRE
        nombre = f'{interesado.get("primer_nombre")}{interesado.get("segundo_nombre")}{interesado.get("primer_apellido")}{interesado.get("segundo_apellido")}'
        
        if self.validar_caracteres_especiales_razon_social(interesado.get('razon_social')):
            raise ValidationError(f"La razon social no puede contener caracteres extraños.")

        if self.validar_caracteres_especiales_nombre(nombre):
            raise ValidationError(f"Los nombres y apellidos no pueden contener caracteres extraños.") 

        if interesado.get('tipo_documento') == 'Pasaporte':
            if self.validar_caracteres_especiales_pasaporte(numero_documento_interesado):
                raise ValidationError(f"Solo se permite el caracter especial '-' en el documento de identificacion")
        elif interesado.get('tipo_documento') == 'NIT':
            if self.validar_caracteres_especiales_nit(numero_documento_interesado):
                raise ValidationError(f"Solo se permite el caracter especial '-' en el NIT")
        else:
            if self.validar_caracteres_especiales_cedula(numero_documento_interesado):
                raise ValidationError(f"No se permiten el caracteres especiales")

        instancia_sexo = CrSexotipo.objects.get(t_id=interesado.get('sexo'))
        instancia_tipo_documento = ColDocumentotipo.objects.get(t_id=interesado.get('tipo_documento'))
        instancia_interesado_tipo = ColInteresadotipo.objects.get(t_id=interesado.get('tipo_interesado'))

        # Definimos los campos para la búsqueda y para la creación
        search_fields = {
            'tipo_documento': instancia_tipo_documento,
            'numero_documento': numero_documento_interesado,
        }
        
        # Para personas naturales, la unicidad depende del nombre completo y sexo.
        # Para personas jurídicas, depende de la razón social.
        if instancia_interesado_tipo.t_id == 6: # Persona Natural
            search_fields.update({
                'primer_nombre': interesado.get('primer_nombre'),
                'segundo_nombre': interesado.get('segundo_nombre'),
                'primer_apellido': interesado.get('primer_apellido'),
                'segundo_apellido': interesado.get('segundo_apellido'),
                'sexo': instancia_sexo,
            })
            defaults = {
                'razon_social': None,
                'tipo_interesado': instancia_interesado_tipo,
            }
        else: # Persona Jurídica
            search_fields['razon_social'] = interesado.get('razon_social')
            defaults = {
                'primer_nombre': None,
                'segundo_nombre': None,
                'primer_apellido': None,
                'segundo_apellido': None,
                'sexo': None,
                'tipo_interesado': instancia_interesado_tipo,
            }

        # Usamos get_or_create para buscar o crear al interesado de forma atómica
        instancia_interesado, created = Interesado.objects.get_or_create(
            **search_fields,
            defaults=defaults
        )

        if created:
            instancia_interesado.save()

        #Crear interesado predio
        return self.create_interesado_predio({
            'interesado':instancia_interesado,
            'predio':instancia_predio,
        })

    def get_interesados_predios_actuales(self, instance_predio_actual):
        """
        Obtiene una lista de todos los interesados asociados a un predio actual.
        """
        return InteresadoPredio.objects.filter(predio=instance_predio_actual).select_related('interesado')

    def incorporar_interesados(self, predio=None, instance_predio=None, instance_predio_actual=None, validar=False):
        
        if predio and predio.get('interesados'):
            # Si se proporcionan interesados nuevos, se crean y asocian
            return self._crear_interesados(
                validate_data=predio.get('interesados'), 
                instance_predio=instance_predio
            )
        elif instance_predio_actual:
            # Si no hay interesados nuevos, se copian los del predio actual
            return self._copiar_interesados(
                instance_predio=instance_predio,
                instance_predio_actual=instance_predio_actual
            )
        return []

    def _crear_interesados(self, validate_data, instance_predio):
        """
        Crea nuevos interesados y los asocia al predio, utilizando el serializador
        para validar y manejar las relaciones de dominio.
        """
        interesados_predio_creados = []
        for interesado_data in validate_data:
            # Asignar valor por defecto para 'autoreconocimientoetnico' si no se proporciona
            if 'autoreconocimientoetnico' not in interesado_data or not interesado_data.get('autoreconocimientoetnico'):
                interesado_data['autoreconocimientoetnico'] = 335 # ID para "No aplica"

            # 1. Usar el serializer para validar y preparar los datos del interesado
            serializer_interesado = InteresadoModelSerializer(data=interesado_data)
            try:
                serializer_interesado.is_valid(raise_exception=True)
                validated_interesado_data = serializer_interesado.validated_data
                
                # 2. Buscar o crear el interesado de forma atómica
                # El serializer ya nos devuelve las instancias de los dominios
                
                # Separar los campos de búsqueda de los campos por defecto
                search_fields = {
                    'tipo_documento': validated_interesado_data.get('tipo_documento'),
                    'numero_documento': validated_interesado_data.get('numero_documento'),
                }
                
                defaults = {
                    'primer_nombre': validated_interesado_data.get('primer_nombre'),
                    'segundo_nombre': validated_interesado_data.get('segundo_nombre'),
                    'primer_apellido': validated_interesado_data.get('primer_apellido'),
                    'segundo_apellido': validated_interesado_data.get('segundo_apellido'),
                    'razon_social': validated_interesado_data.get('razon_social'),
                    'sexo': validated_interesado_data.get('sexo'),
                    'tipo_interesado': validated_interesado_data.get('tipo_interesado'),
                    'autoreconocimientoetnico': validated_interesado_data.get('autoreconocimientoetnico'),
                }

                # Lógica para hacer la búsqueda más específica
                tipo_interesado_obj = defaults.get('tipo_interesado')
                if tipo_interesado_obj and tipo_interesado_obj.t_id == 6: # Persona Natural
                    search_fields.update({
                        'primer_nombre': defaults.get('primer_nombre'),
                        'segundo_nombre': defaults.get('segundo_nombre'),
                        'primer_apellido': defaults.get('primer_apellido'),
                        'segundo_apellido': defaults.get('segundo_apellido'),
                    })
                elif tipo_interesado_obj: # Persona Jurídica u otro
                    search_fields['razon_social'] = defaults.get('razon_social')
                
                # Limpiar el nombre completo para el campo 'nombre'
                nombre_completo = f"{defaults.get('primer_nombre', '')} {defaults.get('segundo_nombre', '')} {defaults.get('primer_apellido', '')} {defaults.get('segundo_apellido', '')}".strip()
                if not nombre_completo:
                    nombre_completo = defaults.get('razon_social')
                
                defaults['nombre'] = nombre_completo

                instancia_interesado, created = Interesado.objects.get_or_create(
                    **search_fields,
                    defaults=defaults
                )
                
                # 3. Crear la relación InteresadoPredio
                relacion, created_relacion = InteresadoPredio.objects.get_or_create(
                    interesado=instancia_interesado,
                    predio=instance_predio
                )
                interesados_predio_creados.append(relacion)

            except ValidationError as e:
                # Re-lanzar el error de validación para que la transacción principal haga rollback
                raise e
            except Exception as e:
                # Capturar otros posibles errores
                raise ValidationError(f"Error inesperado al crear el interesado: {e}")
                
        return interesados_predio_creados

    def _copiar_interesados(self, instance_predio, instance_predio_actual):
        """Copia los interesados del predio actual al nuevo predio."""
        interesados_a_copiar = self.get_interesados_predios_actuales(instance_predio_actual)
        interesados_predio_creados = []
        for relacion_actual in interesados_a_copiar:
            nueva_relacion = self.create_interesado_predio({
                'interesado': relacion_actual.interesado,
                'predio': instance_predio
            })
            interesados_predio_creados.append(nueva_relacion)
        return interesados_predio_creados