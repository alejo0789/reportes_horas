# Plan — Asistente de IA en el Dashboard Betplay

> Objetivo: agregar dentro de la pestaña **Betplay** un **chat con un Asistente de IA** al que se le pueda preguntar sobre la información del dashboard y que pueda **responder en texto y generar visuales (gráficos / tablas)** que se rendericen dentro del propio chat.
>
> Restricción/recurso: el modelo ya está expuesto como **API compatible con OpenAI** desde una Mac local (LM Studio) en `http://10.0.29.27:1234/v1`.

---

## 1. Principios de diseño

1. **El navegador NO habla directo con la Mac.** Toda llamada al modelo pasa por **nuestro backend FastAPI** (proxy). Razones: evitar CORS, no exponer la IP/infra interna al cliente, controlar el contexto que se envía, validar/sanear la salida del modelo y poder cambiar de proveedor sin tocar el front.
2. **Datos ya agregados como contexto.** El endpoint `/api/betplay/resumen` ya calcula agregaciones compactas (por hora, zona, sitio, usuario, etc.). Eso es lo que se le da al modelo como "conocimiento del dashboard" — barato y suficiente. Las filas crudas (miles) **no** se mandan completas.
3. **Nunca ejecutar código generado por el modelo.** Las visualizaciones se generan como **especificaciones declarativas (JSON)** que nuestro front renderiza con librerías ya confiables. Cero `eval`, cero `<script>` inyectado.
4. **Reutilizar el stack actual.** Chart.js y el sistema de estilos "glass-panel" ya están en el proyecto.

---

## 2. Arquitectura propuesta

```
┌─────────────────────────────────────────────────────────────┐
│  Frontend (pestaña Betplay)                                 │
│  ┌──────────────┐     pregunta + contexto actual            │
│  │ Chat IA      │ ──────────────────────────────┐           │
│  │ (burbujas)   │                                │          │
│  │  - texto     │ ◄──── respuesta estructurada ──┤          │
│  │  - tabla     │      { tipo, texto, spec }     │          │
│  │  - gráfico   │                                │          │
│  └──────────────┘                                │          │
└──────────────────────────────────────────────────┼──────────┘
                                                     │ HTTP
┌────────────────────────────────────────────────────▼─────────┐
│  Backend FastAPI  (proxy + orquestación)                     │
│  POST /api/betplay/assistant                                 │
│   1. Toma pregunta + {tipo, desde, hasta}                    │
│   2. Recupera/usa el `resumen` agregado (cache SQLite)       │
│   3. Arma prompt: system + datos + esquema de respuesta      │
│   4. Llama a LM Studio (OpenAI SDK, base_url Mac)            │
│   5. Valida/parsea la salida JSON y la devuelve al front     │
└────────────────────────────────────────────────────┬─────────┘
                                                     │ OpenAI API
                                          http://10.0.29.27:1234/v1
                                                     ▼
                                            Mac local (LM Studio)
```

---

## 3. Cómo "aterrizar" al modelo en los datos (grounding)

| Estrategia | En qué consiste | Pro | Contra | Recomendación |
|-----------|-----------------|-----|--------|---------------|
| **A. Inyección de contexto** | Mandar el JSON del `resumen` (agregaciones) dentro del prompt. | Simple, 1 sola llamada, funciona con modelos locales pequeños. | Limitado al tamaño de contexto; no responde sobre filas crudas individuales. | ✅ **Punto de partida** |
| **B. Function calling / tools** | Dar al modelo "herramientas" (ej. `get_top_sitios`, `get_por_hora`) y que él decida. | Más flexible y exacto; escala a más datos. | Modelos locales suelen ser flojos en tool-calling; más complejo. | Fase 2 |
| **C. Texto-a-SQL** | El modelo genera SQL sobre las tablas y lo ejecutamos. | Responde cualquier pregunta sobre datos crudos. | Riesgo de SQL inseguro; requiere sandbox y validación fuerte. | ❌ No por ahora |

**Recomendado:** empezar con **A** (inyección del resumen agregado). Como las agregaciones ya están pre-calculadas y son compactas, el modelo puede responder la gran mayoría de preguntas ("¿qué zona vendió más?", "¿a qué hora hubo el pico?", "compárame top 3 sitios") sin tocar la BD de nuevo.

---

## 4. Cómo generar y mostrar las visualizaciones (el punto clave)

Tu preferencia: que se parezca a cómo genero **artifacts** en el chat de Claude y que se vean dentro del chat. Estas son las opciones, de la más conservadora a la más "libre":

