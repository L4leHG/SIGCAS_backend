"""
Utilidades para el manejo de tipos de mutación catastral.
"""

def es_tipo_mutacion_soportado(tipo_id):
    """
    Verifica si un tipo de mutación, dado su ID, está soportado por el sistema.
    
    Args:
        tipo_id (int): El ID del tipo de mutación (ej: 1, 2, 3)
        
    Returns:
        bool: True si está soportado, False en caso contrario.
    """
    tipos_soportados = [15, 16]  # IDs para Primera y Tercera Clase
    return tipo_id in tipos_soportados

def validar_coherencia_mutacion(tipo_asignacion_id, tipo_datos_id):
    """
    Valida que el tipo de mutación de la asignación coincida con los datos enviados.
    
    Args:
        tipo_asignacion_id (int): ID del tipo de mutación desde la asignación.
        tipo_datos_id (int): ID del tipo de mutación desde los datos JSON.
        
    Returns:
        tuple: (es_valido: bool, mensaje_error: str)
    """
    if tipo_datos_id != tipo_asignacion_id:
        return False, f"La asignación está configurada para la mutación con ID {tipo_asignacion_id} pero se recibió el ID {tipo_datos_id}"
    
    return True, ""


# Mapeo de tipos de mutación soportados
TIPOS_MUTACION_SOPORTADOS = {
    'Mutacion_Primera_Clase': {
        'nombre': 'Cambio de Propietario',
        'descripcion': 'Permite actualizar o incorporar nuevos propietarios',
        'conserva_terrenos': True,
        'conserva_unidades': True,
        'requiere_interesados': True,
        'requiere_terrenos': False,
        'permite_avaluos_nuevos': False
    },
    'Mutacion_Tercera_Clase': {
        'nombre': 'Modificación de Unidades de un Predio',
        'descripcion': 'Permite modificar unidades constructivas y destinación económica, conservando terrenos e interesados existentes',
        'conserva_terrenos': True,
        'conserva_unidades': False,
        'requiere_interesados': False,
        'requiere_terrenos': False,
        'permite_avaluos_nuevos': True
    },
    # Agregar más tipos según sea necesario
    # 'Mutacion_Segunda_Clase': {
    #     'nombre': 'Otro Tipo',
    #     'descripcion': 'Descripción del segundo tipo',
    #     ...
    # }
}


def obtener_configuracion_mutacion(tipo_base):
    """
    Obtiene la configuración de un tipo de mutación.
    
    Args:
        tipo_base (str): Tipo base de mutación como "Mutacion_Primera_Clase"
        
    Returns:
        dict: Configuración del tipo de mutación o None si no existe
    """
    return TIPOS_MUTACION_SOPORTADOS.get(tipo_base) 

def extraer_tipo_base_mutacion(mutacion_id):
    """
    Extrae el tipo base de mutación a partir del t_id.
    Por ejemplo, si mutacion_id es 15, devuelve 'Mutacion_Primera_Clase'.
    """
    if mutacion_id == 15: # ID de Mutacion_Primera_Clase
        return 15
    elif mutacion_id == 16: # ID de Mutacion_Tercera_Clase
        return 16
    # Agrega más mapeos según sea necesario
    # elif mutacion_id == ID_SEGUNDA:
    #     return 'Mutacion_Segunda_Clase'
    else:
        raise ValueError(f"ID de mutación no reconocido: {mutacion_id}") 