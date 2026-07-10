const formatNum = (num) => {
    if (num === null || num === undefined) return "0";
    return Math.round(num).toLocaleString('es-CO');
};

const formatPct = (num) => {
    if (num === null || num === undefined) return "0,00 %";
    return num.toLocaleString('es-CO', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + " %";
};

const getPctHtml = (num) => {
    const classBg = num >= 100 ? 'bg-green' : 'bg-red';
    return `<span class="percent-box ${classBg}">${formatPct(num)}</span>`;
};

const getDiffHtml = (num) => {
    const classTxt = num < 0 ? 'text-red' : '';
    return `<span class="${classTxt}">${formatNum(num)}</span>`;
};

async function loadData() {
    const urlParams = new URLSearchParams(window.location.search);
    const dateParam = urlParams.get('date');
    const endpoint = dateParam ? `/api/compliance/data?date=${dateParam}` : `/api/compliance/data`;

    try {
        const response = await fetch(endpoint);
        const data = await response.json();
        
        document.getElementById('report-date').textContent = data.date.split('-').reverse().join('/');
        
        const tbody = document.getElementById('table-body');
        tbody.innerHTML = '';

        data.groups.forEach((g3) => {
            let totalProducts = 0;
            g3.products.forEach(p => totalProducts += p.items.length);

            g3.products.forEach((prod, pIndex) => {
                prod.items.forEach((item, iIndex) => {
                    const tr = document.createElement('tr');
                    
                    // Group 3 Col
                    if (pIndex === 0 && iIndex === 0) {
                        const td = document.createElement('td');
                        td.className = 'g3-col';
                        td.rowSpan = totalProducts;
                        td.innerHTML = `<span class="expander">[-]</span> ${g3.name}`;
                        tr.appendChild(td);
                    }
                    
                    // Product Col
                    if (iIndex === 0) {
                        const td = document.createElement('td');
                        td.className = 'prod-col';
                        td.rowSpan = prod.items.length;
                        td.innerHTML = `<span class="expander">[-]</span> ${prod.name}`;
                        tr.appendChild(td);
                    }
                    
                    // Group 1 Col (Item)
                    const tdItem = document.createElement('td');
                    tdItem.className = 'g1-col';
                    tdItem.innerHTML = `<span class="expander">[+]</span> ${item.name}`;
                    tr.appendChild(tdItem);
                    
                    // Values
                    const values = [
                        formatNum(item.presupuesto_dia),
                        formatNum(item.ejecutado_dia),
                        getPctHtml(item.cump_dia),
                        getDiffHtml(item.dif_cump_dia),
                        getDiffHtml(item.dif_acum),
                        getPctHtml(item.cump_acum),
                        formatNum(item.presupuesto_dia_actual)
                    ];
                    
                    values.forEach(v => {
                        const td = document.createElement('td');
                        td.className = 'val-col';
                        td.innerHTML = v;
                        tr.appendChild(td);
                    });
                    
                    tbody.appendChild(tr);
                });
            });
        });
        
    } catch (error) {
        console.error("Error loading data:", error);
        document.getElementById('table-body').innerHTML = '<tr><td colspan="10" align="center">Error cargando datos.</td></tr>';
    }
}

// Load data when page loads
document.addEventListener('DOMContentLoaded', loadData);
