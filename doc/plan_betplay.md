# Plan de Implementación — Módulo Betplay

> Rama de trabajo: `feature/betplay` (GitFlow, nace de `desarrollo`).
> Objetivo: agregar una nueva pestaña en el dashboard con visualizaciones de **Pagos** y **Recargas** del producto Betplay para la toma de decisiones (mejores ventas por usuario, zona, hora, oficina, etc.).

---

## 1. Decisiones tomadas

| Tema | Decisión |
|------|----------|
| **Navegación** | Sistema de **pestañas (tabs)** dentro del mismo `index.html`. Tab 1 = "Ventas por Hora" (lo actual, intacto). Tab 2 = "Betplay" (nuevo). |
| **Rango de fechas** | 3 modos: **día actual (por defecto)**, **fecha puntual** y **rango de fechas**. Implica parametrizar las queries. |
| **Origen de datos** | Ambas bases Oracle: **CAUCAMED + FORTUMED** (unir resultados, igual que `/api/ventas`). |

---

## 2. Arquitectura actual reutilizable

Lo que **ya existe** y vamos a aprovechar (no reinventar):

- **`backend/db.py`** → `db_manager` con `pool_cauca` / `pool_fortuna` y los context managers `get_cauca_connection()` / `get_fortuna_connection()`.
- **`backend/main.py`** → helper `rows_to_dicts(cursor)` para convertir filas Oracle a dicts; patrón de doble consulta (CAUCA + FORTUNA) con `try/except` y `db_failures`, ver `/api/ventas` ([main.py:219](../backend/main.py#L219)).
- **`backend/cache.py`** → capa de caché SQLite (`get_cached_sales` / equivalentes). Reutilizable para cachear por `cache_key = f"{desde}_{hasta}"`.
- **`backend/queries.py`** → ya contiene `PAGOS_BETPLAY_COMPLETO` y `RECARGAS_BETPLAY_COMPLETO` (cruce completo con sitio/ciudad/oficina/subzona/zona). **Falta parametrizar fechas.**
- **`frontend/`** → `index.html` + `app.js` (objeto `State`, `API_BASE`, `fetch`) + `styles.css` (sistema "glass-panel"). **Chart.js ya está cargado** vía CDN ([index.html:14](../frontend/index.html#L14)).

---

## 3. Backend — cambios

### 3.1 Parametrizar las queries (`backend/queries.py`)
Cambiar en `PAGOS_BETPLAY_COMPLETO` y `RECARGAS_BETPLAY_COMPLETO`:

```sql
-- antes
WHERE P.IDE_PRODUCTO = 17288
  AND TRUNC(P.FEC_PAGO) = TRUNC(SYSDATE)

-- después (rango [desde, hasta) inclusivo del día)
WITH params AS (
  SELECT TO_DATE(:desde,'YYYY-MM-DD HH24:MI:SS') AS desde,
         TO_DATE(:hasta,'YYYY-MM-DD HH24:MI:SS') AS hasta
  FROM dual
)
... FROM GANA_SIGA.SIGT_PAGOS P, params pr
WHERE P.IDE_PRODUCTO = 17288
  AND P.FEC_PAGO >= pr.desde
  AND P.FEC_PAGO <  pr.hasta
```
- Pagos filtra por `FEC_PAGO`; Recargas por `FEC_VENTA`.
- El modo "día actual" lo resuelve el frontend mandando `desde = hoy 00:00:00`, `hasta = mañana 00:00:00`.
- Conservamos las versiones básicas `PAGOS_BETPLAY` / `RECARGAS_BETPLAY` por si se usan en otro contexto (o se eliminan si no aportan).

### 3.2 Nuevos endpoints (`backend/main.py`)
Siguiendo el molde de `/api/ventas`:

- **`GET /api/betplay/pagos?desde=&hasta=&force_refresh=`**
- **`GET /api/betplay/recargas?desde=&hasta=&force_refresh=`**

Cada uno:
1. Revisa caché SQLite (`cache_key` propio, ej. `betplay_pagos_{desde}_{hasta}`).
2. Si miss/force → consulta CAUCA + FORTUNA, etiqueta `Fuente`, une resultados.
3. Guarda en caché y responde `{ source, last_updated, data }`.

> **Decidir:** ¿un endpoint combinado `/api/betplay/resumen` que ya devuelva las agregaciones (por usuario/zona/hora) o devolver filas crudas y agregar en el frontend? **Recomendación:** devolver filas crudas + un endpoint de agregación opcional, para no recalcular en JS sobre miles de filas. (Pendiente de confirmar en implementación.)

### 3.3 Caché (`backend/cache.py`)
- Reutilizar la tabla/funciones existentes parametrizando por `cache_key`, o agregar funciones `get_cached_betplay` / `set_cached_betplay` si el esquema actual está acoplado a "ventas". A evaluar al abrir `cache.py`.

---

## 4. Frontend — cambios

### 4.1 Estructura de pestañas (`index.html`)
- Agregar una **barra de tabs** justo bajo el `<header>`:
  - `Tab "Ventas por Hora"` → envuelve TODO el contenido actual (`.kpi-grid`, `.dashboard-grid`, `.table-panel`) en un `<section id="view-ventas">`.
  - `Tab "Betplay"` → nuevo `<section id="view-betplay" hidden>`.
- Toggle de tabs en `app.js` (mostrar/ocultar secciones, marcar tab activa). Sin librerías.

### 4.2 Vista Betplay (nuevo bloque HTML + JS)
Controles superiores:
- Selector de **tipo**: Pagos / Recargas (o ambos).
- Selector de **modo de fecha**: Hoy | Fecha puntual | Rango (inputs `date`).
- Botón refrescar (force_refresh).

Visualizaciones propuestas (Chart.js, reutilizando estilos `glass-panel chart-panel`):
1. **KPIs**: total transacciones, monto total, # usuarios únicos, # sitios.
2. **Top usuarios por venta** (`NUM_IDENTIFICACION`) — barra horizontal.
3. **Ventas por Zona** — barra / dona.
4. **Ventas por Hora** — línea (extraer hora de `FEC_PAGO`/`FEC_VENTA`).
5. **Ventas por Oficina / Sitio** — barra (top N).
6. **Tabla detalle** con búsqueda y filtros (reutilizar patrón de la tabla actual).

### 4.3 `app.js`
- Nuevas funciones: `fetchBetplay(tipo, desde, hasta)`, `renderBetplayCharts(data)`, helpers de agregación (`groupBy` por usuario/zona/hora).
- Reutilizar `API_BASE`, formateadores de moneda y el objeto `State` (añadir `State.betplay`).

### 4.4 `styles.css`
- Agregar estilos de la barra de tabs (`.tab-bar`, `.tab-btn`, `.tab-btn.active`). Reusar variables de color existentes.

---

## 5. Orden de ejecución sugerido

1. **[backend]** Parametrizar las 2 queries Betplay con `:desde`/`:hasta`.
2. **[backend]** Endpoints `/api/betplay/pagos` y `/api/betplay/recargas` (sin caché primero, validar datos reales).
3. **[backend]** Integrar caché SQLite.
4. **[frontend]** Barra de tabs + envolver vista actual sin romperla.
5. **[frontend]** Controles de fecha/tipo + 1 gráfico (ventas por hora) como prueba de extremo a extremo.
6. **[frontend]** Resto de visualizaciones + tabla detalle.
7. **Pruebas** con día actual, fecha puntual y rango.
8. **Merge** `feature/betplay` → `desarrollo` (`git merge --no-ff`).

---

## 6. Preguntas abiertas / a validar

- ¿Agregación en backend o frontend? (ver 3.2).
- ¿La caché actual de `cache.py` es reutilizable tal cual o requiere funciones nuevas?
- ¿"Mejor venta por usuario" se mide por **monto** o por **# de transacciones**? (definir métrica principal).
- ¿Qué columna de monto usar en Pagos (`VALOR_PAGO`?) y en Recargas (`VLR_RECARGA`?) — confirmar nombres reales al inspeccionar `P.*` / `R.*`.

---

## 7. Paso 2 — Propuestas de visualizaciones y datos requeridos

> Estado de las decisiones de este paso:
> - **Monto**: Pagos → `VALOR_PAGO`; Recargas → `VLR_RECARGA`. ✅
> - **Métrica de rankings**: mostrar **monto ($)** y **cantidad de transacciones** por separado (toggle o doble serie). ✅
> - **Coordenadas**: `SV.CX` / `SV.CY` son **lat/long reales** → mapa de puntos y mapa de calor viables. ✅
> - **Filtro de estado**: ❌ **No se aplica** por ahora (se traen todas las filas). Se podrá añadir luego.
> - **Columna extra útil**: `IDE_CANAL` disponible en las tablas transaccionales → habilita análisis por canal.
> - **Zona horaria**: Bogotá/Colombia (America/Bogota). Las fechas se interpretan en hora local de Colombia.
> - **Agregación**: en el **backend** (endpoint `/resumen` con agregaciones pre-calculadas). ✅

### 7.1 Datos que ya tenemos disponibles (del cruce de las queries)
De `PAGOS_BETPLAY_COMPLETO` / `RECARGAS_BETPLAY_COMPLETO`:
- **Monto**: `VALOR_PAGO` (pagos) / `VLR_RECARGA` (recargas).
- **Fecha/hora**: `FEC_PAGO` (pagos) / `FEC_VENTA` (recargas) → para series por hora/día.
- **Usuario**: `NUM_IDENTIFICACION` (identificación del usuario que registró).
- **Geografía comercial**: Zona, Subzona, Ciudad, Oficina, Sitio de venta (códigos + nombres).
- **Sitio**: tipo de SV, nivel/categoría, dirección, activo/inactivo, **`CX`/`CY` (lat/long)**.

### 7.2 Información que aún falta / a validar
1. **Columnas reales de `SIGT_PAGOS` y `SIGT_RECARGAS`** (`P.*` / `R.*`): confirmar si traen otros campos útiles (canal, terminal, número de cuenta/teléfono recargado, tipo de operación). → Se resuelve inspeccionando una fila real al construir el endpoint.
2. **Campo y valores de estado** para filtrar transacciones válidas (ver ⚠️ arriba).
3. **Zona horaria** de `FEC_PAGO`/`FEC_VENTA` (asumimos hora local del servidor Oracle).
4. **Volumen esperado** de filas en rangos amplios → define si agregamos en backend (recomendado) o frontend.

### 7.3 Catálogo de visualizaciones propuestas

**Fila de KPIs (tarjetas superiores)** — reutiliza `kpi-card`:
- Monto total del periodo ($).
- Nº total de transacciones.
- Nº de usuarios únicos (`NUM_IDENTIFICACION`).
- Nº de sitios de venta activos en el periodo.
- Ticket promedio (monto / nº transacciones).

**Gráficos principales** (Chart.js, ya cargado):
1. **Barras por hora** — eje X = hora del día (0–23), eje Y = monto y/o cantidad. Serie doble o toggle monto/cantidad. *(Pagos usa `FEC_PAGO`, Recargas `FEC_VENTA`.)*
2. **Barras por día** — cuando el modo de fecha es "rango", evolución diaria del periodo.
3. **Torta / dona — distribución por Zona** — participación de cada zona en el monto total.
4. **Torta / dona — distribución por Tipo de SV** (`Tipo SV`) — mix de canales/tipos de punto.
5. **Barras horizontales — Top N sitios de venta** (por monto y por cantidad, toggle).
6. **Barras horizontales — Top N usuarios** (`NUM_IDENTIFICACION`) por monto y por cantidad.
7. **Barras — ranking por Oficina** (y drill-down opcional Zona → Oficina → Sitio).
8. **Barras apiladas — Ciudad/Subzona** según necesidad de detalle geográfico.

**Mapa geográfico** (lat/long disponibles → usar **Leaflet** vía CDN):
9. **Mapa de puntos** — un marcador por sitio (`CX`/`CY`), tamaño/color según monto; popup con sitio, oficina, zona y total.
10. **Mapa de calor (heatmap)** — densidad/intensidad de ventas por ubicación (`Leaflet.heat`).

**Tabla detalle**:
11. Tabla con búsqueda y filtros (zona, oficina, usuario), reutilizando el patrón de la tabla actual; exportable a futuro.

### 7.4 Estrategia de agregación (propuesta)
Para no mover miles de filas crudas al navegador, el backend devolverá **agregaciones pre-calculadas** además (o en vez) de las filas:
- `por_hora`, `por_dia`, `por_zona`, `por_tipo_sv`, `por_oficina`, `por_sitio` (incluye `cx`/`cy`), `por_usuario`, y `totales` (KPIs).
- Cada grupo con `monto` y `cantidad`.
- Endpoint propuesto: `GET /api/betplay/resumen?tipo=&desde=&hasta=` que devuelve ese objeto agregado; opcionalmente `GET /api/betplay/detalle` para filas crudas de la tabla.

### 7.5 Librerías nuevas a incorporar
- **Leaflet** (mapa) + **Leaflet.heat** (mapa de calor) vía CDN. Chart.js ya está disponible.
