// Dashboard State Controller
const State = {
    sales: [],             // Transaccional hourly sales
    goals: [],             // Meta Excel rows
    distribution: [],      // Promoters Excel rows
    sites: [],             // Sites catalogue
    products: [],          // Products catalogue
    expandedOffices: new Set(), // Set of offices expanded in tree grid
    whatsappPromoters: [],     // List of whatsapp authorized promoters
    whatsappCoordinators: [],   // List of whatsapp authorized coordinators
    whatsappAdministrators: [], // List of whatsapp authorized administrators
    
    // Selected Filter Values
    selectedDate: '',
    selectedZone: '',
    selectedOffice: '',
    selectedSeller: '',
    selectedProduct: '',

    // Table-specific filter values
    tableFilters: {
        office: '',
        promoter: '',
        products: []
    },
    
    // Chart instances
    charts: {
        hourly: null,
        product: null,
        ranking: null,
        lagging: null
    },

    // Betplay module state
    betplay: {
        loaded: false,        // whether the tab has auto-loaded at least once
        metric: 'monto',      // 'monto' | 'cantidad'
        mapMode: 'points',    // 'points' | 'heat'
        resumen: null,        // last aggregated response (data object)
        map: null,            // Leaflet map instance
        markerLayer: null,    // Leaflet layer group for points
        heatLayer: null,      // Leaflet heat layer
        charts: {             // Chart.js instances for betplay
            time: null,
            zona: null,
            tipo: null,
            sitios: null,
            usuarios: null
        }
    },

    // Asistente IA state
    assistant: {
        history: [],     // [{role:'user'|'assistant', content:'...'}]
        busy: false,     // si hay una respuesta en curso
        model: null      // id del modelo seleccionado
    }
};

// Power BI Product Normalizer & Categorizer
const ProductNormalizer = {
    // List of special products that are treated as product types
    specialProducts: [
        { key: "BET PLAY", patterns: ["BETPLAY", "BET PLAY", "BTP"] },
        { key: "PATA MILLONARIA", patterns: ["PATA MILLONARIA", "PT"] },
        { key: "DOBLE CHANCE", patterns: ["3C DOBLE CH REGIONAL", "4C DOBLE CH REGIONAL", "DOBLE CHANCE", "DOBLE GANA", "DOBLE CH", "DDCH"] },
        { key: "BILLONARIO NACIONAL", patterns: ["BILLONARIO", "BILLONARIO NACIONAL"] },
        { key: "CHANCE MILLONARIO", patterns: ["CHANCE MILLONARIO", "CHML"] },
        { key: "COLOR LOTO", patterns: ["COLOR LOTO", "CLOT"] },
        { key: "MILOTO", patterns: ["MILOTO", "MLT"] },
        { key: "BALOTO", patterns: ["BALOTO", "BLT", "BLL"] },
        { key: "LOTERIA EN LINEA", patterns: ["LOTERIA EN LINEA", "LOT", "LOTE", "RYL"] },
        { key: "GIROS", patterns: ["GIROS", "GIRO", "ENVIO GIRO"] }
    ],

    // Helper to check if a product name matches a special product category
    getSpecialProductKey: (productName) => {
        if (!productName) return null;
        const name = String(productName).trim().replace(/\*/g, "").toUpperCase();
        for (const spec of ProductNormalizer.specialProducts) {
            for (const pat of spec.patterns) {
                if (name.includes(pat) || name === pat) {
                    return spec.key;
                }
            }
        }
        return null;
    },

    normalize: (rawName) => {
        if (!rawName) return "OTROS";
        let name = String(rawName).trim().replace(/\*/g, "").toUpperCase();
        
        // 1. First, check if it matches a special product
        const specialKey = ProductNormalizer.getSpecialProductKey(name);
        if (specialKey) return specialKey;
        
        // 2. Otherwise normalize as usual
        if (name.startsWith("CHON") || name.startsWith("CHOD") || name.startsWith("BOGO") || name.startsWith("CHO")) {
            return "CHANCE";
        }
        if (name.includes("CHANCE") || name === "CH") return "CHANCE";
        if (name.includes("SUPER ASTRO") || name.includes("ASTRO") || name === "SA") return "SUPER ASTRO";
        if (name.includes("GIROS") || name === "GIROS") return "GIROS";
        if (name.includes("RECARGA") || name === "RC") return "RECARGA EN LINEA";
        if (name.includes("TRANSACCIONES CNB") || name.includes("CNB") || name === "TRCNB") return "TRANSACCIONES CNB";
        if (name.includes("RECAUDOS EMPRESARIALES") || name.includes("RECAUDOS EMPRESAS") || name === "RCDEM") return "RECAUDOS EMPRESARIALES";
        if (name.includes("RASPA") || name.includes("INSTAN") || name === "RYL" || name === "RASPITA") return "RASPITA";
        if (name.includes("LOTERIA") || name === "LOT") return "LOTERIA EN LINEA";
        if (name.includes("SOAT")) return "SOAT REFACIL";
        if (name.includes("DEPOSITO")) return "DEPOSITOS REFACIL";
        if (name.includes("RETIRO")) return "RETIROS REFACIL";
        if (name.includes("PAGOS GENER")) return "PAGOS GENÉRICOS";
        if (name.includes("PAGOS")) return "PAGOS";
        
        return name;
    },
    
    getGroup: (normalizedName) => {
        const name = normalizedName.toUpperCase();
        if ([
            "GIROS", "RECARGA EN LINEA", "RECAUDOS EMPRESARIALES", "TRANSACCIONES CNB", "PAGOS", "PAGOS GENÉRICOS"
        ].includes(name)) {
            return "Productos y Servicios";
        }
        if ([
            "SOAT REFACIL", "DEPOSITOS REFACIL", "RETIROS REFACIL"
        ].includes(name)) {
            return "REFACIL";
        }
        return "JSA"; // Power BI major grouping: BALOTO, BET PLAY, CHANCE, SUPER ASTRO, etc.
    }
};

// API Base URL (Dynamic detection supporting subpaths)
const getApiBase = () => {
    let path = window.location.pathname;
    if (!path.endsWith('/') && !path.split('/').pop().includes('.')) {
        path += '/';
    }
    const lastSlashIdx = path.lastIndexOf('/');
    const prefix = lastSlashIdx > 0 ? path.substring(0, lastSlashIdx) : '';
    return `${window.location.origin}${prefix}`;
};
const API_BASE = getApiBase();

// DOM Elements
const elements = {
    btnRefresh: document.getElementById('btn-refresh'),
    updateTimestamp: document.getElementById('update-timestamp'),
    statusIndicator: document.getElementById('status-indicator'),
    statusText: document.getElementById('status-text'),
    
    // KPI Cards
    kpiSales: document.getElementById('kpi-sales'),
    kpiSalesSub: document.getElementById('kpi-sales-sub'),
    kpiGoal: document.getElementById('kpi-goal'),
    kpiGoalSub: document.getElementById('kpi-goal-sub'),
    kpiCompliance: document.getElementById('kpi-compliance'),
    kpiComplianceBar: document.getElementById('kpi-compliance-bar'),
    kpiSites: document.getElementById('kpi-sites'),
    
    // Uploads
    dropMetas: document.getElementById('drop-metas'),
    fileMetas: document.getElementById('file-metas'),
    badgeMetas: document.getElementById('badge-metas'),
    dropDist: document.getElementById('drop-distribucion'),
    fileDist: document.getElementById('file-distribucion'),
    badgeDist: document.getElementById('badge-distribucion'),
    btnClearData: document.getElementById('btn-clear-data'),
    
    // Filter Selects
    filterDate: document.getElementById('filter-date'),
    filterZone: document.getElementById('filter-zone'),
    filterOffice: document.getElementById('filter-office'),
    filterSeller: document.getElementById('filter-seller'),
    filterProduct: document.getElementById('filter-product'),
    
    // Table Specific Filters
    tableFilterOffice: document.getElementById('table-filter-office'),
    tableFilterPromoter: document.getElementById('table-filter-promoter'),
    tableFilterProductsContainer: document.getElementById('table-filter-products-container'),
    productsMultiselectBtn: document.getElementById('products-multiselect-btn'),
    productsMultiselectDropdown: document.getElementById('products-multiselect-dropdown'),
    multiselectSelectAll: document.getElementById('multiselect-select-all'),
    multiselectClear: document.getElementById('multiselect-clear'),
    productsMultiselectOptions: document.getElementById('products-multiselect-options'),
    
    // Table
    tableSearch: document.getElementById('table-search-input'),
    tableBody: document.getElementById('table-body'),
    tableThead: document.getElementById('table-thead'),
    tableResultsCount: document.getElementById('table-results-count'),

    // Tree actions
    btnExpandAll: document.getElementById('btn-expand-all'),
    btnCollapseAll: document.getElementById('btn-collapse-all'),

    // Promoter Consolidated summary panel
    promoterPanel: document.getElementById('promoter-consolidated-panel'),
    promoterPanelName: document.getElementById('promoter-panel-name'),
    promoterPanelSales: document.getElementById('promoter-panel-sales'),
    promoterPanelGoal: document.getElementById('promoter-panel-goal'),
    promoterPanelOverall: document.getElementById('promoter-panel-overall'),
    promoterOfficesGrid: document.getElementById('promoter-offices-grid'),
    promoterProductsSection: document.getElementById('promoter-products-section'),
    promoterProductsGrid: document.getElementById('promoter-products-grid'),

    // WhatsApp Promoters Management
    btnManagePromoters: document.getElementById('btn-manage-promoters'),
    modalPromoters: document.getElementById('modal-promoters'),
    btnClosePromotersModal: document.getElementById('btn-close-promoters-modal'),
    formPromoter: document.getElementById('form-promoter'),
    promoterEditId: document.getElementById('promoter-edit-id'),
    promoterFormTitle: document.getElementById('promoter-form-title'),
    promoterName: document.getElementById('promoter-name'),
    promoterPhone: document.getElementById('promoter-phone'),
    promoterZone: document.getElementById('promoter-zone'),
    btnSavePromoter: document.getElementById('btn-save-promoter'),
    btnCancelEdit: document.getElementById('btn-cancel-edit'),
    searchPromoters: document.getElementById('search-promoters'),
    promotersListBody: document.getElementById('promoters-list-body'),

    // WhatsApp Coordinators Management
    btnManageCoordinators: document.getElementById('btn-manage-coordinators'),
    modalCoordinators: document.getElementById('modal-coordinators'),
    btnCloseCoordinatorsModal: document.getElementById('btn-close-coordinators-modal'),
    formCoordinator: document.getElementById('form-coordinator'),
    coordinatorEditId: document.getElementById('coordinator-edit-id'),
    coordinatorFormTitle: document.getElementById('coordinator-form-title'),
    coordinatorName: document.getElementById('coordinator-name'),
    coordinatorCedula: document.getElementById('coordinator-cedula'),
    coordinatorRole: document.getElementById('coordinator-role'),
    coordinatorPhone: document.getElementById('coordinator-phone'),
    coordinatorZone: document.getElementById('coordinator-zone'),
    btnSaveCoordinator: document.getElementById('btn-save-coordinator'),
    btnCancelCoordinatorEdit: document.getElementById('btn-cancel-coordinator-edit'),
    searchCoordinators: document.getElementById('search-coordinators'),
    coordinatorsListBody: document.getElementById('coordinators-list-body'),

    // WhatsApp Administrators Management
    btnManageAdministrators: document.getElementById('btn-manage-administrators'),
    modalAdministrators: document.getElementById('modal-administrators'),
    btnCloseAdministratorsModal: document.getElementById('btn-close-administrators-modal'),
    formAdministrator: document.getElementById('form-administrator'),
    administratorEditId: document.getElementById('administrator-edit-id'),
    administratorFormTitle: document.getElementById('administrator-form-title'),
    administratorName: document.getElementById('administrator-name'),
    administratorCedula: document.getElementById('administrator-cedula'),
    administratorPhone: document.getElementById('administrator-phone'),
    btnSaveAdministrator: document.getElementById('btn-save-administrator'),
    btnCancelAdministratorEdit: document.getElementById('btn-cancel-administrator-edit'),
    searchAdministrators: document.getElementById('search-administrators'),
    administratorsListBody: document.getElementById('administrators-list-body'),

    // Goals Management Modal
    modalGoals: document.getElementById('modal-goals'),
    btnCloseGoalsModal: document.getElementById('btn-close-goals-modal'),
    goalsListBody: document.getElementById('goals-list-body')
};

// --- INITIALIZATION ---
document.addEventListener('DOMContentLoaded', async () => {
    setupTabs();
    setupBetplayControls();
    setupAssistantChat();
    setupUploadHandlers();
    setupFilterListeners();
    setupRefreshHandlers();
    setupTreeControls();
    setupPromoterManagement();
    setupCoordinatorManagement();
    setupAdministratorManagement();
    setupGoalsManagement();
    
    // Load initial data
    await checkStatus();
    await loadInitialCatalogues();
    await loadUploadedState();
});

// --- TAB NAVIGATION ---
function setupTabs() {
    const tabBar = document.getElementById('tab-bar');
    const tabButtons = document.querySelectorAll('.tab-bar .tab-btn');
    const views = document.querySelectorAll('.tab-view');
    const indicator = document.getElementById('tab-indicator');
    if (!tabButtons.length) return;

    // Desliza el indicador de vidrio bajo el tab activo.
    function moveIndicator(btn) {
        if (!indicator || !btn) return;
        // offsetLeft/Width relativos al .tab-bar (contenedor posicionado).
        indicator.style.width = `${btn.offsetWidth}px`;
        indicator.style.transform = `translateX(${btn.offsetLeft - tabBar.clientLeft}px)`;
    }

    // Posición inicial (esperar layout para medir).
    const initialActive = document.querySelector('.tab-bar .tab-btn.active') || tabButtons[0];
    requestAnimationFrame(() => moveIndicator(initialActive));
    // Reposicionar si cambia el tamaño (iframe/responsive).
    window.addEventListener('resize', () => {
        moveIndicator(document.querySelector('.tab-bar .tab-btn.active'));
    });

    tabButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetId = btn.dataset.view;
            // Toggle active button
            tabButtons.forEach(b => b.classList.toggle('active', b === btn));
            moveIndicator(btn);
            // Toggle visible view
            views.forEach(v => { v.hidden = (v.id !== targetId); });

            // El toolbar del asistente (selector + estado) solo se ve en su vista.
            const asistToolbar = document.getElementById('asistente-conn');
            if (asistToolbar) asistToolbar.hidden = (targetId !== 'view-asistente');

            // Al abrir Betplay por primera vez, consultar automáticamente el día actual.
            if (targetId === 'view-betplay' && !State.betplay.loaded) {
                fetchBetplay();
            }
            // Leaflet necesita recalcular tamaño cuando su contenedor pasa de oculto a visible.
            if (targetId === 'view-betplay' && State.betplay.map) {
                setTimeout(() => State.betplay.map.invalidateSize(), 200);
            }

            // Al abrir el Asistente: verificar conexión, modelos y KPIs del día.
            if (targetId === 'view-asistente') {
                checkAssistantHealth();
                loadAssistantModels();
                loadAssistantKpis();
            }
        });
    });
}

// --- ASISTENTE IA: VERIFICACIÓN DE CONEXIÓN ---
async function checkAssistantHealth() {
    const indicator = document.getElementById('asistente-conn-indicator');
    const text = document.getElementById('asistente-conn-text');
    if (!indicator || !text) return;

    indicator.className = 'status-indicator';
    text.textContent = 'Verificando conexión con el modelo...';

    try {
        const res = await fetch(`${API_BASE}/api/assistant/health?t=${new Date().getTime()}`);
        const json = await res.json();
        if (json.online) {
            indicator.classList.add('online');
            // Mostrar el modelo realmente CARGADO (no el configurado por defecto).
            let modelName = json.configured_model || 'local';
            try {
                const mres = await fetch(`${API_BASE}/api/assistant/models?t=${Date.now()}`);
                const mjson = await mres.json();
                const loaded = (mjson.models || []).find(m => m.loaded);
                if (loaded) modelName = loaded.id || loaded.label;
            } catch (_) { /* si falla, se queda el configurado */ }
            text.textContent = `Modelo conectado (${modelName})`;
        } else {
            indicator.classList.add('offline');
            text.textContent = 'Sin conexión con el modelo (Mac inaccesible)';
        }
    } catch (err) {
        indicator.classList.add('offline');
        text.textContent = 'Error verificando la conexión con el modelo';
    }
}

// --- ASISTENTE IA: SELECTOR DE MODELO (NIVEL DE INTELIGENCIA) ---
let _assistantModelsLoaded = false;
async function loadAssistantModels() {
    const select = document.getElementById('asistente-model-select');
    if (!select) return;
    try {
        const res = await fetch(`${API_BASE}/api/assistant/models?t=${new Date().getTime()}`);
        const json = await res.json();
        const models = json.models || [];
        // Modelo activo: el que esté cargado, o el guardado, o el default.
        const loaded = models.find(m => m.loaded);
        const current = State.assistant.model
            || (loaded && loaded.id)
            || json.default
            || (models[0] && models[0].id);
        State.assistant.model = current;

        select.innerHTML = models
            .map(m => `<option value="${m.id}"${m.id === current ? ' selected' : ''}>${m.label}</option>`)
            .join('');

        if (!_assistantModelsLoaded) {
            select.addEventListener('change', () => selectAssistantModel(select.value));
            _assistantModelsLoaded = true;
        }
    } catch (err) {
        console.error('[Asistente] Error cargando modelos:', err);
        select.innerHTML = '<option>Modelos no disponibles</option>';
    }
}

// Cambia el modelo activo: pide a LM Studio descargar el actual y cargar el nuevo.
async function selectAssistantModel(modelId) {
    const select = document.getElementById('asistente-model-select');
    const status = document.getElementById('asistente-model-status');
    if (State.assistant.busy) return;

    const previous = State.assistant.model;
    State.assistant.model = modelId;
    if (select) select.disabled = true;
    if (status) {
        status.hidden = false;
        status.className = 'asistente-model-status loading';
        status.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Cargando modelo…';
    }
    try {
        const res = await fetch(`${API_BASE}/api/assistant/model/select`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ model: modelId })
        });
        const json = await res.json();
        if (!json.ok) throw new Error(json.error || 'Error desconocido');
        if (status) {
            status.className = 'asistente-model-status ok';
            const secs = json.load_time_seconds != null ? ` (${json.load_time_seconds.toFixed(1)} s)` : '';
            status.innerHTML = json.already_loaded
                ? '<i class="fa-solid fa-check"></i> Modelo activo'
                : `<i class="fa-solid fa-check"></i> Modelo cargado${secs}`;
            setTimeout(() => { if (status) status.hidden = true; }, 3000);
        }
        checkAssistantHealth();
    } catch (err) {
        console.error('[Asistente] Error cambiando de modelo:', err);
        State.assistant.model = previous;
        if (select) select.value = previous;
        if (status) {
            status.className = 'asistente-model-status error';
            status.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i> No se pudo cambiar';
        }
    } finally {
        if (select) select.disabled = false;
    }
}

// --- ASISTENTE IA: KPIs PAGOS + RECARGAS (DÍA ACTUAL) ---
async function loadAssistantKpis() {
    const todayStr = new Date().toISOString().split('T')[0];
    const addDay = (s) => { const d = new Date(`${s}T00:00:00`); d.setDate(d.getDate() + 1); return d.toISOString().split('T')[0]; };
    const desde = `${todayStr} 00:00:00`;
    const hasta = `${addDay(todayStr)} 00:00:00`;

    const dateEl = document.getElementById('asistente-kpis-date');
    if (dateEl) dateEl.textContent = todayStr;

    const fill = (tipo, totales) => {
        document.getElementById(`ak-${tipo}-monto`).textContent = formatCurrency(totales.monto || 0);
        document.getElementById(`ak-${tipo}-cantidad`).textContent = (totales.cantidad || 0).toLocaleString('es-CO');
        document.getElementById(`ak-${tipo}-usuarios`).textContent = (totales.usuarios_unicos || 0).toLocaleString('es-CO');
        document.getElementById(`ak-${tipo}-sitios`).textContent = (totales.sitios_unicos || 0).toLocaleString('es-CO');
    };

    const fetchTipo = async (tipo) => {
        try {
            const url = `${API_BASE}/api/betplay/resumen?tipo=${tipo}&desde=${encodeURIComponent(desde)}`
                + `&hasta=${encodeURIComponent(hasta)}&force_refresh=true&t=${new Date().getTime()}`;
            const res = await fetch(url);
            const json = await res.json();
            fill(tipo, (json.data && json.data.totales) ? json.data.totales : {});
        } catch (err) {
            console.error(`[Asistente] Error cargando KPIs de ${tipo}:`, err);
        }
    };

    await Promise.all([fetchTipo('pagos'), fetchTipo('recargas')]);
}

// --- ASISTENTE IA: CHAT CON STREAMING ---
function setupAssistantChat() {
    const input = document.getElementById('asistente-input');
    const sendBtn = document.getElementById('asistente-send');
    if (!input || !sendBtn) return;

    sendBtn.addEventListener('click', () => sendAssistantMessage());
    // Enter envía; Shift+Enter hace salto de línea.
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendAssistantMessage();
        }
    });
}

// Construye el rango "día actual" para el contexto del asistente.
function assistantTodayRange() {
    const todayStr = new Date().toISOString().split('T')[0];
    const d = new Date(`${todayStr}T00:00:00`);
    d.setDate(d.getDate() + 1);
    const tomorrow = d.toISOString().split('T')[0];
    return { desde: `${todayStr} 00:00:00`, hasta: `${tomorrow} 00:00:00` };
}

// Agrega una burbuja de chat de usuario (texto plano).
function appendChatBubble(role, text) {
    const container = document.getElementById('asistente-messages');
    const msg = document.createElement('div');
    msg.className = `chat-msg ${role}`;
    const icon = role === 'user' ? 'fa-user' : 'fa-robot';
    msg.innerHTML = `
        <div class="chat-avatar"><i class="fa-solid ${icon}"></i></div>
        <div class="chat-bubble"></div>
    `;
    const bubble = msg.querySelector('.chat-bubble');
    bubble.textContent = text;
    container.appendChild(msg);
    container.scrollTop = container.scrollHeight;
    return bubble;
}