### Opción 1 — Spec declarativa propia + Chart.js *(recomendada)*
El modelo devuelve un JSON con un **esquema acotado** que nosotros definimos, y el front lo traduce a Chart.js (ya integrado).

```json
{
  "tipo": "grafico",
  "texto": "La zona Norte concentra el 38% del monto.",
  "spec": {
    "chart_type": "bar",        // bar | line | doughnut | pie | horizontalBar
    "title": "Monto por zona",
    "x": ["Norte","Sur","Centro"],
    "series": [{ "label": "Monto", "data": [3800000, 2100000, 1500000] }]
  }
}
```
- **Pro:** seguro (esquema cerrado), consistente con el resto del dashboard, fácil de validar, funciona con modelos locales (formato simple).
- **Contra:** expresividad limitada a lo que mapeemos.
- **Encaja con:** "cerca de cómo generas gráficas" sin riesgo.

### Opción 2 — Vega-Lite (gramática declarativa de gráficos)
El modelo emite una spec **Vega-Lite** (estándar de la industria para describir visualizaciones como JSON) y el front la renderiza con la librería `vega-embed`.
- **Pro:** muy expresivo; los LLM conocen bien Vega-Lite; declarativo = sin ejecutar código. Es lo más parecido a "describir un gráfico" como hago yo.
- **Contra:** dependencia nueva (Vega + Vega-Lite + vega-embed, ~vía CDN); specs más complejas → más fáciles de "alucinar" en modelos pequeños.
- **Encaja con:** generación de visuales más ricas/variadas.

### Opción 3 — Artifact HTML/JS en iframe aislado (lo más parecido a Claude)
El modelo genera HTML+JS (con Chart.js) y lo mostramos en un `<iframe sandbox>` aislado.
- **Pro:** máxima libertad visual; es literalmente lo que hace un artifact.
- **Contra:** **riesgo de seguridad** (ejecutar código del modelo); requiere sandbox estricto (`sandbox="allow-scripts"`, sin acceso a la app ni a cookies); salida menos predecible. Modelos locales pueden generar código roto.
- **Encaja con:** prototipos; **no recomendado** para datos/infra reales sin endurecer el sandbox.

### Opción 4 — Generación de código ejecutado (estilo repo *Dynamic-dashboard-using-llm*)
El enfoque del repo que enviaste: el LLM genera código (Python/JS) que se **ejecuta** para construir el dashboard.
- **Pro:** flexibilidad total.
- **Contra:** **ejecución de código arbitrario** = el mayor riesgo de seguridad; pensado para entornos de confianza/demo. Difícil de mantener determinista.
- **Encaja con:** experimentación, no producción interna con datos sensibles.

### Tabla resumen

| Opción | Seguridad | Expresividad | Esfuerzo | Fit con modelo local | Veredicto |
|--------|-----------|--------------|----------|----------------------|-----------|
| 1. Spec propia + Chart.js | 🟢 Alta | 🟡 Media | 🟢 Bajo | 🟢 Bueno | ✅ **Recomendada (fase 1)** |
| 2. Vega-Lite | 🟢 Alta | 🟢 Alta | 🟡 Medio | 🟡 Medio | ⭐ **Fase 2 (gráficos ricos)** |
| 3. Artifact en iframe | 🔴 Baja* | 🟢 Alta | 🟡 Medio | 🟡 Medio | ⚠️ Solo con sandbox fuerte |
| 4. Código ejecutado | 🔴 Muy baja | 🟢 Alta | 🔴 Alto | 🔴 Frágil | ❌ No |

\* mitigable con `iframe sandbox`, pero nunca tan seguro como una spec declarativa.

**Recomendación final:** **Opción 1 como base** (spec propia → Chart.js + tablas HTML), con **Opción 2 (Vega-Lite) como evolución** cuando se necesiten gráficos más variados. Ambas evitan ejecutar código del modelo y se ven dentro del chat como "tarjetas" (texto, tabla o gráfico), que es justo el efecto artifact que buscas.

---

## 5. Protocolo de respuesta del asistente

El backend instruye al modelo (system prompt) para responder **siempre** con un JSON con esta forma; el front decide cómo pintarlo:

