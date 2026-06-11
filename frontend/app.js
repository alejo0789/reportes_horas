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

    // Goals Management Modal
    modalGoals: document.getElementById('modal-goals'),
    btnCloseGoalsModal: document.getElementById('btn-close-goals-modal'),
    goalsListBody: document.getElementById('goals-list-body')
};

// --- INITIALIZATION ---
document.addEventListener('DOMContentLoaded', async () => {
    setupUploadHandlers();
    setupFilterListeners();
    setupRefreshHandlers();
    setupTreeControls();
    setupPromoterManagement();
    setupCoordinatorManagement();
    setupGoalsManagement();
    
    // Load initial data
    await checkStatus();
    await loadInitialCatalogues();
    await loadUploadedState();
});

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
    elements.updateTimestamp.style.color = '#94a3b8';
    
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
        totalSales += item.venta;
        totalGoals += item.meta;
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
                    backgroundColor: 'rgba(6, 182, 212, 0.65)',
                    borderColor: '#06b6d4',
                    borderWidth: 1,
                    borderRadius: 4,
                    order: 2
                },
                {
                    label: 'Meta Prorrateada ($)',
                    data: goalPerHour,
                    type: 'line',
                    borderColor: '#6366f1',
                    borderWidth: 3,
                    pointBackgroundColor: '#6366f1',
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
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: {
                        color: '#94a3b8',
                        callback: value => '$' + value.toLocaleString()
                    }
                },
                x: {
                    grid: { display: false },
                    ticks: { color: '#94a3b8' }
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
                datasets: [{ data: [1], backgroundColor: ['rgba(255,255,255,0.05)'], borderWidth: 0 }]
            },
            options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } }
        });
        return;
    }

    const colors = [
        'rgba(99, 102, 241, 0.7)',  // Indigo
        'rgba(6, 182, 212, 0.7)',   // Cyan
        'rgba(16, 185, 129, 0.7)',  // Emerald
        'rgba(245, 158, 11, 0.7)',  // Amber
        'rgba(239, 68, 68, 0.7)',   // Red
        'rgba(168, 85, 247, 0.7)'   // Purple
    ];

    State.charts.product = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: dataset,
                backgroundColor: colors.slice(0, labels.length),
                borderWidth: 1,
                borderColor: 'rgba(255, 255, 255, 0.1)'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { color: '#94a3b8', boxWidth: 12, font: { family: 'Outfit', size: 11 } }
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
                datasets: [{ data: [0], backgroundColor: ['rgba(255,255,255,0.05)'] }]
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
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: {
                        color: '#94a3b8',
                        callback: value => value + '%'
                    },
                    max: Math.max(100, ...dataset) // dynamic max scale
                },
                y: {
                    grid: { display: false },
                    ticks: { color: '#94a3b8', font: { family: 'Outfit', size: 10 } }
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
                datasets: [{ data: [0], backgroundColor: ['rgba(255,255,255,0.05)'] }]
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
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: {
                        color: '#94a3b8',
                        callback: value => value + '%'
                    },
                    max: 100 // keep it scaled up to 100% since they are lagging
                },
                y: {
                    grid: { display: false },
                    ticks: { color: '#94a3b8', font: { family: 'Outfit', size: 10 } }
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
                    <span style="color:#ffffff; font-weight: 600;">${office.oficina}</span>
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
                        <span style="color:#ffffff; font-weight: 500;">${site.sitio_venta}</span>
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
    const badge = document.querySelector('.promoters-whatsapp-section .section-desc');
    if (badge) {
        badge.innerHTML = `Autorizados: ${activePromoters} Promotores y ${activeCoordinators} Coordinadores activos.`;
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
            <td style="font-weight: 600; color: #ffffff;">${c.name}</td>
            <td>${c.cedula}</td>
            <td>${c.role}</td>
            <td><span class="badge" style="background: rgba(255,255,255,0.05); padding: 4px 8px; border-radius: 6px;">${c.zone}</span></td>
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
            <td style="font-weight: 600; color: #ffffff;">${p.name}</td>
            <td>${p.phone}</td>
            <td><span class="badge" style="background: rgba(255,255,255,0.05); padding: 4px 8px; border-radius: 6px;">${p.zone}</span></td>
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