// Crea un mensaje del asistente con avatar + columna de contenido (texto + islas).
// Devuelve la columna de contenido, que se re-renderiza con renderAssistantMessage().
function appendAssistantMessage() {
    const container = document.getElementById('asistente-messages');
    const msg = document.createElement('div');
    msg.className = 'chat-msg assistant';
    msg.innerHTML = `
        <div class="chat-avatar"><i class="fa-solid fa-robot"></i></div>
        <div class="chat-col">
            <div class="chat-content"></div>
            <div class="chat-timer" hidden><i class="fa-regular fa-clock"></i> <span class="chat-timer-val"></span></div>
        </div>
    `;
    container.appendChild(msg);
    container.scrollTop = container.scrollHeight;
    return {
        content: msg.querySelector('.chat-content'),
        timer: msg.querySelector('.chat-timer'),
        timerVal: msg.querySelector('.chat-timer-val'),
    };
}

// Cronómetro de respuesta: muestra el tiempo transcurrido en vivo y lo congela
// al terminar. Devuelve una función stop(label) para fijar el valor final.
function startResponseTimer(timerEl, valEl) {
    const t0 = performance.now();
    timerEl.hidden = false;
    timerEl.classList.add('running');
    const fmt = (ms) => `${(ms / 1000).toFixed(1)} s`;
    valEl.textContent = fmt(0);
    const id = setInterval(() => { valEl.textContent = fmt(performance.now() - t0); }, 100);
    return (prefix) => {
        clearInterval(id);
        timerEl.classList.remove('running');
        valEl.textContent = `${prefix || 'Respondió en'} ${fmt(performance.now() - t0)}`;
    };
}

// --- MARKDOWN MÍNIMO (seguro) ---
function escapeHtml(s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
function mdInline(s) {
    return escapeHtml(s)
        .replace(/`([^`]+)`/g, '<code>$1</code>')
        .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
        .replace(/(^|[^*])\*([^*\n]+)\*/g, '$1<em>$2</em>')
        .replace(/(^|[^_])_([^_\n]+)_/g, '$1<em>$2</em>');
}
function mdToHtml(text) {
    const lines = String(text).split('\n');
    const isSep = (l) => /^\s*\|?[\s:|-]*-[-\s:|]*\|?\s*$/.test(l) && l.includes('-');
    const parseRow = (l) => l.replace(/^\s*\|/, '').replace(/\|\s*$/, '').split('|').map(c => c.trim());

    let html = '';
    let inList = false;
    let i = 0;
    const closeList = () => { if (inList) { html += '</ul>'; inList = false; } };

    while (i < lines.length) {
        const line = lines[i].replace(/\s+$/, '');

        // ¿Tabla markdown? (admite líneas en blanco intercaladas entre filas)
        if (line.includes('|')) {
            const tableLines = [];
            let j = i;
            while (j < lines.length) {
                const l = lines[j];
                if (l.trim() === '') {
                    let k = j + 1;
                    while (k < lines.length && lines[k].trim() === '') k++;
                    if (k < lines.length && lines[k].includes('|')) { j = k; continue; }
                    break;
                }
                if (l.includes('|')) { tableLines.push(l); j++; } else break;
            }
            const sepIdx = tableLines.findIndex(isSep);
            if (tableLines.length >= 2 && sepIdx >= 0) {
                closeList();
                const header = parseRow(tableLines[Math.max(0, sepIdx - 1)]);
                const rows = tableLines.slice(sepIdx + 1).map(parseRow);
                html += `<table class="data-table"><thead><tr>${header.map(h => `<th>${mdInline(h)}</th>`).join('')}</tr></thead><tbody>`
                    + rows.map(r => `<tr>${r.map(c => `<td>${mdInline(c)}</td>`).join('')}</tr>`).join('')
                    + `</tbody></table>`;
                i = j;
                continue;
            }
        }

        const li = line.match(/^\s*[-*]\s+(.*)$/);
        if (li) {
            if (!inList) { html += '<ul>'; inList = true; }
            html += `<li>${mdInline(li[1])}</li>`;
            i++;
            continue;
        }
        closeList();
        if (line.trim() !== '') html += `<p>${mdInline(line)}</p>`;
        i++;
    }
    closeList();
    return html;
}

// --- PARSER DE SEGMENTOS (texto + bloques cercados ```chart / ```table) ---
function parseAssistantSegments(raw) {
    const segs = [];
    const re = /```([a-zA-Z]*)[ \t]*\n?([\s\S]*?)```/g;
    let lastIndex = 0;
    let m;
    while ((m = re.exec(raw)) !== null) {
        if (m.index > lastIndex) segs.push({ type: 'text', content: raw.slice(lastIndex, m.index) });
        const lang = (m[1] || '').toLowerCase();
        const kind = (lang === 'chart' || lang === 'table') ? lang : 'code';
        segs.push({ type: kind, content: m[2], lang });
        lastIndex = re.lastIndex;
    }
    const tail = raw.slice(lastIndex);
    const openIdx = tail.indexOf('```');
    if (openIdx !== -1) {
        const before = tail.slice(0, openIdx);
        if (before.trim()) segs.push({ type: 'text', content: before });
        const after = tail.slice(openIdx + 3);
        const lm = after.match(/^([a-zA-Z]*)/);
        segs.push({ type: 'pending', lang: (lm ? lm[1] : '').toLowerCase() });
    } else if (tail.trim()) {
        segs.push({ type: 'text', content: tail });
    }
    return segs;
}

// Separa el razonamiento (entre <|channel>thought y <channel|>) de la respuesta.
// Devuelve { reasoning, answer, thinking } donde thinking=true si el bloque de
// razonamiento aún no se ha cerrado (sigue llegando por el stream).
const REASON_START = '<|channel>thought';
const REASON_END = '<channel|>';
function splitReasoning(raw) {
    const start = raw.indexOf(REASON_START);
    if (start === -1) return { reasoning: '', answer: raw, thinking: false };
    const afterStart = start + REASON_START.length;
    const end = raw.indexOf(REASON_END, afterStart);
    const before = raw.slice(0, start);
    if (end === -1) {
        // Razonamiento en curso: todo lo posterior al tag es pensamiento.
        return { reasoning: raw.slice(afterStart), answer: before, thinking: true };
    }
    const reasoning = raw.slice(afterStart, end);
    const answer = before + raw.slice(end + REASON_END.length);
    return { reasoning: reasoning.trim(), answer, thinking: false };
}

// Re-renderiza el contenido del asistente. Durante el stream (isFinal=false) los
// bloques de visualización se muestran como placeholder; al finalizar se renderizan.
function renderAssistantMessage(contentEl, raw, isFinal) {
    const container = document.getElementById('asistente-messages');
    // ¿El usuario está pegado al fondo? Solo entonces auto-desplazamos.
    const stick = container
        ? (container.scrollHeight - container.scrollTop - container.clientHeight) < 80
        : true;

    const { reasoning, answer, thinking } = splitReasoning(raw);
    contentEl.innerHTML = '';

    // Panel de razonamiento (plegable). Se mantiene abierto mientras "piensa".
    if (reasoning.trim() || thinking) {
        const det = document.createElement('details');
        det.className = 'chat-reasoning' + (thinking ? ' thinking' : '');
        if (thinking) det.open = true;
        const label = thinking ? 'Razonando…' : 'Razonamiento';
        const icon = thinking ? 'fa-spinner fa-spin' : 'fa-brain';
        det.innerHTML = `
            <summary><i class="fa-solid fa-chevron-right chevron"></i><i class="fa-solid ${icon}"></i> ${label}</summary>
            <div class="chat-reasoning-body"></div>
        `;
        det.querySelector('.chat-reasoning-body').textContent = reasoning.trim();
        contentEl.appendChild(det);
    }

    const segments = parseAssistantSegments(answer);

    for (const seg of segments) {
        if (seg.type === 'text' || seg.type === 'code') {
            if (!seg.content.trim()) continue;
            const bubble = document.createElement('div');
            bubble.className = 'chat-bubble';
            bubble.innerHTML = mdToHtml(seg.content);
            contentEl.appendChild(bubble);
        } else if (seg.type === 'pending') {
            contentEl.appendChild(buildIslandPlaceholder(seg.lang));
        } else if (seg.type === 'chart' || seg.type === 'table') {
            if (!isFinal) {
                contentEl.appendChild(buildIslandPlaceholder(seg.type));
                continue;
            }
            const island = (seg.type === 'chart')
                ? buildChartIsland(seg.content)
                : buildTableIsland(seg.content);
            contentEl.appendChild(island);
        }
    }

    if (container && stick) container.scrollTop = container.scrollHeight;
}

function buildIslandPlaceholder(kind) {
    const el = document.createElement('div');
    el.className = 'chat-island';
    const label = kind === 'table' ? 'tabla' : 'gráfico';
    el.innerHTML = `
        <div class="chat-island-header"><i class="fa-solid fa-spinner fa-spin"></i> Generando ${label}…</div>
        <div class="chat-island-placeholder"><i class="fa-solid fa-chart-pie"></i><span>Preparando visualización…</span></div>
    `;
    return el;
}

let _islandChartCounter = 0;
function buildChartIsland(jsonStr) {
    const el = document.createElement('div');
    el.className = 'chat-island';
    let spec;
    try {
        spec = JSON.parse(jsonStr);
    } catch (e) {
        el.innerHTML = `<div class="chat-island-header"><i class="fa-solid fa-triangle-exclamation"></i> Gráfico no válido</div>
            <div class="chat-island-placeholder"><span>El modelo devolvió un gráfico con formato incorrecto.</span></div>`;
        return el;
    }

    const typeMap = { bar: 'bar', horizontalbar: 'bar', line: 'line', doughnut: 'doughnut', pie: 'pie' };
    const rawType = String(spec.chart_type || 'bar').toLowerCase();
    const chartType = typeMap[rawType] || 'bar';
    const horizontal = rawType === 'horizontalbar';
    const isPieLike = chartType === 'doughnut' || chartType === 'pie';

    const labels = spec.x || [];
    const series = spec.series || [];
    const datasets = series.map((s, i) => {
        const color = BETPLAY_PALETTE[i % BETPLAY_PALETTE.length];
        return {
            label: s.label || `Serie ${i + 1}`,
            data: s.data || [],
            backgroundColor: isPieLike ? BETPLAY_PALETTE : (chartType === 'line' ? 'rgba(18,87,209,0.2)' : color + '99'),
            borderColor: isPieLike ? '#ffffff' : color,
            borderWidth: isPieLike ? 2 : 1.5,
            borderRadius: chartType === 'bar' ? 4 : 0,
            fill: chartType === 'line'
        };
    });

    const canvasId = `island-chart-${++_islandChartCounter}`;
    el.innerHTML = `
        <div class="chat-island-header"><i class="fa-solid fa-chart-column"></i> ${escapeHtml(spec.title || 'Gráfico')}</div>
        <div class="chat-island-body"><canvas id="${canvasId}"></canvas></div>
    `;

    // Instanciar Chart.js tras insertar el canvas en el DOM
    setTimeout(() => {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;
        new Chart(canvas.getContext('2d'), {
            type: chartType,
            data: { labels, datasets },
            options: {
                indexAxis: horizontal ? 'y' : 'x',
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: isPieLike || datasets.length > 1, labels: { color: '#52627a', font: { size: 11 } } }
                },
                scales: isPieLike ? {} : {
                    x: { ticks: { color: '#52627a', font: { size: 10 } }, grid: { color: 'rgba(15,37,64,0.08)' } },
                    y: { ticks: { color: '#52627a', font: { size: 10 } }, grid: { color: 'rgba(15,37,64,0.08)' } }
                }
            }
        });
    }, 30);

    return el;
}

function buildTableIsland(jsonStr) {
    const el = document.createElement('div');
    el.className = 'chat-island';
    let spec;
    try {
        spec = JSON.parse(jsonStr);
    } catch (e) {
        el.innerHTML = `<div class="chat-island-header"><i class="fa-solid fa-triangle-exclamation"></i> Tabla no válida</div>
            <div class="chat-island-placeholder"><span>El modelo devolvió una tabla con formato incorrecto.</span></div>`;
        return el;
    }
    const columns = spec.columns || [];
    const rows = spec.rows || [];
    const thead = `<tr>${columns.map(c => `<th>${escapeHtml(c)}</th>`).join('')}</tr>`;
    const tbody = rows.map(r => `<tr>${r.map(c => `<td>${escapeHtml(c)}</td>`).join('')}</tr>`).join('');
    el.innerHTML = `
        <div class="chat-island-header"><i class="fa-solid fa-table-list"></i> ${escapeHtml(spec.title || 'Tabla')}</div>
        <div class="chat-island-body table-responsive">
            <table class="data-table"><thead>${thead}</thead><tbody>${tbody}</tbody></table>
        </div>
    `;
    return el;
}

async function sendAssistantMessage() {
    const input = document.getElementById('asistente-input');
    const sendBtn = document.getElementById('asistente-send');
    const container = document.getElementById('asistente-messages');
    if (!input || State.assistant.busy) return;

    const pregunta = input.value.trim();
    if (!pregunta) return;

    // Pinta la pregunta del usuario
    appendChatBubble('user', pregunta);
    State.assistant.history.push({ role: 'user', content: pregunta });
    input.value = '';

    // Contenedor del mensaje del asistente (se re-renderiza con el stream)
    const { content: contentEl, timer: timerEl, timerVal } = appendAssistantMessage();
    contentEl.innerHTML = '<div class="chat-bubble"><em>Pensando…</em></div>';
    const stopTimer = startResponseTimer(timerEl, timerVal);

    State.assistant.busy = true;
    input.disabled = true;
    sendBtn.disabled = true;

    const range = assistantTodayRange();
    let acumulado = '';

    try {
        const res = await fetch(`${API_BASE}/api/assistant/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                pregunta,
                historial: State.assistant.history.slice(-8),
                desde: range.desde,
                hasta: range.hasta,
                model: State.assistant.model
            })
        });
        if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`);

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            acumulado += decoder.decode(value, { stream: true });
            renderAssistantMessage(contentEl, acumulado, false);
        }
        // Render final (instancia gráficos/tablas)
        if (!acumulado.trim()) {
            contentEl.innerHTML = '<div class="chat-bubble">(sin respuesta del modelo)</div>';
        } else {
            renderAssistantMessage(contentEl, acumulado, true);
        }
        // Guardamos solo la respuesta (sin el razonamiento) para no reenviarlo.
        State.assistant.history.push({ role: 'assistant', content: splitReasoning(acumulado).answer.trim() });
        stopTimer('Respondió en');
    } catch (err) {
        console.error('[Asistente] Error en el chat:', err);
        contentEl.innerHTML = '<div class="chat-bubble">No se pudo obtener respuesta del modelo. Verifica la conexión con la Mac.</div>';
        stopTimer('Falló tras');
    } finally {
        State.assistant.busy = false;
        input.disabled = false;
        sendBtn.disabled = false;
        input.focus();
    }
}

// --- BETPLAY: TIPO Y RANGO DE FECHAS ---
function setupBetplayControls() {
    const modeSelect = document.getElementById('betplay-date-mode');
    if (!modeSelect) return;

    const singleField = document.getElementById('betplay-single-field');
    const fromField = document.getElementById('betplay-range-from-field');
    const toField = document.getElementById('betplay-range-to-field');
    const singleInput = document.getElementById('betplay-date-single');
    const fromInput = document.getElementById('betplay-date-from');
    const toInput = document.getElementById('betplay-date-to');
    const applyBtn = document.getElementById('btn-betplay-apply');

    // Default all date inputs to today
    const todayStr = new Date().toISOString().split('T')[0];
    [singleInput, fromInput, toInput].forEach(i => { if (i && !i.value) i.value = todayStr; });

    // Show/hide date fields according to selected mode
    const refreshFields = () => {
        const mode = modeSelect.value;
        singleField.hidden = (mode !== 'single');
        fromField.hidden = (mode !== 'range');
        toField.hidden = (mode !== 'range');
    };
    modeSelect.addEventListener('change', refreshFields);
    refreshFields();

    // Botón "Consultar" (necesario para fecha puntual / rango).
    if (applyBtn) {
        applyBtn.addEventListener('click', () => fetchBetplay());
    }

    // Cambiar el tipo (Pagos/Recargas) vuelve a consultar.
    const typeSelect = document.getElementById('betplay-type');
    if (typeSelect) {
        typeSelect.addEventListener('change', () => fetchBetplay());
    }

    // Toggle de métrica Monto / Cantidad (no requiere volver a consultar).
    const metricToggle = document.getElementById('betplay-metric-toggle');
    if (metricToggle) {
        metricToggle.querySelectorAll('.metric-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                State.betplay.metric = btn.dataset.metric;
                metricToggle.querySelectorAll('.metric-btn').forEach(b => b.classList.toggle('active', b === btn));
                if (State.betplay.resumen) renderBetplay(getBetplayRenderData());
            });
        });
    }

    // Toggle de mapa Puntos / Calor.
    const mapToggle = document.getElementById('betplay-map-toggle');
    if (mapToggle) {
        mapToggle.querySelectorAll('.metric-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                State.betplay.mapMode = btn.dataset.map;
                mapToggle.querySelectorAll('.metric-btn').forEach(b => b.classList.toggle('active', b === btn));
                if (State.betplay.resumen) renderBetplayMap(getBetplayRenderData().por_sitio || []);
            });
        });
    }

    // Filtros generales del dashboard (se aplican en el navegador).
    const muniSel = document.getElementById('bp-filter-municipio');
    if (muniSel) muniSel.addEventListener('change', () => {
        refreshZonaOptionsForMunicipio();  // zonas dependientes del municipio
        applyBetplayFilters();
    });
    ['bp-filter-tipo', 'bp-filter-zona'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('change', applyBetplayFilters);
    });
    ['bp-filter-sitio', 'bp-filter-cliente'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('input', applyBetplayFilters);
    });
    const clearBtn = document.getElementById('bp-filter-clear');
    if (clearBtn) clearBtn.addEventListener('click', () => {
        ['bp-filter-municipio', 'bp-filter-tipo', 'bp-filter-zona', 'bp-filter-sitio', 'bp-filter-cliente']
            .forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; });
        refreshZonaOptionsForMunicipio();  // restaura todas las zonas
        applyBetplayFilters();
    });

    // Restablecer el orden original de la tabla de sitios.
    const sortResetBtn = document.getElementById('bp-table-sort-reset');
    if (sortResetBtn) sortResetBtn.addEventListener('click', () => {
        State.betplay.tableSort = { key: null, dir: 1, type: 'text' };
        updateBetplaySortIcons();
        if (State.betplay._tableDraw) State.betplay._tableDraw();
    });

    // Exportar tabla "Detalle por Sitio de Venta" a Excel.
    const exportBtn = document.getElementById('bp-table-export');
    if (exportBtn) exportBtn.addEventListener('click', exportBetplayTable);

    // Exportar visuales a PDF (modal de selección).
    const pdfBtn = document.getElementById('bp-export-pdf');
    if (pdfBtn) pdfBtn.addEventListener('click', openBetplayPdfModal);
    const pdfClose = document.getElementById('bp-pdf-close');
    const pdfCancel = document.getElementById('bp-pdf-cancel');
    [pdfClose, pdfCancel].forEach(b => { if (b) b.addEventListener('click', () => {
        const m = document.getElementById('bp-pdf-modal'); if (m) m.style.display = 'none';
    }); });
    const pdfAll = document.getElementById('bp-pdf-all');
    if (pdfAll) pdfAll.addEventListener('change', () => {
        document.querySelectorAll('#bp-pdf-list input[type="checkbox"]').forEach(c => c.checked = pdfAll.checked);
    });
    const pdfGen = document.getElementById('bp-pdf-generate');
    if (pdfGen) pdfGen.addEventListener('click', generateBetplayPDF);

    // Maximizar / restaurar el mapa a pantalla completa.
    const maxBtn = document.getElementById('bp-map-maximize');
    const closeBtn = document.getElementById('bp-map-close');
    if (maxBtn) maxBtn.addEventListener('click', () => toggleBetplayMapFullscreen());
    if (closeBtn) closeBtn.addEventListener('click', () => toggleBetplayMapFullscreen(false));
    // ESC también cierra.
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            const w = document.getElementById('bp-map-wrapper');
            if (w && w.classList.contains('bp-map-fullscreen')) toggleBetplayMapFullscreen(false);
        }
    });
}

// Alterna el mapa a pantalla completa. El panel del mapa es .glass-panel
// (backdrop-filter) → rompe position:fixed, por eso movemos el mapa al <body>
// (portal) al maximizar y lo devolvemos a su lugar al restaurar.
// force: true = maximizar, false = restaurar, undefined = alternar.
function toggleBetplayMapFullscreen(force) {
    const wrapper = document.getElementById('bp-map-wrapper');
    const maxBtn = document.getElementById('bp-map-maximize');
    if (!wrapper) return;
    const isFull = wrapper.classList.contains('bp-map-fullscreen');
    const goFull = force === undefined ? !isFull : force;
    if (goFull === isFull) return;

    if (goFull) {
        State.betplay._mapPlaceholder = document.createComment('bp-map-portal');
        wrapper.parentNode.insertBefore(State.betplay._mapPlaceholder, wrapper);
        document.body.appendChild(wrapper);
        wrapper.classList.add('bp-map-fullscreen');
        if (maxBtn) maxBtn.innerHTML = '<i class="fa-solid fa-compress"></i> Restaurar';
    } else {
        wrapper.classList.add('bp-map-closing');
        wrapper.classList.remove('bp-map-fullscreen');
        const ph = State.betplay._mapPlaceholder;
        const finish = () => {
            wrapper.classList.remove('bp-map-closing');
            if (ph && ph.parentNode) {
                ph.parentNode.insertBefore(wrapper, ph);
                ph.parentNode.removeChild(ph);
            }
            State.betplay._mapPlaceholder = null;
            if (State.betplay.map) State.betplay.map.invalidateSize();
        };
        setTimeout(finish, 380);
        if (maxBtn) maxBtn.innerHTML = '<i class="fa-solid fa-expand"></i> Maximizar';
    }
    if (State.betplay.map) setTimeout(() => State.betplay.map.invalidateSize(), 420);
}