```json
{
  "tipo": "texto | tabla | grafico",
  "texto": "explicación en lenguaje natural (siempre presente)",
  "tabla": { "columns": ["...","..."], "rows": [["...","..."]] },   // si tipo=tabla
  "spec":  { "chart_type": "bar", "title": "...", "x": [...], "series": [...] } // si tipo=grafico
}
```
- `texto` siempre va (aunque haya gráfico) → el chat siempre muestra una explicación.
- El backend **valida** el JSON contra un esquema (Pydantic). Si el modelo devuelve algo inválido, se reintenta o se degrada a `tipo:"texto"` mostrando lo que se pueda.
- Se fuerza salida JSON con `response_format={"type":"json_object"}` (soportado por LM Studio en muchos modelos) y/o instrucciones estrictas en el system prompt.

---

## 6. Backend — diseño del endpoint

- **Nuevo endpoint:** `POST /api/betplay/assistant`
  - Body: `{ pregunta, tipo, desde, hasta, historial? }`
  - Recupera el `resumen` (de caché o consultando) para ese `tipo/desde/hasta`.
  - Construye el prompt: *system* (rol + esquema + reglas) + *datos* (resumen JSON, recortado) + *historial* + *pregunta*.
  - Llama a LM Studio con el SDK de OpenAI:
    ```python
    from openai import OpenAI
    client = OpenAI(base_url=os.getenv("LLM_BASE_URL"), api_key=os.getenv("LLM_API_KEY","lm-studio"))
    ```
  - Valida la respuesta y la devuelve al front.
- **Config en `.env`:** `LLM_BASE_URL=http://10.0.29.27:1234/v1`, `LLM_API_KEY=lm-studio`, `LLM_MODEL=local-model`.
- **Dependencia nueva:** agregar `openai` a `requirements.txt` (o usar `httpx`/`requests` directo al endpoint `/chat/completions` si se prefiere cero dependencias nuevas).
- **Robustez:** timeout configurable, manejo de Mac apagada/inaccesible (mensaje claro al usuario), límite de tokens, y opción de **streaming** (SSE) para que la respuesta aparezca progresiva como en un chat real (fase 2).

---

## 7. Frontend — UI del chat

- Panel de chat dentro de `#view-betplay` (por ejemplo, un botón flotante "Asistente IA" que abre un panel lateral, o una sección plegable al final).
- Burbujas de conversación; cada respuesta del asistente puede contener:
  - **texto** (markdown simple),
  - **tabla** (render HTML con los estilos `data-table` existentes),
  - **gráfico** (un `<canvas>` nuevo por mensaje, renderizado con Chart.js).
- El front envía como contexto el estado actual del dashboard (`tipo`, rango de fechas, métrica activa) para que el asistente hable de "lo que estás viendo".
- Estados: "pensando…", error de conexión con el modelo, reintentar.

---

## 8. Seguridad y privacidad

- Todo pasa por el backend; la IP de la Mac nunca llega al navegador.
- No se ejecuta código del modelo (specs declarativas validadas).
- Se envía al modelo solo el **resumen agregado** (sin PII innecesaria). Ojo: `NUM_IDENTIFICACION` es dato personal → decidir si se anonimiza/omite o se permite (ver preguntas abiertas).
- El modelo es **local** (no sale data a internet) — buen punto a favor de privacidad.

---

## 9. Plan de implementación sugerido

1. **Backend mínimo:** `.env` + dependencia + `POST /api/betplay/assistant` que solo devuelva `tipo:"texto"` (validar conexión con la Mac y grounding con el resumen).
2. **Chat UI básico:** panel + burbujas + envío de pregunta + render de texto.
3. **Tablas:** soportar `tipo:"tabla"`.
4. **Gráficos (Opción 1):** soportar `tipo:"grafico"` → Chart.js en burbuja.
5. **Pulido:** streaming, historial, manejo de errores, prompt-tuning.
6. **(Opcional) Vega-Lite (Opción 2)** para visualizaciones más ricas.

---

## 10. Preguntas abiertas (para decidir antes de implementar)

1. **Alcance de los datos:** ¿el asistente responde solo sobre el **resumen agregado** (recomendado) o también necesita razonar sobre filas crudas individuales (ej. "muéstrame las transacciones del usuario X")? Esto define si basta la Opción A o hay que ir a tools/SQL.
2. **PII:** ¿se le puede pasar `NUM_IDENTIFICACION` al modelo? (Es local, pero conviene confirmar política).
3. **Visualización:** ¿arrancamos con **Opción 1 (Chart.js)** y luego evaluamos Vega-Lite? (recomendado) ¿o quieres directamente Vega-Lite?
4. **Ubicación en la UI:** ¿panel lateral, modal, o sección al final de la pestaña Betplay?
5. **Modelo:** ¿qué modelo está cargado en LM Studio? (su tamaño/capacidad define cuánto exigirle en JSON estructurado y tool-calling).
6. **Streaming:** ¿lo quieres desde el inicio (respuesta progresiva) o más adelante?

