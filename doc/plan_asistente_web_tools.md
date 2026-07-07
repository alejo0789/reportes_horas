# Plan — Herramientas web para el Asistente IA (Betplay)

Rama de desarrollo: `feature/asistente-web-tools` (a partir de `desarrollo`).

## Objetivo

Dar al asistente IA tres fuentes externas gratuitas para **explicar comportamientos
atípicos** (picos altos/bajos) y enriquecer el análisis:

| Herramienta | Fuente | Red | Uso |
|-------------|--------|-----|-----|
| ` ```buscar `  | DuckDuckGo (`ddgs`) | Sí | Búsqueda web general (causas de picos, eventos, contexto). |
| ` ```deporte ` | TheSportsDB (API pública) | Sí | Calendario/resultados de fútbol (¿jugó Colombia esa fecha?). |
| ` ```festivo ` | Librería `holidays` (CO) | **No (local)** | ¿La fecha fue festivo en Colombia? |

## Decisiones tomadas

1. El backend de producción **tiene salida a internet** → DDG y TheSportsDB son viables.
2. Presupuesto de iteraciones **separado** para web (`LLM_MAX_WEB_ITERS`), no comparte
   con los turnos de SQL (`LLM_MAX_SQL_ITERS`).
3. Se mantiene el **patrón ReAct de bloques cercados** (regex + reinyección), NO se migra
   a tool-calling nativo (Gemma local es inconsistente con function-calling; el patrón
   actual es aditivo y tolerante).
4. **Doble control de cuándo usar web:**
   - Regla en el system prompt: el modelo usa `buscar`/`deporte` **solo si la pregunta lo
     requiere** (nunca en preguntas de puro dato de BD).
   - **Toggle web** en la UI: permite/bloquea el acceso a internet (default: activado).
     `festivo` es local y **queda inmune al toggle** (siempre disponible).

## Arquitectura de referencia (lo que ya existe)

- LLM local vía LM Studio, API OpenAI-compat: `backend/main.py:2084`.
- Loop ReAct con streaming: `backend/main.py:2759-2860`.
- Detección de herramientas por regex `_TOOL_FENCE_RE`: `backend/main.py:2605`.
- Ejecutores existentes: `_run_assistant_sql`, `_run_assistant_resumen`.
- System prompt: `ASSISTANT_SYSTEM_PROMPT` en `backend/main.py:2526`.
- Chips en frontend: `buildToolChip` en `frontend/app.js:974` (labels quemados por `kind`).

---

## Fases

### Fase 0 — Preparación
- [x] Crear rama `feature/asistente-web-tools`.
- [ ] Añadir dependencias a `backend/requirements.txt`: `ddgs`, `holidays`.
  (TheSportsDB no requiere librería: se llama por `urllib`/`requests`.)
- [ ] Nuevas variables de entorno con defaults quemados (patrón actual):
  - `WEB_SEARCH_ENABLED=1`
  - `LLM_MAX_WEB_ITERS=2`
  - `WEB_SEARCH_TIMEOUT=8`
  - `WEB_SEARCH_MAX_RESULTS=5`
  - `SPORTSDB_BASE_URL=https://www.thesportsdb.com/api/v1/json/3`
  - `HOLIDAYS_COUNTRY=CO`

### Fase 1 — Herramienta `festivo` (local, sin red) — primer entregable
Valida el patrón end-to-end sin depender de red.
- [ ] `_run_holiday_check(params)`: params JSON `{"fecha":"YYYY-MM-DD"}` o
  `{"desde":..., "hasta":...}`. Usa `holidays.CO`. Devuelve `{es_festivo, nombre, fecha}`
  (o lista para rango). Sin red, sin timeout.
- [ ] Registrar `festivo` en `_TOOL_FENCE_RE`.
- [ ] Rama `elif kind == "festivo"` en el loop: emite chip run/done y arma la observación.
- [ ] Chip en `buildToolChip` (label "Verificando festivos…"/"Festivos listo", ícono
  `fa-calendar`).