// --- BETPLAY: CONSULTA A LA API ---
async function fetchBetplay() {
    const range = getBetplayDateRange();
    updateBetplaySelectionSummary(range);

    const loadingEl = document.getElementById('betplay-loading');
    const emptyEl = document.getElementById('betplay-empty');
    const contentEl = document.getElementById('betplay-content');

    loadingEl.hidden = false;
    emptyEl.hidden = true;
    contentEl.hidden = true;

    try {
        // El día actual cambia durante el día → siempre consultar fresco.
        // Las fechas pasadas son inmutables → usar caché.
        const forceRefresh = range.mode === 'today';
        const url = `${API_BASE}/api/betplay/resumen?tipo=${encodeURIComponent(range.type)}`
            + `&desde=${encodeURIComponent(range.desde)}&hasta=${encodeURIComponent(range.hasta)}`
            + (forceRefresh ? '&force_refresh=true' : '')
            + `&t=${new Date().getTime()}`;
        const res = await fetch(url);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const json = await res.json();

        State.betplay.loaded = true;
        State.betplay.resumen = json.data;
        State.betplay.type = range.type;
        State.betplay.filters = { municipio: '', tipo: '', zona: '', sitio: '', cliente: '' };

        loadingEl.hidden = true;
        const totalCantidad = json.data && json.data.totales ? json.data.totales.cantidad : 0;
        if (!totalCantidad) {
            emptyEl.hidden = false;
            contentEl.hidden = true;
            return;
        }
        contentEl.hidden = false;
        populateBetplayFilters(json.data);
        renderBetplay(getBetplayRenderData());
    } catch (err) {
        console.error('[Betplay] Error consultando resumen:', err);
        loadingEl.hidden = true;
        emptyEl.hidden = false;
        document.querySelector('#betplay-empty p').textContent =
            'Error al consultar los datos de Betplay. Revisa la conexión e inténtalo de nuevo.';
    }
}

// Resuelve el rango [desde, hasta) en formato 'YYYY-MM-DD HH:MM:SS' según el modo elegido.
function getBetplayDateRange() {
    const mode = document.getElementById('betplay-date-mode').value;
    const type = document.getElementById('betplay-type').value;
    const addDay = (dateStr) => {
        const d = new Date(`${dateStr}T00:00:00`);
        d.setDate(d.getDate() + 1);
        return d.toISOString().split('T')[0];
    };

    let startDay, endDayExclusive;
    if (mode === 'today') {
        startDay = new Date().toISOString().split('T')[0];
        endDayExclusive = addDay(startDay);
    } else if (mode === 'single') {
        startDay = document.getElementById('betplay-date-single').value;
        endDayExclusive = addDay(startDay);
    } else { // range
        startDay = document.getElementById('betplay-date-from').value;
        const lastDay = document.getElementById('betplay-date-to').value;
        endDayExclusive = addDay(lastDay);
    }

    return {
        type,
        mode,
        desde: `${startDay} 00:00:00`,
        hasta: `${endDayExclusive} 00:00:00`
    };
}

function updateBetplaySelectionSummary(range) {
    const el = document.getElementById('betplay-selection-text');
    if (!el) return;
    const tipo = range.type === 'pagos' ? 'Pagos' : 'Recargas';
    let periodo;
    if (range.mode === 'today') periodo = 'día actual';
    else if (range.mode === 'single') periodo = `fecha ${range.desde.split(' ')[0]}`;
    else periodo = `del ${range.desde.split(' ')[0]} al ${document.getElementById('betplay-date-to').value}`;
    el.textContent = `Mostrando: ${tipo} — ${periodo}`;
}

// --- PALETA CATEGÓRICA DE MARCA (tortas / barras multicolor) ---
// Empieza por azul y amarillo de marca; el resto son colores bien
// diferenciables para muchas categorías.
const CHART_PALETTE = [
    '#1257d1', // azul marca
    '#ffc400', // amarillo marca
    '#16a34a', // verde
    '#f97316', // naranja
    '#8b5cf6', // violeta
    '#06b6d4', // cian
    '#ec4899', // rosa
    '#0a2e73', // azul profundo
    '#14b8a6', // teal
    '#eab308', // ocre
    '#ef4444', // rojo
    '#64748b'  // gris azulado
];

// --- BETPLAY: RENDER ---
const BETPLAY_PALETTE = CHART_PALETTE;

// Devuelve el valor de la métrica activa (monto o cantidad) de un grupo agregado.
function bpMetricValue(item) {
    return State.betplay.metric === 'cantidad' ? (item.cantidad || 0) : (item.monto || 0);
}

// Formatea un valor según la métrica activa.
function bpFormatMetric(val) {
    return State.betplay.metric === 'cantidad'
        ? Math.round(val).toLocaleString('es-CO')
        : formatCurrency(val);
}

// Nombres de columna crudas por tipo (para agregar en el navegador).
const BP_KEYS = {
    pagos:    { amount: 'VALOR_PAGO',  date: 'FEC_PAGO',  client: 'IDENTIFICACION' },
    recargas: { amount: 'VLR_RECARGA', date: 'FEC_VENTA', client: 'NUM_CELULAR' },
    ambos:    { amount: 'VALOR_UNIFICADO', date: 'FECHA_UNIFICADA', client: 'CLIENTE_UNIFICADO' }
};

// Re-agrega las filas crudas del detalle (misma forma que el backend) para
// soportar el filtrado del dashboard en el navegador.
function aggregateBetplayClient(rows, type) {
    const k = BP_KEYS[type] || BP_KEYS.pagos;
    const byHour = {}, byDay = {}, byZone = {}, byCity = {}, byType = {}, bySite = {}, byUser = {};
    const siteClients = {};
    let totalMonto = 0, totalCant = 0;
    const usuarios = new Set(), clientes = new Set(), sitios = new Set();

    const bump = (d, key, monto, labels) => {
        if (key === null || key === undefined) key = '(sin)';
        if (!d[key]) d[key] = { monto: 0, cantidad: 0, ...(labels || {}) };
        d[key].monto += monto;
        d[key].cantidad += 1;
    };

    rows.forEach(r => {
        const monto = parseFloat(r[k.amount]) || 0;
        totalMonto += monto; totalCant += 1;

        const dt = new Date(r[k.date]);
        if (!isNaN(dt.getTime())) {
            bump(byHour, dt.getHours(), monto);
            bump(byDay, dt.toISOString().slice(0, 10), monto);
        }
        const zona = r['Zona'] || 'Sin Zona'; bump(byZone, zona, monto, { zona });
        const ciudad = r['Ciudad'] || 'Sin Ciudad'; bump(byCity, ciudad, monto, { ciudad });
        const tipo = r['Tipo SV'] || 'Sin Tipo'; bump(byType, tipo, monto, { tipo });

        const cod = r['Cod. Sitio'];
        bump(bySite, cod, monto, {
            cod_sitio: cod, sitio: r['Sitio de venta'] || 'Sin Sitio',
            oficina: r['Oficina'] || 'Sin Oficina', zona, ciudad, tipo_sv: tipo,
            cx: r['CX'], cy: r['CY']
        });
        if (cod !== null && cod !== undefined) sitios.add(cod);

        const ident = r['NUM_IDENTIFICACION'];
        if (ident !== null && ident !== undefined && String(ident).trim() !== '') {
            bump(byUser, ident, monto, { identificacion: ident });
            usuarios.add(ident);
        }
        const cli = r[k.client];
        if (cli !== null && cli !== undefined && String(cli).trim() !== '') {
            clientes.add(cli);
            if (cod !== null && cod !== undefined) {
                (siteClients[cod] = siteClients[cod] || new Set()).add(cli);
            }
        }
    });

    Object.keys(bySite).forEach(cod => {
        const e = bySite[cod];
        e.clientes = siteClients[cod] ? siteClients[cod].size : 0;
        e.ticket_promedio = e.cantidad ? Math.round(e.monto / e.cantidad * 100) / 100 : 0;
    });

    const toList = (d, labelKey) => {
        const items = Object.keys(d).map(kk => {
            const e = { ...d[kk] };
            if (labelKey && e[labelKey] === undefined) e[labelKey] = kk;
            return e;
        });
        items.sort((a, b) => (b.monto || 0) - (a.monto || 0));
        return items;
    };

    return {
        totales: {
            monto: Math.round(totalMonto * 100) / 100,
            cantidad: totalCant,
            usuarios_unicos: usuarios.size,
            clientes_unicos: clientes.size,
            sitios_unicos: sitios.size,
            ticket_promedio: totalCant ? Math.round(totalMonto / totalCant * 100) / 100 : 0,
        },
        por_hora: Object.keys(byHour).map(h => ({ hora: Number(h), ...byHour[h] })).sort((a, b) => a.hora - b.hora),
        por_dia: Object.keys(byDay).sort().map(dd => ({ fecha: dd, ...byDay[dd] })),
        por_zona: toList(byZone, 'zona'),
        por_ciudad: toList(byCity, 'ciudad'),
        por_tipo_sv: toList(byType, 'tipo'),
        por_sitio: toList(bySite, 'cod_sitio'),
        por_usuario: toList(byUser, 'identificacion'),
        detalle: rows,
        detalle_total: rows.length,
    };
}

// Devuelve la data a renderizar: la del servidor si no hay filtros, o una
// re-agregación de las filas del detalle filtradas.
function getBetplayRenderData() {
    const base = State.betplay.resumen;
    if (!base) return base;
    const f = State.betplay.filters || {};
    const active = f.municipio || f.tipo || f.zona || f.sitio || f.cliente;
    const infoEl = document.getElementById('bp-filters-info');
    if (!active) { if (infoEl) infoEl.textContent = ''; return base; }

    const k = BP_KEYS[State.betplay.type] || BP_KEYS.pagos;
    const rows = (base.detalle || []).filter(r => {
        if (f.municipio && (r['Ciudad'] || 'Sin Ciudad') !== f.municipio) return false;
        if (f.tipo && (r['Tipo SV'] || 'Sin Tipo') !== f.tipo) return false;
        if (f.zona && (r['Zona'] || 'Sin Zona') !== f.zona) return false;
        if (f.sitio) {
            const s = (String(r['Sitio de venta'] || '') + ' ' + String(r['Cod. Sitio'] || '')).toLowerCase();
            if (!s.includes(f.sitio.toLowerCase())) return false;
        }
        if (f.cliente) {
            const c = String(r[k.client] ?? '').toLowerCase();
            if (!c.includes(f.cliente.toLowerCase())) return false;
        }
        return true;
    });

    if (infoEl) {
        const capped = (base.detalle_total || 0) > (base.detalle || []).length;
        infoEl.textContent = `Filtrado: ${rows.length.toLocaleString('es-CO')} transacciones`
            + (capped ? ` (sobre muestra de ${(base.detalle || []).length.toLocaleString('es-CO')})` : '');
    }
    return aggregateBetplayClient(rows, State.betplay.type);
}

// Llena los selects de filtro con los valores disponibles del periodo.
function populateBetplayFilters(data) {
    const uniq = (arr) => Array.from(new Set(arr.filter(x => x !== null && x !== undefined && x !== '')))
        .sort((a, b) => String(a).localeCompare(String(b), 'es'));
    const fill = (id, items, ph) => {
        const el = document.getElementById(id);
        if (!el) return;
        const cur = el.value;
        el.innerHTML = `<option value="">${ph}</option>`
            + items.map(v => `<option value="${String(v).replace(/"/g, '&quot;')}">${v}</option>`).join('');
        el.value = cur;
    };
    fill('bp-filter-municipio', uniq((data.por_ciudad || []).map(c => c.ciudad)), 'Todos los municipios');
    fill('bp-filter-tipo', uniq((data.por_tipo_sv || []).map(t => t.tipo)), 'Todos los tipos de SV');
    fill('bp-filter-zona', uniq((data.por_zona || []).map(z => z.zona)), 'Todas las zonas');
}

// Recalcula las zonas del selector según el municipio elegido (filtros
// dependientes): si hay municipio, solo aparecen las zonas presentes en él.
function refreshZonaOptionsForMunicipio() {
    const base = State.betplay.resumen;
    const muni = (document.getElementById('bp-filter-municipio') || {}).value || '';
    const zonaSel = document.getElementById('bp-filter-zona');
    if (!base || !zonaSel) return;
    const prev = zonaSel.value;

    let zonas;
    if (!muni) {
        zonas = Array.from(new Set((base.por_zona || []).map(z => z.zona)));
    } else {
        const set = new Set();
        (base.detalle || []).forEach(r => {
            if ((r['Ciudad'] || 'Sin Ciudad') === muni) set.add(r['Zona'] || 'Sin Zona');
        });
        zonas = Array.from(set);
    }
    zonas = zonas.filter(z => z !== null && z !== undefined && z !== '')
        .sort((a, b) => String(a).localeCompare(String(b), 'es'));

    zonaSel.innerHTML = '<option value="">Todas las zonas</option>'
        + zonas.map(z => `<option value="${String(z).replace(/"/g, '&quot;')}">${z}</option>`).join('');
    // Conservar la zona previa solo si sigue siendo válida para el municipio.
    zonaSel.value = zonas.includes(prev) ? prev : '';
}

// Lee los filtros y re-renderiza el dashboard.
function applyBetplayFilters() {
    if (!State.betplay.resumen) return;
    const val = (id) => { const e = document.getElementById(id); return e ? e.value.trim() : ''; };
    State.betplay.filters = {
        municipio: val('bp-filter-municipio'),
        tipo: val('bp-filter-tipo'),
        zona: val('bp-filter-zona'),
        sitio: val('bp-filter-sitio'),
        cliente: val('bp-filter-cliente'),
    };
    renderBetplay(getBetplayRenderData());
}

// Exporta la tabla "Detalle por Sitio de Venta" (respetando filtros) a Excel.
function exportBetplayTable() {
    if (typeof XLSX === 'undefined') { alert('No se pudo cargar el exportador de Excel.'); return; }
    const data = getBetplayRenderData();
    const sites = (data && data.por_sitio) || [];
    if (!sites.length) { alert('No hay datos para exportar.'); return; }
    const rows = sites.map(s => ({
        'Cod. Sitio': s.cod_sitio ?? '',
        'Sitio de Venta': s.sitio || '',
        'Oficina': s.oficina || '',
        'Zona': s.zona || '',
        'Municipio': s.ciudad || '',
        'Monto': s.monto || 0,
        'Transacciones': s.cantidad || 0,
        'Prom. Transacción': s.ticket_promedio || 0,
        'Clientes': s.clientes || 0,
    }));
    const ws = XLSX.utils.json_to_sheet(rows);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Detalle por Sitio');
    const tipo = State.betplay.type || 'betplay';
    const fecha = new Date().toISOString().slice(0, 10);
    XLSX.writeFile(wb, `betplay_${tipo}_detalle_sitios_${fecha}.xlsx`);
}

// ===================== EXPORTAR A PDF =====================
let _pdfLogos = null;
function _pdfLoadImg(src) {
    return new Promise((resolve, reject) => {
        const im = new Image();
        im.crossOrigin = 'anonymous';
        im.onload = () => resolve(im);
        im.onerror = reject;
        im.src = src;
    });
}
async function getPdfLogos() {
    if (_pdfLogos) return _pdfLogos;
    const [a, s, n, b] = await Promise.all([
        _pdfLoadImg('assets/logos/acertemos.png'),
        _pdfLoadImg('assets/logos/sured.png'),
        _pdfLoadImg('assets/logos/negativo.png'),
        _pdfLoadImg('assets/logos/betplay.jpg'),
    ]);
    _pdfLogos = { a, s, n, b };
    return _pdfLogos;
}

function betplayPdfPeriodText() {
    const el = document.getElementById('betplay-selection-text');
    return el ? el.textContent.replace('Mostrando:', '').trim() : '';
}

// Dibuja el header de marca (logos, sin estado de conexión). Devuelve su alto en mm.
async function drawBetplayPdfHeader(doc, pageW) {
    const logos = await getPdfLogos();
    const H = 24;
    doc.setFillColor(10, 46, 115);      // azul profundo
    doc.rect(0, 0, pageW, H, 'F');
    doc.setFillColor(255, 196, 0);      // línea amarilla inferior
    doc.rect(0, H, pageW, 1, 'F');

    let x = 10;
    const cy = 6, logoH = 12;
    const aW = logos.a.width * logoH / logos.a.height;
    doc.addImage(logos.a, 'PNG', x, cy, aW, logoH); x += aW + 5;
    doc.setDrawColor(255, 255, 255); doc.setLineWidth(0.2);
    doc.line(x, cy, x, cy + logoH); x += 5;
    const sW = logos.s.width * logoH / logos.s.height;
    doc.addImage(logos.s, 'PNG', x, cy, sW, logoH); x += sW + 5;
    doc.line(x, cy, x, cy + logoH); x += 5;
    const nW = logos.n.width * logoH / logos.n.height;
    doc.addImage(logos.n, 'PNG', x, cy, nW, logoH); x += nW + 6;

    // Logo Betplay como chip blanco redondeado
    const bH = logoH - 1;
    const bW = logos.b.width * bH / logos.b.height;
    const chipW = bW + 6, chipH = logoH + 2;
    doc.setFillColor(255, 255, 255);
    doc.roundedRect(x, cy - 1, chipW, chipH, 1.6, 1.6, 'F');
    doc.addImage(logos.b, 'JPEG', x + 3, cy, bW, bH);

    // Título + tipo/periodo a la derecha
    const tipo = State.betplay.type;
    const tipoLabel = tipo === 'ambos' ? 'Pagos y Recargas' : (tipo === 'recargas' ? 'Recargas' : 'Pagos');
    doc.setTextColor(255, 255, 255); doc.setFontSize(12);
    doc.text('Dashboard de Operaciones — Betplay', pageW - 10, 10, { align: 'right' });
    doc.setFontSize(9); doc.setTextColor(210, 224, 248);
    doc.text(`${tipoLabel} · ${betplayPdfPeriodText()}`, pageW - 10, 16, { align: 'right' });

    return H + 1;
}

// Lista de visuales exportables presentes y visibles en el dashboard.
// kind: 'wide' (ancho completo) | 'compact' (media página, 2 por fila).
function getBetplayPdfTargets() {
    const panelOf = (id) => {
        const c = document.getElementById(id);
        return c ? (c.closest('.chart-panel') || c.closest('.table-panel')) : null;
    };
    const list = [
        { name: 'Indicadores (KPIs)', el: document.querySelector('#betplay-content .kpi-strip'), kind: 'wide' },
        { name: 'Comportamiento en el tiempo', el: panelOf('bp-chart-time'), kind: 'wide' },
        { name: 'Distribución por Zona', el: panelOf('bp-chart-zona'), kind: 'compact' },
        { name: 'Distribución por Tipo de SV', el: panelOf('bp-chart-tipo'), kind: 'compact' },
        { name: 'Top 10 Municipios', el: panelOf('bp-chart-municipio'), kind: 'compact' },
        { name: 'Distribución por Municipio', el: panelOf('bp-chart-municipio-donut'), kind: 'compact' },
        { name: 'Top 10 Sitios de Venta', el: panelOf('bp-chart-sitios'), kind: 'compact' },
        { name: 'Top 10 Usuarios', el: panelOf('bp-chart-usuarios'), kind: 'compact' },
        { name: 'Top 10 Menos Recargas', el: panelOf('bp-chart-menos'), kind: 'compact' },
        { name: 'Mapa de Ventas', el: document.getElementById('bp-map-wrapper'), kind: 'wide', isMap: true },
        { name: 'Detalle por Sitio de Venta', el: panelOf('bp-table'), kind: 'wide', tableEl: document.getElementById('bp-table') },
    ];
    return list.filter(t => t.el && t.el.offsetParent !== null);
}

// Captura una visual a canvas. Casos especiales: mapa (leaflet-image, sin
// offset) y tabla (expandir scroll y capturar solo la tabla, sin botones).
async function captureBetplayTarget(t) {
    if (t.isMap && State.betplay.map && typeof leafletImage === 'function') {
        try {
            const map = State.betplay.map;
            const base = await new Promise((res, rej) =>
                leafletImage(map, (err, canvas) => err ? rej(err) : res(canvas)));
            // leaflet-image trae los tiles bien ubicados pero NO los circleMarker,
            // así que dibujamos los puntos nosotros usando la proyección del mapa.
            const size = map.getSize();
            const scaleX = base.width / size.x, scaleY = base.height / size.y;
            const points = bpComputeMapPoints((getBetplayRenderData() || {}).por_sitio || []);
            const maxVal = Math.max(1, ...points.map(p => bpMetricValue(p)));
            const ctx = base.getContext('2d');
            points.forEach(p => {
                const pt = map.latLngToContainerPoint([p.lat, p.lng]);
                const x = pt.x * scaleX, y = pt.y * scaleY;
                const r = (6 + 18 * (bpMetricValue(p) / maxVal)) * scaleX;
                ctx.beginPath();
                ctx.arc(x, y, r, 0, 2 * Math.PI);
                ctx.fillStyle = 'rgba(18, 87, 209, 0.5)';
                ctx.fill();
                ctx.lineWidth = Math.max(1, scaleX);
                ctx.strokeStyle = '#1257d1';
                ctx.stroke();
            });
            return base;
        } catch (e) { console.warn('[PDF] leaflet-image falló, uso html2canvas:', e); }
    }
    if (t.tableEl) {
        const sc = t.el.querySelector('.betplay-detalle-scroll');
        const prevMax = sc ? sc.style.maxHeight : null;
        const prevOv = sc ? sc.style.overflow : null;
        if (sc) { sc.style.maxHeight = 'none'; sc.style.overflow = 'visible'; }
        const canvas = await html2canvas(t.tableEl, { scale: 2, backgroundColor: '#ffffff', useCORS: true, logging: false });
        if (sc) { sc.style.maxHeight = prevMax || ''; sc.style.overflow = prevOv || ''; }
        return canvas;
    }
    return await html2canvas(t.el, { scale: 2, backgroundColor: '#ffffff', useCORS: true, logging: false });
}

