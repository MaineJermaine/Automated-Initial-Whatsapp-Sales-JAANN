/* --- 1. SHARED STORAGE HELPERS --- */
window.registerGlobalItem = function(category, name, page) {
    let registry = JSON.parse(localStorage.getItem('crm_search_index') || '[]');
    if (!registry.find(item => item.display === name)) {
        registry.push({ keyword: name.toLowerCase(), display: name, category: category, page: page });
        localStorage.setItem('crm_search_index', JSON.stringify(registry));
    }
};

/* --- AUTO-INDEXER --- */
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
    usage_ratio: { label: "Bot Usage Ratio", value: "4.2 : 1", color: "var(--green)" },
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
            slot.innerHTML = `
                <h3 style="margin-top:0;font-size:12px;color:var(--gray);text-transform:uppercase;letter-spacing:0.05em;">${metric.label}</h3>
                <p style="font-size:24px;margin:10px 0 0;font-weight:700;color:${metric.color}">${metric.value}</p>
            `;
        }
    });
}

// Logic to build the customization form inside the modal
document.getElementById('customizeModal').addEventListener('show.bs.modal', function () {
    const configForm = document.getElementById('configForm');
    configForm.innerHTML = currentLayout.map((key, i) => `
        <div class="form-group">
            <label>Metric Slot ${i+1}</label>
            <select id="select-slot-${i}" class="form-select">
                ${Object.keys(availableMetrics).map(m => `
                    <option value="${m}" ${m===key?'selected':''}>${availableMetrics[m].label}</option>
                `).join('')}
            </select>
        </div>`).join('');
});

window.saveDashboardConfig = function() {
    for (let i=0; i<4; i++) { 
        currentLayout[i] = document.getElementById(`select-slot-${i}`).value; 
    }
    localStorage.setItem('dash_layout', JSON.stringify(currentLayout));
    renderDashboard();
    
    // Bootstrap 5 Modal Close Logic
    const modalEl = document.getElementById('customizeModal');
    const modalInstance = bootstrap.Modal.getInstance(modalEl);
    modalInstance.hide();
};

/* --- 3. IMPROVED GLOBAL SEARCH LOGIC --- */
document.addEventListener('input', function (e) {
    if (e.target && e.target.classList.contains('taskbar-search')) {
        const query = e.target.value.toLowerCase();
        const searchContainer = e.target.parentElement;
        
        // 1. Local Filtering (hides items currently on the screen)
        document.querySelectorAll('tbody tr, .customer-item, .chat-thread, .card').forEach(item => {
            // We skip the search bar itself and containers
            if (item.classList.contains('search-container')) return;
            item.style.display = item.textContent.toLowerCase().includes(query) ? '' : 'none';
        });

        // 2. Global Dropdown Logic
        let oldDropdown = document.getElementById('search-dropdown');
        if (oldDropdown) oldDropdown.remove();
        
        if (query.length < 2) return;

        const registry = JSON.parse(localStorage.getItem('crm_search_index') || '[]');
        const matches = registry.filter(item => item.keyword.includes(query));

        if (matches.length > 0) {
            const dd = document.createElement('div');
            dd.id = 'search-dropdown';
            // Styling to ensure it appears over the dashboard cards
            dd.style = "position:absolute; top:100%; left:0; width:100%; background:white; border:1px solid #e2e8f0; z-index:9999; border-radius:8px; box-shadow:0 10px 15px -3px rgba(0,0,0,0.1); max-height: 300px; overflow-y: auto;";
            
            matches.forEach(m => {
                const div = document.createElement('div');
                div.style = "padding:12px 15px; cursor:pointer; border-bottom:1px solid #f1f5f9; font-size:14px; display: flex; justify-content: space-between;";
                div.innerHTML = `
                    <span><b style="color:var(--blue)">[${m.category}]</b> ${m.display}</span>
                    <span style="font-size: 11px; color: var(--gray);">Go to Page →</span>
                `;
                div.onclick = () => {
                    // Redirects to the specific page and highlights the result
                    window.location.href = `${m.page}?find=${encodeURIComponent(m.keyword)}`;
                };
                dd.appendChild(div);
            });
            searchContainer.appendChild(dd);
        }
    }
});

// Close dropdown if clicking outside
document.addEventListener('click', function(e) {
    const dd = document.getElementById('search-dropdown');
    if (dd && !e.target.closest('.search-container')) {
        dd.remove();
    }
});

