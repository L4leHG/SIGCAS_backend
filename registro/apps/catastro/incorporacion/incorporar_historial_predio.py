from registro.apps.catastro.models import Historial_predio

class IncorporacionHistorialPredioSerializer:
    """
    Clase para manejar la incorporación de registros al historial de predios.
    """

    def create_resolucion_historica(self, data_dict):
        """
        Crea registros históricos para predios basados en interesados y unidades espaciales.
        
        Args:
            data_dict (dict): Diccionario con datos base y listas de 'interesado_predio' y 'predio_unidadespacial'
            
        Returns:
            list: Lista de instancias de Historial_predio creadas
        """
        if not data_dict:
            return []
            
        # Extraer listas y datos base
        interesados_predio = data_dict.get('interesado_predio', [])
        unidades_espaciales = data_dict.get('predio_unidadespacial', [])
        
        # Crear datos base sin las listas
        base_data = {k: v for k, v in data_dict.items() 
                    if k not in ['interesado_predio', 'predio_unidadespacial']}
        
        instancias_creadas = []
        
        # Crear registros para interesados_predio
        for interesado_predio in interesados_predio:
            registro_data = base_data.copy()
            registro_data['interesado_predio'] = interesado_predio
            registro_data['predio_unidadespacial'] = None
            instancias_creadas.append(Historial_predio(**registro_data))
        
        # Crear registros para unidades espaciales
        for unidad_espacial in unidades_espaciales:
            registro_data = base_data.copy()
            registro_data['interesado_predio'] = None
            registro_data['predio_unidadespacial'] = unidad_espacial
            instancias_creadas.append(Historial_predio(**registro_data))
        
        # Crear todos los registros de una vez (más eficiente)
        if instancias_creadas:
            Historial_predio.objects.bulk_create(instancias_creadas)
        
        return instancias_creadas