function openBetplayPdfModal() {
    if (!State.betplay.resumen) { alert('Primero consulta datos de Betplay.'); return; }
    const targets = getBetplayPdfTargets();
    State.betplay._pdfTargets = targets;
    const listEl = document.getElementById('bp-pdf-list');
    if (listEl) listEl.innerHTML = targets.map((t, i) =>
        `<label class="bp-pdf-item"><input type="checkbox" data-idx="${i}" checked> ${t.name}</label>`
    ).join('');
    const all = document.getElementById('bp-pdf-all'); if (all) all.checked = true;
    const prog = document.getElementById('bp-pdf-progress'); if (prog) { prog.hidden = true; prog.textContent = ''; }
    const modal = document.getElementById('bp-pdf-modal'); if (modal) modal.style.display = 'flex';
}

async function generateBetplayPDF() {
    const targets = State.betplay._pdfTargets || [];
    const checks = [...document.querySelectorAll('#bp-pdf-list input[type="checkbox"]')];
    const selected = checks.filter(c => c.checked).map(c => targets[Number(c.dataset.idx)]).filter(Boolean);
    if (!selected.length) { alert('Selecciona al menos una visual.'); return; }

    const prog = document.getElementById('bp-pdf-progress');
    const genBtn = document.getElementById('bp-pdf-generate');
    const setProg = (t) => { if (prog) { prog.hidden = false; prog.textContent = t; } };
    if (genBtn) genBtn.disabled = true;

    try {
        setProg('Preparando…');
        const { jsPDF } = window.jspdf;
        const doc = new jsPDF('p', 'mm', 'a4');
        const pageW = doc.internal.pageSize.getWidth();
        const pageH = doc.internal.pageSize.getHeight();
        const margin = 10, gap = 6;
        const fullW = pageW - margin * 2;
        const colW = (fullW - gap) / 2;

        let y = (await drawBetplayPdfHeader(doc, pageW)) + 6;
        const newPage = async () => { doc.addPage(); y = (await drawBetplayPdfHeader(doc, pageW)) + 6; };

        // Añade una imagen a lo ancho completo, partiéndola en varias páginas si es alta.
        const addWidePaged = async (name, canvas) => {
            if (y + 12 > pageH - margin) await newPage();
            doc.setFontSize(11); doc.setTextColor(18, 87, 209);
            doc.text(name, margin, y); y += 6;
            const pxPerMm = canvas.width / fullW;
            let srcY = 0, remaining = canvas.height;
            while (remaining > 0) {
                const availMm = pageH - margin - y;
                if (availMm < 20) { await newPage(); continue; }
                const slicePx = Math.min(remaining, availMm * pxPerMm);
                const sliceMm = slicePx / pxPerMm;
                const tmp = document.createElement('canvas');
                tmp.width = canvas.width; tmp.height = Math.round(slicePx);
                tmp.getContext('2d').drawImage(canvas, 0, srcY, canvas.width, slicePx, 0, 0, canvas.width, slicePx);
                doc.addImage(tmp.toDataURL('image/png'), 'PNG', margin, y, fullW, sliceMm);
                y += sliceMm + 3; srcY += slicePx; remaining -= slicePx;
                if (remaining > 0) await newPage();
            }
            y += 5;
        };

        // Procesa una fila de hasta 2 visuales compactas (media página c/u).
        const addCompactRow = async (a, b) => {
            const ca = await captureBetplayTarget(a);
            const cb = b ? await captureBetplayTarget(b) : null;
            const ha = colW * ca.height / ca.width;
            const hb = cb ? colW * cb.height / cb.width : 0;
            const rowH = 6 + Math.max(ha, hb);
            if (y + rowH > pageH - margin) await newPage();
            doc.setFontSize(9); doc.setTextColor(18, 87, 209);
            doc.text(a.name, margin, y + 4);
            doc.addImage(ca.toDataURL('image/png'), 'PNG', margin, y + 6, colW, ha);
            if (b) {
                doc.text(b.name, margin + colW + gap, y + 4);
                doc.addImage(cb.toDataURL('image/png'), 'PNG', margin + colW + gap, y + 6, colW, hb);
            }
            y += rowH + gap;
        };

        // Recorre en orden: agrupa compactas de a 2; las anchas van solas.
        let pending = null;
        let done = 0;
        const total = selected.length;
        for (const t of selected) {
            setProg(`Generando ${++done}/${total}: ${t.name}…`);
            if (t.kind === 'compact') {
                if (!pending) { pending = t; }
                else { await addCompactRow(pending, t); pending = null; }
            } else {
                if (pending) { await addCompactRow(pending, null); pending = null; }
                const canvas = await captureBetplayTarget(t);
                await addWidePaged(t.name, canvas);
            }
        }
        if (pending) await addCompactRow(pending, null);

        const tipo = State.betplay.type || 'betplay';
        const fecha = new Date().toISOString().slice(0, 10);
        setProg('Guardando…');
        doc.save(`betplay_${tipo}_${fecha}.pdf`);
        const modal = document.getElementById('bp-pdf-modal'); if (modal) modal.style.display = 'none';
    } catch (err) {
        console.error('[PDF] Error:', err);
        setProg('Error generando el PDF: ' + (err && err.message ? err.message : err));
    } finally {
        if (genBtn) genBtn.disabled = false;
    }
}

function renderBetplay(data) {
    renderBetplayKPIs(data.totales || {});
    renderBetplayTimeChart(data);
    renderBetplayDonut('zona', 'bp-chart-zona', data.por_zona || [], 'zona');
    renderBetplayDonut('tipo', 'bp-chart-tipo', data.por_tipo_sv || [], 'tipo');
    renderBetplayBar('municipio', 'bp-chart-municipio', (data.por_ciudad || []).slice(0, 10), 'ciudad');
    renderBetplayDonut('municipioDonut', 'bp-chart-municipio-donut', (data.por_ciudad || []).slice(0, 8), 'ciudad');
    renderBetplayBar('sitios', 'bp-chart-sitios', (data.por_sitio || []).slice(0, 10), 'sitio');
    renderBetplayBar('usuarios', 'bp-chart-usuarios', (data.por_usuario || []).slice(0, 10), 'identificacion');

    // Solo recargas: Top 10 sitios con MENOS recargas (menor métrica, entre los que vendieron).
    const menosRow = document.getElementById('bp-menos-row');
    if (menosRow) {
        const isRecargas = State.betplay.type === 'recargas';
        menosRow.hidden = !isRecargas;
        if (isRecargas) {
            const menos = (data.por_sitio || [])
                .filter(s => bpMetricValue(s) > 0)
                .sort((a, b) => bpMetricValue(a) - bpMetricValue(b))
                .slice(0, 10);
            renderBetplayBar('menos', 'bp-chart-menos', menos, 'sitio');
        }
    }
    renderBetplayMap(data.por_sitio || []);
    renderBetplayRaw(data.detalle || [], data.detalle_total || 0);
    renderBetplayTable(data.por_sitio || []);
}

function renderBetplayKPIs(totales) {
    document.getElementById('bp-kpi-monto').textContent = formatCurrency(totales.monto || 0);
    document.getElementById('bp-kpi-ticket').textContent = `Ticket prom. ${formatCurrency(totales.ticket_promedio || 0)}`;
    document.getElementById('bp-kpi-cantidad').textContent = (totales.cantidad || 0).toLocaleString('es-CO');
    document.getElementById('bp-kpi-usuarios').textContent = (totales.usuarios_unicos || 0).toLocaleString('es-CO');
    document.getElementById('bp-kpi-sitios').textContent = (totales.sitios_unicos || 0).toLocaleString('es-CO');
    const cliEl = document.getElementById('bp-kpi-clientes');
    if (cliEl) cliEl.textContent = (totales.clientes_unicos || 0).toLocaleString('es-CO');
    const cliSub = document.getElementById('bp-kpi-clientes-sub');
    if (cliSub) cliSub.textContent = State.betplay.type === 'recargas' ? 'Por N° celular'
        : State.betplay.type === 'ambos' ? 'Identificación + celular' : 'Por identificación';
}

// Callbacks reutilizables para tortas: muestran porcentaje en tooltip.
function donutPercentTooltip(formatter) {
    return {
        label: (ctx) => {
            const val = ctx.parsed;
            const total = ctx.dataset.data.reduce((a, b) => a + (b || 0), 0) || 1;
            const pct = (val / total * 100).toFixed(1);
            const shown = formatter ? formatter(val) : val.toLocaleString('es-CO');
            return `${ctx.label}: ${shown} (${pct}%)`;
        }
    };
}

// Plugin de labels de leyenda con porcentaje para donuts.
function donutLegendLabels(chart) {
    const data = chart.data;
    const values = data.datasets[0].data;
    const total = values.reduce((a, b) => a + (b || 0), 0) || 1;
    return data.labels.map((label, i) => {
        const pct = (values[i] / total * 100).toFixed(1);
        return {
            text: `${label} (${pct}%)`,
            fillStyle: data.datasets[0].backgroundColor[i],
            strokeStyle: '#ffffff',
            lineWidth: 1,
            index: i
        };
    });
}

// Gráfico de barras temporal: por hora (1 día) o por día (rango con varios días).
function renderBetplayTimeChart(data) {
    const porDia = data.por_dia || [];
    const useDaily = porDia.length > 1;
    const titleEl = document.getElementById('bp-time-title');
    let labels, values;

    if (useDaily) {
        if (titleEl) titleEl.textContent = 'Comportamiento por Día';
        labels = porDia.map(d => d.fecha);
        values = porDia.map(bpMetricValue);
    } else {
        if (titleEl) titleEl.textContent = 'Comportamiento por Hora';
        const porHora = data.por_hora || [];
        const map = {};
        porHora.forEach(h => { map[h.hora] = bpMetricValue(h); });
        labels = Array.from({ length: 24 }, (_, h) => `${String(h).padStart(2, '0')}:00`);
        values = Array.from({ length: 24 }, (_, h) => map[h] || 0);
    }

    const metricLabel = State.betplay.metric === 'cantidad' ? 'Transacciones' : 'Monto';
    drawBetplayChart('time', 'bp-chart-time', {
        type: 'bar',
        data: {
            labels,
            datasets: [{
                label: metricLabel,
                data: values,
                backgroundColor: 'rgba(18, 87, 209, 0.6)',
                borderColor: '#1257d1',
                borderWidth: 1,
                borderRadius: 4
            }]
        },
        options: betplayChartOptions(false)
    });
}

function renderBetplayDonut(key, canvasId, items, labelField) {
    const top = items.slice(0, 8);
    const labels = top.map(i => i[labelField] || 'N/D');
    const values = top.map(bpMetricValue);
    drawBetplayChart(key, canvasId, {
        type: 'doughnut',
        data: {
            labels,
            datasets: [{
                data: values,
                backgroundColor: BETPLAY_PALETTE,
                borderColor: '#ffffff',
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                    labels: {
                        color: '#52627a',
                        font: { size: 11 },
                        generateLabels: donutLegendLabels
                    }
                },
                tooltip: { callbacks: donutPercentTooltip(bpFormatMetric) }
            }
        }
    });
}

function renderBetplayBar(key, canvasId, items, labelField) {
    const labels = items.map(i => String(i[labelField] ?? 'N/D'));
    const values = items.map(bpMetricValue);
    // Colores alternados amarillo/azul de marca (una sí, una no).
    const bg = values.map((_, i) => i % 2 === 0 ? 'rgba(255, 196, 0, 0.80)' : 'rgba(18, 87, 209, 0.72)');
    const bd = values.map((_, i) => i % 2 === 0 ? '#e0a800' : '#1257d1');
    drawBetplayChart(key, canvasId, {
        type: 'bar',
        data: {
            labels,
            datasets: [{
                label: State.betplay.metric === 'cantidad' ? 'Transacciones' : 'Monto',
                data: values,
                backgroundColor: bg,
                borderColor: bd,
                borderWidth: 1,
                borderRadius: 4
            }]
        },
        options: betplayChartOptions(true)
    });
}

// Opciones comunes para gráficos de barras. horizontal=true → barras horizontales.
function betplayChartOptions(horizontal) {
    return {
        indexAxis: horizontal ? 'y' : 'x',
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: { display: false },
            tooltip: { callbacks: { label: ctx => bpFormatMetric(horizontal ? ctx.parsed.x : ctx.parsed.y) } }
        },
        scales: {
            x: { ticks: { color: '#52627a', font: { size: 10 } }, grid: { color: 'rgba(15,37,64,0.08)' } },
            y: { ticks: { color: '#52627a', font: { size: 10 } }, grid: { color: 'rgba(15,37,64,0.08)' } }
        }
    };
}

// Crea/reemplaza una instancia de Chart.js guardada en State.betplay.charts[key].
function drawBetplayChart(key, canvasId, config) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    if (State.betplay.charts[key]) {
        State.betplay.charts[key].destroy();
    }
    State.betplay.charts[key] = new Chart(canvas.getContext('2d'), config);
}

// Extrae los puntos con coordenadas válidas de una lista de sitios.
function bpComputeMapPoints(sites) {
    return (sites || [])
        .map(s => ({ lat: parseFloat(s.cy), lng: parseFloat(s.cx), monto: s.monto || 0, cantidad: s.cantidad || 0, sitio: s.sitio, oficina: s.oficina, zona: s.zona, ciudad: s.ciudad, tipo_sv: s.tipo_sv, clientes: s.clientes || 0 }))
        .filter(p => Number.isFinite(p.lat) && Number.isFinite(p.lng) && p.lat !== 0 && p.lng !== 0);
}

// Mapa Leaflet: puntos o mapa de calor según State.betplay.mapMode.
function renderBetplayMap(sites) {
    const mapEl = document.getElementById('bp-map');
    if (!mapEl || typeof L === 'undefined') return;

    // Sitios con coordenadas válidas
    const points = bpComputeMapPoints(sites);

    // Inicializar el mapa una sola vez
    if (!State.betplay.map) {
        State.betplay.map = L.map(mapEl, { scrollWheelZoom: false }).setView([4.6, -74.08], 6);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; OpenStreetMap', maxZoom: 19
        }).addTo(State.betplay.map);
    }
    const map = State.betplay.map;

    // Limpiar capas previas
    if (State.betplay.markerLayer) { map.removeLayer(State.betplay.markerLayer); State.betplay.markerLayer = null; }
    if (State.betplay.heatLayer) { map.removeLayer(State.betplay.heatLayer); State.betplay.heatLayer = null; }

    if (!points.length) return;

    if (State.betplay.mapMode === 'heat' && typeof L.heatLayer === 'function') {
        const maxVal = Math.max(...points.map(p => bpMetricValue(p))) || 1;
        const heatData = points.map(p => [p.lat, p.lng, bpMetricValue(p) / maxVal]);
        State.betplay.heatLayer = L.heatLayer(heatData, { radius: 25, blur: 18, maxZoom: 12 }).addTo(map);
    } else {
        const maxVal = Math.max(...points.map(p => bpMetricValue(p))) || 1;
        const layer = L.layerGroup();
        points.forEach(p => {
            const radius = 6 + 18 * (bpMetricValue(p) / maxVal);
            L.circleMarker([p.lat, p.lng], {
                radius, color: '#1257d1', fillColor: '#1257d1', fillOpacity: 0.5, weight: 1
            }).bindPopup(
                `<strong>${p.sitio || 'Sitio'}</strong><br>${p.oficina || ''} — ${p.zona || ''}<br>`
                + `${p.ciudad ? 'Municipio: ' + p.ciudad + '<br>' : ''}`
                + `${p.tipo_sv ? 'Tipo SV: ' + p.tipo_sv + '<br>' : ''}`
                + `Monto: ${formatCurrency(p.monto)}<br>Transacciones: ${p.cantidad.toLocaleString('es-CO')}<br>`
                + `Clientes: ${p.clientes.toLocaleString('es-CO')}<br>`
                + `<span style="color:#64748b;">Lat: ${p.lat.toFixed(5)} · Long: ${p.lng.toFixed(5)}</span>`
            ).addTo(layer);
        });
        layer.addTo(map);
        State.betplay.markerLayer = layer;
    }

    // Ajustar el encuadre a los puntos
    const bounds = L.latLngBounds(points.map(p => [p.lat, p.lng]));
    if (bounds.isValid()) map.fitBounds(bounds, { padding: [30, 30], maxZoom: 13 });
    setTimeout(() => map.invalidateSize(), 100);
}

// Tabla de filas crudas de la consulta base, con columnas dinámicas.
function renderBetplayRaw(detalle, total) {
    const thead = document.getElementById('bp-raw-thead');
    const body = document.getElementById('bp-raw-body');
    const countEl = document.getElementById('bp-raw-count');
    const searchEl = document.getElementById('bp-raw-search');
    if (!thead || !body) return;

    State.betplay._rawRows = detalle;

    // Columnas = claves de la primera fila (guardadas en estado por si cambia el tipo)
    const columns = detalle.length ? Object.keys(detalle[0]) : [];
    State.betplay._rawColumns = columns;
    thead.innerHTML = columns.length
        ? `<tr>${columns.map(c => `<th>${c}</th>`).join('')}</tr>`
        : '';

    const fmtCell = (val) => {
        if (val === null || val === undefined) return '';
        return String(val);
    };

    const draw = (filterText) => {
        const cols = State.betplay._rawColumns || [];
        const ft = (filterText || '').toLowerCase().trim();
        const rows = (State.betplay._rawRows || []).filter(r =>
            !ft || cols.some(c => String(r[c] ?? '').toLowerCase().includes(ft))
        );

        if (countEl) {
            countEl.textContent = total > detalle.length
                ? `${rows.length} de ${total} (limitado a ${detalle.length})`
                : `${rows.length} filas`;
        }

        if (!cols.length || !rows.length) {
            body.innerHTML = `<tr><td class="empty-table" colspan="${cols.length || 1}">Sin resultados.</td></tr>`;
            return;
        }
        body.innerHTML = rows.map(r =>
            `<tr>${cols.map(c => `<td>${fmtCell(r[c])}</td>`).join('')}</tr>`
        ).join('');
    };

    draw('');
    if (searchEl && !searchEl.dataset.bound) {
        searchEl.dataset.bound = '1';
        searchEl.addEventListener('input', () => draw(searchEl.value));
    }
}

function renderBetplayTable(sites) {
    const body = document.getElementById('bp-table-body');
    const countEl = document.getElementById('bp-table-count');
    const searchEl = document.getElementById('bp-table-search');
    if (!body) return;

    // Guardar los sitios actuales para que la búsqueda use siempre el último dataset.
    State.betplay._tableSites = sites;
    if (!State.betplay.tableSort) State.betplay.tableSort = { key: null, dir: 1, type: 'text' };

    const draw = () => {
        const ft = (searchEl ? searchEl.value : '').toLowerCase().trim();
        let rows = (State.betplay._tableSites || []).filter(s => !ft
            || String(s.sitio || '').toLowerCase().includes(ft)
            || String(s.oficina || '').toLowerCase().includes(ft)
            || String(s.zona || '').toLowerCase().includes(ft)
            || String(s.ciudad || '').toLowerCase().includes(ft)
            || String(s.cod_sitio || '').toLowerCase().includes(ft));

        // Orden por columna (alfabético para texto, numérico para números).
        const sort = State.betplay.tableSort;
        if (sort.key) {
            rows = rows.slice().sort((a, b) => {
                let va = a[sort.key], vb = b[sort.key];
                if (sort.type === 'num') return ((Number(va) || 0) - (Number(vb) || 0)) * sort.dir;
                return String(va ?? '').localeCompare(String(vb ?? ''), 'es', { numeric: true }) * sort.dir;
            });
        }

        if (countEl) countEl.textContent = `${rows.length} sitios`;

        if (!rows.length) {
            body.innerHTML = '<tr><td class="empty-table" colspan="9">Sin resultados.</td></tr>';
            return;
        }
        body.innerHTML = rows.map(s => `
            <tr>
                <td>${s.cod_sitio ?? ''}</td>
                <td>${s.sitio || 'N/D'}</td>
                <td>${s.oficina || 'N/D'}</td>
                <td>${s.zona || 'N/D'}</td>
                <td>${s.ciudad || 'N/D'}</td>
                <td style="text-align: right;">${formatCurrency(s.monto || 0)}</td>
                <td style="text-align: right;">${(s.cantidad || 0).toLocaleString('es-CO')}</td>
                <td style="text-align: right;">${formatCurrency(s.ticket_promedio || 0)}</td>
                <td style="text-align: right;">${(s.clientes || 0).toLocaleString('es-CO')}</td>
            </tr>
        `).join('');
    };

    State.betplay._tableDraw = draw;
    draw();

    if (searchEl && !searchEl.dataset.bound) {
        searchEl.dataset.bound = '1';
        searchEl.addEventListener('input', draw);
    }

    // Encabezados ordenables: primer clic ordena, segundo invierte.
    const thead = document.querySelector('#bp-table thead');
    if (thead && !thead.dataset.sortBound) {
        thead.dataset.sortBound = '1';
        thead.querySelectorAll('th.bp-sortable').forEach(th => {
            th.addEventListener('click', () => {
                const key = th.dataset.sort;
                const type = th.dataset.type || 'text';
                const s = State.betplay.tableSort;
                if (s.key === key) {
                    s.dir = -s.dir;
                } else {
                    s.key = key; s.type = type;
                    s.dir = type === 'num' ? -1 : 1;  // números: mayor→menor; texto: A→Z
                }
                updateBetplaySortIcons();
                if (State.betplay._tableDraw) State.betplay._tableDraw();
            });
        });
    }
    updateBetplaySortIcons();
}

// Actualiza los íconos de orden (▲/▼) en la cabecera de la tabla de sitios.
function updateBetplaySortIcons() {
    const s = State.betplay.tableSort || {};
    document.querySelectorAll('#bp-table th.bp-sortable').forEach(th => {
        const icon = th.querySelector('.bp-sort-icon');
        if (!icon) return;
        if (th.dataset.sort === s.key) {
            icon.className = 'fa-solid bp-sort-icon ' + (s.dir === 1 ? 'fa-sort-up' : 'fa-sort-down');
            th.classList.add('bp-sort-active');
        } else {
            icon.className = 'fa-solid fa-sort bp-sort-icon';
            th.classList.remove('bp-sort-active');
        }
    });
}

