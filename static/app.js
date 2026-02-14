/* ==========================================================================
   1. SHARED STORAGE & SEARCH ENGINE
   ========================================================================== */

window.registerGlobalItem = function (category, name, page) {
    let registry = JSON.parse(localStorage.getItem('crm_search_index') || '[]');
    if (!registry.find(item => item.display === name)) {
        registry.push({
            keyword: name.toLowerCase(),
            display: name,
            category: category,
            page: page
        });
        localStorage.setItem('crm_search_index', JSON.stringify(registry));
    }
};

function autoIndexPage() {
    const pageId = document.body.id;

    if (pageId === 'page-scoring') {
        document.querySelectorAll('#ruleTable tr td:first-child').forEach(td => {
            window.registerGlobalItem("Rule", td.innerText.trim(), "/scoring");
        });
    }

    if (pageId === 'page-customers') {
        document.querySelectorAll('.card h5').forEach(el => {
            const name = el.innerText.trim();
            if (name) window.registerGlobalItem("Customer", name, "/customers");
        });
    }

    if (pageId === 'page-repository') {
        setTimeout(() => {
            document.querySelectorAll('#inquiry-tbody tr').forEach(tr => {
                const customerName = tr.cells[1]?.innerText.trim();
                if (customerName) {
                    window.registerGlobalItem("Inquiry", customerName, "/repository");
                }
            });
        }, 800);
    }
}

function setupSearch() {
    const searchBar = document.querySelector('.taskbar-search');
    if (!searchBar) return; // No search bar on this page

    const resultsDiv = document.createElement('div');
    resultsDiv.className = 'search-results-dropdown shadow';
    document.body.appendChild(resultsDiv);

    searchBar.addEventListener('input', (e) => {
        const val = e.target.value.toLowerCase();
        const registry = JSON.parse(localStorage.getItem('crm_search_index') || '[]');

        if (!val) { resultsDiv.style.display = 'none'; return; }

        const filtered = registry.filter(item => item.keyword.includes(val)).slice(0, 5);

        if (filtered.length > 0) {
            resultsDiv.innerHTML = filtered.map(item => `
                <div class="search-item" onclick="window.location.href='${item.page}'">
                    <span class="badge bg-light text-dark me-2">${item.category}</span>
                    ${item.display}
                </div>
            `).join('');

            const rect = searchBar.getBoundingClientRect();
            resultsDiv.style.position = 'fixed';
            resultsDiv.style.top = `${rect.bottom}px`;
            resultsDiv.style.left = `${rect.left}px`;
            resultsDiv.style.width = `${rect.width}px`;
            resultsDiv.style.display = 'block';
            resultsDiv.style.zIndex = '10000';
        } else {
            resultsDiv.style.display = 'none';
        }
    });

    document.addEventListener('click', (e) => {
        if (!searchBar.contains(e.target) && !resultsDiv.contains(e.target)) {
            resultsDiv.style.display = 'none';
        }
    });
}

/* ==========================================================================
   2. PAGE SPECIFIC LOGIC (Dashboard, Scoring, Repository)
   ========================================================================== */

function renderDashboard() {
    const container = document.getElementById('metrics-container');
    if (!container) return;
    const metrics = [
        { label: "Highest Leads (Past 7 Days)", value: "156", color: "var(--blue)" },
        { label: "Bot Usage Ratio", value: "4.2 : 1", color: "var(--green)" },
        { label: "Total Chat Summary", value: "1,204", color: "var(--red)" }
    ];
    container.innerHTML = metrics.map(m => `
        <div class="metric-card">
            <div class="small text-muted mb-1">${m.label}</div>
            <div class="h2 mb-0" style="color: ${m.color}">${m.value}</div>
        </div>`).join('');
}

function initLeadsChart() {
    const ctx = document.getElementById('leadsChart');
    if (!ctx) return;
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
            datasets: [{ label: 'Leads', data: [12, 19, 15, 25, 22, 30, 28], borderColor: '#3F88C5', tension: 0.4, fill: true }]
        },
        options: { responsive: true, maintainAspectRatio: false }
    });
}