/* --- 4. CHARTS & UI RENDERING --- */
function initLeadsChart() {
    const ctx = document.getElementById('leadsChart');
    if (!ctx) return;
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
            datasets: [{
                label: 'New Leads',
                data: [42, 58, 45, 82, 71, 95, 88],
                borderColor: '#3F88C5',
                backgroundColor: 'rgba(63, 136, 197, 0.1)',
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: { y: { beginAtZero: true }, x: { grid: { display: false } } }
        }
    });
}

function renderHighValueLeads() {
    const container = document.getElementById('highValueLeadsContainer');
    if (!container) return;
    const topLeads = [
        { name: "Sarah Jenkins", phone: "+65 9123 4567", score: 98, note: "Interested in Enterprise plan." },
        { name: "Marcus Tan", phone: "+65 8822 1133", score: 92, note: "Requested a demo." },
        { name: "Elena Rodriguez", phone: "+1 415 555 0199", score: 89, note: "Cart value > $5,000." }
    ];
    container.innerHTML = topLeads.map(lead => `
        <div class="customer-item">
            <div class="customer-info">
                <strong>${lead.name}</strong><br>
                <p>${lead.phone}</p>
                <p style="font-style: italic; font-size: 11px;">"${lead.note}"</p>
            </div>
            <span class="status-badge status-new" style="background:var(--green); color:white;">Score: ${lead.score}</span>
        </div>
    `).join('');
}

function renderLatestChats() {
    const container = document.getElementById('latestChatsContainer');
    if (!container) return;
    const recentChats = [
        { name: "Lightningboi676", lastMsg: "How do I upgrade?", time: "2m ago" },
        { name: "Sarah Jenkins", lastMsg: "Thanks for help!", time: "15m ago" }
    ];
    container.innerHTML = recentChats.map(chat => `
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 12px; border-bottom: 1px solid #f1f5f9;">
            <div>
                <strong style="font-size: 14px;">${chat.name}</strong>
                <p style="margin: 0; font-size: 12px; color: var(--gray);">${chat.lastMsg}</p>
            </div>
            <button class="btn btn-blue" style="padding: 4px 10px; font-size: 11px;" onclick="goToChat('${chat.name}')">View</button>
        </div>
    `).join('');
}

window.goToChat = function(userName) {
    window.location.href = `/history?user=${encodeURIComponent(userName)}`;
};

/* --- 5. INITIALIZATION --- */
window.addEventListener('DOMContentLoaded', () => {
    autoIndexPage(); 
    if (document.body.id === 'page-dashboard') {
        renderDashboard();
        initLeadsChart();
        renderHighValueLeads();
        renderLatestChats();
    }

    const findTerm = new URLSearchParams(window.location.search).get('find');
    if (findTerm) {
        const bar = document.querySelector('.taskbar-search');
        if (bar) { bar.value = findTerm; bar.dispatchEvent(new Event('input')); }
    }
});

/* --- 6. LEAD SCORING LOGIC --- */
function applyFilters(resetPage = true) {
    const searchTerm = document.getElementById('searchInput').value.toLowerCase();
    const statusFilter = document.getElementById('filterStatus').value;
    const opFilter = document.getElementById('filterOperation').value;

    // We select the rows from the table
    const tableBody = document.getElementById("ruleTable");
    if (!tableBody) return; // Exit if we aren't on the scoring page
    
    const rows = Array.from(tableBody.querySelectorAll("tr")).filter(row => row.cells.length > 1);

    rows.forEach(row => {
        const name = row.cells[0].textContent.toLowerCase();
        const op = row.cells[1].innerText.trim();
        // This looks for the label we fixed earlier
        const statusLabel = row.querySelector('.status-label');
        const status = statusLabel ? statusLabel.innerText.trim() : "";

        const matchesSearch = name.includes(searchTerm);
        const matchesStatus = (statusFilter === 'all' || status === statusFilter);
        const matchesOp = (opFilter === 'all' || op === opFilter);

        if (matchesSearch && matchesStatus && matchesOp) {
            row.style.display = "";
        } else {
            row.style.display = "none";
        }
    });
}

// Global function so the checkbox onchange="toggleStatus(...)" can find it
window.toggleStatus = function(id, checkbox) {
    fetch('/toggle_status/' + id, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ active: checkbox.checked })
    }).then(() => {
        const label = checkbox.parentElement.querySelector('.status-label');
        if (label) {
            label.innerText = checkbox.checked ? "Active" : "Not Active";
        }
        // Re-run the filter to update the view
        applyFilters(false);
    });
};