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

// Store fetched data globally so modal + render can share it
window._dashboardData = null;
window._chartInstances = {};

window.crm_preferences = null;

async function getDashboardConfig() {
    if (window.crm_preferences) return window.crm_preferences;
    try {
        const res = await fetch('/api/user/preferences');
        const data = await res.json();
        window.crm_preferences = data;
        return data;
    } catch (e) {
        console.error("Failed to fetch user preferences:", e);
        return {};
    }
}

async function setDashboardConfig(config) {
    window.crm_preferences = config;
    try {
        await fetch('/api/user/preferences', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });
    } catch (e) {
        console.error("Failed to save user preferences:", e);
    }
}

function isItemEnabled(config, category, key) {
    if (!config) return true; // No config = show all
    if (!config[category]) return true;
    return config[category][key] !== false;
}

async function loadDashboardData() {
    try {
        // Fetch stats and preferences in parallel
        const [statsRes, prefs] = await Promise.all([
            fetch('/api/dashboard/stats'),
            getDashboardConfig()
        ]);

        window._dashboardData = await statsRes.json();
        renderDashboardStats(prefs);
        renderDashboardGraphs(prefs);
    } catch (e) {
        console.error('Failed to load dashboard stats:', e);
        const loading = document.getElementById('statsLoading');
        if (loading) loading.innerHTML = '<span style="color:var(--red)">Failed to load stats.</span>';
    }
}

function renderDashboardStats(config) {
    const container = document.getElementById('statsRow');
    if (!container || !window._dashboardData) return;

    if (!config) config = {};
    const stats = window._dashboardData.solid_stats;
    const enabledStats = stats.filter(s => isItemEnabled(config, 'stats', s.key));

    if (enabledStats.length === 0) {
        container.innerHTML = '<div class="col-12"><div class="card" style="text-align:center; color:var(--gray); padding:30px;">No stats enabled. Click <strong>⚙️ Customize Stats</strong> to select which stats to display.</div></div>';
        return;
    }

    // Choose column class based on count
    let colClass = 'col-12 col-sm-6 col-xl-3';
    if (enabledStats.length <= 2) colClass = 'col-12 col-sm-6';
    if (enabledStats.length === 1) colClass = 'col-12';

    container.innerHTML = enabledStats.map(s => `
        <div class="${colClass} stat-card-wrapper" data-stat-key="${s.key}">
            <div class="card stat-card">
                <div class="stat-card-icon" style="background: ${s.color}15; color: ${s.color};">${s.icon}</div>
                <div class="stat-card-info">
                    <span class="stat-card-label">${s.label}</span>
                    <span class="stat-card-value" style="color: ${s.color};">${s.value}</span>
                </div>
            </div>
        </div>
    `).join('');
}

