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

    // Prevent multiple dropdowns
    if (document.querySelector('.search-results-dropdown')) return;

    const resultsDiv = document.createElement('div');
    resultsDiv.className = 'search-results-dropdown shadow';
    
    // Basic styling for the dropdown to ensure it looks good if not fully covered by CSS
    resultsDiv.style.backgroundColor = 'white';
    resultsDiv.style.border = '1px solid #ddd';
    resultsDiv.style.borderRadius = '4px';
    resultsDiv.style.maxHeight = '300px';
    resultsDiv.style.overflowY = 'auto';
    resultsDiv.style.display = 'none'; // Hidden by default

    document.body.appendChild(resultsDiv);

    let debounceTimer;

    searchBar.addEventListener('input', (e) => {
        const val = e.target.value.trim();
        
        clearTimeout(debounceTimer);
        
        if (!val) { 
            resultsDiv.style.display = 'none'; 
            return; 
        }

        debounceTimer = setTimeout(async () => {
            try {
                const res = await fetch(`/api/global-search?q=${encodeURIComponent(val)}`);
                if (!res.ok) throw new Error('Search failed');
                
                const results = await res.json();
                
                if (results.length > 0) {
                    resultsDiv.innerHTML = results.map(item => `
                        <div class="search-item" onclick="window.location.href='${item.url}'" style="padding: 10px; cursor: pointer; border-bottom: 1px solid #eee;">
                            <span class="badge bg-light text-dark me-2">${item.category}</span>
                            <span style="font-weight:500;">${item.display}</span>
                        </div>
                    `).join('');

                    // Hover effect
                    resultsDiv.querySelectorAll('.search-item').forEach(item => {
                        item.addEventListener('mouseenter', () => item.style.backgroundColor = '#f8f9fa');
                        item.addEventListener('mouseleave', () => item.style.backgroundColor = 'white');
                    });

                    const rect = searchBar.getBoundingClientRect();
                    resultsDiv.style.position = 'fixed';
                    resultsDiv.style.top = `${rect.bottom + 5}px`;
                    resultsDiv.style.left = `${rect.left}px`;
                    resultsDiv.style.width = `${rect.width}px`;
                    resultsDiv.style.display = 'block';
                    resultsDiv.style.zIndex = '10000';
                } else {
                    resultsDiv.innerHTML = '<div style="padding:10px; color:#666;">No results found</div>';
                    
                    const rect = searchBar.getBoundingClientRect();
                    resultsDiv.style.position = 'fixed';
                    resultsDiv.style.top = `${rect.bottom + 5}px`;
                    resultsDiv.style.left = `${rect.left}px`;
                    resultsDiv.style.width = `${rect.width}px`;
                    resultsDiv.style.display = 'block';
                    resultsDiv.style.zIndex = '10000';
                }
            } catch (err) {
                console.error("Global search error:", err);
            }
        }, 300); // 300ms debounce
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

function showToast(message, color = "green") {
    const toast = document.getElementById("siteToast");
    const msg = document.getElementById("toastMessage");

    msg.innerText = message;

    // color types
    const colors = {
        green: "#16a34a",
        red: "#dc2626",
        blue: "#2563eb"
    };

    toast.style.background = colors[color] || colors.green;

    toast.classList.remove("hidden");

    // auto hide after 4s
    setTimeout(hideToast, 4000);
}

function hideToast() {
    document.getElementById("siteToast").classList.add("hidden");
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
    if (document.getElementById('notifBellBtn')) return;
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
        const date = new Date(dateStr.replace(' ', 'T'));
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
        
        // Spelled out date for older notifs
        return date.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
    } catch (e) {
        return dateStr;
    }
}

function formatChatMessageTime(dateStr) {
    if (!dateStr) return '';
    try {
        // Handle "10:30 AM" legacy format
        if (dateStr.includes('AM') || dateStr.includes('PM')) {
            if (!dateStr.includes('-')) return dateStr; 
        }

        const date = new Date(dateStr.replace(' ', 'T'));
        const now = new Date();
        
        const isToday = date.toDateString() === now.toDateString();
        const isYesterday = new Date(now.setDate(now.getDate() - 1)).toDateString() === date.toDateString();
        
        const timeStr = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        
        if (isToday) return timeStr;
        if (isYesterday) return `Yesterday, ${timeStr}`;
        
        // 14 Feb, 10:30 AM
        const datePart = date.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' });
        return `${datePart}, ${timeStr}`;
    } catch (e) {
        return dateStr;
    }
}


function escapeNotifHtml(str) {
    const div = document.createElement('div');
    div.textContent = str || '';
    return div.innerHTML;
}

document.addEventListener('DOMContentLoaded', setupSearch);

/* ==========================================================================
   3. AGENT PROFILE MODAL (Standardized)
   ========================================================================== */
window.showAgentProfile = async function(userId) {
    // Check if a standard modal exists, or if we need to inject it
    let modalEl = document.getElementById('agentProfileModal');

    // If 'agentProfileModal' doesn't exist, inject the standard one.
    // NOTE: 'my_team.html' has its own 'agentProfileModal' hardcoded in the HTML.
    // If we are on 'my_team.html', this element WILL exist, and we will use it.
    // BUT 'my_team.html' ALSO has its own 'showAgentProfile' function defined in the template.
    // That local function should override this global one on that page.
    
    if (!modalEl) {
        const modalHtml = `
<div class="modal fade" id="agentProfileModal" tabindex="-1" aria-hidden="true">
    <div class="modal-dialog modal-dialog-centered">
        <div class="modal-content border-0 shadow-lg" style="border-radius: 20px; overflow: hidden;">
            <div class="modal-header border-0 pb-0 pt-4 px-4">
                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
            </div>
            <div class="modal-body p-4 text-center">
                <div class="mb-4 d-flex justify-content-center">
                    <div style="width: 100px; height: 100px; border-radius: 30px; overflow: hidden; position: relative; box-shadow: 0 10px 25px rgba(0,0,0,0.1);">
                        <img id="stdProfPic" src="" style="width: 100%; height: 100%; object-fit: cover; display: none;">
                        <div id="stdProfInitials" style="width: 100%; height: 100%; background: var(--blue); color: white; display: none; align-items: center; justify-content: center; font-size: 2.5rem; font-weight: 700;"></div>
                    </div>
                </div>
                <h3 id="stdProfName" class="fw-bold mb-1"></h3>
                <p id="stdProfUser" class="text-primary fw-600 mb-3"></p>
                <div class="mb-4">
                    <span id="stdProfRole" class="badge rounded-pill bg-light text-dark px-3 py-2 border shadow-sm" style="font-size: 0.75rem; letter-spacing: 0.05em;"></span>
                </div>

                <div class="mb-3" id="stdProfTeamSection" style="display:none;">
                    <div class="d-flex align-items-center mb-1">
                        <label class="small text-muted fw-bold text-uppercase" style="font-size: 0.65rem;">Team</label>
                    </div>
                    <div class="d-flex align-items-center gap-3 p-3 border rounded-4 bg-white shadow-sm hover-effect">
                        <div class="avatar-circle bg-light text-dark border" style="width: 42px; height: 42px; font-size: 1rem; display: flex; align-items: center; justify-content: center;">
                            <img id="stdProfTeamPic" src="" style="width:100%; height:100%; object-fit:cover; border-radius:50%; display:none;">
                            <span id="stdProfTeamInitial" style="display:none;">T</span>
                        </div>
                        <div class="text-start flex-grow-1">
                            <div class="fw-bold text-dark" id="stdProfTeamName"></div>
                            <div class="text-muted small" id="stdProfTeamRole"></div>
                        </div>
                        <span class="badge bg-light text-secondary border" id="stdProfTeamTag"></span>
                    </div>
                </div>

                <div class="mb-3" id="stdProfScoreSection">
                    <div class="d-flex align-items-center mb-1">
                        <label class="small text-muted fw-bold text-uppercase" style="font-size: 0.65rem;">Performance Score</label>
                    </div>
                    <div class="d-flex align-items-center justify-content-between p-3 border rounded-4 bg-white shadow-sm hover-effect">
                        <div>
                            <div class="h3 fw-bold text-primary mb-0" id="stdProfScore">0</div>
                            <div class="small text-muted">Individual Score</div>
                        </div>
                        <i class="bi bi-trophy-fill fs-1 text-warning opacity-75"></i>
                    </div>
                </div>

                <div class="p-3 bg-light rounded-4 text-start mb-2" style="border: 1px dashed #ced4da;">
                    <label class="small text-muted fw-bold mb-1 d-block text-uppercase" style="font-size: 0.65rem;">Biography</label>
                    <p id="stdProfBio" class="small mb-0 text-secondary" style="line-height: 1.6;"></p>
                </div>
                
                <!-- Container for page-specific actions (e.g., team management buttons) -->
                <div id="stdProfActionContainer"></div>
            </div>
            <div class="modal-footer border-0 p-4">
                <button type="button" class="btn btn-blue w-100 py-2 fw-bold" data-bs-dismiss="modal" style="border-radius: 12px;">Close Profile</button>
            </div>
        </div>
    </div>
</div>`;
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        modalEl = document.getElementById('agentProfileModal');
    }

    try {
        const res = await fetch(`/api/admin/user/${userId}`);
        if (!res.ok) throw new Error('Failed to fetch user');
        const user = await res.json();

        // Helper to safely set text content
        const setText = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
        
        // Populate fields
        setText('stdProfName', user.name);
        setText('stdProfUser', '@' + user.username);
        setText('stdProfBio', user.bio || 'No bio available.');
        
        // Populate Score - ensure it's properly set
        const scoreEl = document.getElementById('stdProfScore');
        if (scoreEl) {
            scoreEl.textContent = user.agent_score || 0;
        }

        const roleEl = document.getElementById('stdProfRole');
        if (roleEl) {
            // Add lightning symbol for ultra admins
            const roleText = user.role.replace('_', ' ').toUpperCase();
            roleEl.textContent = user.role === 'ultra_admin' ? '⚡ ' + roleText : roleText;
            
            // Set colors: Ultra Admin = Yellow, Super Admin = Dark Blue, Admin = Light Blue, Agent = Light Gray
            roleEl.className = 'badge rounded-pill px-3 py-2 border shadow-sm ' + 
                (user.role === 'ultra_admin' ? 'bg-warning text-dark' : 
                 (user.role === 'super_admin' ? 'bg-primary text-white' : 
                  (user.role === 'admin' ? 'bg-info text-white' : 'bg-light text-dark')));
        }

        // Profile Picture
        const picEl = document.getElementById('stdProfPic');
        const initEl = document.getElementById('stdProfInitials');
        if (user.profile_picture) {
            let picUrl = user.profile_picture.startsWith('http') ? user.profile_picture : `/static/uploads/${user.profile_picture}`;
            if (picEl) { picEl.src = picUrl; picEl.style.display = 'block'; }
            if (initEl) initEl.style.display = 'none';
        } else {
            if (initEl) {
                initEl.textContent = user.name ? user.name[0].toUpperCase() : '?';
                initEl.style.display = 'flex';
            }
            if (picEl) picEl.style.display = 'none';
        }

        // Team Section
        const teamSec = document.getElementById('stdProfTeamSection');
        if (user.team_id) {
            if (teamSec) teamSec.style.display = 'block';
            setText('stdProfTeamName', user.team_name);
            setText('stdProfTeamRole', (user.team_role || 'Member').toUpperCase());
            setText('stdProfTeamTag', user.team_tag || 'TEAM');
            
            const tPic = document.getElementById('stdProfTeamPic');
            const tInit = document.getElementById('stdProfTeamInitial');
            
            if (user.team_pic) {
                let tUrl = user.team_pic.includes('http') ? user.team_pic : `/static/uploads/${user.team_pic}`;
                if (tPic) { tPic.src = tUrl; tPic.style.display = 'block'; }
                if (tInit) tInit.style.display = 'none';
            } else {
                if (tInit) {
                    tInit.textContent = user.team_name ? user.team_name[0].toUpperCase() : 'T';
                    tInit.style.display = 'flex';
                }
                if (tPic) tPic.style.display = 'none';
            }
            
            // Make team section clickable to view team details
            if (teamSec) {
                teamSec.style.cursor = 'pointer';
                teamSec.onclick = () => {
                    // Close agent profile modal
                    const agentModal = bootstrap.Modal.getInstance(modalEl);
                    if (agentModal) agentModal.hide();
                    // Show team details modal after a brief delay
                    setTimeout(() => window.showTeamDetails(user.team_id), 300);
                };
                // Add hover effect
                teamSec.classList.add('hover-effect');
            }
        } else {
            if (teamSec) teamSec.style.display = 'none';
        }


        // Show Modal
        const modal = new bootstrap.Modal(modalEl);
        modal.show();

    } catch (e) {
        console.error("Error viewing profile:", e);
        // Fallback or basic alert if something goes wrong
        alert('Failed to load profile. Please try again.');
    }
};

/* ==========================================================================
   4. STANDARDIZED TEAM DETAILS MODAL
   ========================================================================== */
window.showTeamDetails = async function(teamId) {
    // Check if modal exists, or inject it
    let modalEl = document.getElementById('teamDetailsModal');
    
    if (!modalEl) {
        const modalHtml = `
<div class="modal fade" id="teamDetailsModal" tabindex="-1">
    <div class="modal-dialog modal-lg">
        <div class="modal-content border-0 shadow-lg" style="border-radius: 16px;">
            <div class="modal-header border-0 pb-0 pt-4 px-4">
                <h5 class="modal-title fw-bold" id="stdTeamTitle">Team Details</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body p-4">
                <!-- VIEW MODE -->
                <div id="stdTeamViewMode">
                    <div class="row mb-4">
                        <div class="col-md-4 text-center border-end">
                            <img id="stdTeamPic" src="" class="rounded mb-3 shadow-sm"
                                style="width: 100px; height: 100px; object-fit: cover;">
                            <div class="badge bg-primary-subtle text-primary px-3 py-2 mb-2" id="stdTeamTag">TAG</div>
                            <div class="small fw-bold text-muted mb-1">TEAM SCORE</div>
                            <div class="h4 fw-bold text-primary" id="stdTeamScore">0</div>
                        </div>
                        <div class="col-md-8 ps-4">
                            <div class="mb-3">
                                <label class="small fw-bold text-muted text-uppercase mb-1 d-block">Description</label>
                                <p id="stdTeamDesc" class="mb-0 text-dark" style="font-size: 0.95rem;"></p>
                            </div>
                            <div class="row">
                                <div class="col-6">
                                    <label class="small fw-bold text-muted text-uppercase mb-1 d-block">Role</label>
                                    <p id="stdTeamRole" class="fw-bold text-primary"></p>
                                </div>
                                <div class="col-6">
                                    <label class="small fw-bold text-muted text-uppercase mb-1 d-block">Department</label>
                                    <p id="stdTeamDept" class="fw-bold text-blue"></p>
                                </div>
                            </div>
                        </div>
                    </div>

                    <h6 class="fw-bold mb-3 border-bottom pb-2">Team Roster</h6>
                    <div class="table-responsive" style="max-height: 250px; overflow-y: auto;">
                        <table class="table table-sm align-middle">
                            <thead class="table-light small">
                                <tr>
                                    <th>Member</th>
                                    <th>Account Role</th>
                                    <th>Team Role</th>
                                </tr>
                            </thead>
                            <tbody id="stdTeamMembers"></tbody>
                        </table>
                    </div>
                </div>

                <!-- EDIT MODE -->
                <div id="stdTeamEditMode" style="display:none;">
                    <form id="stdEditTeamForm">
                        <div class="row g-3 mb-4">
                            <div class="col-md-8">
                                <label class="form-label small fw-bold">Team Name</label>
                                <input type="text" id="stdEditTeamName" name="name" class="form-control" required>
                            </div>
                            <div class="col-md-4">
                                <label class="form-label small fw-bold">Tag</label>
                                <input type="text" id="stdEditTeamTag" name="team_tag" class="form-control" maxlength="5">
                            </div>
                            <div class="col-12">
                                <label class="form-label small fw-bold">Description</label>
                                <textarea id="stdEditTeamDesc" name="description" class="form-control" rows="2"></textarea>
                            </div>
                            <div class="col-md-6">
                                <label class="form-label small fw-bold">Role / Purpose</label>
                                <input type="text" id="stdEditTeamRole" name="role" class="form-control">
                            </div>
                            <div class="col-md-6">
                                <label class="form-label small fw-bold">Department</label>
                                <input type="text" id="stdEditTeamDept" name="department" class="form-control">
                            </div>
                        </div>
                        <div class="text-end">
                            <button type="button" class="btn btn-light" id="stdCancelEditBtn">Cancel</button>
                            <button type="submit" class="btn btn-primary px-4">Save Changes</button>
                        </div>
                    </form>
                </div>

                <div class="d-flex justify-content-between align-items-center mt-3 pt-3 border-top" id="stdTeamFooter">
                    <div>
                         <button class="btn btn-outline-danger btn-sm" id="stdDeleteTeamBtn" style="display:none;">
                            <i class="bi bi-trash me-1"></i> Delete Team
                         </button>
                    </div>
                    <div class="d-flex gap-2">
                        <button class="btn btn-light" data-bs-dismiss="modal" id="stdCloseModalBtn">Close</button>
                        <button class="btn btn-outline-primary" id="stdEditTeamBtn" style="display:none;">Edit Team</button>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>`;
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        modalEl = document.getElementById('teamDetailsModal');

        // Attach event listeners for the modal elements (only once)
        document.getElementById('stdEditTeamBtn').onclick = () => toggleStdTeamEditMode(true);
        document.getElementById('stdCancelEditBtn').onclick = () => toggleStdTeamEditMode(false);
        
        document.getElementById('stdEditTeamForm').onsubmit = async (e) => {
            e.preventDefault();
            const tid = modalEl.getAttribute('data-team-id');
            const formData = new FormData(e.target);
            try {
                const res = await fetch(`/api/teams/${tid}/update`, {
                    method: 'POST',
                    body: formData
                });
                if (res.ok) location.reload();
                else alert("Failed to update team");
            } catch (err) { console.error(err); }
        };

        document.getElementById('stdDeleteTeamBtn').onclick = () => {
             const tid = modalEl.getAttribute('data-team-id');
             const name = document.getElementById('stdTeamName').textContent;
             if (confirm(`Are you sure you want to delete "${name}"? This will unassign all members.`)) {
                 fetch(`/api/teams/${tid}/delete`, { method: 'POST' })
                     .then(res => res.json())
                     .then(data => {
                         if (data.success) location.reload();
                         else alert(data.error || "Failed to delete team");
                     })
                     .catch(err => console.error(err));
             }
        };
    }

    // Helper to toggle edit mode
    const toggleStdTeamEditMode = (enable) => {
        document.getElementById('stdTeamViewMode').style.display = enable ? 'none' : 'block';
        document.getElementById('stdTeamEditMode').style.display = enable ? 'block' : 'none';
        document.getElementById('stdCloseModalBtn').style.display = enable ? 'none' : 'block';
        document.getElementById('stdEditTeamBtn').style.display = enable ? 'none' : (modalEl.getAttribute('data-can-edit') === 'true' ? 'block' : 'none');
        document.getElementById('stdDeleteTeamBtn').style.display = enable ? 'none' : (modalEl.getAttribute('data-can-edit') === 'true' ? 'block' : 'none');
        document.getElementById('stdTeamTitle').textContent = enable ? 'Edit Team Details' : 'Team Details';
    };

    try {
        const res = await fetch(`/api/teams/${teamId}/details`);
        if (!res.ok) throw new Error("Failed to load team");
        const data = await res.json();
        const team = data.team;

        modalEl.setAttribute('data-team-id', teamId);
        toggleStdTeamEditMode(false); // Reset to view mode

        // Determine if user has edit rights
        // Check global window variables or similar. Many pages provide session info.
        const myId = window.currUserId || 0; 
        const myRole = window.currUserRole || 'agent';
        // Fallback: If on create_account.html, we likely have access to some indicators
        // For now, simplify logic: if they are ultra/super admin, they can edit.
        // We can find the role from navigation if needed, or just let the API tell us later.
        // Better: Fetch current user if not available.
        
        let canEdit = false;
        // Attempt to find user role from common page elements if window variables aren't set
        const roleIndicator = document.body.getAttribute('data-user-role'); 
        const actualRole = myRole !== 'agent' ? myRole : (roleIndicator || '');
        
        if (actualRole === 'ultra_admin' || actualRole === 'super_admin') {
            canEdit = true;
        } else {
            // Check if they are the leader of this team
            const leader = data.members.find(m => m.username === window.currUsername && m.team_role === 'leader');
            if (leader) canEdit = true;
        }
        
        modalEl.setAttribute('data-can-edit', canEdit);
        document.getElementById('stdEditTeamBtn').style.display = canEdit ? 'block' : 'none';
        document.getElementById('stdDeleteTeamBtn').style.display = canEdit ? 'block' : 'none';

        // Helper to safely set text content
        const setText = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
        const setVal = (id, val) => { const el = document.getElementById(id); if (el) el.value = val; };

        // Populate view mode
        setText('stdTeamName', team.name);
        setText('stdTeamTag', team.team_tag || 'TEAM');
        setText('stdTeamScore', team.team_score || 0);
        setText('stdTeamDesc', team.description || 'No description.');
        setText('stdTeamRole', team.role || 'N/A');
        setText('stdTeamDept', team.department || 'General');

        // Populate edit mode fields
        setVal('stdEditTeamName', team.name);
        setVal('stdEditTeamTag', team.team_tag || '');
        setVal('stdEditTeamDesc', team.description || '');
        setVal('stdEditTeamRole', team.role || '');
        setVal('stdEditTeamDept', team.department || '');

        // Team picture
        const picEl = document.getElementById('stdTeamPic');
        if (picEl) {
            if (team.profile_picture) {
                picEl.src = team.profile_picture.includes('http') ? team.profile_picture : `/static/uploads/${team.profile_picture}`;
            } else {
                picEl.src = `https://ui-avatars.com/api/?name=${encodeURIComponent(team.name)}&background=random`;
            }
        }

        // Populate members table
        const membersBody = document.getElementById('stdTeamMembers');
        if (membersBody) {
            membersBody.innerHTML = '';
            data.members.forEach(m => {
                const tr = document.createElement('tr');
                const picUrl = (m.pic && m.pic.includes('http')) ? m.pic : (m.pic ? '/static/uploads/' + m.pic : 'https://ui-avatars.com/api/?name=' + encodeURIComponent(m.name));
                
                tr.innerHTML = `
                    <td>
                        <div class="d-flex align-items-center">
                            <img src="${picUrl}" 
                                 class="rounded-circle me-2" style="width:24px;height:24px;object-fit:cover;">
                            <div>
                                <div class="fw-bold small">${m.name}</div>
                                <div class="text-muted" style="font-size:0.7em">@${m.username}</div>
                            </div>
                        </div>
                    </td>
                    <td class="small">${m.role.replace('_', ' ')}</td>
                    <td><span class="badge bg-light text-dark border small" style="font-size:0.75em">${m.team_role || 'member'}</span></td>
                `;
                
                tr.style.cursor = 'pointer';
                tr.onclick = () => {
                    const teamModal = bootstrap.Modal.getInstance(modalEl);
                    if (teamModal) teamModal.hide();
                    setTimeout(() => window.showAgentProfile(m.id), 300);
                };
                
                membersBody.appendChild(tr);
            });
        }

        // Show Modal
        const modal = new bootstrap.Modal(modalEl);
        modal.show();

    } catch (err) {
        console.error(err);
        alert("Error loading team details");
    }
};
