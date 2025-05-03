from django.utils.http import urlsafe_base64_encode
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.utils import timezone

from dotenv import load_dotenv
import os
load_dotenv()
FRONTEND_URL = os.getenv('FRONTEND_URL')
FRONTEND_URL = 'http://localhost:8080'

def create_token_reset(user, bodyMail, path):
    # GENERAR TOKEN
    token = default_token_generator.make_token(user)
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))

    # GENERACION DE ENLACE DE ACTIVACION
    link = f'{FRONTEND_URL}/{path}/{uidb64}/{token}'
    user.activation_token_created = timezone.now()
    user.save()
    
    subject = bodyMail.get('subject')
    template = bodyMail.get('template')

    # Datos para el template
    context = {
        'username': user.username,
        'link': link
    }

    # Renderizar el contenido HTML del correo
    html_content = render_to_string(template, context)
    text_content = strip_tags(html_content)  # Versión de texto sin formato
    
    # Crear el mensaje de correo electrónico
    email = EmailMultiAlternatives(
        subject,
        text_content,
        'info@valleavanza.com',
        [user.email]
    )
    
    # Adjuntar la versión HTML
    email.attach_alternative(html_content, "text/html")

    # Enviar el correo
    email.send()
