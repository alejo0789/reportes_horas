# Reportes de Operaciones - Ventas y Cumplimiento 📊

Sistema integral para el monitoreo, consolidación y consulta de ventas, metas y recaudo para las operaciones comerciales. Este proyecto cuenta con un dashboard analítico web, integración directa a bases de datos corporativas (Oracle) y un bot de consultas en tiempo real vía WhatsApp.

## 🚀 Características Principales
* **Dashboard Interactivo:** Vista centralizada con KPIs de ventas por hora, porcentajes de cumplimiento de metas diarias y estado del recaudo.
* **Proceso ETL Integrado:** Carga y transformación de presupuestos, metas y jerarquías comerciales a partir de la importación de archivos de Excel.
* **Sistema de Caché Inteligente:** Utiliza una capa de persistencia en SQLite para minimizar la sobrecarga de consultas en la base de datos principal (Oracle), garantizando un rendimiento óptimo y tiempos de respuesta sub-segundo.
* **Integración con WhatsApp:** Los promotores y coordinadores pueden consultar sus ventas por WhatsApp. Las notificaciones de los mensajes (vía la API Oficial de WhatsApp) llegan directamente al backend a través de un webhook, el cual procesa la respuesta y contesta de manera inmediata sin herramientas intermediarias.
* **Verificación de Pagos (Asíncrona):** Módulo especializado para la validación en tiempo real de transacciones bancarias, evitando demoras en el flujo de los agentes.

## 🏗️ Documentación de Arquitectura
Para comprender en profundidad cómo fluyen los datos, la lógica del ETL y los mecanismos de comunicación del sistema, visita el siguiente documento:

👉 **[Ver Arquitectura del Sistema (doc/architecture.md)](doc/architecture.md)**

## 💻 Stack Tecnológico
* **Backend:** Python, FastAPI, Uvicorn.
* **Bases de Datos:** Oracle Database (Maestra), SQLite (Caché y persistencia de configuración).
* **Frontend:** HTML5, Vanilla CSS, JavaScript (Dashboard de reportes).
* **Automatización y Notificaciones:** API Oficial de WhatsApp.
* **Tratamiento de Datos:** Pandas, cx_Oracle / oracledb.

## ⚙️ Instalación y Despliegue Local

1. **Clonar el repositorio:**
   ```bash
   git clone http://192.168.2.76:8081/ia/reportes_operaciones.git
   cd reportes_operaciones
   ```

2. **Crear y activar un entorno virtual (Recomendado):**
   ```bash
   python -m venv venv
   # En Windows:
   venv\Scripts\activate
   # En macOS/Linux:
   source venv/bin/activate
   ```

3. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Variables de Entorno:**
   Asegúrate de crear un archivo `.env` en la raíz del proyecto tomando como referencia las configuraciones de tu infraestructura local. Debes incluir las credenciales de conexión a la base de datos Oracle (`CAUCAMED`) y los puertos de ejecución.

5. **Ejecutar el servidor:**
   ```bash
   python run.py
   ```
   La aplicación se expondrá (por defecto) en `http://localhost:8000`.
