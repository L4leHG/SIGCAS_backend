from rest_framework.serializers import ModelSerializer, ValidationError

#Modelos
from registro.apps.catastro.models import ( Predio,EstructuraAvaluo,
                                CrCondicionprediotipo,CrDestinacioneconomicatipo,
                                ColUnidadadministrativabasicatipo,CrEstadotipo,CrPrediotipo
                                    )                            

# UTILS
import datetime

class PredioSerializer(ModelSerializer):
    
    class Meta:
        model = Predio
        fields = '__all__'
        depth = 1

class AvaluoSerializer(ModelSerializer):
    
    class Meta:
        model = EstructuraAvaluo
        fields = '__all__'
        # Remover depth para manejar relaciones correctamente
    
    def create(self, validated_data):
        """
        Crear avalúo asegurándose de que las relaciones se manejen correctamente
        """
        # Crear la instancia directamente con los datos validados
        avaluo = EstructuraAvaluo.objects.create(**validated_data)
        return avaluo

class PredioIncorporacionSerializer():

    def create_predio_novedad_from_active(self, npn):
        """
        Crea un nuevo predio en estado 'novedad' a partir del predio activo.
        - Valida que no exista previamente un predio en estado 'novedad'.
        - Si ya existe, lanza un error para que sea corregido manualmente.
        - Si no existe, crea una copia del predio activo y la retorna.
        """
        # Validar que no exista un predio en estado 'novedad'
        estado_novedad = CrEstadotipo.objects.get(t_id=106)
        if Predio.objects.filter(numero_predial_nacional=npn, estado=estado_novedad).exists():
            raise ValidationError(
                f"Ya existe un predio con NPN {npn} en estado 'novedad'. "
                f"Debe ser eliminado o procesado antes de iniciar un nuevo trámite."
            )

        # Buscar el predio activo para copiarlo (estado activo = 105)
        try:
            predio_activo = Predio.objects.get(numero_predial_nacional=npn, estado__t_id=105)
        except Predio.DoesNotExist:
            raise ValidationError(f'El número predial nacional {npn} no existe o no está activo.')

        # Crear una copia REAL del objeto usando el método Django correcto
        # Usar copy.deepcopy para asegurar que sea una copia independiente
        import copy
        
        # Crear una copia profunda del objeto para evitar referencias compartidas
        predio_novedad = copy.deepcopy(predio_activo)
        
        # Resetear campos para crear nuevo objeto
        predio_novedad.pk = None
        predio_novedad.id = None
        
        # Asignar el nuevo estado y resetear ambos campos de vida útil a None
        predio_novedad.estado = estado_novedad
        predio_novedad.comienzo_vida_util_version = None
        predio_novedad.fin_vida_util_version = None
        
        # Guardar la nueva instancia 'novedad'
        predio_novedad.save()
        print(f"DEBUG: Predio novedad creado ID: {predio_novedad.id}, NPN: {predio_novedad.numero_predial_nacional}")
        print(f"DEBUG: Predio activo original ID: {predio_activo.id}, NPN: {predio_activo.numero_predial_nacional}")

        return predio_novedad, predio_activo

    def actualizar_direccion(self, instance_predio, direccion=None):
        """
        Actualiza el campo de dirección en la instancia del predio en memoria.
        NO GUARDA en la base de datos.
        """
        if direccion:
            instance_predio.direccion = direccion.strip()
        return instance_predio

    def actualizar_destino(self, instance_predio, destino=None):
        """
        Actualiza el campo de destinación económica en la instancia del predio en memoria.
        NO GUARDA en la base de datos.
        """
        if destino:
            try:
                instance_destinacion = CrDestinacioneconomicatipo.objects.get(ilicode=destino)
                instance_predio.destinacion_economica = instance_destinacion
            except CrDestinacioneconomicatipo.DoesNotExist:
                raise ValidationError(f"El código de destino económico '{destino}' no es válido.")
        return instance_predio
    
    # La función get_or_create_predio_novedad ha sido reemplazada por 
    # create_predio_novedad_from_active para cumplir con la nueva regla de negocio.
    
    def get_instance_predio_and_actual(self, predio):
        npn = predio.get('npn')
        
        predio_novedad, predio_activo = self.create_predio_novedad_from_active(npn)
        
        return predio_novedad, predio_activo

    def create_avaluo(self, avaluos_data, instance_predio=None, instance_tramitecatastral_predio=None):
        """
        Crea registros de avalúo en la tabla EstructuraAvaluo.
        
        Args:
            avaluos_data (list): Lista de diccionarios con datos de avalúos
            instance_predio (Predio): Instancia del predio NOVEDAD
            instance_tramitecatastral_predio (PredioTramitecatastral): Instancia del trámite
            
        Returns:
            dict: Información del último avalúo creado
        """
        if not avaluos_data:
            print("DEBUG: No hay datos de avalúos para crear")
            return None
            
        if not instance_predio:
            raise ValidationError('Se requiere una instancia de predio válida para crear avalúos.')
            
        # Validar que el predio tenga ID
        if not instance_predio.id:
            raise ValidationError('El predio debe estar guardado en la base de datos antes de crear avalúos.')
            
        ultimo_avaluo = None
        
        for avaluo_data in avaluos_data:
            # Validar que las instancias sean válidas
            if not instance_predio or not hasattr(instance_predio, 'id') or not instance_predio.id:
                raise ValidationError(f'Instancia de predio inválida: {instance_predio}')
            
            # El campo predio_tramitecatastral es opcional (null=True), 
            # pero si se proporciona, debe ser válido
            if instance_tramitecatastral_predio is not None:
                if not hasattr(instance_tramitecatastral_predio, 'id') or not instance_tramitecatastral_predio.id:
                    raise ValidationError(f'Instancia de trámite catastral inválida: {instance_tramitecatastral_predio}')
            
            # Mapear campos correctos según el modelo EstructuraAvaluo
            # El serializer espera pk values, no instancias completas
            data_avaluo = {
                'fecha_avaluo': avaluo_data.get('fecha_avaluo', datetime.date.today()),
                'avaluo_catastral': avaluo_data.get('avaluo') or avaluo_data.get('avaluo_catastral'),
                'vigencia': avaluo_data.get('vigencia'),
                'predio': instance_predio.id,  # ENVIAR ID, no instancia
                'predio_tramitecatastral': instance_tramitecatastral_predio.id if instance_tramitecatastral_predio else None,  # ENVIAR ID, no instancia
            }
            
            # DEBUG: Mostrar qué datos se están intentando crear
            print(f"DEBUG: Creando avalúo con datos:")
            print(f"  - Predio ID enviado: {data_avaluo['predio']} (novedad)")
            print(f"  - Avalúo catastral: {data_avaluo['avaluo_catastral']}")
            print(f"  - Vigencia: {data_avaluo['vigencia']}")
            print(f"  - Fecha avalúo: {data_avaluo['fecha_avaluo']}")
            print(f"  - Trámite catastral ID enviado: {data_avaluo['predio_tramitecatastral']}")
            print(f"  - Datos completos enviados al serializer: {data_avaluo}")
            
            # Validar y crear el avalúo
            serializer = AvaluoSerializer(data=data_avaluo)
            print(f"DEBUG: Serializer is_valid: {serializer.is_valid()}")
            
            if not serializer.is_valid():
                print(f"DEBUG: Errores del serializer: {serializer.errors}")
                print(f"DEBUG: Datos que causaron error: {serializer.initial_data}")
                
            serializer.is_valid(raise_exception=True)
            
            # Verificar datos validados antes de guardar
            print(f"DEBUG: Datos validados por serializer: {serializer.validated_data}")
            
            # El save() respetará la transacción atómica del contexto padre
            avaluo_instance = serializer.save()
            print(f"DEBUG: ✅ Avalúo creado ID: {avaluo_instance.id} para predio {instance_predio.id}")
            
            ultimo_avaluo = {
                'avaluo': avaluo_instance.avaluo_catastral,
                'vigencia': avaluo_instance.vigencia,
                'fecha_avaluo': avaluo_instance.fecha_avaluo
            }
        
        return ultimo_avaluo

    def incorporar_nuevos_avaluos(self, avaluos=None, instance_predio=None, 
                                instance_tramitecatastral_predio=None, instance_predio_actual=None, 
                                validar=False):
        """
        Incorpora avalúos al predio, ya sea nuevos o copiados del predio actual.
        
        Args:
            avaluos (list): Lista de avalúos nuevos (opcional)
            instance_predio (Predio): Instancia del predio novedad
            instance_tramitecatastral_predio (PredioTramitecatastral): Instancia del trámite
            instance_predio_actual (Predio): Instancia del predio actual (opcional)
            validar (bool): Si True, valida que los avalúos sean obligatorios
            
        Raises:
            ValidationError: Si hay errores en validación o datos
        """
        if not instance_predio:
            raise ValidationError('Se requiere una instancia de predio válida.')
            
        if validar and not avaluos:
            raise ValidationError('Los avalúos son obligatorios para esta mutación.')

        if avaluos:
            # Escenario 1: Se proporcionan avalúos nuevos
            avaluo_predial = self.create_avaluo(avaluos, instance_predio, instance_tramitecatastral_predio)
            
            if avaluo_predial:
                # Actualizar campos del predio con el último avalúo creado
                # Nota: El modelo Predio no tiene campo 'avaluo_catastral' ni 'vigencia'
                # Estos se manejan a través de la tabla EstructuraAvaluo
                pass
                
        elif instance_predio_actual:
            # Escenario 2: Copiar avalúo del predio actual
            try:
                npn = instance_predio_actual.numero_predial_nacional
                
                # DEBUG: Log para verificar qué predio se está buscando
                print(f"DEBUG: Buscando avalúos para predio_actual ID: {instance_predio_actual.id}, NPN: {npn}")
                
                # Buscar el avalúo del predio activo con la vigencia más alta
                # Buscar SOLO en predios activos (estado 105) con el mismo NPN
                avaluo_actual = EstructuraAvaluo.objects.filter(
                    predio__numero_predial_nacional=npn,
                    predio__estado__t_id=105  # Solo predios activos
                ).order_by('-vigencia', '-fecha_avaluo').first()  # Prioridad por vigencia más alta
                
                if avaluo_actual:
                    print(f"DEBUG: Avalúo encontrado ID: {avaluo_actual.id}, Valor: {avaluo_actual.avaluo_catastral}, Vigencia: {avaluo_actual.vigencia}")
                    print(f"DEBUG: Avalúo del predio activo ID: {avaluo_actual.predio.id}")
                    
                    # Crear nuevo avalúo basado en el actual
                    avaluo_data = [{
                        'avaluo_catastral': avaluo_actual.avaluo_catastral,
                        'vigencia': avaluo_actual.vigencia,
                        'fecha_avaluo': avaluo_actual.fecha_avaluo,
                    }]
                    
                    self.create_avaluo(avaluo_data, instance_predio, instance_tramitecatastral_predio)
                else:
                    # DEBUG: Información detallada sobre por qué no se encuentra
                    print(f"DEBUG: No se encontró ningún avalúo para NPN: {npn}")
                    print(f"DEBUG: instance_predio_actual ID: {instance_predio_actual.id}")
                    print(f"DEBUG: instance_predio_actual estado: {instance_predio_actual.estado.ilicode}")
                    
                    # Verificar si existen avalúos en general para este NPN
                    avaluos_por_npn = EstructuraAvaluo.objects.filter(
                        predio__numero_predial_nacional=npn
                    ).select_related('predio')
                    
                    print(f"DEBUG: Total avalúos en BD para NPN {npn}: {avaluos_por_npn.count()}")
                    for av in avaluos_por_npn:
                        print(f"DEBUG: Avalúo ID: {av.id}, Predio ID: {av.predio.id}, Estado: {av.predio.estado.ilicode}, Vigencia: {av.vigencia}")
                    
                    raise ValidationError(
                        f'El predio {npn} no tiene avalúos registrados en el predio activo. '
                        f'Contacte al área técnica para registrar el avalúo base.'
                    )
                    
            except Exception as e:
                npn = instance_predio_actual.numero_predial_nacional if instance_predio_actual else 'N/A'
                raise ValidationError(f'Error procesando avalúos del predio {npn}: {str(e)}')
        
        # Si no hay avalúos nuevos ni predio actual, no hacer nada
        # (esto es válido en algunos casos de incorporación)
    