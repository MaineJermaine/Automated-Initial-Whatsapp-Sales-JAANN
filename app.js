/* --- 1. GLOBAL SEARCH FEATURE --- */
// This runs on every page. It looks for any input with "Search" in the placeholder.
document.addEventListener('input', function (e) {
    if (e.target && e.target.placeholder && e.target.placeholder.includes('Search')) {
        const searchTerm = e.target.value.toLowerCase();
        
        // Target Tables (Repository, Lead Scoring)
        const tableRows = document.querySelectorAll('tbody tr');
        tableRows.forEach(row => {
            row.style.display = row.textContent.toLowerCase().includes(searchTerm) ? '' : 'none';
        });

        // Target Lists (Customer List cards or Chat threads)
        const cards = document.querySelectorAll('.card, .customer-item, .chat-thread');
        cards.forEach(card => {
            // We skip the dashboard metrics cards so they don't disappear while searching
            if (card.closest('.dashboard-grid') && document.body.id === 'page-dashboard') return;
            
            card.style.display = card.textContent.toLowerCase().includes(searchTerm) ? '' : 'none';
        });
    }
});

/* --- 2. CUSTOMIZABLE DASHBOARD LOGIC --- */
const availableMetrics = {
    leads_7d: { label: "Highest Leads (7 Days)", value: "142", color: "var(--green)" },
    bot_ratio: { label: "Bot Usage vs Engagement", value: "4.2:1", color: "var(--blue)" },
    open_inq: { label: "Open Inquiries", value: "37", color: "var(--red)" },
    high_leads: { label: "High-Value Leads", value: "92", color: "var(--slate-900)" },
    total_cust: { label: "Total Customers", value: "1,284", color: "var(--slate-900)" },
    chat_summary: { label: "Latest Chat Summary", value: "3 New / 2 Pending", color: "var(--orange)" }
};

// Default slots
let currentLayout = ['leads_7d', 'bot_ratio', 'open_inq', 'high_leads'];

function renderDashboard() {
    const container = document.getElementById('metricsContainer');
    if (!container) return; // Exit if we aren't on the dashboard page

    currentLayout.forEach((metricKey, index) => {
        const metric = availableMetrics[metricKey];
        const slot = document.getElementById(`slot-${index}`);
        if (slot) {
            slot.innerHTML = `
                <h3 style="margin-top: 0; font-size: 14px; color: var(--gray);">${metric.label}</h3>
                <p style="font-size: 24px; margin: 10px 0 0; font-weight: 700; color: ${metric.color}">${metric.value}</p>
            `;
        }
    });
}

/* --- 3. MODAL CONTROLS --- */
window.openCustomizeModal = function() {
    const form = document.getElementById('configForm');
    form.innerHTML = '';
    currentLayout.forEach((currentKey, index) => {
        let options = Object.keys(availableMetrics).map(key => 
            `<option value="${key}" ${key === currentKey ? 'selected' : ''}>${availableMetrics[key].label}</option>`
        ).join('');
        form.innerHTML += `<div style="margin-bottom:15px;"><label>Slot ${index + 1}</label><select id="select-slot-${index}" style="width:100%; padding:8px; border-radius:5px;">${options}</select></div>`;
    });
    document.getElementById('customizeModal').style.display = 'flex';
};

window.closeModal = function() {
    document.querySelectorAll('.modal').forEach(m => m.style.display = 'none');
};

window.saveDashboardConfig = function() {
    for (let i = 0; i < 4; i++) {
        currentLayout[i] = document.getElementById(`select-slot-${i}`).value;
    }
    renderDashboard();
    closeModal();
};

// Auto-run dashboard renderer when the page loads
window.addEventListener('DOMContentLoaded', renderDashboard);