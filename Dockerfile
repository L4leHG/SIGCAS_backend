# Usar una imagen base de Python
FROM python:3.11-slim

# Establecer variables de entorno
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Establecer el directorio de trabajo
WORKDIR /app

RUN apt-get update && \
    apt-get -y upgrade && \
    apt-get -y install \
    locales locales-all\
    libffi-dev \
    libpq-dev \
    libffi-dev \
    python-dev-is-python3 \
    build-essential \
    gdal-bin binutils libproj-dev libgdal-dev \
    libpango-1.0-0 \
    libharfbuzz0b \
    libpangoft2-1.0-0 \
    libffi-dev \
    libjpeg-dev \
    libopenjp2-7-dev \
    libcairo2 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt


# Copiar el código del proyecto
COPY . /app/

# Exponer el puerto en el que correrá la aplicación
EXPOSE 8500

# Comando para correr la aplicación
CMD ["python", "manage.py", "runserver", "0.0.0.0:8500"] 