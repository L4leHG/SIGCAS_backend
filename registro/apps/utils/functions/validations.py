from re import compile

def validar_caracteres_especiales_npn(cadena):
        # Definimos una expresión regular que busca caracteres no alfabéticos o numéricos
        #patron = re.compile(r'[^a-zA-Z1-9ñÑ\-]')

        if len(cadena) != 30:
            return True, 'El npn debe tener 30 digitos'

        if cadena:
            patron = compile(r'[^0-9]')
            #patron = re.compile(r'\bfoo\b')
            # Usamos re.search para buscar coincidencias en la cadena
            if patron.search(str(cadena)):
                return True, 'El npn no puede contener datos alfanumericos o caracteres extraños' # Si se encuentra un carácter extraño, devolvemos False
            
        return False, 'pass'