---

## 11. Decisiones acordadas e implementación

### 11.1 Decisiones (respuestas a la sección 10)

| # | Decisión |
|---|----------|
| Grounding | **Híbrido**: se inyecta un **resumen agregado** (compacto) como contexto **y** el modelo puede **generar SQL de solo lectura** cuando lo necesite, para razonar sobre datos crudos. |
| PII | **Acceso total**, sin anonimizar (incluye `NUM_IDENTIFICACION`). |
| Visualización | **Opción 1** — spec declarativa propia → **Chart.js**. |
| Ubicación | **Pestaña independiente** ("Asistente IA"), que ocupe buena parte de la pantalla, con **verificación de conexión** a la Mac del modelo. |
| Modelo | **gemma-4-12B-it-qat** en LM Studio (12B, cuantizado). Capaz de JSON simple; el SQL/loop se maneja con protocolo propio (no tool-calling nativo, más fiable en local). |
| Streaming | **Sí**: se hace streaming del razonamiento/texto; al detectar el inicio de un bloque de visualización (gráfico/tabla) se **buffer-ea hasta completarlo** y se renderiza como burbuja-isla. |

> **Pendiente menor (grounding):** qué tan detallado va el contexto de esquema. **Recomendación:** dar (a) el **resumen agregado** + (b) un **catálogo de esquema acotado** (solo las tablas/columnas de las consultas base de Betplay: `SIGT_PAGOS`, `SIGT_RECARGAS`, `MAET_USUARIOS`, `MAET_SITIOSVENTA`, `MAET_*` geográficas) para que el SQL salga aterrizado. No darle todo el diccionario de la BD.

### 11.2 Nueva pestaña "Asistente IA"

- Tercera tab junto a "Ventas por Hora" y "Betplay".
- **Indicador de conexión** con la Mac (verde/rojo) que consulta un endpoint de salud al abrir la pestaña y periódicamente.
- **Panel de KPIs generales** arriba (sin tener que elegir tipo): **dos filas**, una para **Pagos** y otra para **Recargas**, cada una con: Monto Total · Transacciones · Usuarios Únicos · Sitios de Venta. (Por defecto, día actual.)
- **Zona de chat** que ocupa el grueso de la pantalla: historial de burbujas + caja de texto para preguntar.
- Las gráficas/tablas generadas aparecen como **burbuja-isla** dentro de la progresión del chat (una tarjeta independiente intercalada entre los mensajes).

### 11.3 Protocolo de conversación (streaming + SQL en loop)

Se usa un **protocolo propio basado en bloques marcados** dentro del texto del modelo (no `json_object` global, para permitir streaming natural). El modelo escribe en lenguaje natural y, cuando necesita algo estructurado, abre un bloque cercado:

- **Solicitar datos (SQL):**
  ```` ```sql ````  → `SELECT ... ` →  ```` ``` ````
- **Generar un gráfico:**
  ```` ```chart ````  → `{ "chart_type": "...", "title": "...", "x": [...], "series": [...] }` → ```` ``` ````
- **Generar una tabla:**
  ```` ```table ````  → `{ "columns": [...], "rows": [[...]] }` → ```` ``` ````

**Orquestación en el backend (ReAct simplificado):**
1. Backend arma el prompt (system + esquema acotado + resumen agregado + historial + pregunta).
2. Llama al modelo. Si la respuesta contiene un bloque ` ```sql `:
   - **Valida** el SQL (solo `SELECT`, una sola sentencia, sin DML/DDL, esquemas permitidos, `FETCH FIRST N ROWS ONLY`, timeout) y lo ejecuta en **CAUCA/FORTUNA** en modo lectura.
   - Inserta el resultado (recortado) como nuevo mensaje y vuelve a llamar al modelo. Máximo **N iteraciones** (ej. 3) para evitar loops.
3. Cuando el modelo produce la **respuesta final** (sin más `sql`), se hace **streaming** al front:
   - El texto/razonamiento se muestra token a token.
   - Al detectar ` ```chart ` o ` ```table `, el front **pausa el render** de ese fragmento, **acumula** hasta el cierre ` ``` `, parsea el JSON, lo **valida** y lo pinta como burbuja-isla (Chart.js o tabla HTML). Si el JSON es inválido, se muestra el texto crudo como fallback.

