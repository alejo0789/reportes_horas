# Arquitectura del Sistema - Reportes de Operaciones

Este documento describe la estructura organizativa, el flujo de procesamiento de datos, la persistencia de información y el sistema de mensajería (WhatsApp) que conforma el proyecto.

## 1. Estructura y Componentes del Proyecto
El sistema sigue un enfoque monolítico separando de manera lógica el backend (API) del frontend (Dashboard visual).
* **`backend/`**: Capa de acceso a datos y lógica de negocio basada en **FastAPI**.
  * `main.py`: Punto de entrada de la API. Define todos los endpoints y webhooks, gestionando las respuestas a los clientes web y los bots.
  * `db.py`: Administra la conexión a la base de datos relacional de producción en **Oracle** (esquema CAUCAMED).
  * `cache.py`: Interfaz de operaciones (CRUD) contra la base de datos **SQLite** local, la cual actúa como capa de velocidad.
  * `queries.py`: Colección de sentencias SQL y procedimientos almacenados estructurados para la lectura de datos de Oracle.
  * `excel_parser.py`: Motor responsable de las lógicas ETL.
* **`frontend/`**: Cliente nativo construido en JavaScript y HTML sin librerías complejas. Se encarga de hacer peticiones asíncronas a la API y renderizar gráficos y métricas (ubicado bajo los archivos `app.js`, `styles.css` e `index.html`).
* **`uploads/`**: Directorio donde se almacenan y consolidan los archivos subidos (como excels) y los `.json` generados durante el ETL.
* **`scripts/` & `scratch/`**: Conjunto de rutinas para ejecutar tareas de limpieza de caché o diagnósticos aislados.

## 2. Proceso ETL (Extracción, Transformación y Carga)
Dado que las reglas de negocio, la estructura comercial (Coordinadores, Promotores) y las metas financieras de la empresa se manejan usualmente a través de hojas de cálculo, el sistema incluye un proceso ETL ligero:

1. **Extracción:** Un administrador o proceso carga los archivos de Excel (por ejemplo, "Directorio Promotores", "Productos tipo") hacia el sistema.
2. **Transformación (`excel_parser.py`):** El sistema lee las matrices, depura filas vacías, normaliza los textos (ej. nombres de asesores y zonas) y mapea los montos de "Meta" con los "Códigos de Agencia".
3. **Carga:** Una vez normalizados los datos, se persisten en formato plano en la carpeta `uploads/` (ej. `distribution.json`, `goals.json`) y simultáneamente en la base de datos de caché local (SQLite). Esto permite un acceso veloz al momento de cruzar la información sin incurrir en lecturas lentas sobre archivos pesados en cada petición.

## 3. Almacenamiento y Mecanismo de Caché
El procesamiento de millones de filas de transacciones de ventas no puede ejecutarse directamente a la base de datos principal por cada vez que un usuario abra el Dashboard. Para mitigarlo, se utiliza una **Arquitectura de Caché basada en SQLite**:

* **Base de Datos Principal (Oracle DB):** Contiene la verdad absoluta de todas las transacciones generadas en la plataforma de giros y chance.
* **Base de Datos Caché (SQLite):** 
  * Cada vez que se consulta la API de ventas por un periodo o fecha específica, el backend revisa primero si el registro ya existe en SQLite y si está "fresco".
  * **Hit de Caché:** Si los datos existen y tienen menos de *N* minutos de antigüedad, la API los despacha instantáneamente.
  * **Miss de Caché:** Si los datos no existen o expiraron, el backend dispara las macros / consultas en `queries.py` hacia Oracle, espera la respuesta, guarda el resumen consolidado en SQLite e inmediatamente se lo entrega al usuario web.

## 4. Consultas Principales de la Aplicación
El bloque de `queries.py` y `db.py` está configurado para ejecutar principalmente tres tipos de extracción:
1. **Ventas en Vivo / Diarias:** Agregaciones con cláusulas `GROUP BY` por `Cod_Sitio` (Zona), sumando el valor de ventas de recargas, chance, giros, etc., en la base de datos Oracle.
2. **Consultas de Cumplimiento:** Aquellas donde el motor local cruza los totales de ventas provenientes de la caché con los objetivos diarios almacenados en el archivo `.json` producto del ETL.
3. **Trazabilidad de Recaudos / Pagos:** Procedimientos almacenados para conciliar pagos (`/api/payments/verify`), determinando el estado contable de una consignación para su aprobación al agente.

## 5. Integración y Comunicación con WhatsApp
Una de las funcionalidades críticas del sistema es la capacidad de enviar reportes personalizados a los celulares de los promotores de la operación usando la API de WhatsApp.

**Diagrama de Comunicación:**
1. **Recepción del Mensaje (Webhook Directo):** Las notificaciones de los mensajes de WhatsApp llegan directamente al backend (FastAPI) mediante un webhook configurado desde la API Oficial de WhatsApp cuando el usuario escribe a la línea corporativa. No hay herramientas intermedias.
2. **Procesamiento de la Solicitud:** Al detectar la palabra clave (ej. "ventas" o "reporte"), el backend extrae directamente el `phone` del promotor (ej. `3108723207`) desde el payload recibido.
3. **Match e Identificación:** 
   * FastAPI aplica expresiones regulares para normalizar el número (retirar prefijos +57, guiones, etc.) y busca al asesor en la base de datos local pre-cargada.
   * Se recupera su jerarquía y las zonas bajo su responsabilidad.
4. **Cruce de KPIs:** Usando la información del Caché (SQLite) y el archivo de metas (`goals.json`), el sistema computa el Total de Venta del día, la Meta fijada y el porcentaje de cumplimiento actual.
5. **Retorno de Mensaje:** El backend arma una cadena de texto formateada con emojis (🟢/🔴, 📊) listando de forma detallada el comportamiento oficina por oficina. Esta cadena es devuelta a la API Oficial de WhatsApp para que se envíe al celular del solicitante.