// Helper setup for expand/collapse all buttons
function setupTreeControls() {
    if (elements.btnExpandAll && elements.btnCollapseAll) {
        elements.btnExpandAll.addEventListener('click', () => {
            const offices = new Set(getFilteredCombinedData().joined.map(item => item.oficina || `Oficina ${item.cod_oficina}`));
            offices.forEach(o => State.expandedOffices.add(o));
            renderTable();
        });
        elements.btnCollapseAll.addEventListener('click', () => {
            State.expandedOffices.clear();
            renderTable();
        });
    }
}

// --- API CONNECTIONS ---

async function checkStatus() {
    try {
        const res = await fetch(`${API_BASE}/api/status?t=${new Date().getTime()}`);
        const status = await res.json();
        
        State.uploadedProducts = status.goals_uploaded_products || [];
        
        const isOnline = status.cauca_connected || status.fortuna_connected;
        elements.statusIndicator.className = 'status-indicator ' + (isOnline ? 'online' : 'offline');
        
        let text = [];
        if (status.cauca_connected) text.push('CAUCA OK');
        if (status.fortuna_connected) text.push('FORTUNA OK');
        
        elements.statusText.textContent = text.length > 0 
            ? `Conectado a Oracle (${text.join(', ')})` 
            : 'Sin conexión a bases de datos (Modo Demo)';
            
        // Render badges according to uploaded lists
        const goalsContainer = document.getElementById('goals-management-link-container');
        if (status.all_goals_products && status.all_goals_products.length > 0) {
            if (goalsContainer) goalsContainer.style.display = 'flex';
            elements.badgeMetas.style.display = 'inline-block';
            const activeCount = status.goals_uploaded_products.length;
            const totalCount = status.all_goals_products.length;
            elements.badgeMetas.innerHTML = `<i class="fa-solid fa-gear"></i> ${activeCount}/${totalCount} Metas (Gestionar)`;
        } else {
            if (goalsContainer) goalsContainer.style.display = 'none';
            elements.badgeMetas.style.display = 'none';
        }
        
        if (status.distribution_records_count > 0) {
            elements.badgeDist.style.display = 'block';
            elements.badgeDist.textContent = `${status.distribution_records_count} Promotores`;
        } else {
            elements.badgeDist.style.display = 'none';
        }
        
    } catch (e) {
        console.error("Error checking system status:", e);
        elements.statusIndicator.className = 'status-indicator offline';
        elements.statusText.textContent = 'Servidor Backend desconectado';
    }
}

async function loadInitialCatalogues() {
    try {
        const [resSitios, resProds] = await Promise.all([
            fetch(`${API_BASE}/api/sitios`),
            fetch(`${API_BASE}/api/productos`)
        ]);
        
        const sitiosData = await resSitios.json();
        const prodsData = await resProds.json();
        
        State.sites = sitiosData.data || [];
        // Inject OWO and APP custom sites manually so they map to offices 333 / 334 respectively
        State.sites.push(
            { Cod_Sitio: 333033, Sitio_Venta: "Ventas OWO", Cod_Oficina: 333, Oficina: "Ventas OWO", Zona: "Aplicativo" },
            { Cod_Sitio: 334034, Sitio_Venta: "Ventas APP Su Red", Cod_Oficina: 334, Oficina: "Ventas APP Su Red", Zona: "Aplicativo" }
        );
        State.products = prodsData.data || [];
        
        console.log(`Loaded catalogues: ${State.sites.length} sites, ${State.products.length} products`);
    } catch (e) {
        console.error("Error loading catalogue caches:", e);
    }
}

async function loadUploadedState() {
    try {
        const todayStr = new Date().toLocaleDateString('en-CA'); // 'en-CA' gives YYYY-MM-DD
        elements.filterDate.value = todayStr;
        State.selectedDate = todayStr;

        const [resMetas, resDist] = await Promise.all([
            fetch(`${API_BASE}/api/metas?fecha=${todayStr}&t=${new Date().getTime()}`),
            fetch(`${API_BASE}/api/distribucion?t=${new Date().getTime()}`)
        ]);
        
        State.goals = await resMetas.json();
        State.distribution = await resDist.json();
        
        console.log(`Loaded stores: ${State.goals.length} goals, ${State.distribution.length} distribution records.`);
        
        // Populate standard filters
        populateStaticFilters();
        
        // Trigger initial data load for today
        await fetchAndRenderData();
        
    } catch (e) {
        console.error("Error loading uploaded state:", e);
    }
}

// --- UPLOAD HANDLERS ---

function setupUploadHandlers() {
    // Metas upload trigger
    elements.dropMetas.addEventListener('click', () => elements.fileMetas.click());
    elements.fileMetas.addEventListener('change', (e) => uploadMetasFiles(e.target.files));
    
    // Distribution upload trigger
    elements.dropDist.addEventListener('click', () => elements.fileDist.click());
    elements.fileDist.addEventListener('change', (e) => uploadDistFile(e.target.files[0]));
    
    // Setup drag and drop
    ['dropMetas', 'dropDist'].forEach(id => {
        const el = elements[id];
        el.addEventListener('dragover', (e) => {
            e.preventDefault();
            el.style.borderColor = 'var(--secondary)';
        });
        el.addEventListener('dragleave', () => {
            el.style.borderColor = 'rgba(255,255,255,0.12)';
        });
        el.addEventListener('drop', (e) => {
            e.preventDefault();
            el.style.borderColor = 'rgba(255,255,255,0.12)';
            if (e.dataTransfer.files.length > 0) {
                if (id === 'dropMetas') uploadMetasFiles(e.dataTransfer.files);
                else uploadDistFile(e.dataTransfer.files[0]);
            }
        });
    });

    // Clear data button
    elements.btnClearData.addEventListener('click', async () => {
        if (confirm("¿Estás seguro de que quieres limpiar todos los excels cargados en el servidor?")) {
            try {
                await fetch(`${API_BASE}/api/clear`, { method: 'POST' });
                State.goals = [];
                State.distribution = [];
                State.sales = [];
                const todayStr = new Date().toLocaleDateString('en-CA');
                elements.filterDate.value = todayStr;
                State.selectedDate = todayStr;
                await checkStatus();
                renderDashboard();
            } catch (e) {
                alert("Error limpiando datos: " + e);
            }
        }
    });
}

async function uploadMetasFiles(files) {
    if (files.length === 0) return;
    
    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
        formData.append('files', files[i]);
    }
    
    elements.badgeMetas.style.display = 'block';
    elements.badgeMetas.textContent = 'Procesando...';
    
    try {
        const res = await fetch(`${API_BASE}/api/upload/metas`, {
            method: 'POST',
            body: formData
        });
        
        if (!res.ok) throw new Error(await res.text());
        const data = await res.json();
        
        alert(`¡Éxito! Se cargaron ${data.total_records} metas desde ${data.parsed_files.length} archivos.`);
        
        await checkStatus();
        await loadUploadedState();
        
    } catch (e) {
        alert("Error al cargar metas: " + e.message);
        elements.badgeMetas.style.display = 'none';
    }
}

async function uploadDistFile(file) {
    if (!file) return;
    
    const formData = new FormData();
    formData.append('file', file);
    
    elements.badgeDist.style.display = 'block';
    elements.badgeDist.textContent = 'Procesando...';
    
    try {
        const res = await fetch(`${API_BASE}/api/upload/distribucion`, {
            method: 'POST',
            body: formData
        });
        
        if (!res.ok) throw new Error(await res.text());
        const data = await res.json();
        
        alert(`¡Éxito! Distribución comercial cargada con ${data.records_count} promotores.`);
        
        await checkStatus();
        await loadUploadedState();
        
    } catch (e) {
        alert("Error al cargar promotores: " + e.message);
        elements.badgeDist.style.display = 'none';
    }
}

// --- REFRESH ACTIONS ---

function setupRefreshHandlers() {
    elements.btnRefresh.addEventListener('click', async () => {
        if (!State.selectedDate) {
            alert("Por favor selecciona un Día en los filtros para actualizar sus ventas.");
            return;
        }
        await fetchAndRenderData(true);
    });
}

async function fetchAndRenderData(forceRefresh = false) {
    if (!State.selectedDate) return;
    
    // Add spin animation to the refresh button
    elements.btnRefresh.classList.add('spinning');
    elements.updateTimestamp.textContent = "Actualizando...";
    elements.updateTimestamp.style.color = '#52627a';
    
    try {
        const desde = `${State.selectedDate} 00:00:00`;
        const hasta = `${State.selectedDate} 23:59:59`;
        
        logger(`Cargando ventas de ${desde} a ${hasta} (forceRefresh=${forceRefresh})...`);
        
        const url = `${API_BASE}/api/ventas?desde=${encodeURIComponent(desde)}&hasta=${encodeURIComponent(hasta)}${forceRefresh ? '&force_refresh=true' : ''}`;
        const [resSales, resMetas] = await Promise.all([
            fetch(url),
            fetch(`${API_BASE}/api/metas?fecha=${State.selectedDate}&t=${new Date().getTime()}`)
        ]);
        
        if (!resSales.ok) {
            const errText = await resSales.text();
            let errMsg = "No se pudo conectar a las bases de datos de Oracle.";
            try {
                const errJson = JSON.parse(errText);
                if (errJson.detail) errMsg = errJson.detail;
            } catch(jsonErr) {}
            throw new Error(errMsg);
        }
        
        const salesResult = await resSales.json();
        
        State.sales = salesResult.data || [];
        logger(`Loaded ${State.sales.length} sales records from ${salesResult.source}.`);
        
        if (resMetas.ok) {
            State.goals = await resMetas.json();
            logger(`Loaded ${State.goals.length} goal records.`);
        }
        
        // Update timestamp with visual source/cache indication
        let timestampText = '';
        if (salesResult.source === 'LOCAL_CACHE') {
            const cacheTime = new Date(salesResult.last_updated);
            timestampText = `${cacheTime.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})} (Caché Local)`;
            elements.updateTimestamp.style.color = '#10b981'; // Green color for cached success
        } else if (salesResult.source === 'LOCAL_CACHE_STALE') {
            const cacheTime = new Date(salesResult.last_updated);
            timestampText = `${cacheTime.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})} (Caché Offline)`;
            elements.updateTimestamp.style.color = '#f59e0b'; // Amber warning color
        } else {
            const now = new Date();
            timestampText = `${now.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})} (Base de Datos Real)`;
            elements.updateTimestamp.style.color = '#38bdf8'; // Cyan online success color
        }
        elements.updateTimestamp.textContent = timestampText;
        
        // Re-check database pool status to update visual network indicator
        await checkStatus();
        
        // Redraw dashboard view
        renderDashboard();
        
    } catch (e) {
        console.error("Error updating sales:", e);
        elements.updateTimestamp.textContent = "Error de Conexión";
        elements.updateTimestamp.style.color = '#f43f5e'; // Crimson danger color
        
        // Visual alert notification as requested
        alert(`⚠️ ${e.message}\n\nPor favor, asegúrate de que tu VPN corporativa esté activa y vuelve a intentarlo.`);
        
        // Keep connectivity indicator in sync
        await checkStatus();
    } finally {
        elements.btnRefresh.classList.remove('spinning');
    }
}

// --- FILTER CONTROLLERS (CASCADE FILTERING) ---

function setupFilterListeners() {
    // 1. Date Filter
    elements.filterDate.addEventListener('change', async (e) => {
        State.selectedDate = e.target.value;
        if (State.selectedDate) {
            await fetchAndRenderData();
        } else {
            State.sales = [];
            renderDashboard();
        }
    });

    // 2. Zone Filter (Cascades to Office)
    elements.filterZone.addEventListener('change', (e) => {
        State.selectedZone = e.target.value;
        State.selectedOffice = ''; // Reset office and down
        State.selectedSeller = '';
        
        populateOfficeDropdown();
        populateSellerDropdown();
        renderDashboard();
    });

    // 3. Office Filter (Cascades to Seller)
    elements.filterOffice.addEventListener('change', (e) => {
        State.selectedOffice = e.target.value;
        State.selectedSeller = ''; // Reset seller
        
        populateSellerDropdown();
        renderDashboard();
    });

    // 4. Seller Filter
    elements.filterSeller.addEventListener('change', (e) => {
        State.selectedSeller = e.target.value;
        State.tableFilters.promoter = e.target.value;
        if (elements.tableFilterPromoter) {
            elements.tableFilterPromoter.value = e.target.value;
        }
        renderDashboard();
    });

    // 5. Product Filter
    elements.filterProduct.addEventListener('change', (e) => {
        State.selectedProduct = e.target.value;
        renderDashboard();
    });

    // --- Table-specific Filter Listeners ---
    // A. Office Text Filter
    elements.tableFilterOffice.addEventListener('input', (e) => {
        State.tableFilters.office = e.target.value.trim().toLowerCase();
        renderTable();
    });

    // B. Promoter Select Filter
    elements.tableFilterPromoter.addEventListener('change', (e) => {
        State.tableFilters.promoter = e.target.value;
        State.selectedSeller = e.target.value;
        if (elements.filterSeller) {
            elements.filterSeller.value = e.target.value;
        }
        renderDashboard(); // Re-render everything to update charts as well!
    });

    // C. Custom Product Multiselect Dropdown toggles
    elements.productsMultiselectBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        elements.tableFilterProductsContainer.classList.toggle('active');
    });

    // Close dropdown when clicking outside
    document.addEventListener('click', (e) => {
        if (elements.tableFilterProductsContainer && !elements.tableFilterProductsContainer.contains(e.target)) {
            elements.tableFilterProductsContainer.classList.remove('active');
        }
    });

    // Select all products
    elements.multiselectSelectAll.addEventListener('click', (e) => {
        e.stopPropagation();
        const checkboxes = elements.productsMultiselectOptions.querySelectorAll('input[type="checkbox"]');
        State.tableFilters.products = [];
        checkboxes.forEach(cb => {
            cb.checked = true;
            if (!State.tableFilters.products.includes(cb.value)) {
                State.tableFilters.products.push(cb.value);
            }
        });
        updateMultiselectTriggerText();
        renderTable();
    });

    // Clear product selection (None selected means all are shown)
    elements.multiselectClear.addEventListener('click', (e) => {
        e.stopPropagation();
        const checkboxes = elements.productsMultiselectOptions.querySelectorAll('input[type="checkbox"]');
        checkboxes.forEach(cb => {
            cb.checked = false;
        });
        State.tableFilters.products = [];
        updateMultiselectTriggerText();
        renderTable();
    });

    // Search bar
    elements.tableSearch.addEventListener('input', () => {
        renderTable();
    });
}

function getDistinctGoalDates() {
    const dates = [...new Set(State.goals.map(g => g.fecha))];
    dates.sort((a, b) => b.localeCompare(a)); // Descending order
    return dates;
}

// populateDateDropdown removed since date picker input is now used.

function populateStaticFilters() {
    // 1. Populate Zone Dropdown
    // We can extract zones from Promoters Excel or the sites catalogue
    let zones = new Set();
    State.distribution.forEach(d => { if (d.zona) zones.add(d.zona); });
    State.sites.forEach(s => { if (s.Zona) zones.add(s.Zona); });
    
    elements.filterZone.innerHTML = '<option value="">Todas las Zonas</option>';
    [...zones].sort().forEach(z => {
        const opt = document.createElement('option');
        opt.value = z;
        opt.textContent = z;
        elements.filterZone.appendChild(opt);
    });
    
    // 2. Populate Product Dropdown (Normalized according to Power BI)
    let products = new Set();
    
    // Use the global list of uploaded products if available
    if (State.uploadedProducts && State.uploadedProducts.length > 0) {
        State.uploadedProducts.forEach(p => products.add(ProductNormalizer.normalize(p)));
    } else {
        State.goals.forEach(g => { if (g.producto_excel) products.add(ProductNormalizer.normalize(g.producto_excel)); });
    }
    
    // If no goals files have been uploaded yet, show standard default Power BI core products
    if (products.size === 0) {
        [
            "BALOTO", "BET PLAY", "BILLONARIO NACIONAL", "CHANCE", "CHANCE MILLONARIO", 
            "COLOR LOTO", "DOBLE CHANCE", "MILOTO", "PATA MILLONARIA", "RASPITA",
            "SUPER ASTRO", "GIROS", "RECARGA EN LINEA", "RECAUDOS EMPRESARIALES", "TRANSACCIONES CNB"
        ].forEach(p => products.add(p));
    }
    
    elements.filterProduct.innerHTML = '<option value="">Todos los Productos</option>';
    [...products].sort().forEach(p => {
        const opt = document.createElement('option');
        opt.value = p;
        opt.textContent = `${p} (${ProductNormalizer.getGroup(p)})`;
        elements.filterProduct.appendChild(opt);
    });

    populateOfficeDropdown();
    populateSellerDropdown();
}

function populateOfficeDropdown() {
    let offices = [];
    
    // Filter offices based on selected Zone
    if (State.selectedZone) {
        // Find office codes belonging to this zone in the distribution or sites
        let officeIds = new Set();
        State.distribution.forEach(d => {
            if (d.zona === State.selectedZone && d.cod_oficina) officeIds.add(d.cod_oficina);
        });
        State.sites.forEach(s => {
            if (s.Zona === State.selectedZone && s.Cod_Oficina) officeIds.add(s.Cod_Oficina);
        });
        
        // Map back to names
        officeIds.forEach(id => {
            const distItem = State.distribution.find(d => d.cod_oficina === id);
            const siteItem = State.sites.find(s => s.Cod_Oficina === id);
            const name = (distItem && distItem.oficina) || (siteItem && siteItem.Oficina) || `Oficina ${id}`;
            offices.push({ id, name });
        });
    } else {
        // All offices
        let officeIds = new Set();
        State.distribution.forEach(d => { if (d.cod_oficina) officeIds.add(d.cod_oficina); });
        State.sites.forEach(s => { if (s.Cod_Oficina) officeIds.add(s.Cod_Oficina); });
        
        officeIds.forEach(id => {
            const distItem = State.distribution.find(d => d.cod_oficina === id);
            const siteItem = State.sites.find(s => s.Cod_Oficina === id);
            const name = (distItem && distItem.oficina) || (siteItem && siteItem.Oficina) || `Oficina ${id}`;
            offices.push({ id, name });
        });
    }
    
    offices.sort((a, b) => a.name.localeCompare(b.name));
    
    elements.filterOffice.innerHTML = '<option value="">Todas las Oficinas</option>';
    offices.forEach(o => {
        const opt = document.createElement('option');
        opt.value = o.id;
        opt.textContent = o.name;
        elements.filterOffice.appendChild(opt);
    });
    
    elements.filterOffice.value = State.selectedOffice;
}

function populateSellerDropdown() {
    let sellers = new Set();
    
    // Filter sellers based on selected Zone/Office
    State.distribution.forEach(d => {
        let match = true;
        if (State.selectedZone && d.zona !== State.selectedZone) match = false;
        if (State.selectedOffice && d.cod_oficina !== parseInt(State.selectedOffice)) match = false;
        
        if (match && d.promotor) {
            sellers.add(d.promotor);
        }
    });
    
    elements.filterSeller.innerHTML = '<option value="">Todos los Promotores</option>';
    [...sellers].sort().forEach(s => {
        const opt = document.createElement('option');
        opt.value = s;
        opt.textContent = s;
        elements.filterSeller.appendChild(opt);
    });
    
    elements.filterSeller.value = State.selectedSeller;
}

// --- DATA JOINING & COMPUTATIONS ---

/**
 * Normalizes all transaccional, goal and promotor rows into a single combined collection
 * filtered by the current selections in the sidebar
 */