> Los pasos de SQL (paso 2) se muestran en el chat como chips de estado: *"🔎 Consultando base de datos…"*, sin exponer el SQL salvo en un detalle plegable opcional.

### 11.4 Seguridad del SQL (solo lectura)

- Lista blanca: la sentencia debe empezar por `SELECT` (tras `WITH` permitido), **una sola** sentencia (sin `;` múltiples).
- **Verificación por regex (obligatoria):** si la sentencia contiene cualquier término de escritura/DDL/DCL **no se ejecuta** y se devuelve un error al modelo. Patrón de bloqueo (case-insensitive, límites de palabra): `INSERT, UPDATE, DELETE, MERGE, DROP, ALTER, CREATE, TRUNCATE, GRANT, REVOKE, EXEC, EXECUTE, BEGIN, DECLARE, CALL, COMMIT, ROLLBACK, INTO, RENAME, REPLACE`. Cualquier coincidencia ⇒ rechazo.
- Restringir a esquemas permitidos (`GANA_SIGA`, `GANA_MAESTROS`).
- Forzar límite de filas (`FETCH FIRST 500 ROWS ONLY`) y **timeout** de consulta.
- Usuario de BD ya es de reportes (lectura), reforzando la barrera.
- Las filas devueltas al modelo se **recortan** (tope de filas/columnas) para no desbordar el contexto.

### 11.5 Backend — endpoints nuevos

- `GET /api/assistant/health` → hace ping a `LLM_BASE_URL` (ej. `GET /v1/models`); devuelve `{ online: true/false, model }`. Para el indicador de conexión.
- `POST /api/assistant/chat` → body `{ pregunta, historial, contexto: { desde, hasta } }`. Orquesta el loop SQL y **streamea** la respuesta final (SSE / `text/event-stream`).
- (Reutiliza `/api/betplay/resumen` para armar el resumen agregado de Pagos y Recargas que se inyecta como contexto y para los KPIs de la cabecera.)
- **Config `.env`:** `LLM_BASE_URL=http://10.0.29.27:1234/v1`, `LLM_API_KEY=lm-studio`, `LLM_MODEL=local-model`, `LLM_MAX_SQL_ITERS=3`, `LLM_SQL_ROW_LIMIT=500`.
- **Dependencia:** agregar `openai` a `requirements.txt` (cliente compatible; soporta `stream=True`).

### 11.6 Frontend — componentes

- Tab "Asistente IA" + indicador de conexión (consulta `/api/assistant/health`).
- Cabecera KPIs Pagos/Recargas (2 filas) usando `/api/betplay/resumen` para hoy.
- Chat: lista de mensajes, input, botón enviar; manejo de **streaming** (lectura incremental del `ReadableStream`/SSE).
- **Parser de bloques** en el cliente: detecta ` ```chart `/` ```table `/` ```sql `, separa texto de specs, y renderiza burbujas-isla. Validación de la spec antes de instanciar Chart.js.
- Estados: "pensando…", chips de SQL, error de conexión con reintento.

### 11.7 Pasos de implementación

1. **Config + salud:** `.env`, dependencia `openai`, endpoint `/api/assistant/health` y el indicador en una nueva tab (sin chat aún). → *Valida conexión con la Mac.*
2. **Chat texto (sin SQL):** `/api/assistant/chat` con streaming, system prompt + resumen agregado como contexto; render de burbujas de texto.
3. **Bloques de visualización:** soportar ` ```chart ` y ` ```table ` con parser + render (Chart.js / tabla) como burbuja-isla.
4. **Loop SQL de solo lectura:** validación + ejecución + reinyección, con chips de estado.
5. **KPIs Pagos/Recargas** en la cabecera de la pestaña.
6. **Pulido:** historial multi-turno, manejo de errores/timeout, prompt-tuning para gemma, detalle plegable del SQL.

### 11.8 Riesgos / notas

- **gemma-3-12B** puede equivocarse en SQL o en el JSON de las specs → por eso validamos todo y degradamos a texto si algo viene mal.
- Si la Mac está apagada/inaccesible, la pestaña debe avisar claramente (indicador rojo + mensaje) y deshabilitar el envío.
- El streaming con loop de SQL implica que **solo la respuesta final** se streamea; los pasos intermedios de SQL se ven como estados, no como tokens.
