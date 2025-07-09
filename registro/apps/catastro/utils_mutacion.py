"""
Utilidades para el manejo de tipos de mutación catastral.

Este módulo contiene funciones helper para trabajar con los tipos de mutación
que tienen estructura como: "Mutacion_Primera_Clase.Cambio_Propietario"
"""

def extraer_tipo_base_mutacion(ilicode_completo):
    """
    Extrae el tipo base de mutación desde el ilicode completo.
    
    Args:
        ilicode_completo (str): El ilicode completo como "Mutacion_Primera_Clase.Cambio_Propietario"
        
    Returns:
        str: El tipo base como "Mutacion_Primera_Clase"
        
    Ejemplos:
        >>> extraer_tipo_base_mutacion("Mutacion_Primera_Clase.Cambio_Propietario")
        "Mutacion_Primera_Clase"
        
        >>> extraer_tipo_base_mutacion("Mutacion_Tercera_Clase.Incorporacion_Nueva")
        "Mutacion_Tercera_Clase"
        
        >>> extraer_tipo_base_mutacion("Tipo_Simple")
        "Tipo_Simple"
    """
    if not ilicode_completo:
        return ""
    
    return ilicode_completo.split('.')[0] if '.' in ilicode_completo else ilicode_completo


def obtener_subtipo_mutacion(ilicode_completo):
    """
    Extrae el subtipo de mutación desde el ilicode completo.
    
    Args:
        ilicode_completo (str): El ilicode completo como "Mutacion_Primera_Clase.Cambio_Propietario"
        
    Returns:
        str: El subtipo como "Cambio_Propietario" o None si no existe
        
    Ejemplos:
        >>> obtener_subtipo_mutacion("Mutacion_Primera_Clase.Cambio_Propietario")
        "Cambio_Propietario"
        
        >>> obtener_subtipo_mutacion("Tipo_Simple")
        None
    """
    if not ilicode_completo or '.' not in ilicode_completo:
        return None
    
    partes = ilicode_completo.split('.', 1)  # Solo dividir en el primer punto
    return partes[1] if len(partes) > 1 else None


def validar_coherencia_mutacion(tipo_asignacion, tipo_datos):
    """
    Valida que el tipo de mutación de la asignación coincida exactamente con los datos enviados.
    
    Args:
        tipo_asignacion (str): Tipo de mutación desde la asignación (completo, ej: "Mutacion_Primera_Clase.Cambio_Propietario")
        tipo_datos (str): Tipo de mutación desde los datos JSON (debe ser igual al completo)
        
    Returns:
        tuple: (es_valido: bool, mensaje_error: str)
        
    Ejemplos:
        >>> validar_coherencia_mutacion("Mutacion_Primera_Clase.Cambio_Propietario", "Mutacion_Primera_Clase.Cambio_Propietario")
        (True, "")
        
        >>> validar_coherencia_mutacion("Mutacion_Primera_Clase.Cambio_Propietario", "Mutacion_Tercera_Clase.Incorporacion_Nueva")
        (False, "La asignación está configurada para Mutacion_Primera_Clase.Cambio_Propietario pero se recibió Mutacion_Tercera_Clase.Incorporacion_Nueva")
    """
    if tipo_datos != tipo_asignacion:
        return False, f"La asignación está configurada para {tipo_asignacion} pero se recibió {tipo_datos}"
    
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


def es_tipo_mutacion_soportado(tipo_base):
    """
    Verifica si un tipo de mutación está soportado.
    
    Args:
        tipo_base (str): Tipo base de mutación como "Mutacion_Primera_Clase"
        
    Returns:
        bool: True si está soportado, False en caso contrario
    """
    return tipo_base in TIPOS_MUTACION_SOPORTADOS 