function getFilteredCombinedData() {
    if (!State.selectedDate) return { joined: [], totals: { sales: 0, goals: 0, compliance: 0, activeSites: 0 } };
    
    // 1. Filter goals for selected day
    let goalsFiltered = State.goals.filter(g => g.fecha === State.selectedDate);
    
    // 2. Filter sales for selected day and EXCLUDE payout/disbursement tables
    let salesFiltered = State.sales.filter(s => {
        const sDate = s.Fecha_Dia ? s.Fecha_Dia.split('T')[0] : '';
        const isSameDate = sDate === State.selectedDate;
        
        const isPayout = s.Tabla_Origen === 'SIGT_PAGOS' || 
                          s.Tabla_Origen === 'SIGT_PAGOGEN_MAESTRO';
                          
        return isSameDate && !isPayout;
    });

    // 3. Setup dynamic mappings for joins
    // Map cod_sitio -> promoter & zone details (through cod_oficina mapping)
    const siteToOffice = {};
    State.sites.forEach(s => {
        if (s.Cod_Sitio && s.Cod_Oficina) siteToOffice[s.Cod_Sitio] = s.Cod_Oficina;
    });
    // Add office mappings from metas
    State.goals.forEach(g => {
        if (g.cod_sitio && g.cod_oficina) siteToOffice[g.cod_sitio] = g.cod_oficina;
    });

    const officeToDist = {};
    State.distribution.forEach(d => {
        if (d.cod_oficina) {
            officeToDist[d.cod_oficina] = {
                promotor: d.promotor,
                coordinador: d.coordinador,
                zona: d.zona,
                oficina: d.oficina
            };
        }
    });

    // Helper resolver
    const resolveMetadata = (cod_sitio) => {
        const officeId = siteToOffice[cod_sitio];
        const dist = officeId ? officeToDist[officeId] : null;
        
        return {
            cod_oficina: officeId || null,
            oficina: dist ? dist.oficina : (officeId ? `Oficina ${officeId}` : 'Sin Oficina'),
            promotor: dist ? dist.promotor : 'Sin Promotor',
            coordinador: dist ? dist.coordinador : 'Sin Coordinador',
            zona: dist ? dist.zona : 'Sin Zona'
        };
    };

    // 4. Group data by key: {cod_sitio}-{normalized_product} to calculate side-by-side compliance
    const compositeStore = {};
    
    // Pre-populate with goals
    goalsFiltered.forEach(g => {
        const metaInfo = resolveMetadata(g.cod_sitio);
        const normProd = ProductNormalizer.normalize(g.producto_excel);
        
        // Filter out if filters are active
        if (State.selectedZone && metaInfo.zona !== State.selectedZone) return;
        if (State.selectedOffice && metaInfo.cod_oficina !== parseInt(State.selectedOffice)) return;
        if (State.selectedSeller && metaInfo.promotor !== State.selectedSeller) return;
        if (State.selectedProduct && normProd !== State.selectedProduct) return;

        const key = `${g.cod_sitio}-${normProd}`;
        if (!compositeStore[key]) {
            compositeStore[key] = {
                cod_sitio: g.cod_sitio,
                sitio_venta: g.sitio_venta,
                cod_oficina: metaInfo.cod_oficina,
                oficina: metaInfo.oficina,
                promotor: metaInfo.promotor,
                zona: metaInfo.zona,
                producto: normProd,
                meta: 0,
                venta: 0,
                hourly_sales: Array(24).fill(0)
            };
        }
        const isCountBased = ["RECAUDOS EMPRESARIALES", "GIROS", "TRANSACCIONES CNB"].includes(normProd);
        const metaVal = isCountBased ? Math.round(g.meta || 0) : (g.meta || 0);
        compositeStore[key].meta += metaVal;
    });

    // Populate or merge with actual sales
    salesFiltered.forEach(s => {
        const metaInfo = resolveMetadata(s.Cod_Sitio);
        
        // Get product name: prioritize Tabla_Origen (reliable) then catalog lookup
        const tablaToProductName = {
            'SIGT_CHANCES':              'CHANCE',
            'SIGT_CHANCES_RASPA':        'RASPITA',   // Power BI: Raspitas = RASPITA, not CHANCE
            'SIGT_DOBLE_GANA':           'DOBLE CHANCE',
            'SIGT_SUPER_ASTRO':          'SUPER ASTRO',
            'SIGT_BALOTO':               'BALOTO',
            'SIGT_RECARGAS':             'RECARGA EN LINEA',
            'SIGT_SG_GIROS_CREADOS':     'GIROS',
            'SIGT_SG_GIROS_PAGADOS':     'GIROS',
            'SIGT_LOTERIAS_LINEA':       'LOTERIA EN LINEA',
            'SIGT_RECAUDOS_EMPRESAS':    'RECAUDOS EMPRESARIALES',
            'SIGT_VENTA_INCENTIVO_COBRO':'TRANSACCIONES CNB',
        };

        let normProd;
        const prod = State.products.find(p => String(p.Cod_Producto) === String(s.Cod_Producto));
        if (prod) {
            const prodName = prod.Producto;
            const prodType = prod["Tipo Producto"] || prod.Tipo_Producto;
            const specialKey = ProductNormalizer.getSpecialProductKey(prodName);
            if (specialKey) {
                normProd = specialKey;
            } else {
                normProd = ProductNormalizer.normalize(prodType || prodName);
            }
        } else {
            const codeMap = {
                22059: "BALOTO",
                22070: "MILOTO",
                22075: "COLOR LOTO",
                22069: "RASPITA",
                5: "SUPER ASTRO",
                22005: "TRANSACCIONES CNB"
            };
            const sCode = parseInt(s.Cod_Producto);
            if (sCode && codeMap[sCode]) {
                normProd = codeMap[sCode];
            } else if (s.Tabla_Origen && tablaToProductName[s.Tabla_Origen]) {
                normProd = tablaToProductName[s.Tabla_Origen];
            } else {
                const prodName = s.Cod_Producto === 22005 ? "TRANSACCIONES CNB" : s.Cod_Producto === 5 ? "SUPER ASTRO" : `Producto ${s.Cod_Producto}`;
                normProd = ProductNormalizer.normalize(prodName);
            }
        }
        
        // Filter out if filters are active
        if (State.selectedZone && metaInfo.zona !== State.selectedZone) return;
        if (State.selectedOffice && metaInfo.cod_oficina !== parseInt(State.selectedOffice)) return;
        if (State.selectedSeller && metaInfo.promotor !== State.selectedSeller) return;
        if (State.selectedProduct && normProd !== State.selectedProduct) return;

        const key = `${s.Cod_Sitio}-${normProd}`;
        
        // Get hour index (0-23)
        let hourIdx = 0;
        if (s.Hora) {
            hourIdx = parseInt(s.Hora.split(':')[0]);
        } else if (s.Fecha) {
            hourIdx = new Date(s.Fecha).getHours();
        }

        if (!compositeStore[key]) {
            // Find site name (type-safe comparison)
            const sCat = State.sites.find(site => String(site.Cod_Sitio) === String(s.Cod_Sitio));
            const sitName = sCat ? sCat.Sitio_Venta : `Sitio ${s.Cod_Sitio}`;
            
            compositeStore[key] = {
                cod_sitio: s.Cod_Sitio,
                sitio_venta: sitName,
                cod_oficina: metaInfo.cod_oficina,
                oficina: metaInfo.oficina,
                promotor: metaInfo.promotor,
                zona: metaInfo.zona,
                producto: normProd,
                meta: 0,
                venta: 0,
                hourly_sales: Array(24).fill(0)
            };
        }

        const increment = s.Venta_Neta || 0;

        compositeStore[key].venta += increment;
        if (hourIdx >= 0 && hourIdx < 24) {
            compositeStore[key].hourly_sales[hourIdx] += increment;
        }
    });

    const joined = Object.values(compositeStore);

    // Calculate totals
    let totalSales = 0;
    let totalGoals = 0;
    let reportingSites = new Set();

    joined.forEach(item => {
        // Exclude count-based products from overall totals if no specific product filter is active
        const isCountBased = ["RECAUDOS EMPRESARIALES", "GIROS", "TRANSACCIONES CNB"].includes(item.producto);
        const shouldExclude = !State.selectedProduct && isCountBased;

        if (!shouldExclude) {
            totalSales += item.venta;
            totalGoals += item.meta;
        }
        if (item.venta > 0) {
            reportingSites.add(item.cod_sitio);
        }
    });

    const compliance = calculateCompliance(totalSales, totalGoals);

    return {
        joined,
        totals: {
            sales: totalSales,
            goals: totalGoals,
            compliance: compliance,
            activeSites: reportingSites.size
        }
    };
}

// --- RENDER CONTROLLER ---

function renderDashboard() {
    const { joined, totals } = getFilteredCombinedData();
    
    // 1. Render top KPI cards
    elements.kpiSales.textContent = formatCurrency(totals.sales);
    elements.kpiGoal.textContent = formatCurrency(totals.goals);
    elements.kpiCompliance.textContent = `${totals.compliance}%`;
    elements.kpiComplianceBar.style.width = `${Math.min(totals.compliance, 100)}%`;
    elements.kpiSites.textContent = totals.activeSites;
    
    // Change subtext trend color or descriptive strings
    elements.kpiSalesSub.innerHTML = `<i class="fa-solid fa-arrow-trend-up"></i> Ventas acumuladas reales`;
    elements.kpiGoalSub.textContent = `Meta mensual prorrateada`;
    
    if (totals.compliance >= 100) {
        elements.kpiComplianceBar.style.background = 'linear-gradient(90deg, #10b981 0%, #059669 100%)';
    } else if (totals.compliance >= 70) {
        elements.kpiComplianceBar.style.background = 'linear-gradient(90deg, #06b6d4 0%, #6366f1 100%)';
    } else {
        elements.kpiComplianceBar.style.background = 'linear-gradient(90deg, #ef4444 0%, #f59e0b 100%)';
    }

    // 2. Render Charts
    renderHourlyChart(joined);
    renderProductChart(joined);
    renderComplianceRanking(joined);
    renderComplianceLagging(joined);
    
    // Dynamic table filters population
    populateTableFilters(joined);
    
    // 3. Render detailed report table
    renderTable(joined);
}

// --- CHARTS DRAWING ---

function renderHourlyChart(data) {
    const ctx = document.getElementById('chart-hourly').getContext('2d');
    
    // Aggregate sales and target curves per hour
    const salesPerHour = Array(24).fill(0);
    let totalGoal = 0;
    
    data.forEach(item => {
        totalGoal += item.meta;
        for (let h = 0; h < 24; h++) {
            salesPerHour[h] += item.hourly_sales[h];
        }
    });

    // Target hour model: distribute target values realistically across opening hours 7 AM - 9 PM
    // Weight curve for target: peak sales at noon (12:00) and evening (18:00)
    const targetWeights = Array(24).fill(0);
    let totalWeight = 0;
    for (let h = 7; h <= 21; h++) {
        let w = 1.0;
        if (h === 12 || h === 13 || h === 18 || h === 19) w = 1.6; // Peak weights
        if (h === 7 || h === 21) w = 0.5; // Off-peak weights
        targetWeights[h] = w;
        totalWeight += w;
    }
    
    const goalPerHour = Array(24).fill(0);
    if (totalWeight > 0) {
        for (let h = 0; h < 24; h++) {
            goalPerHour[h] = (targetWeights[h] / totalWeight) * totalGoal;
        }
    }

    // Generate Labels (00:00 to 23:00)
    const labels = Array.from({ length: 24 }, (_, i) => `${i.toString().padStart(2, '0')}:00`);

    // Clean old chart
    if (State.charts.hourly) State.charts.hourly.destroy();

    // Chart Options
    State.charts.hourly = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Venta Real ($)',
                    data: salesPerHour,
                    backgroundColor: 'rgba(255, 196, 0, 0.75)',
                    borderColor: '#e0a800',
                    borderWidth: 1,
                    borderRadius: 4,
                    order: 2
                },
                {
                    label: 'Meta Prorrateada ($)',
                    data: goalPerHour,
                    type: 'line',
                    borderColor: '#1257d1',
                    borderWidth: 3,
                    pointBackgroundColor: '#1257d1',
                    pointHoverRadius: 6,
                    fill: false,
                    tension: 0.35,
                    order: 1
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false } // Custom legend is in HTML
            },
            scales: {
                y: {
                    grid: { color: 'rgba(15,37,64,0.08)' },
                    ticks: {
                        color: '#52627a',
                        callback: value => '$' + value.toLocaleString()
                    }
                },
                x: {
                    grid: { display: false },
                    ticks: { color: '#52627a' }
                }
            }
        }
    });
}

function renderProductChart(data) {
    const ctx = document.getElementById('chart-product').getContext('2d');
    
    // Group sales by product
    const salesByProd = {};
    data.forEach(item => {
        if (!salesByProd[item.producto]) salesByProd[item.producto] = 0;
        salesByProd[item.producto] += item.venta;
    });

    const labels = Object.keys(salesByProd);
    const dataset = Object.values(salesByProd);

    if (State.charts.product) State.charts.product.destroy();

    if (labels.length === 0) {
        // Placeholder
        State.charts.product = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Cargar metas/ventas'],
                datasets: [{ data: [1], backgroundColor: ['rgba(15,37,64,0.08)'], borderWidth: 0 }]
            },
            options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } }
        });
        return;
    }

    const colors = CHART_PALETTE;

    State.charts.product = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: dataset,
                backgroundColor: colors.slice(0, labels.length),
                borderWidth: 1,
                borderColor: '#ffffff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { color: '#52627a', boxWidth: 12, font: { family: 'Outfit', size: 11 } }
                }
            },
            cutout: '65%'
        }
    });
}

function renderComplianceRanking(data) {
    const ctx = document.getElementById('chart-compliance-ranking').getContext('2d');
    
    // Group sales and targets by Office
    const officeStats = {};
    data.forEach(item => {
        if (!officeStats[item.oficina]) {
            officeStats[item.oficina] = { sales: 0, goals: 0 };
        }
        officeStats[item.oficina].sales += item.venta;
        officeStats[item.oficina].goals += item.meta;
    });

    // Compute compliance rates (only rank offices with active goals > 0 and compliance >= 95%)
    const ranking = [];
    Object.keys(officeStats).forEach(name => {
        const stat = officeStats[name];
        if (stat.goals > 0) {
            const compliance = calculateCompliance(stat.sales, stat.goals);
            if (compliance >= 95) {
                ranking.push({ name, compliance });
            }
        }
    });

    // Sort descending and take top 5
    ranking.sort((a, b) => b.compliance - a.compliance);
    const top5 = ranking.slice(0, 5);

    const labels = top5.map(item => item.name);
    const dataset = top5.map(item => item.compliance);

    if (State.charts.ranking) State.charts.ranking.destroy();

    if (labels.length === 0) {
        State.charts.ranking = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['Sin oficinas >= 95%'],
                datasets: [{ data: [0], backgroundColor: ['rgba(15,37,64,0.08)'] }]
            },
            options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } }
        });
        return;
    }

    State.charts.ranking = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: '% Cumplimiento',
                data: dataset,
                backgroundColor: 'rgba(16, 185, 129, 0.7)',
                borderColor: '#10b981',
                borderWidth: 1,
                borderRadius: 4
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                x: {
                    grid: { color: 'rgba(15,37,64,0.08)' },
                    ticks: {
                        color: '#52627a',
                        callback: value => value + '%'
                    },
                    max: Math.max(100, ...dataset) // dynamic max scale
                },
                y: {
                    grid: { display: false },
                    ticks: { color: '#52627a', font: { family: 'Outfit', size: 10 } }
                }
            }
        }
    });
}

function renderComplianceLagging(data) {
    const ctx = document.getElementById('chart-compliance-lagging').getContext('2d');
    
    // Group sales and targets by Office
    const officeStats = {};
    data.forEach(item => {
        if (!officeStats[item.oficina]) {
            officeStats[item.oficina] = { sales: 0, goals: 0 };
        }
        officeStats[item.oficina].sales += item.venta;
        officeStats[item.oficina].goals += item.meta;
    });

    // Compute compliance rates (only rank offices with active goals > 0 and compliance < 95%)
    const ranking = [];
    Object.keys(officeStats).forEach(name => {
        const stat = officeStats[name];
        if (stat.goals > 0) {
            const compliance = calculateCompliance(stat.sales, stat.goals);
            if (compliance < 95) {
                ranking.push({ name, compliance });
            }
        }
    });

    // Sort ASCENDING (lowest compliance first) and take bottom 5
    ranking.sort((a, b) => a.compliance - b.compliance);
    const bottom5 = ranking.slice(0, 5);

    const labels = bottom5.map(item => item.name);
    const dataset = bottom5.map(item => item.compliance);

    if (State.charts.lagging) State.charts.lagging.destroy();

    if (labels.length === 0) {
        State.charts.lagging = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['Sin oficinas < 95%'],
                datasets: [{ data: [0], backgroundColor: ['rgba(15,37,64,0.08)'] }]
            },
            options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } }
        });
        return;
    }

    State.charts.lagging = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: '% Cumplimiento (Menor)',
                data: dataset,
                backgroundColor: 'rgba(239, 68, 68, 0.7)',
                borderColor: '#ef4444',
                borderWidth: 1,
                borderRadius: 4
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                x: {
                    grid: { color: 'rgba(15,37,64,0.08)' },
                    ticks: {
                        color: '#52627a',
                        callback: value => value + '%'
                    },
                    max: 100 // keep it scaled up to 100% since they are lagging
                },
                y: {
                    grid: { display: false },
                    ticks: { color: '#52627a', font: { family: 'Outfit', size: 10 } }
                }
            }
        }
    });
}

// --- DETAILED GRID TABLE & PROMOTER SUMMARY (UX VISTA PREMIUM) ---

/**
 * Renders a premium summary panel of promoter performance per office
 */
function renderPromoterSummary() {
    const activePromoter = State.selectedSeller || State.tableFilters.promoter;
    
    // If no promoter is selected, hide the panel
    if (!activePromoter) {
        if (elements.promoterPanel) {
            elements.promoterPanel.style.display = 'none';
        }
        return;
    }

    // Get filtered day sales/goals
    const rawData = getFilteredCombinedData().joined;
    const promoterRecords = rawData.filter(item => item.promotor === activePromoter);

    if (promoterRecords.length === 0) {
        if (elements.promoterPanel) {
            elements.promoterPanel.style.display = 'none';
        }
        return;
    }

    // Group sales and targets by Office
    const officeGroups = {};
    let totalSales = 0;
    let totalGoal = 0;

    promoterRecords.forEach(rec => {
        const officeName = rec.oficina || `Oficina ${rec.cod_oficina}` || 'Sin Oficina';
        if (!officeGroups[officeName]) {
            officeGroups[officeName] = {
                name: officeName,
                sales: 0,
                goal: 0
            };
        }
        officeGroups[officeName].sales += rec.venta;
        officeGroups[officeName].goal += rec.meta;
        totalSales += rec.venta;
        totalGoal += rec.meta;
    });

    // Update Overall metrics
    if (elements.promoterPanelName) elements.promoterPanelName.textContent = activePromoter;
    if (elements.promoterPanelSales) elements.promoterPanelSales.textContent = formatCurrency(totalSales);
    if (elements.promoterPanelGoal) elements.promoterPanelGoal.textContent = formatCurrency(totalGoal);

    const overallCompliance = totalGoal > 0 ? Math.round((totalSales / totalGoal) * 100) : 0;
    let badgeClass = 'badge-danger';
    if (overallCompliance >= 100) badgeClass = 'badge-success';
    else if (overallCompliance >= 70) badgeClass = 'badge-warning';

    if (elements.promoterPanelOverall) {
        elements.promoterPanelOverall.textContent = `${overallCompliance}%`;
        elements.promoterPanelOverall.className = `compliance-badge ${badgeClass}`;
    }

    // Render each office card in the grid
    if (elements.promoterOfficesGrid) {
        elements.promoterOfficesGrid.innerHTML = '';
        
        Object.values(officeGroups).sort((a,b) => a.name.localeCompare(b.name)).forEach(group => {
            const compliance = calculateCompliance(group.sales, group.goal);
            
            let fillClass = 'bg-danger';
            if (compliance >= 100) fillClass = 'bg-success';
            else if (compliance >= 70) fillClass = 'bg-warning';
            
            const card = document.createElement('div');
            card.className = 'promoter-office-card';
            card.innerHTML = `
                <div class="promoter-card-header">
                    <span class="promoter-office-name"><i class="fa-solid fa-building"></i> ${group.name}</span>
                    <span class="compliance-badge ${compliance >= 100 ? 'badge-success' : compliance >= 70 ? 'badge-warning' : 'badge-danger'}">${compliance}%</span>
                </div>
                <div class="promoter-card-details" style="margin-top: 6px;">
                    <span>Venta Real:</span>
                    <strong>${formatCurrency(group.sales)}</strong>
                </div>
                <div class="promoter-card-details">
                    <span>Meta Día:</span>
                    <strong>${formatCurrency(group.goal)}</strong>
                </div>
                <div class="promoter-bar-container">
                    <div class="promoter-bar-fill ${fillClass}" style="width: ${Math.min(compliance, 100)}%"></div>
                </div>
            `;
            elements.promoterOfficesGrid.appendChild(card);
        });
    }

    // Render each product card in the products grid
    if (elements.promoterProductsGrid) {
        elements.promoterProductsGrid.innerHTML = '';
        
        // Group sales and targets by Product
        const productGroups = {};
        promoterRecords.forEach(rec => {
            const prodName = rec.producto || 'Otros';
            if (!productGroups[prodName]) {
                productGroups[prodName] = {
                    name: prodName,
                    sales: 0,
                    goal: 0,
                    hourly_sales: Array(24).fill(0)
                };
            }
            productGroups[prodName].sales += rec.venta;
            productGroups[prodName].goal += rec.meta;
            for (let h = 0; h < 24; h++) {
                productGroups[prodName].hourly_sales[h] += rec.hourly_sales[h];
            }
        });

        // Determine reference hour
        const todayStr = new Date().toLocaleDateString('en-CA');
        const isToday = State.selectedDate === todayStr;
        let refHour = new Date().getHours();
        if (!isToday) {
            refHour = 21; // Show full day for historical data
        } else {
            refHour = Math.max(7, Math.min(21, refHour));
        }
        const refHourStr = `${refHour.toString().padStart(2, '0')}:00`;
        const nextHour = refHour < 21 ? refHour + 1 : 21;
        const nextHourStr = `${nextHour.toString().padStart(2, '0')}:00`;

        // Calculate weights (distributed as in hourly chart)
        const targetWeights = Array(24).fill(0);
        let totalWeight = 0;
        for (let h = 7; h <= 21; h++) {
            let w = 1.0;
            if (h === 12 || h === 13 || h === 18 || h === 19) w = 1.6;
            if (h === 7 || h === 21) w = 0.5;
            targetWeights[h] = w;
            totalWeight += w;
        }

        const sortedProductNames = Object.keys(productGroups).sort();
        
        sortedProductNames.forEach(pName => {
            const group = productGroups[pName];
            const compliance = calculateCompliance(group.sales, group.goal);
            
            let fillClass = 'bg-danger';
            if (compliance >= 100) fillClass = 'bg-success';
            else if (compliance >= 70) fillClass = 'bg-warning';

            // Accumulated sales up to refHour
            let accumulatedSales = 0;
            for (let h = 0; h <= refHour; h++) {
                accumulatedSales += group.hourly_sales[h];
            }

            // Next hour goal
            const nextHourGoal = totalWeight > 0 ? (targetWeights[nextHour] / totalWeight) * group.goal : 0;

            const card = document.createElement('div');
            card.className = 'promoter-product-card';
            card.innerHTML = `
                <div class="promoter-card-header">
                    <span class="promoter-office-name"><i class="fa-solid fa-tag"></i> ${group.name}</span>
                    <span class="compliance-badge ${compliance >= 100 ? 'badge-success' : compliance >= 70 ? 'badge-warning' : 'badge-danger'}">${compliance}%</span>
                </div>
                <div class="promoter-card-details" style="margin-top: 6px;">
                    <span>Venta Acum. (hasta ${refHourStr}):</span>
                    <strong>${formatProductValue(accumulatedSales, group.name)}</strong>
                </div>
                <div class="promoter-card-details">
                    <span>Meta Hora Sig. (${nextHourStr}):</span>
                    <strong>${formatProductValue(nextHourGoal, group.name)}</strong>
                </div>
                <div class="promoter-card-details">
                    <span>Meta del Día:</span>
                    <strong>${formatProductValue(group.goal, group.name)}</strong>
                </div>
                <div class="promoter-bar-container">
                    <div class="promoter-bar-fill ${fillClass}" style="width: ${Math.min(compliance, 100)}%"></div>
                </div>
            `;
            elements.promoterProductsGrid.appendChild(card);
        });

        // Hide or show products section depending on active data
        if (elements.promoterProductsSection) {
            elements.promoterProductsSection.style.display = sortedProductNames.length > 0 ? 'block' : 'none';
        }
    }

    // Show panel
    if (elements.promoterPanel) {
        elements.promoterPanel.style.display = 'block';
    }
}

