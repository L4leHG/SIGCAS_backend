from rest_framework.serializers import ModelSerializer, ValidationError

# MODELS 
from registro.apps.catastro.models import Terreno, TerrenoZonas, Historial_predio


class TerrenoSerializer(ModelSerializer):
    class Meta:
        model = TerrenoZonas
        fields = '__all__'
        depth = 1


class TerrenoGeoSerializer(ModelSerializer):
    class Meta:
        model = Terreno
        fields = '__all__'
        depth = 1


class IncorporacionTerrenoSerializer:
    """
    Clase para manejar la incorporación de terrenos en el sistema catastral.
    """

    def create_terreno(self, data_terrenos=None, instance_terreno_geo=None):
        """
        Crea registros de TerrenoZonas asociados a un Terreno geográfico.
        
        Args:
            data_terrenos (dict): Datos que contienen la lista de terrenos
            instance_terreno_geo (Terreno): Instancia del terreno geográfico
            
        Returns:
            list: Lista de instancias TerrenoZonas creadas
        """
        if not data_terrenos or not instance_terreno_geo:
            return []

        terrenos_data = data_terrenos.get('terrenos', [])
        if not terrenos_data:
            return []

        instancias_creadas = []
        
        for terreno_info in terrenos_data:
            data_terreno = {
                'area_catastral_terreno': round(terreno_info.get('area_digitada', 0), 2),
                'zona_fisica': terreno_info.get('zona_fisica'),
                'zona_geoeconomica': terreno_info.get('zona_geoeconomica'),  # Corregido
                'avaluo_terreno': terreno_info.get('avaluo'),
                'terreno': instance_terreno_geo,
            }
            
            serializer = TerrenoSerializer(data=data_terreno)
            serializer.is_valid(raise_exception=True)
            instance_terreno = serializer.save()
            instancias_creadas.append(instance_terreno)
        
        return instancias_creadas

    def get_terrenos_actuales(self, instance_predio_actual):
        """
        Obtiene los terrenos actuales de un predio desde el historial.
        
        Args:
            instance_predio_actual (Predio): Instancia del predio actual
            
        Returns:
            list: Lista de instancias Terreno o None si no existen
        """
        if not instance_predio_actual:
            raise ValidationError('El predio a consultar no existe')

        instances_historicas = Historial_predio.objects.filter(
            predio=instance_predio_actual,
            predio__estado__t_id=105,  # Corregido: usar t_id para estados
            predio_unidadespacial__terreno__isnull=False  # Corregido nombre de campo
        ).select_related('predio_unidadespacial__terreno')

        if instances_historicas.exists():
            # Obtener las instancias de terreno desde el historial
            instances = [
                hist.predio_unidadespacial.terreno 
                for hist in instances_historicas 
                if hist.predio_unidadespacial and hist.predio_unidadespacial.terreno
            ]
            return instances if instances else None
        
        return None

    def get_suma_area_terreno(self, predio_data):
        """
        Calcula la suma total del área de terrenos.
        
        Args:
            predio_data (dict): Datos del predio con información de terrenos
            
        Returns:
            float: Suma total del área de terrenos
        """
        if not predio_data:
            return 0

        terrenos = predio_data.get('terrenos') or predio_data.get('edicion', [])
        if not terrenos:
            return 0
            
        try:
            suma = sum(float(item.get('area_digitada', 0)) for item in terrenos)
            return round(suma, 2)
        except (ValueError, TypeError):
            return 0

    def get_terrenos_actuales_unidadespacial(self, instance_predio_actual):
        """
        Obtiene las unidades espaciales de terreno actuales de un predio.
        
        Args:
            instance_predio_actual (Predio): Instancia del predio actual
            
        Returns:
            list: Lista de instancias PredioUnidadespacial o None si no existen
        """
        if not instance_predio_actual:
            return None

        instances_historicas = Historial_predio.objects.filter(
            predio=instance_predio_actual,
            predio__estado__t_id=105,  # Corregido: usar t_id para estados
            predio_unidadespacial__terreno__isnull=False  # Corregido nombre de campo
        ).select_related('predio_unidadespacial')

        if instances_historicas.exists():
            # Obtener las unidades espaciales desde el historial
            instances = [
                hist.predio_unidadespacial 
                for hist in instances_historicas 
                if hist.predio_unidadespacial
            ]
            return instances if instances else None
        
        return None

    def incorporar_terreno_geo(self, predio=None, instance_predio=None, instance_predio_actual=None):
        """
        Método para incorporar/procesar geometría de terreno.
        Para mutaciones de primera clase (cambio propietario), retorna None
        ya que no se modifica la geometría.
        
        Args:
            predio (dict): Datos del predio
            instance_predio (Predio): Instancia del predio
            instance_predio_actual (Predio): Instancia del predio actual
            
        Returns:
            None: Para cambio de propietario no se modifica geometría
        """
        # Para cambio de propietario, no se modifica geometría de terreno
        return None

    def incorporar_terrenos(self, predio=None, instance_predio=None, 
                          instance_predio_actual=None, instance_predio_novedad=None, 
                          instance_terreno_geo=None):
        """
        Incorpora terrenos según diferentes escenarios.
        
        Args:
            predio (dict): Datos del predio con información de terrenos
            instance_predio (Predio): Instancia del predio a actualizar
            instance_predio_actual (Predio): Instancia del predio actual
            instance_predio_novedad (QuerySet): QuerySet de predios novedad
            instance_terreno_geo (Terreno): Instancia del terreno geográfico
            
        Returns:
            list: Lista de terrenos incorporados o consultados
        """
        # Caso 1: Hay nuevos terrenos para incorporar
        if predio and predio.get('terrenos'):
            instance_terrenos = self.create_terreno(predio, instance_terreno_geo)
            
            # Actualizar área total del predio si es posible
            if instance_predio and hasattr(instance_predio, 'area_catastral_terreno'):
                suma_area = self.get_suma_area_terreno(predio)
                instance_predio.area_catastral_terreno = suma_area
                instance_predio.save()
            
            return instance_terrenos
        
        # Caso 2: Consultar terrenos de una novedad específica
        elif instance_predio_novedad and hasattr(instance_predio_novedad, 'exists') and instance_predio_novedad.exists():
            primera_novedad = instance_predio_novedad.order_by('-id').first()
            return self.get_terrenos_actuales(primera_novedad)
        
        # Caso 3: Consultar terrenos del predio actual
        elif instance_predio_actual:
            return self.get_terrenos_actuales(instance_predio_actual)
        
        # Caso 4: No hay datos suficientes
        return []
    