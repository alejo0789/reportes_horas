# Usa una imagen base oficial de Python ligera
FROM python:3.11-slim

# Establece variables de entorno
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8032

# Crea y establece el directorio de trabajo
WORKDIR /app

# Instala dependencias del sistema operativo que puedan ser necesarias para compilar o ejecutar librerías
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copia primero los requerimientos para aprovechar la caché de Docker
COPY requirements.txt .

# Instala las dependencias de Python
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copia el resto del código del proyecto
COPY . .

# Crea el directorio uploads por si no existe, ya que ahí se guarda la DB y los JSON
RUN mkdir -p uploads && chmod -R 777 uploads

# Expone el puerto configurado (el mismo que usa Coolify para enrutar)
EXPOSE 8032

# Comando para ejecutar la aplicación
CMD ["python", "run.py"]