/**
 * Main Table rendering using an interactive tree hierarchical format with horizontal product columns
 */
function renderTable(prejoinedData) {
    // 1. Render promoter consolidated summary first
    renderPromoterSummary();

    const data = prejoinedData || getFilteredCombinedData().joined;
    const searchVal = elements.tableSearch.value.trim().toLowerCase();
    
    // Apply general search, table promoter and table office filters
    // Note: product checklist is handled by toggling horizontal column visibility, NOT filtering rows out!
    const filteredData = data.filter(item => {
        // A. General Search Bar
        if (searchVal) {
            const matchSearch = (
                item.sitio_venta.toLowerCase().includes(searchVal) ||
                item.oficina.toLowerCase().includes(searchVal) ||
                item.zona.toLowerCase().includes(searchVal) ||
                item.promotor.toLowerCase().includes(searchVal) ||
                String(item.cod_sitio).includes(searchVal)
            );
            if (!matchSearch) return false;
        }
        
        // B. Table Office Filter (Name or Code)
        if (State.tableFilters.office) {
            const officeQuery = State.tableFilters.office;
            const matchOffice = (
                item.oficina.toLowerCase().includes(officeQuery) ||
                (item.cod_oficina && String(item.cod_oficina).includes(officeQuery))
            );
            if (!matchOffice) return false;
        }
        
        // C. Table Promoter Filter
        if (State.tableFilters.promoter) {
            if (item.promotor !== State.tableFilters.promoter) return false;
        }
        
        return true;
    });

    // 2. Identify products to display horizontally (selected checklist or active ones)
    let displayedProducts = [];
    if (State.tableFilters.products && State.tableFilters.products.length > 0) {
        displayedProducts = [...State.tableFilters.products].sort();
    } else {
        const activeProds = new Set();
        filteredData.forEach(item => {
            if (item.venta > 0 || item.meta > 0) {
                activeProds.add(item.producto);
            }
        });
        displayedProducts = [...activeProds].sort();
        
        // Fallback standard products if completely empty
        if (displayedProducts.length === 0) {
            displayedProducts = ["BALOTO", "BET PLAY", "CHANCE", "SUPER ASTRO", "GIROS"];
        }
    }

    // 3. Dynamically build table headers (Two-row dynamic thead)
    if (elements.tableThead) {
        elements.tableThead.innerHTML = `
            <tr>
                <th rowspan="2" style="width: 80px;">Zona</th>
                <th rowspan="2" style="min-width: 280px; text-align: left;">Oficina / Sitio de Venta</th>
                <th rowspan="2" style="min-width: 140px; text-align: left;">Promotor</th>
                ${displayedProducts.map(prod => `
                    <th colspan="3" class="product-col-group-header">${prod}</th>
                `).join('')}
            </tr>
            <tr>
                ${displayedProducts.map(() => `
                    <th class="num-col">Venta</th>
                    <th class="num-col">Meta</th>
                    <th class="num-col">% Cump.</th>
                `).join('')}
            </tr>
        `;
    }

    elements.tableBody.innerHTML = '';

    // 4. Group data by Office and Sales Site
    const officesMap = {};
    filteredData.forEach(item => {
        const officeKey = item.oficina || `Oficina ${item.cod_oficina}` || 'Sin Oficina';
        
        if (!officesMap[officeKey]) {
            officesMap[officeKey] = {
                oficina: officeKey,
                cod_oficina: item.cod_oficina,
                zona: item.zona || 'Sin Zona',
                promotores: new Set(),
                sitios: {},
                productos: {}
            };
        }
        
        const officeObj = officesMap[officeKey];
        if (item.promotor && item.promotor !== 'Sin Promotor') {
            officeObj.promotores.add(item.promotor);
        }
        
        // Accumulate on Office level
        if (!officeObj.productos[item.producto]) {
            officeObj.productos[item.producto] = { venta: 0, meta: 0 };
        }
        officeObj.productos[item.producto].venta += item.venta;
        officeObj.productos[item.producto].meta += item.meta;
        
        // Accumulate on Site level
        const siteKey = item.cod_sitio;
        if (!officeObj.sitios[siteKey]) {
            officeObj.sitios[siteKey] = {
                cod_sitio: item.cod_sitio,
                sitio_venta: item.sitio_venta,
                promotor: item.promotor,
                zona: item.zona,
                productos: {}
            };
        }
        
        const siteObj = officeObj.sitios[siteKey];
        if (!siteObj.productos[item.producto]) {
            siteObj.productos[item.producto] = { venta: 0, meta: 0 };
        }
        siteObj.productos[item.producto].venta += item.venta;
        siteObj.productos[item.producto].meta += item.meta;
    });

    const totalOffices = Object.keys(officesMap).length;
    let totalSites = 0;
    Object.values(officesMap).forEach(o => totalSites += Object.keys(o.sitios).length);

    // Update dynamic results counter badge
    if (elements.tableResultsCount) {
        elements.tableResultsCount.textContent = `${totalOffices} oficinas (${totalSites} sitios)`;
    }

    if (totalOffices === 0) {
        elements.tableBody.innerHTML = `
            <tr>
                <td colspan="${3 + displayedProducts.length * 3}" class="empty-table">No se encontraron registros que coincidan con la búsqueda o los filtros activos.</td>
            </tr>
        `;
        return;
    }

    // 5. Render Office Parent Rows and Site Child Rows (Tree Grid layout)
    const sortedOfficeNames = Object.keys(officesMap).sort();
    
    sortedOfficeNames.forEach(offName => {
        const office = officesMap[offName];
        const isCollapsed = !State.expandedOffices.has(offName);
        const officeSitesCount = Object.keys(office.sitios).length;
        
        // Render Office Parent Row
        const trOffice = document.createElement('tr');
        trOffice.className = 'tr-office-parent';
        trOffice.dataset.office = offName;
        
        // Click toggles collapse state
        trOffice.addEventListener('click', (e) => {
            // Prevent toggling if user clicks a link/text selection inside
            if (State.expandedOffices.has(offName)) {
                State.expandedOffices.delete(offName);
            } else {
                State.expandedOffices.add(offName);
            }
            renderTable();
        });
        
        let officeRowHtml = `
            <td>${office.zona}</td>
            <td>
                <div class="office-name-container">
                    <span class="office-chevron ${!isCollapsed ? 'expanded' : ''}">
                        <i class="fa-solid fa-chevron-right"></i>
                    </span>
                    <span style="color:var(--text-primary); font-weight: 600;">${office.oficina}</span>
                    <span class="office-sites-count">${officeSitesCount} sitios</span>
                </div>
            </td>
            <td>${Array.from(office.promotores).join(', ') || 'Varios'}</td>
        `;
        
        // Horizontal columns for each product on Office level
        displayedProducts.forEach((prod, index) => {
            const prodData = office.productos[prod] || { venta: 0, meta: 0 };
            const compliance = calculateCompliance(prodData.venta, prodData.meta);
            
            let cumpColor = 'var(--danger)';
            if (compliance >= 95) cumpColor = 'var(--accent)';
            
            const isFirst = index === 0;
            const isLast = index === displayedProducts.length - 1;
            const cellClasses = `product-cell ${isFirst ? 'product-cell-first' : ''} ${isLast ? 'product-cell-last' : ''}`;
            
            officeRowHtml += `
                <td class="num-col ${cellClasses}">${formatProductValue(prodData.venta, prod)}</td>
                <td class="num-col ${cellClasses}" style="color:rgba(255,255,255,0.45);">${formatProductValue(prodData.meta, prod)}</td>
                <td class="num-col ${cellClasses}" style="color: ${cumpColor} !important; font-weight: 600 !important;">${compliance}%</td>
            `;
        });
        
        trOffice.innerHTML = officeRowHtml;
        elements.tableBody.appendChild(trOffice);
        
        // Render Site Child Rows (only if parent is NOT collapsed)
        const sortedSiteKeys = Object.keys(office.sitios).sort();
        
        sortedSiteKeys.forEach(siteKey => {
            const site = office.sitios[siteKey];
            
            const trSite = document.createElement('tr');
            trSite.className = `tr-site-child ${isCollapsed ? 'collapsed-row' : ''}`;
            
            let siteRowHtml = `
                <td style="color:var(--text-muted);">${site.zona}</td>
                <td>
                    <div class="indent-site-container">
                        <span class="tree-branch-icon">└─</span>
                        <span style="color:var(--text-primary); font-weight: 500;">${site.sitio_venta}</span>
                        <span style="font-size: 10px; color: var(--text-muted); font-family: monospace;">(${site.cod_sitio})</span>
                    </div>
                </td>
                <td>${site.promotor || 'Sin Promotor'}</td>
            `;
            
            // Horizontal columns for each product on Site level
            displayedProducts.forEach((prod, index) => {
                const prodData = site.productos[prod] || { venta: 0, meta: 0 };
                const compliance = calculateCompliance(prodData.venta, prodData.meta);
                
                let cumpColor = 'var(--danger)';
                if (compliance >= 95) cumpColor = 'var(--accent)';
                
                const isFirst = index === 0;
                const isLast = index === displayedProducts.length - 1;
                const cellClasses = `product-cell ${isFirst ? 'product-cell-first' : ''} ${isLast ? 'product-cell-last' : ''}`;
                
                siteRowHtml += `
                    <td class="num-col ${cellClasses}">${formatProductValue(prodData.venta, prod)}</td>
                    <td class="num-col ${cellClasses}" style="color:var(--text-muted);">${formatProductValue(prodData.meta, prod)}</td>
                    <td class="num-col ${cellClasses}" style="color: ${cumpColor} !important; font-weight: 600 !important;">${compliance}%</td>
                `;
            });
            
            trSite.innerHTML = siteRowHtml;
            elements.tableBody.appendChild(trSite);
        });
    });
}

// --- DYNAMIC TABLE FILTERS POPULATOR ---

function populateTableFilters(joined) {
    if (!elements.tableFilterPromoter || !elements.productsMultiselectOptions) return;
    
    // 1. Get unique promoters present globally (from loaded distribution)
    const promoters = new Set();
    State.distribution.forEach(d => {
        if (d.promotor) {
            promoters.add(d.promotor);
        }
    });
    
    // Fallback if no distribution loaded yet: use active day's records
    if (promoters.size === 0) {
        joined.forEach(item => {
            if (item.promotor && item.promotor !== 'Sin Promotor') {
                promoters.add(item.promotor);
            }
        });
    }
    
    const sortedPromoters = [...promoters].sort();
    
    // Keep active selection if it's still available in the list
    const currentPromoter = State.tableFilters.promoter;
    elements.tableFilterPromoter.innerHTML = '<option value="">Todos los Promotores</option>';
    
    sortedPromoters.forEach(p => {
        const opt = document.createElement('option');
        opt.value = p;
        opt.textContent = p;
        elements.tableFilterPromoter.appendChild(opt);
    });
    
    if (sortedPromoters.includes(currentPromoter)) {
        elements.tableFilterPromoter.value = currentPromoter;
    } else {
        State.tableFilters.promoter = '';
        elements.tableFilterPromoter.value = '';
    }
    
    // 2. Get unique products present globally (from loaded goals)
    const products = new Set();
    
    // Use the global list of uploaded products if available
    if (State.uploadedProducts && State.uploadedProducts.length > 0) {
        State.uploadedProducts.forEach(p => products.add(ProductNormalizer.normalize(p)));
    } else {
        State.goals.forEach(g => { if (g.producto_excel) products.add(ProductNormalizer.normalize(g.producto_excel)); });
    }
    
    // Fallback to active day's records if no goals are loaded yet
    if (products.size === 0) {
        joined.forEach(item => {
            if (item.producto) {
                products.add(item.producto);
            }
        });
    }
    
    // Final fallback to core standard products if completely empty
    if (products.size === 0) {
        [
            "BALOTO", "BET PLAY", "BILLONARIO NACIONAL", "CHANCE", "CHANCE MILLONARIO", 
            "COLOR LOTO", "DOBLE CHANCE", "MILOTO", "PATA MILLONARIA", "RASPITA",
            "SUPER ASTRO", "GIROS", "RECARGA EN LINEA", "RECAUDOS EMPRESARIALES", "TRANSACCIONES CNB"
        ].forEach(p => products.add(p));
    }
    
    const sortedProducts = [...products].sort();
    
    // Clear list options
    elements.productsMultiselectOptions.innerHTML = '';
    
    // Keep only currently selected products that exist in the active set
    State.tableFilters.products = State.tableFilters.products.filter(p => sortedProducts.includes(p));
    
    sortedProducts.forEach(prod => {
        const optionDiv = document.createElement('div');
        optionDiv.className = 'multiselect-option';
        
        const isChecked = State.tableFilters.products.includes(prod);
        
        optionDiv.innerHTML = `
            <input type="checkbox" id="t-prod-${prod}" value="${prod}" ${isChecked ? 'checked' : ''}>
            <span>${prod}</span>
        `;
        
        // Allow toggling when clicking the option div row
        optionDiv.addEventListener('click', (e) => {
            const cb = optionDiv.querySelector('input');
            if (e.target !== cb) {
                cb.checked = !cb.checked;
            }
            handleProductCheckboxChange(cb.value, cb.checked);
        });
        
        elements.productsMultiselectOptions.appendChild(optionDiv);
    });
    
    updateMultiselectTriggerText();
}

function handleProductCheckboxChange(product, checked) {
    if (checked) {
        if (!State.tableFilters.products.includes(product)) {
            State.tableFilters.products.push(product);
        }
    } else {
        State.tableFilters.products = State.tableFilters.products.filter(p => p !== product);
    }
    updateMultiselectTriggerText();
    renderTable();
}

function updateMultiselectTriggerText() {
    const selectedCount = State.tableFilters.products.length;
    const btnText = elements.productsMultiselectBtn.querySelector('.trigger-text');
    
    if (selectedCount === 0) {
        btnText.textContent = "Todos los Productos";
    } else if (selectedCount === 1) {
        btnText.textContent = State.tableFilters.products[0];
    } else {
        btnText.textContent = `${selectedCount} Seleccionados`;
    }
}

// --- HELPERS ---

function calculateCompliance(sales, goals) {
    if (goals <= 0) {
        return sales > 0 ? 100 : 0;
    }
    return Math.round((sales / goals) * 100);
}

function formatCurrency(val) {
    return '$' + Math.round(val).toLocaleString('es-CO');
}

function formatProductValue(val, prodName) {
    if (val === undefined || val === null || isNaN(val)) return '0';
    const isCountBased = ["RECAUDOS EMPRESARIALES", "GIROS", "TRANSACCIONES CNB"].includes(prodName);
    if (isCountBased) {
        return Math.round(val).toLocaleString('es-CO');
    }
    return '$' + Math.round(val).toLocaleString('es-CO');
}


function logger(msg) {
    console.log(`[Dashboard] ${msg}`);
}

// --- WHATSAPP PROMOTERS MANAGEMENT ---

// --- WHATSAPP PROMOTERS MANAGEMENT ---

async function loadWhatsAppPromoters() {
    try {
        const res = await fetch(`${API_BASE}/api/whatsapp-promoters`);
        if (!res.ok) throw new Error("Error al obtener promotores");
        State.whatsappPromoters = await res.json();
        renderPromotersList();
        updatePersonnelSidebarCount();
    } catch (e) {
        console.error("Error loading whatsapp promoters:", e);
    }
}

function updatePersonnelSidebarCount() {
    const activePromoters = State.whatsappPromoters.filter(p => p.active === 1).length;
    const activeCoordinators = State.whatsappCoordinators ? State.whatsappCoordinators.filter(c => c.active === 1).length : 0;
    const activeAdministrators = State.whatsappAdministrators ? State.whatsappAdministrators.filter(a => a.active === 1).length : 0;
    const badge = document.querySelector('.promoters-whatsapp-section .section-desc');
    if (badge) {
        badge.innerHTML = `Autorizados: ${activePromoters} Promotores, ${activeCoordinators} Coordinadores y ${activeAdministrators} Administradores activos.`;
    }
}


// --- WHATSAPP COORDINATORS MANAGEMENT ---

async function loadWhatsAppCoordinators() {
    try {
        const res = await fetch(`${API_BASE}/api/whatsapp-coordinators`);
        if (!res.ok) throw new Error("Error al obtener coordinadores");
        State.whatsappCoordinators = await res.json();
        renderCoordinatorsList();
        updatePersonnelSidebarCount();
    } catch (e) {
        console.error("Error loading whatsapp coordinators:", e);
    }
}

function renderCoordinatorsList() {
    if (!elements.coordinatorsListBody) return;
    
    const searchVal = elements.searchCoordinators.value.toLowerCase().trim();
    
    const filtered = State.whatsappCoordinators.filter(c => {
        return (
            (c.name && c.name.toLowerCase().includes(searchVal)) || 
            (c.cedula && c.cedula.toLowerCase().includes(searchVal)) || 
            (c.role && c.role.toLowerCase().includes(searchVal)) || 
            (c.zone && c.zone.toLowerCase().includes(searchVal)) || 
            (c.phone && c.phone.toLowerCase().includes(searchVal))
        );
    });
    
    if (filtered.length === 0) {
        elements.coordinatorsListBody.innerHTML = `
            <tr>
                <td colspan="7" style="text-align: center; color: var(--text-muted); padding: 20px;">
                    No se encontraron coordinadores.
                </td>
            </tr>
        `;
        return;
    }
    
    elements.coordinatorsListBody.innerHTML = filtered.map(c => `
        <tr data-id="${c.id}">
            <td style="font-weight: 600; color: var(--text-primary);">${c.name}</td>
            <td>${c.cedula}</td>
            <td>${c.role}</td>
            <td><span class="badge" style="background: rgba(15,37,64,0.08); padding: 4px 8px; border-radius: 6px;">${c.zone}</span></td>
            <td>${c.phone}</td>
            <td style="text-align: center;">
                <label class="switch">
                    <input type="checkbox" class="toggle-coordinator-active" ${c.active === 1 ? 'checked' : ''}>
                    <span class="slider"></span>
                </label>
            </td>
            <td style="text-align: center;">
                <button class="btn-icon btn-icon-edit btn-edit-coordinator" title="Editar"><i class="fa-solid fa-pen"></i></button>
                <button class="btn-icon btn-icon-delete btn-delete-coordinator" title="Eliminar"><i class="fa-solid fa-trash-can"></i></button>
            </td>
        </tr>
    `).join('');
    
    // Add event listeners to the list
    elements.coordinatorsListBody.querySelectorAll('.toggle-coordinator-active').forEach(checkbox => {
        checkbox.addEventListener('change', async (e) => {
            const tr = e.target.closest('tr');
            const cid = parseInt(tr.dataset.id);
            const coordinator = State.whatsappCoordinators.find(c => c.id === cid);
            if (coordinator) {
                const newActive = e.target.checked ? 1 : 0;
                // Visual feedback: disable checkbox and fade the row
                checkbox.disabled = true;
                tr.style.opacity = '0.5';
                const slider = checkbox.nextElementSibling;
                if (slider) slider.style.filter = 'grayscale(1) opacity(0.5)';
                
                await saveCoordinatorStatus(cid, { ...coordinator, active: newActive });
            }
        });
    });
    
    elements.coordinatorsListBody.querySelectorAll('.btn-edit-coordinator').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const tr = e.target.closest('tr');
            const cid = parseInt(tr.dataset.id);
            const coordinator = State.whatsappCoordinators.find(c => c.id === cid);
            if (coordinator) {
                startEditCoordinator(coordinator);
            }
        });
    });

    elements.coordinatorsListBody.querySelectorAll('.btn-delete-coordinator').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            const tr = e.target.closest('tr');
            const cid = parseInt(tr.dataset.id);
            const coordinator = State.whatsappCoordinators.find(c => c.id === cid);
            if (coordinator && confirm(`¿Estás seguro de eliminar al coordinador ${coordinator.name}?`)) {
                await deleteCoordinatorRequest(cid);
            }
        });
    });
}

function startEditCoordinator(coordinator) {
    elements.coordinatorEditId.value = coordinator.id;
    elements.coordinatorName.value = coordinator.name;
    elements.coordinatorCedula.value = coordinator.cedula;
    elements.coordinatorRole.value = coordinator.role;
    elements.coordinatorPhone.value = coordinator.phone;
    elements.coordinatorZone.value = coordinator.zone;
    elements.coordinatorFormTitle.textContent = "Editar Coordinador: " + coordinator.name;
    elements.btnCancelCoordinatorEdit.style.display = "inline-block";
    elements.coordinatorName.focus();
}

function resetCoordinatorForm() {
    elements.coordinatorEditId.value = "";
    elements.formCoordinator.reset();
    elements.coordinatorFormTitle.textContent = "Agregar Nuevo Coordinador";
    elements.btnCancelCoordinatorEdit.style.display = "none";
}