- [ ] Documentar la herramienta en `ASSISTANT_SYSTEM_PROMPT`.
- [ ] Prueba manual: "¿el 20 de julio fue festivo?".

### Fase 2 — Herramienta `buscar` (DuckDuckGo)
- [ ] `_run_web_search(query, max_results)`: usa `ddgs`, timeout `WEB_SEARCH_TIMEOUT`,
  devuelve `[{titulo, cuerpo, url}]`. try/except → mensaje de error legible para reinyección.
- [ ] Observación compacta y **recortada** (evitar desbordar el contexto del modelo local),
  al estilo de `_observation_text_sql`.
- [ ] Presupuesto separado: contador de iteraciones web contra `LLM_MAX_WEB_ITERS` en el loop.
- [ ] Respetar el **toggle**: si `web_enabled` es falso, la herramienta responde
  "acceso web deshabilitado" sin salir a internet.
- [ ] Registrar en regex + rama en el loop + chip (`fa-magnifying-glass`).
- [ ] Documentar en el system prompt (con ejemplo y regla de "solo si se requiere").

### Fase 3 — Herramienta `deporte` (TheSportsDB)
- [ ] `_run_sports_lookup(params)`: params `{"equipo":"Colombia","fecha":"YYYY-MM-DD"}`.
  Flujo: buscar equipo → eventos por fecha/temporada → devolver partidos + marcador.
  Timeout + fallback.
- [ ] Sujeto al toggle web y al presupuesto `LLM_MAX_WEB_ITERS`.
- [ ] Registrar en regex + rama en el loop + chip (`fa-futbol`).
- [ ] Documentar en el system prompt.

### Fase 4 — Toggle web en la UI
- [ ] `AssistantChatRequest`: nuevo campo `web_enabled: Optional[bool] = True`.
- [ ] Frontend: interruptor junto al selector de modelo; guarda en `State.assistant`
  y lo envía en el request a `/api/assistant/chat`.
- [ ] Backend: gobierna solo `buscar` y `deporte`; `festivo` ignora el flag.

### Fase 5 — Estrategia de "explicar picos" en el prompt
Sección nueva en `ASSISTANT_SYSTEM_PROMPT`:
> Si detectas un día/hora con monto atípico (muy alto o bajo), antes de concluir la causa:
> (1) verifica si fue festivo con ` ```festivo `; (2) revisa si hubo partido relevante con
> ` ```deporte ` o ` ```buscar `. Correlaciona, pero no afirmes causalidad como certeza.
> Cita la fuente cuando uses un dato externo y distínguelo de los datos de la BD.

### Fase 6 — Pruebas y cierre
- [ ] Unitarias de `_run_holiday_check` (sin red) y de `_run_web_search`/`_run_sports_lookup`
  con mocks (CI sin dependencia de red).
- [ ] Manual E2E: "¿por qué hubo un pico el 5 de julio?" → valida encadenamiento
  sql/resumen → festivo → deporte/buscar.
- [ ] Verificar comportamiento con toggle web apagado (solo BD + festivos).
- [ ] Revisión de código y merge a `desarrollo`.

---

## Otros usos que habilita (exploración futura)
- Proyecciones más finas al incorporar festivos y calendario deportivo.
- Anomalías con explicación causal automática.
- Alertas proactivas ("hoy juega Colombia 20:00 → esperar pico").
- Enriquecer reportes de WhatsApp con el "por qué" del día.

## Riesgos y mitigaciones
- **Latencia/caída de DDG (scraping):** timeout corto + fallback + toggle para apagar.
- **Desborde de contexto del modelo local:** recorte agresivo de resultados web.
- **Causalidad falsa:** el prompt obliga a correlacionar sin afirmar certeza.
- **Consumo de turnos:** presupuesto web separado del de SQL.

## Orden de desarrollo
Fase 1 (`festivo`) → Fase 2 (`buscar`) → Fase 3 (`deporte`) → Fase 4 (toggle) →
Fase 5 (prompt de picos) → Fase 6 (pruebas).
