/* --- 1. SHARED STORAGE HELPERS --- */
window.registerGlobalItem = function(category, name, page) {
    let registry = JSON.parse(localStorage.getItem('crm_search_index') || '[]');
    if (!registry.find(item => item.display === name)) {
        registry.push({ keyword: name.toLowerCase(), display: name, category: category, page: page });
        localStorage.setItem('crm_search_index', JSON.stringify(registry));
    }
};

/* --- NEW: AUTO-INDEXER (Scans page for content) --- */
function autoIndexPage() {
    const pageId = document.body.id;
    if (pageId === 'page-scoring') {
        document.querySelectorAll('#ruleTable tr td:first-child').forEach(td => {
            window.registerGlobalItem("Rule", td.innerText, "lead-scoring.html");
        });
    }
    if (pageId === 'page-customers') {
        document.querySelectorAll('.customer-item strong').forEach(el => {
            window.registerGlobalItem("Customer", el.innerText, "customer-list.html");
        });
    }
}

/* --- 2. DASHBOARD & METRICS LOGIC --- */
const availableMetrics = {
    leads_7d: { label: "Highest Leads (Past 7 Days)", value: "156", color: "var(--blue)" },
    usage_ratio: { label: "Bot Usage : Engagement Ratio", value: "4.2 : 1", color: "var(--green)" },
    chat_summary: { label: "Latest Customer Chats", value: "3 New / 2 Pending", color: "var(--slate-900)" },
    total_cust: { label: "Total Customers", value: "1,284", color: "var(--slate-900)" },
    total_chats: { label: "Total Conversations", value: "5,421", color: "var(--slate-900)" },
    open_inq: { label: "Open Inquiries", value: "37", color: "var(--red)" },
    high_leads: { label: "High-Value Leads", value: "92", color: "var(--green)" }
};

let currentLayout = JSON.parse(localStorage.getItem('dash_layout')) || ['leads_7d', 'usage_ratio', 'chat_summary', 'high_leads'];

function renderDashboard() {
    const container = document.getElementById('metricsContainer');
    if (!container) return; 
    currentLayout.forEach((metricKey, index) => {
        const metric = availableMetrics[metricKey];
        const slot = document.getElementById(`slot-${index}`);
        if (slot) {
            slot.innerHTML = `<h3 style="margin-top:0;font-size:14px;color:var(--gray);">${metric.label}</h3><p style="font-size:28px;margin:10px 0 0;font-weight:700;color:${metric.color}">${metric.value}</p>`;
        }
    });
}

window.openCustomizeModal = function() {
    document.getElementById('configForm').innerHTML = currentLayout.map((key, i) => `
        <div style="margin-bottom:15px;">
            <label style="display:block;font-weight:600;">Slot ${i+1}</label>
            <select id="select-slot-${i}" style="width:100%;padding:8px;">
                ${Object.keys(availableMetrics).map(m => `<option value="${m}" ${m===key?'selected':''}>${availableMetrics[m].label}</option>`).join('')}
            </select>
        </div>`).join('');
    document.getElementById('customizeModal').style.display = 'flex';
};

window.saveDashboardConfig = function() {
    for (let i=0; i<4; i++) { currentLayout[i] = document.getElementById(`select-slot-${i}`).value; }
    localStorage.setItem('dash_layout', JSON.stringify(currentLayout));
    renderDashboard();
    document.getElementById('customizeModal').style.display = 'none';
};

/* --- 3. SEARCH LOGIC --- */
document.addEventListener('input', function (e) {
    if (e.target && e.target.classList.contains('taskbar-search')) {
        const query = e.target.value.toLowerCase();
        
        // Filter Local Content
        document.querySelectorAll('tbody tr, .customer-item, .chat-thread').forEach(item => {
            item.style.display = item.textContent.toLowerCase().includes(query) ? '' : 'none';
        });

        // Show Global Dropdown
        let old = document.getElementById('search-dropdown');
        if (old) old.remove();
        if (query.length < 2) return;

        const registry = JSON.parse(localStorage.getItem('crm_search_index') || '[]');
        const matches = registry.filter(item => item.keyword.includes(query));

        if (matches.length > 0) {
            const dd = document.createElement('div');
            dd.id = 'search-dropdown';
            dd.style = "position:absolute; top:45px; left:0; width:100%; background:white; border:1px solid #ddd; z-index:9999; border-radius:8px; box-shadow:0 4px 10px rgba(0,0,0,0.1);";
            matches.forEach(m => {
                const div = document.createElement('div');
                div.style = "padding:10px; cursor:pointer; border-bottom:1px solid #eee; font-size:13px;";
                div.innerHTML = `<b style="color:var(--blue)">[${m.category}]</b> ${m.display}`;
                div.onclick = () => window.location.href = `${m.page}?find=${encodeURIComponent(m.keyword)}`;
                dd.appendChild(div);
            });
            e.target.parentElement.style.position = 'relative';
            e.target.parentElement.appendChild(dd);
        }
    }
});

/* --- 4. INIT --- */
window.addEventListener('DOMContentLoaded', () => {
    autoIndexPage(); // Scan page for searchable items
    if (document.body.id === 'page-dashboard') renderDashboard();

    const findTerm = new URLSearchParams(window.location.search).get('find');
    if (findTerm) {
        const bar = document.querySelector('.taskbar-search');
        if (bar) { bar.value = findTerm; bar.dispatchEvent(new Event('input')); }
    }
});