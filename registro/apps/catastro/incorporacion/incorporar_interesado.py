from rest_framework.serializers import ModelSerializer
from re import compile
from datetime import date, datetime

from registro.apps.catastro.models import (Predio, Interesado, 
InteresadoPredio, CrEstadotipo, FuenteAdministrativa,
CrMutaciontipo, TramiteCatastral, PredioTramitecatastral,
PredioFuenteadministrativa, EnteEmisortipo, ColEstadodisponibilidadtipo, ColFuenteadministrativatipo, ColDocumentotipo, ColInteresadotipo,
CrSexotipo, Historial_predio
) 

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
                instancia_ente_emisor = EnteEmisortipo.objects.get(ilicode = ente_emisor)
            except EnteEmisortipo.DoesNotExist:
                raise ValidationError('El ente emisor no existe')
            
            #Validar estado disponibilidad
            try:
                instancia_estado_disponibilidad = ColEstadodisponibilidadtipo.objects.get(ilicode = estado_disponibilidad)
            except ColEstadodisponibilidadtipo.DoesNotExist:
                raise ValidationError('El estado de disponibilidad no existe')
            
            #Validar tipo
            try:
                instancia_tipo = ColFuenteadministrativatipo.objects.get(ilicode = tipo)
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
        """
        Crea las relaciones InteresadoPredio de forma masiva y eficiente.
        Utiliza bulk_create para insertar todos los registros en una sola consulta.
        """
        if not list_json:
            return []

        instancias_a_crear = []
        for data in list_json:
            serializer = InteresadoPredioSerializer(data=data)
            serializer.is_valid(raise_exception=True)
            # Se crea la instancia en memoria, sin guardarla en la BD todavía.
            instancias_a_crear.append(InteresadoPredio(**data))

        # Se insertan todas las instancias en la base de datos de una sola vez.
        if instancias_a_crear:
            return InteresadoPredio.objects.bulk_create(instancias_a_crear)

        return []
    
    def create_interesado(self, validate_data = None, instancia_predio = None, instancia_resolucion_predio = None):
        list_id_interesado = []

        if validate_data.get('interesados'):
            for interesado in validate_data.get('interesados'):
                
                # OBTENER LAS VARIABLES DEL DICCIONARIO
                tipo_documento = interesado.get('tipo_documento')
                primer_nombre=interesado.get('primer_nombre').upper().strip() if interesado.get('primer_nombre') else None
                segundo_nombre=interesado.get('segundo_nombre').upper().strip() if interesado.get('segundo_nombre') else None
                primer_apellido=interesado.get('primer_apellido').upper().strip() if interesado.get('primer_apellido') else None
                segundo_apellido=interesado.get('segundo_apellido').upper().strip() if interesado.get('segundo_apellido') else None
                sexo = interesado.get('sexo')
                razon_social = interesado.get('razon_social').upper().strip() if interesado.get('razon_social') else None
                tipo_interesado = interesado.get('tipo_interesado')                
                numero_documento = interesado.get('numero_documento')

                #VALIDAR CARACTERES ESPECIALES EN EL NOMBRE
                nombre = f'{primer_nombre}{segundo_nombre}{primer_apellido}{segundo_apellido}'
                
                if self.validar_caracteres_especiales_razon_social(razon_social):
                    raise ValidationError(f"La razon social no puede contener caracteres extraños.")

                if self.validar_caracteres_especiales_nombre(nombre):
                    raise ValidationError(f"Los nombres y apellidos no pueden contener caracteres extraños.") 

                if tipo_documento == 'Pasaporte':
                    if self.validar_caracteres_especiales_pasaporte(numero_documento):
                        raise ValidationError(f"Solo se permite el caracter especial '-' en el documento de identificacion")
                elif tipo_documento == 'NIT':
                    if self.validar_caracteres_especiales_nit(numero_documento):
                        raise ValidationError(f"Solo se permite el caracter especial '-' en el NIT")
                else:
                    if self.validar_caracteres_especiales_cedula(numero_documento):
                        raise ValidationError(f"No se permiten el caracteres especiales")

                instancia_sexo = CrSexotipo.objects.get(ilicode=sexo)
                instancia_tipo_documento = ColDocumentotipo.objects.get(ilicode=tipo_documento)
                instancia_interesado_tipo = ColInteresadotipo.objects.get(ilicode=tipo_interesado)

                # Definimos los campos para la búsqueda y para la creación
                search_fields = {
                    'tipo_documento': instancia_tipo_documento,
                    'numero_documento': numero_documento,
                }
                
                # Para personas naturales, la unicidad depende del nombre completo y sexo.
                # Para personas jurídicas, depende de la razón social.
                if instancia_interesado_tipo.t_id == 6: # Persona Natural
                    search_fields.update({
                        'primer_nombre': primer_nombre,
                        'segundo_nombre': segundo_nombre,
                        'primer_apellido': primer_apellido,
                        'segundo_apellido': segundo_apellido,
                        'sexo': instancia_sexo,
                    })
                    defaults = {
                        'razon_social': None,
                        'tipo_interesado': instancia_interesado_tipo,
                    }
                else: # Persona Jurídica
                    search_fields['razon_social'] = razon_social
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

                # Añadimos el interesado (existente o nuevo) a la lista para asociarlo al predio
                list_id_interesado.append({
                    'interesado': instancia_interesado,
                    'predio': instancia_predio
                })

        elif validate_data.get('CrMutaciontipo') in (
            'Mutacion_Primera_Clase.Cambio_Propietario'):
            raise ValidationError(f"La mutacion de {validate_data.get('mutacion')} para el predio {validate_data.get('npn')} debe tener asociado minimo un propietario.")
        return list_id_interesado

    def get_interesados_predios_actuales(self, instance_predio_actual):
        """
        Obtiene una lista de objetos Interesado asociados a un predio activo.
        Retorna siempre una lista (vacía si no hay resultados), nunca None.
        """
        if not instance_predio_actual:
            return []
            
        interesados_predios = Historial_predio.objects.filter(
            predio=instance_predio_actual,
            predio__estado__t_id=105, # Siempre busca sobre el predio activo.
            interesado_predio__isnull=False
        ).select_related('interesado_predio__interesado')
        
        return [resolucion.interesado_predio.interesado for resolucion in interesados_predios]
    
    def incorporar_interesados(self, predio=None, instance_predio=None, instance_predio_actual=None, validar=False):
        """
        Orquesta la creación o copia de interesados y los asocia a un predio.
        Garantiza que el tipo de retorno sea siempre una lista de objetos InteresadoPredio.
        """
        interesados_json = predio.get('interesados')
        npn = predio.get('npn')

        if validar and not interesados_json:
            raise ValidationError(f'Para el predio {npn} los interesados son obligatorios.')
        
        list_para_asociar = []

        if interesados_json:
            # Escenario 1: Se proporcionan nuevos interesados en la solicitud.
            list_para_asociar = self.create_interesado(
                validate_data=predio, 
                instancia_predio=instance_predio
            )
        elif instance_predio_actual:
            # Escenario 2: No hay interesados en el JSON, se copian del predio activo anterior.
            interesados_a_copiar = self.get_interesados_predios_actuales(instance_predio_actual)

            if interesados_a_copiar:
                list_para_asociar = [
                    {'interesado': interesado, 'predio': instance_predio} 
                    for interesado in interesados_a_copiar
                ]

        # Con la lista de asociaciones preparada, se crean las relaciones.
        return self.create_interesado_predio(list_json=list_para_asociar)

    def _crear_interesados(self, validate_data, instance_predio):
        """
        Crea las relaciones InteresadoPredio de forma masiva y eficiente.
        Utiliza bulk_create para insertar todos los registros en una sola consulta.
        """
        if not validate_data.get('interesados'):
            return []

        instancias_a_crear = []
        for interesado in validate_data.get('interesados'):
            serializer = InteresadoPredioSerializer(data=interesado)
            serializer.is_valid(raise_exception=True)
            # Se crea la instancia en memoria, sin guardarla en la BD todavía.
            instancias_a_crear.append(InteresadoPredio(**interesado))

        # Se insertan todas las instancias en la base de datos de una sola vez.
        nuevos_interesado_predio = []
        if instancias_a_crear:
            nuevos_interesado_predio = InteresadoPredio.objects.bulk_create(instancias_a_crear)

        return nuevos_interesado_predio

    def _copiar_interesados(self, instance_predio, instance_predio_actual):
        """
        Copia los interesados del predio actual al nuevo predio.
        """
        interesados_actuales = InteresadoPredio.objects.filter(predio=instance_predio_actual)
        nuevas_relaciones = [
            InteresadoPredio(predio=instance_predio, interesado=relacion.interesado)
            for relacion in interesados_actuales
        ]
        
        if nuevas_relaciones:
            return InteresadoPredio.objects.bulk_create(nuevas_relaciones)
        
        return []