function renderDashboardGraphs(config) {
    const container = document.getElementById('graphsRow');
    if (!container || !window._dashboardData) return;

    // Destroy existing chart instances
    Object.values(window._chartInstances).forEach(c => { try { c.destroy(); } catch (e) { } });
    window._chartInstances = {};

    if (!config) config = {};
    const graphs = window._dashboardData.graphs;
    const enabledGraphs = graphs.filter(g => isItemEnabled(config, 'graphs', g.key));

    if (enabledGraphs.length === 0) {
        container.innerHTML = '<div class="col-12"><div class="card" style="text-align:center; color:var(--gray); padding:30px;">No graphs enabled. Click <strong>⚙️ Customize Stats</strong> to add graphs.</div></div>';
        return;
    }

    // Choose column layout based on count
    let colClass = 'col-12 col-lg-6';
    if (enabledGraphs.length === 1) colClass = 'col-12';

    container.innerHTML = enabledGraphs.map(g => {
        if (g.type === 'doughnut') {
            const total = g.datasets[0].data.reduce((a, b) => a + b, 0);
            const breakdownHtml = g.labels.map((label, i) => {
                const val = g.datasets[0].data[i];
                const color = g.datasets[0].backgroundColor[i];
                const pct = total > 0 ? ((val / total) * 100).toFixed(1) : 0;
                return `
                    <div class="breakdown-item">
                        <div class="breakdown-label">
                            <span class="breakdown-dot" style="background-color: ${color}"></span>
                            ${label}
                        </div>
                        <div class="breakdown-value">
                            <strong>${val}</strong>
                            <span class="breakdown-percent">(${pct}%)</span>
                        </div>
                    </div>
                `;
            }).join('');

            return `
                <div class="${colClass} graph-card-wrapper" data-graph-key="${g.key}">
                    <div class="card graph-card" style="padding: 25px; min-height: 350px;">
                        <h3 style="margin-top:0; color: var(--slate-900); font-size: 1.05rem; margin-bottom: 20px;">${g.label}</h3>
                        <div class="doughnut-layout">
                            <div class="doughnut-chart-container" style="height: 250px; position: relative;">
                                <canvas id="chart-${g.key}"></canvas>
                            </div>
                            <div class="doughnut-breakdown">
                                ${breakdownHtml}
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }

        return `
            <div class="${colClass} graph-card-wrapper" data-graph-key="${g.key}">
                <div class="card graph-card" style="padding: 25px;">
                    <h3 style="margin-top:0; color: var(--slate-900); font-size: 1.05rem; margin-bottom: 15px;">${g.label}</h3>
                    <div style="height: 220px; position: relative;">
                        <canvas id="chart-${g.key}"></canvas>
                    </div>
                </div>
            </div>
        `;
    }).join('');

    // Create Chart.js instances
    enabledGraphs.forEach(g => {
        const ctx = document.getElementById(`chart-${g.key}`);
        if (!ctx) return;

        const datasets = g.datasets.map(ds => {
            const base = { ...ds };
            if (g.type === 'line') {
                base.tension = 0.4;
                base.fill = true;
                base.pointRadius = 4;
                base.pointHoverRadius = 6;
            }
            if (g.type === 'bar') {
                base.borderRadius = 6;
            }
            return base;
        });

        window._chartInstances[g.key] = new Chart(ctx, {
            type: g.type,
            data: { labels: g.labels, datasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: g.type !== 'doughnut', position: 'bottom' }
                },
                ...(g.type !== 'doughnut' ? {
                    scales: {
                        y: { beginAtZero: true, grid: { color: '#f1f5f9' } },
                        x: { grid: { display: false } }
                    }
                } : {})
            }
        });
    });
}

// --- CUSTOMIZE MODAL LOGIC ---

async function openCustomizeModal() {
    if (!window._dashboardData) return;
    const config = await getDashboardConfig();

    // Populate Stats tab
    const statsList = document.getElementById('customizeStatsList');
    if (statsList) {
        statsList.innerHTML = window._dashboardData.solid_stats.map(s => {
            const checked = isItemEnabled(config, 'stats', s.key) ? 'checked' : '';
            return `
                <div class="customize-item">
                    <div class="customize-item-left">
                        <span class="customize-item-icon" style="background: ${s.color}15; color: ${s.color};">${s.icon}</span>
                        <div>
                            <strong>${s.label}</strong>
                            <small style="display:block; color:var(--gray); font-size:0.75rem;">Current: ${s.value}</small>
                        </div>
                    </div>
                    <div class="form-check form-switch">
                        <input class="form-check-input customize-toggle" type="checkbox" id="cfg-stat-${s.key}" data-category="stats" data-key="${s.key}" ${checked}>
                    </div>
                </div>
            `;
        }).join('');
    }

    // Populate Graphs tab
    const graphsList = document.getElementById('customizeGraphsList');
    if (graphsList) {
        const graphIcons = { line: '📉', bar: '📊', doughnut: '🍩' };
        graphsList.innerHTML = window._dashboardData.graphs.map(g => {
            const checked = isItemEnabled(config, 'graphs', g.key) ? 'checked' : '';
            return `
                <div class="customize-item">
                    <div class="customize-item-left">
                        <span class="customize-item-icon" style="background: #f1f5f9; color: var(--slate-900);">${graphIcons[g.type] || '📈'}</span>
                        <div>
                            <strong>${g.label}</strong>
                            <small style="display:block; color:var(--gray); font-size:0.75rem;">Type: ${g.type.charAt(0).toUpperCase() + g.type.slice(1)} chart</small>
                        </div>
                    </div>
                    <div class="form-check form-switch">
                        <input class="form-check-input customize-toggle" type="checkbox" id="cfg-graph-${g.key}" data-category="graphs" data-key="${g.key}" ${checked}>
                    </div>
                </div>
            `;
        }).join('');
    }
}

async function saveDashboardConfig() {
    const toggles = document.querySelectorAll('.customize-toggle');
    const config = { stats: {}, graphs: {} };

    toggles.forEach(t => {
        const cat = t.dataset.category;
        const key = t.dataset.key;
        config[cat][key] = t.checked;
    });

    await setDashboardConfig(config);

    // Re-render dashboard immediately
    renderDashboardStats(config);
    renderDashboardGraphs(config);

    // Close modal
    const modal = bootstrap.Modal.getInstance(document.getElementById('customizeModal'));
    if (modal) modal.hide();
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
        loadDashboardData();
        if (typeof renderHighValueLeads === 'function') renderHighValueLeads();
        if (typeof renderLatestChats === 'function') renderLatestChats();
    }

    // E. SCORING PAGE SPECIFIC
    // (Filter logic is handled inline in lead-scoring.html)


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

    // I. NOTIFICATION BELL (runs on EVERY page)
    initNotificationBell();
});

/* ==========================================================================
   5. NOTIFICATION BELL SYSTEM
   ========================================================================== */

function initNotificationBell() {
    const sidebar = document.querySelector('.sidebar');
    if (!sidebar) return;

    // Inject bell button at the bottom of sidebar
    const bellWrapper = document.createElement('div');
    bellWrapper.className = 'notif-bell-wrapper';
    bellWrapper.innerHTML = `
        <button class="notif-bell-btn" id="notifBellBtn" onclick="toggleNotifPanel(event)">
            <span class="bell-icon">🔔</span>
            <span>Notifications</span>
            <span class="notif-badge hidden" id="notifBadge">0</span>
        </button>
    `;
    sidebar.appendChild(bellWrapper);

    // Inject notification panel into body
    const panel = document.createElement('div');
    panel.className = 'notif-panel';
    panel.id = 'notifPanel';
    panel.innerHTML = `
        <div class="notif-panel-header">
            <h4>🔔 Notifications</h4>
            <button class="notif-mark-all" onclick="markAllNotificationsRead()">Mark all read</button>
        </div>
        <div class="notif-panel-body" id="notifPanelBody">
            <div class="notif-empty">
                <div class="notif-empty-icon">🔔</div>
                Loading...
            </div>
        </div>
    `;
    document.body.appendChild(panel);

    // Close panel on outside click
    document.addEventListener('click', (e) => {
        const panel = document.getElementById('notifPanel');
        const btn = document.getElementById('notifBellBtn');
        if (panel && btn && !panel.contains(e.target) && !btn.contains(e.target)) {
            panel.classList.remove('open');
        }
    });

    // Fetch notifications
    fetchNotifications();

    // Auto refresh every 30 seconds
    setInterval(fetchNotifications, 30000);
}

function toggleNotifPanel(e) {
    e.stopPropagation();
    const panel = document.getElementById('notifPanel');
    if (panel) {
        panel.classList.toggle('open');
        if (panel.classList.contains('open')) {
            fetchNotifications();
        }
    }
}

async function fetchNotifications() {
    try {
        const res = await fetch('/api/notifications');
        const data = await res.json();
        renderNotifications(data.notifications, data.unread_count);
    } catch (err) {
        console.error('Failed to fetch notifications:', err);
    }
}

function renderNotifications(notifications, unreadCount) {
    // Update badge
    const badge = document.getElementById('notifBadge');
    if (badge) {
        if (unreadCount > 0) {
            badge.textContent = unreadCount > 99 ? '99+' : unreadCount;
            badge.classList.remove('hidden');
        } else {
            badge.classList.add('hidden');
        }
    }

    // Render list
    const body = document.getElementById('notifPanelBody');
    if (!body) return;

    if (notifications.length === 0) {
        body.innerHTML = `
            <div class="notif-empty">
                <div class="notif-empty-icon">✨</div>
                No notifications this week
            </div>
        `;
        return;
    }

    body.innerHTML = notifications.map(n => {
        const iconClass = `notif-icon-${n.type}`;
        const unreadClass = n.is_read ? '' : 'unread';
        const timeAgo = formatNotifTime(n.created_at);

        return `
            <div class="notif-item ${unreadClass}" data-notif-id="${n.id}">
                <div class="notif-item-icon ${iconClass}">${n.icon}</div>
                <div class="notif-item-content">
                    <div class="notif-item-title">${escapeNotifHtml(n.title)}</div>
                    <div class="notif-item-message">${escapeNotifHtml(n.message)}</div>
                    <div class="notif-item-time">${timeAgo}</div>
                </div>
                ${!n.is_read ? '<div class="notif-unread-dot"></div>' : ''}
            </div>
        `;
    }).join('');
}

async function markAllNotificationsRead() {
    try {
        await fetch('/api/notifications/read', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ids: 'all' })
        });
        fetchNotifications();
    } catch (err) {
        console.error('Failed to mark notifications as read:', err);
    }
}

function formatNotifTime(dateStr) {
    if (!dateStr) return '';
    try {
        // dateStr is like "2026-02-16 14:05"
        const parts = dateStr.split(' ');
        const dateParts = parts[0].split('-');
        const timeParts = parts[1].split(':');
        const date = new Date(dateParts[0], dateParts[1] - 1, dateParts[2], timeParts[0], timeParts[1]);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMins / 60);
        const diffDays = Math.floor(diffHours / 24);

        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffHours < 24) return `${diffHours}h ago`;
        if (diffDays === 1) return 'Yesterday';
        if (diffDays < 7) return `${diffDays}d ago`;
        return dateStr;
    } catch (e) {
        return dateStr;
    }
}

function escapeNotifHtml(str) {
    const div = document.createElement('div');
    div.textContent = str || '';
    return div.innerHTML;
}