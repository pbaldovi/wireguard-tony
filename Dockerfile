# Imagen base oficial de Python 3.10 (versión 'slim' es más ligera).
FROM python:3.10-slim

# Establecemos el directorio de trabajo en /app
WORKDIR /app

# Copiamos el archivo de dependencias al contenedor
COPY requirements.txt requirements.txt

# Instalamos dependencias (Flask, etc.)
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos el resto de archivos de la carpeta actual a /app
COPY . .

# Exponemos el puerto 8080 (o el que uses en app.run).
EXPOSE 8080

# Ejecutamos la aplicación
CMD [ "python", "main.py" ]