async function refreshInquiryTable() {
    const search = document.getElementById('search-input')?.value || "";
    const checkboxes = document.querySelectorAll('.filter-cb:checked');
    let url = `/api/inquiries?search=${search}`;
    checkboxes.forEach(cb => url += `&status[]=${cb.value}`);

    try {
        const res = await fetch(url);
        const data = await res.json();
        const tbody = document.getElementById('inquiry-tbody');
        if (!tbody) return;

        tbody.innerHTML = data.map(i => `
            <tr>
                <td>${i.id}</td>
                <td><b>${i.customer}</b></td>
                <td>${i.inquiry_type}</td>
                <td><span class="badge rounded-pill bg-info-subtle text-dark">${i.status}</span></td>
                <td>${i.assigned_rep}</td>
                <td><a href="/inquiry/${i.id}" class="btn btn-sm btn-outline-primary">View</a></td>
            </tr>`).join('');
    } catch (err) {
        console.error("Error fetching inquiries:", err);
    }
}

/* ==========================================================================
   3. CUSTOMER LIST LOGIC
   ========================================================================== */

async function saveCustomer() {
    const name = document.getElementById('newCustName').value.trim();
    const email = document.getElementById('newCustEmail').value.trim();
    const phone = document.getElementById('newCustPhone').value.trim();

    if (!name || !email) {
        alert("Name and Email are required!");
        return;
    }

    const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailPattern.test(email)) {
        alert("Please enter a valid email address!");
        return;
    }

    const res = await fetch('/api/customer/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, email, phone })
    });

    if (res.ok) {
        window.location.reload();
    } else {
        const data = await res.json();
        alert("Error: " + (data.error || "Could not save customer"));
    }
}

/* ==========================================================================
   4. SINGLE INITIALIZATION (runs ONCE on every page)
   ========================================================================== */

window.addEventListener('DOMContentLoaded', () => {
    const pageId = document.body.id;

    // A. CLEAR GHOST DATA (Sync with Database)
    localStorage.removeItem('crm_search_index');
    console.log("Search Index Synced.");

    // B. SETUP SEARCH UI
    setupSearch();

    // C. LOAD DATABASE DATA FROM PYTHON (backendSearchSeed)
    //    This is the KEY FIX: we load all items from all 3 tables
    //    immediately, BEFORE any page-specific logic runs.
    if (window.backendSearchSeed) {
        window.backendSearchSeed.forEach(item => {
            window.registerGlobalItem(item.category, item.display, item.page);
        });
        console.log("Global Search Ready: " + window.backendSearchSeed.length + " items from database.");
    }

    // D. DASHBOARD SPECIFIC
    if (pageId === 'page-dashboard') {
        renderDashboard();
        initLeadsChart();
        if (typeof renderHighValueLeads === 'function') renderHighValueLeads();
        if (typeof renderLatestChats === 'function') renderLatestChats();
    }

    // E. SCORING PAGE SPECIFIC
    // (Filter logic is handled inline in lead-scoring.html)

    // F. REPOSITORY PAGE SPECIFIC
    if (pageId === 'page-repository') {
        refreshInquiryTable();
        document.getElementById('search-input')?.addEventListener('input', refreshInquiryTable);
        document.querySelectorAll('.filter-cb').forEach(cb => {
            cb.addEventListener('change', refreshInquiryTable);
        });
    }

    // G. CUSTOMER PAGE SPECIFIC
    if (pageId === 'page-customers') {
        document.querySelectorAll('.card h5').forEach(el => {
            window.registerGlobalItem("Customer", el.innerText.trim(), "/customers");
        });
    }

    // H. HANDLE URL SEARCH PARAM (e.g. ?find=test)
    const findTerm = new URLSearchParams(window.location.search).get('find');
    if (findTerm) {
        const bar = document.querySelector('.taskbar-search');
        if (bar) {
            bar.value = findTerm;
            bar.dispatchEvent(new Event('input'));
        }
    }
});