async function saveCoordinatorStatus(cid, coordinatorData) {
    try {
        const res = await fetch(`${API_BASE}/api/whatsapp-coordinators/${cid}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(coordinatorData)
        });
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Error al actualizar");
        }
        await loadWhatsAppCoordinators();
    } catch (e) {
        alert("Error al actualizar coordinador: " + e.message);
        loadWhatsAppCoordinators(); // reload to reset UI checkbox
    }
}

async function deleteCoordinatorRequest(cid) {
    try {
        const res = await fetch(`${API_BASE}/api/whatsapp-coordinators/${cid}`, {
            method: 'DELETE'
        });
        if (!res.ok) throw new Error("Error al eliminar");
        await loadWhatsAppCoordinators();
    } catch (e) {
        alert("Error al eliminar coordinador: " + e.message);
    }
}

function setupCoordinatorManagement() {
    if (!elements.btnManageCoordinators) return;
    
    // Toggle modal visibility
    elements.btnManageCoordinators.addEventListener('click', () => {
        elements.modalCoordinators.style.display = 'flex';
        loadWhatsAppCoordinators();
    });
    
    elements.btnCloseCoordinatorsModal.addEventListener('click', () => {
        elements.modalCoordinators.style.display = 'none';
        resetCoordinatorForm();
    });
    
    // Close on click outside modal content
    elements.modalCoordinators.addEventListener('click', (e) => {
        if (e.target === elements.modalCoordinators) {
            elements.modalCoordinators.style.display = 'none';
            resetCoordinatorForm();
        }
    });
    
    // Search filter
    elements.searchCoordinators.addEventListener('input', () => {
        renderCoordinatorsList();
    });
    
    // Form submit
    elements.formCoordinator.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const cid = elements.coordinatorEditId.value;
        const name = elements.coordinatorName.value;
        const cedula = elements.coordinatorCedula.value;
        const role = elements.coordinatorRole.value;
        const phone = elements.coordinatorPhone.value;
        const zone = elements.coordinatorZone.value;
        
        const payload = { name, cedula, role, phone, zone, active: 1 };
        
        const submitBtn = elements.formCoordinator.querySelector('button[type="submit"]');
        const originalText = submitBtn.innerHTML;
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Guardando...';
        
        try {
            let url = `${API_BASE}/api/whatsapp-coordinators`;
            let method = 'POST';
            
            if (cid) {
                // We are editing. Find existing to preserve active status.
                const existing = State.whatsappCoordinators.find(c => c.id === parseInt(cid));
                payload.active = existing ? existing.active : 1;
                url = `${url}/${cid}`;
                method = 'PUT';
            }
            
            const res = await fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            
            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || "Error al guardar");
            }
            
            resetCoordinatorForm();
            await loadWhatsAppCoordinators();
        } catch (e) {
            alert("Error al guardar coordinador: " + e.message);
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalText;
        }
    });
    
    elements.btnCancelCoordinatorEdit.addEventListener('click', () => {
        resetCoordinatorForm();
    });
    
    // Load counts initially
    loadWhatsAppCoordinators();
}

// --- WHATSAPP ADMINISTRATORS MANAGEMENT ---

async function loadWhatsAppAdministrators() {
    try {
        const res = await fetch(`${API_BASE}/api/whatsapp-administrators`);
        if (!res.ok) throw new Error("Error al obtener administradores");
        State.whatsappAdministrators = await res.json();
        renderAdministratorsList();
        updatePersonnelSidebarCount();
    } catch (e) {
        console.error("Error loading whatsapp administrators:", e);
    }
}

function renderAdministratorsList() {
    if (!elements.administratorsListBody) return;
    
    const searchVal = elements.searchAdministrators.value.toLowerCase().trim();
    
    const filtered = State.whatsappAdministrators.filter(a => {
        return (
            (a.name && a.name.toLowerCase().includes(searchVal)) || 
            (a.cedula && a.cedula.toLowerCase().includes(searchVal)) || 
            (a.phone && a.phone.toLowerCase().includes(searchVal))
        );
    });
    
    if (filtered.length === 0) {
        elements.administratorsListBody.innerHTML = `
            <tr>
                <td colspan="5" style="text-align: center; color: var(--text-muted); padding: 20px;">
                    No se encontraron administradores.
                </td>
            </tr>
        `;
        return;
    }
    
    elements.administratorsListBody.innerHTML = filtered.map(a => `
        <tr data-id="${a.id}">
            <td style="font-weight: 600; color: var(--text-primary);">${a.name}</td>
            <td>${a.cedula}</td>
            <td>${a.phone}</td>
            <td style="text-align: center;">
                <label class="switch">
                    <input type="checkbox" class="toggle-administrator-active" ${a.active === 1 ? 'checked' : ''}>
                    <span class="slider"></span>
                </label>
            </td>
            <td style="text-align: center;">
                <button class="btn-icon btn-icon-edit btn-edit-administrator" title="Editar"><i class="fa-solid fa-pen"></i></button>
                <button class="btn-icon btn-icon-delete btn-delete-administrator" title="Eliminar"><i class="fa-solid fa-trash-can"></i></button>
            </td>
        </tr>
    `).join('');
    
    // Add event listeners to the list
    elements.administratorsListBody.querySelectorAll('.toggle-administrator-active').forEach(checkbox => {
        checkbox.addEventListener('change', async (e) => {
            const tr = e.target.closest('tr');
            const aid = parseInt(tr.dataset.id);
            const administrator = State.whatsappAdministrators.find(a => a.id === aid);
            if (administrator) {
                const newActive = e.target.checked ? 1 : 0;
                checkbox.disabled = true;
                tr.style.opacity = '0.5';
                const slider = checkbox.nextElementSibling;
                if (slider) slider.style.filter = 'grayscale(1) opacity(0.5)';
                
                await saveAdministratorStatus(aid, { ...administrator, active: newActive });
            }
        });
    });
    
    elements.administratorsListBody.querySelectorAll('.btn-edit-administrator').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const tr = e.target.closest('tr');
            const aid = parseInt(tr.dataset.id);
            const administrator = State.whatsappAdministrators.find(a => a.id === aid);
            if (administrator) {
                startEditAdministrator(administrator);
            }
        });
    });

    elements.administratorsListBody.querySelectorAll('.btn-delete-administrator').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            const tr = e.target.closest('tr');
            const aid = parseInt(tr.dataset.id);
            const administrator = State.whatsappAdministrators.find(a => a.id === aid);
            if (administrator && confirm(`¿Estás seguro de eliminar al administrador ${administrator.name}?`)) {
                await deleteAdministratorRequest(aid);
            }
        });
    });
}

function startEditAdministrator(administrator) {
    elements.administratorEditId.value = administrator.id;
    elements.administratorName.value = administrator.name;
    elements.administratorCedula.value = administrator.cedula;
    elements.administratorPhone.value = administrator.phone;
    elements.administratorFormTitle.textContent = "Editar Administrador: " + administrator.name;
    elements.btnCancelAdministratorEdit.style.display = "inline-block";
    elements.administratorName.focus();
}

function resetAdministratorForm() {
    elements.administratorEditId.value = "";
    elements.formAdministrator.reset();
    elements.administratorFormTitle.textContent = "Agregar Nuevo Administrador";
    elements.btnCancelAdministratorEdit.style.display = "none";
}

async function saveAdministratorStatus(aid, administratorData) {
    try {
        const res = await fetch(`${API_BASE}/api/whatsapp-administrators/${aid}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(administratorData)
        });
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Error al actualizar");
        }
        await loadWhatsAppAdministrators();
    } catch (e) {
        alert("Error al actualizar administrador: " + e.message);
        loadWhatsAppAdministrators();
    }
}

async function deleteAdministratorRequest(aid) {
    try {
        const res = await fetch(`${API_BASE}/api/whatsapp-administrators/${aid}`, {
            method: 'DELETE'
        });
        if (!res.ok) throw new Error("Error al eliminar");
        await loadWhatsAppAdministrators();
    } catch (e) {
        alert("Error al eliminar administrador: " + e.message);
    }
}

function setupAdministratorManagement() {
    if (!elements.btnManageAdministrators) return;
    
    // Toggle modal visibility
    elements.btnManageAdministrators.addEventListener('click', () => {
        elements.modalAdministrators.style.display = 'flex';
        loadWhatsAppAdministrators();
    });
    
    elements.btnCloseAdministratorsModal.addEventListener('click', () => {
        elements.modalAdministrators.style.display = 'none';
        resetAdministratorForm();
    });
    
    // Close on click outside modal content
    elements.modalAdministrators.addEventListener('click', (e) => {
        if (e.target === elements.modalAdministrators) {
            elements.modalAdministrators.style.display = 'none';
            resetAdministratorForm();
        }
    });
    
    // Search filter
    elements.searchAdministrators.addEventListener('input', () => {
        renderAdministratorsList();
    });
    
    // Form submit
    elements.formAdministrator.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const aid = elements.administratorEditId.value;
        const name = elements.administratorName.value;
        const cedula = elements.administratorCedula.value;
        const phone = elements.administratorPhone.value;
        
        const payload = { name, cedula, phone, active: 1 };
        
        const submitBtn = elements.formAdministrator.querySelector('button[type="submit"]');
        const originalText = submitBtn.innerHTML;
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Guardando...';
        
        try {
            let url = `${API_BASE}/api/whatsapp-administrators`;
            let method = 'POST';
            
            if (aid) {
                const existing = State.whatsappAdministrators.find(a => a.id === parseInt(aid));
                payload.active = existing ? existing.active : 1;
                url = `${url}/${aid}`;
                method = 'PUT';
            }
            
            const res = await fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            
            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || "Error al guardar");
            }
            
            resetAdministratorForm();
            await loadWhatsAppAdministrators();
        } catch (e) {
            alert("Error al guardar administrador: " + e.message);
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalText;
        }
    });
    
    elements.btnCancelAdministratorEdit.addEventListener('click', () => {
        resetAdministratorForm();
    });
    
    // Load counts initially
    loadWhatsAppAdministrators();
}

function renderPromotersList() {
    if (!elements.promotersListBody) return;
    
    const searchVal = elements.searchPromoters.value.toLowerCase().trim();
    
    const filtered = State.whatsappPromoters.filter(p => {
        return (
            (p.name && p.name.toLowerCase().includes(searchVal)) || 
            (p.phone && p.phone.toLowerCase().includes(searchVal)) || 
            (p.zone && p.zone.toLowerCase().includes(searchVal))
        );
    });
    
    if (filtered.length === 0) {
        elements.promotersListBody.innerHTML = `
            <tr>
                <td colspan="5" style="text-align: center; color: var(--text-muted); padding: 20px;">
                    No se encontraron promotores.
                </td>
            </tr>
        `;
        return;
    }
    
    elements.promotersListBody.innerHTML = filtered.map(p => `
        <tr data-id="${p.id}">
            <td style="font-weight: 600; color: var(--text-primary);">${p.name}</td>
            <td>${p.phone}</td>
            <td><span class="badge" style="background: rgba(15,37,64,0.08); padding: 4px 8px; border-radius: 6px;">${p.zone}</span></td>
            <td style="text-align: center;">
                <label class="switch">
                    <input type="checkbox" class="toggle-active" ${p.active === 1 ? 'checked' : ''}>
                    <span class="slider"></span>
                </label>
            </td>
            <td style="text-align: center;">
                <button class="btn-icon btn-icon-edit btn-edit-promoter" title="Editar"><i class="fa-solid fa-pen"></i></button>
                <button class="btn-icon btn-icon-delete btn-delete-promoter" title="Eliminar"><i class="fa-solid fa-trash-can"></i></button>
            </td>
        </tr>
    `).join('');
    
    // Add event listeners to the list
    elements.promotersListBody.querySelectorAll('.toggle-active').forEach(checkbox => {
        checkbox.addEventListener('change', async (e) => {
            const tr = e.target.closest('tr');
            const pid = parseInt(tr.dataset.id);
            const promoter = State.whatsappPromoters.find(p => p.id === pid);
            if (promoter) {
                const newActive = e.target.checked ? 1 : 0;
                // Visual feedback: disable checkbox and fade the row
                checkbox.disabled = true;
                tr.style.opacity = '0.5';
                const slider = checkbox.nextElementSibling;
                if (slider) slider.style.filter = 'grayscale(1) opacity(0.5)';
                
                await savePromoterStatus(pid, { ...promoter, active: newActive });
            }
        });
    });
    
    elements.promotersListBody.querySelectorAll('.btn-edit-promoter').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const tr = e.target.closest('tr');
            const pid = parseInt(tr.dataset.id);
            const promoter = State.whatsappPromoters.find(p => p.id === pid);
            if (promoter) {
                startEditPromoter(promoter);
            }
        });
    });

    elements.promotersListBody.querySelectorAll('.btn-delete-promoter').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            const tr = e.target.closest('tr');
            const pid = parseInt(tr.dataset.id);
            const promoter = State.whatsappPromoters.find(p => p.id === pid);
            if (promoter && confirm(`¿Estás seguro de eliminar a ${promoter.name}?`)) {
                await deletePromoterRequest(pid);
            }
        });
    });
}

function startEditPromoter(promoter) {
    elements.promoterEditId.value = promoter.id;
    elements.promoterName.value = promoter.name;
    elements.promoterPhone.value = promoter.phone;
    elements.promoterZone.value = promoter.zone;
    elements.promoterFormTitle.textContent = "Editar Promotor: " + promoter.name;
    elements.btnCancelEdit.style.display = "inline-block";
    elements.promoterName.focus();
}

function resetPromoterForm() {
    elements.promoterEditId.value = "";
    elements.formPromoter.reset();
    elements.promoterFormTitle.textContent = "Agregar Nuevo Promotor";
    elements.btnCancelEdit.style.display = "none";
}

async function savePromoterStatus(pid, promoterData) {
    try {
        const res = await fetch(`${API_BASE}/api/whatsapp-promoters/${pid}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(promoterData)
        });
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Error al actualizar");
        }
        await loadWhatsAppPromoters();
    } catch (e) {
        alert("Error al actualizar promotor: " + e.message);
        loadWhatsAppPromoters(); // reload to reset UI checkbox
    }
}

async function deletePromoterRequest(pid) {
    try {
        const res = await fetch(`${API_BASE}/api/whatsapp-promoters/${pid}`, {
            method: 'DELETE'
        });
        if (!res.ok) throw new Error("Error al eliminar");
        await loadWhatsAppPromoters();
    } catch (e) {
        alert("Error al eliminar promotor: " + e.message);
    }
}

function setupPromoterManagement() {
    if (!elements.btnManagePromoters) return;
    
    // Toggle modal visibility
    elements.btnManagePromoters.addEventListener('click', () => {
        elements.modalPromoters.style.display = 'flex';
        loadWhatsAppPromoters();
    });
    
    elements.btnClosePromotersModal.addEventListener('click', () => {
        elements.modalPromoters.style.display = 'none';
        resetPromoterForm();
    });
    
    // Close on click outside modal content
    elements.modalPromoters.addEventListener('click', (e) => {
        if (e.target === elements.modalPromoters) {
            elements.modalPromoters.style.display = 'none';
            resetPromoterForm();
        }
    });
    
    // Search filter
    elements.searchPromoters.addEventListener('input', () => {
        renderPromotersList();
    });
    
    elements.formPromoter.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const pid = elements.promoterEditId.value;
        const name = elements.promoterName.value;
        const phone = elements.promoterPhone.value;
        const zone = elements.promoterZone.value;
        
        const payload = { name, phone, zone, active: 1 };
        
        const submitBtn = elements.formPromoter.querySelector('button[type="submit"]');
        const originalText = submitBtn.innerHTML;
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Guardando...';
        
        try {
            let url = `${API_BASE}/api/whatsapp-promoters`;
            let method = 'POST';
            
            if (pid) {
                // We are editing. Find existing to preserve active status.
                const existing = State.whatsappPromoters.find(p => p.id === parseInt(pid));
                payload.active = existing ? existing.active : 1;
                url = `${url}/${pid}`;
                method = 'PUT';
            }
            
            const res = await fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            
            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || "Error al guardar");
            }
            
            resetPromoterForm();
            await loadWhatsAppPromoters();
        } catch (e) {
            alert("Error al guardar promotor: " + e.message);
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalText;
        }
    });
    
    elements.btnCancelEdit.addEventListener('click', () => {
        resetPromoterForm();
    });
    
    // Load counts initially
    loadWhatsAppPromoters();
}

function setupGoalsManagement() {
    if (!elements.badgeMetas) return;
    
    // Clicking the loaded badge opens the goals management modal
    elements.badgeMetas.addEventListener('click', (e) => {
        e.stopPropagation(); // Prevent opening file chooser!
        openGoalsModal();
    });
    
    if (elements.btnCloseGoalsModal) {
        elements.btnCloseGoalsModal.addEventListener('click', () => {
            elements.modalGoals.style.display = 'none';
        });
    }
    
    if (elements.modalGoals) {
        elements.modalGoals.addEventListener('click', (e) => {
            if (e.target === elements.modalGoals) {
                elements.modalGoals.style.display = 'none';
            }
        });
    }
}

async function openGoalsModal() {
    elements.modalGoals.style.display = 'flex';
    await loadModalGoalsList();
}

async function loadModalGoalsList() {
    try {
        const res = await fetch(`${API_BASE}/api/metas/products?t=${new Date().getTime()}`);
        if (!res.ok) throw new Error("No se pudo cargar la lista de productos");
        const products = await res.json();
        
        // Sort products alphabetically
        products.sort((a, b) => a.producto.localeCompare(b.producto));
        
        renderModalGoalsList(products);
    } catch (e) {
        console.error("Error loading goals products list:", e);
        elements.goalsListBody.innerHTML = `<tr><td colspan="3" style="text-align:center;color:red;">Error al cargar la lista: ${e.message}</td></tr>`;
    }
}

function renderModalGoalsList(products) {
    elements.goalsListBody.innerHTML = '';
    
    if (products.length === 0) {
        elements.goalsListBody.innerHTML = `<tr><td colspan="3" style="text-align:center;color:var(--text-muted);padding: 20px;">No hay metas cargadas.</td></tr>`;
        return;
    }
    
    products.forEach(p => {
        const tr = document.createElement('tr');
        
        // 1. Product Name
        const tdName = document.createElement('td');
        tdName.style.fontWeight = '600';
        tdName.style.padding = '12px 8px';
        tdName.textContent = p.producto;
        tr.appendChild(tdName);
        
        // 2. Status Badge / Toggle Button
        const tdStatus = document.createElement('td');
        tdStatus.style.textAlign = 'center';
        tdStatus.style.padding = '12px 8px';
        
        const btnToggle = document.createElement('button');
        btnToggle.className = p.activo ? 'status-badge active' : 'status-badge inactive';
        btnToggle.style.border = 'none';
        btnToggle.style.cursor = 'pointer';
        btnToggle.style.borderRadius = '20px';
        btnToggle.style.padding = '4px 12px';
        btnToggle.style.fontSize = '11px';
        btnToggle.style.fontWeight = 'bold';
        btnToggle.style.outline = 'none';
        btnToggle.style.transition = 'all 0.2s';
        
        if (p.activo) {
            btnToggle.textContent = 'Activo';
            btnToggle.style.background = 'rgba(16, 185, 129, 0.1)';
            btnToggle.style.color = '#10b981';
            btnToggle.style.border = '1px solid rgba(16, 185, 129, 0.3)';
        } else {
            btnToggle.textContent = 'Inactivo';
            btnToggle.style.background = 'rgba(239, 68, 68, 0.1)';
            btnToggle.style.color = '#ef4444';
            btnToggle.style.border = '1px solid rgba(239, 68, 68, 0.3)';
        }
        
        btnToggle.addEventListener('click', async () => {
            // Visual loading state
            btnToggle.disabled = true;
            const originalText = btnToggle.textContent;
            btnToggle.textContent = 'Guardando...';
            btnToggle.style.opacity = '0.6';
            
            console.log("Toggle clicked for:", p.producto, "current status:", p.activo);
            try {
                const res = await fetch(`${API_BASE}/api/metas/toggle`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ producto: p.producto, activo: !p.activo })
                });
                console.log("Response status:", res.status);
                if (!res.ok) {
                    const errText = await res.text();
                    throw new Error("HTTP " + res.status + ": " + errText);
                }
                const data = await res.json();
                console.log("Response data:", data);
                
                // Refresh list first
                await loadModalGoalsList();
                
                // Refresh dashboard background stats in parallel
                checkStatus();
                loadUploadedState();
            } catch (err) {
                console.error("Toggle error:", err);
                alert("Error al cambiar estado: " + err.message);
                
                // Re-enable if failed
                btnToggle.disabled = false;
                btnToggle.textContent = originalText;
                btnToggle.style.opacity = '1';
            }
        });
        
        tdStatus.appendChild(btnToggle);
        tr.appendChild(tdStatus);
        
        // 4. Delete Action Button
        const tdAction = document.createElement('td');
        tdAction.style.textAlign = 'center';
        tdAction.style.padding = '12px 8px';
        
        const btnDelete = document.createElement('button');
        btnDelete.className = 'btn-action-delete';
        btnDelete.style.background = 'none';
        btnDelete.style.border = 'none';
        btnDelete.style.color = '#ef4444';
        btnDelete.style.cursor = 'pointer';
        btnDelete.style.fontSize = '14px';
        btnDelete.style.padding = '4px 8px';
        btnDelete.style.transition = 'all 0.2s';
        btnDelete.innerHTML = '<i class="fa-solid fa-trash-can"></i>';
        btnDelete.title = "Eliminar metas de este producto";
        
        btnDelete.addEventListener('mouseenter', () => btnDelete.style.transform = 'scale(1.2)');
        btnDelete.addEventListener('mouseleave', () => btnDelete.style.transform = 'scale(1)');
        
        btnDelete.addEventListener('click', async () => {
            if (confirm(`¿Estás seguro de que deseas eliminar permanentemente todas las metas del producto "${p.producto}"?`)) {
                // Visual loading state
                btnDelete.disabled = true;
                btnDelete.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
                
                try {
                    const res = await fetch(`${API_BASE}/api/metas/product/${encodeURIComponent(p.producto)}`, {
                        method: 'DELETE'
                    });
                    if (!res.ok) throw new Error("Error al eliminar");
                    
                    // Refresh list first
                    await loadModalGoalsList();
                    
                    // Refresh dashboard background stats in parallel
                    checkStatus();
                    loadUploadedState();
                } catch (err) {
                    alert("Error al eliminar: " + err.message);
                    btnDelete.disabled = false;
                    btnDelete.innerHTML = '<i class="fa-solid fa-trash-can"></i>';
                }
            }
        });
        
        tdAction.appendChild(btnDelete);
        tr.appendChild(tdAction);
        
        elements.goalsListBody.appendChild(tr);
    });
}
