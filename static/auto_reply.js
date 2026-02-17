// Global State for Auto-Reply Manager
let templates = [];
let faqs = [];
let currentKeywords = [];
let faqToggling = false; // Prevent rapid toggling
let faqSectionOpen = false; // Track if FAQ section should be open
let toggleCallCount = 0; // Count how many times toggle is called

function initializeApp() {
    // Only run this logic if we are on the templates page
    if (document.body.id !== 'page-templates') return;

    console.log('Initializing Auto-Reply Template Manager');
    loadTemplates();
    loadFAQs();
    initializeTabs();
    initializeStatCards();
    setupFAQToggle();

    // Listen for Enter key on chat input
    const chatInput = document.getElementById('chatInput');
    if (chatInput) {
        chatInput.addEventListener('keypress', function (e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                sendMessage();
            }
        });
    }

    // Periodic enforcement of FAQ state (every 500ms)
    setInterval(() => {
        if (faqSectionOpen) {
            // Only log when state is open to reduce console spam
            const section = document.getElementById('chatFaqSection');
            if (section && section.style.display === 'none') {
                console.warn('FAQ section closed unexpectedly! Reopening...');
            }
        }
        enforceFAQSectionState();
    }, 500);
}

function setupFAQToggle() {
    const btn = document.getElementById('showFaqButton');
    const hideBtn = document.querySelector('[id="chatFaqSection"] button.btn-link');

    if (btn) {
        btn.addEventListener('click', function (e) {
            e.stopPropagation();
            e.preventDefault();
            console.log('Show FAQ button clicked');
            toggleChatFAQ(null);
        });
    }

    if (hideBtn) {
        hideBtn.addEventListener('click', function (e) {
            e.stopPropagation();
            e.preventDefault();
            console.log('Hide FAQ button clicked');
            toggleChatFAQ(null);
        });
    }
}

// Run initialization when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeApp);
} else {
    // If script is loaded at the end of body, DOM is already ready
    initializeApp();
}

// --- TABS LOGIC ---
function initializeTabs() {
    document.querySelectorAll('.tab-button').forEach(btn => {
        btn.addEventListener('click', () => {
            // Remove active class from all buttons and contents
            document.querySelectorAll('.tab-button').forEach(b => b.classList.remove('active', 'text-primary', 'fw-bold'));
            document.querySelectorAll('.tab-button').forEach(b => b.classList.add('text-muted'));
            document.querySelectorAll('.tab-pane').forEach(c => c.classList.remove('active'));

            // Activate clicked tab
            btn.classList.add('active', 'fw-bold');
            btn.classList.remove('text-muted');
            const tabId = btn.getAttribute('data-tab') + '-tab';
            document.getElementById(tabId).classList.add('active');
        });
    });

    // Search Listeners
    document.getElementById('searchInput')?.addEventListener('input', renderTemplates);
    document.getElementById('categoryFilter')?.addEventListener('change', renderTemplates);
    document.getElementById('faqSearchInput')?.addEventListener('input', renderFAQs);
    document.getElementById('faqCategoryFilter')?.addEventListener('change', renderFAQs);

    // Form Submits
    document.getElementById('templateForm')?.addEventListener('submit', handleTemplateSubmit);
    document.getElementById('faqForm')?.addEventListener('submit', handleFAQSubmit);
}

// --- TOAST NOTIFICATIONS ---
function showToast(message, type = 'success', duration = 3000) {
    console.log('showToast called:', message, type);

    const container = document.getElementById('toastContainer');
    console.log('Toast container:', container);

    if (!container) {
        console.error('Toast container not found!');
        return;
    }

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    const icons = {
        'success': '✓',
        'error': '✕',
        'info': 'ℹ',
        'warning': '⚠'
    };

    toast.innerHTML = `
        <div class="toast-message">
            <span class="toast-icon">${icons[type] || icons['info']}</span>
            <span class="toast-text">${message}</span>
        </div>
        <button class="toast-close" onclick="this.parentElement.remove()">×</button>
    `;

    container.appendChild(toast);
    console.log('Toast appended to container');

    // Auto remove after duration
    setTimeout(() => {
        if (toast.parentElement) {
            toast.classList.add('removing');
            setTimeout(() => toast.remove(), 300);
        }
    }, duration);
}

// --- STAT CARDS INTERACTION ---
function initializeStatCards() {
    const statCards = document.querySelectorAll('.row.g-4 .card');

    statCards.forEach((card, index) => {
        card.addEventListener('click', () => {
            if (index === 0) {
                // Click on Total Templates card -> go to templates tab
                const templatesBtn = document.querySelector('[data-tab="templates"]');
                if (templatesBtn) templatesBtn.click();
                console.log('Navigating to Templates tab');
            } else if (index === 1) {
                // Click on Total FAQs card -> go to FAQs tab
                const faqsBtn = document.querySelector('[data-tab="faqs"]');
                if (faqsBtn) faqsBtn.click();
                console.log('Navigating to FAQs tab');
            } else if (index === 2) {
                // Click on Total Usage card -> scroll to top and highlight
                document.querySelector('.main').scrollTop = 0;
                console.log('Showing usage stats');
            }
        });

        // Add hover effect feedback
        card.addEventListener('mouseenter', () => {
            card.style.cursor = 'pointer';
        });
    });
}

// --- TEMPLATE MANAGEMENT ---
async function loadTemplates() {
    try {
        const res = await fetch('/api/templates');
        if (!res.ok) throw new Error('Failed to fetch templates');
        templates = await res.json();
    } catch (error) {
        console.error('Error loading templates:', error);
        templates = [];
    }
    renderTemplates();
    updateStats();
}

function renderTemplates() {
    const searchInput = document.getElementById('searchInput');
    const categoryFilter = document.getElementById('categoryFilter');
    const container = document.getElementById('templateList');

    if (!container) {
        console.error('Template list container not found');
        return;
    }

    const search = searchInput ? searchInput.value.toLowerCase() : '';
    const cat = categoryFilter ? categoryFilter.value : '';

    const filtered = templates.filter(t => {
        const matchSearch = t.title.toLowerCase().includes(search) || t.message.toLowerCase().includes(search);
        const matchCat = cat === "" || t.category === cat;
        return matchSearch && matchCat;
    });

    container.innerHTML = filtered.map(t => `
        <div class="template-card">
            <div class="template-header">
                <div>
                    <h5 class="mb-1">${t.title}</h5>
                    <span class="category-badge">${t.category}</span>
                </div>
                <div>
                    <button class="btn btn-sm btn-link" onclick="editTemplate(${t.id})">Edit</button>
                    <button class="btn btn-sm btn-link text-danger" onclick="deleteTemplate(${t.id})">Del</button>
                </div>
            </div>
            <p class="text-muted small mb-2">${t.message.substring(0, 100)}...</p>
            <div class="mb-2">
                ${t.keywords.map(k => `<span class="badge bg-light text-dark border">${k}</span>`).join(' ')}
            </div>
            <div class="small text-muted mt-auto pt-2 border-top d-flex justify-content-between flex-wrap">
                <span>Used: ${t.usageCount} times</span>
                <span>Edit: ${t.updated_at || 'Recently'} by ${t.updated_by || 'System'}</span>
            </div>
        </div>
    `).join('');
}

// --- FAQ MANAGEMENT ---
async function loadFAQs() {
    try {
        const res = await fetch('/api/faqs');
        if (!res.ok) throw new Error('Failed to fetch FAQs');
        faqs = await res.json();
        console.log('FAQs loaded successfully:', faqs);
    } catch (error) {
        console.error('Error loading FAQs:', error);
        faqs = [];
    }
    renderFAQs();
    // Only try to render chat FAQs if the containers exist
    try {
        if (document.getElementById('chatFaqList') && document.getElementById('chatFaqFilters')) {
            console.log('Chat FAQ containers exist, rendering...');
            renderChatFAQs();
        } else {
            console.log('Chat FAQ containers not visible yet, skipping render');
        }
    } catch (error) {
        console.error('Error rendering chat FAQs:', error);
    }
    updateStats();

    // Enforce the FAQ section state
    enforceFAQSectionState();
}

function enforceFAQSectionState() {
    const section = document.getElementById('chatFaqSection');
    const btn = document.getElementById('showFaqButton');

    if (!section || !btn) {
        return;
    }

    const actualDisplay = section.style.display;
    const shouldBeOpen = faqSectionOpen;

    // If section should be open but is closed, open it
    if (shouldBeOpen && actualDisplay === 'none') {
        console.warn('ENFORCEMENT: FAQ should be OPEN but is CLOSED! Fixing...');
        section.style.display = 'block';
        btn.style.display = 'none';
    }
    // If section should be closed but is open, close it  
    else if (!shouldBeOpen && actualDisplay !== 'none') {
        console.log('ENFORCEMENT: FAQ should be CLOSED but is OPEN. Closing...');
        section.style.display = 'none';
        btn.style.display = 'block';
    }
}

function renderFAQs() {
    const faqSearchInput = document.getElementById('faqSearchInput');
    const faqCategoryFilter = document.getElementById('faqCategoryFilter');
    const container = document.getElementById('faqList');

    if (!container) {
        console.error('FAQ list container not found');
        return;
    }

    const search = faqSearchInput ? faqSearchInput.value.toLowerCase() : '';
    const cat = faqCategoryFilter ? faqCategoryFilter.value : '';

    const filtered = faqs.filter(f => {
        const matchSearch = f.question.toLowerCase().includes(search);
        const matchCat = cat === "" || f.category === cat;
        return matchSearch && matchCat;
    });

    container.innerHTML = filtered.map(f => `
        <div class="faq-card">
            <div class="faq-header">
                <div>
                    <h6 class="mb-1 fw-bold">${f.question}</h6>
                    <span class="category-badge">${f.category}</span>
                </div>
                <div>
                    <button class="btn btn-sm btn-link" onclick="editFAQ(${f.id})">Edit</button>
                    <button class="btn btn-sm btn-link text-danger" onclick="deleteFAQ(${f.id})">Del</button>
                </div>
            </div>
            <p class="text-muted small">${f.answer}</p>
            <div class="small text-muted mt-auto pt-2 border-top d-flex justify-content-between flex-wrap">
                <span>Clicks: ${f.clickCount}</span>
                <span>Edit: ${f.updated_at || 'Recently'} by ${f.updated_by || 'System'}</span>
            </div>
        </div>
    `).join('');
}

// --- MODAL & FORM LOGIC ---

// Template Modal
function openTemplateModal(mode, id = null) {
    const modal = document.getElementById('templateModal');
    modal.style.display = 'flex'; // Flex to center
    currentKeywords = [];

    if (mode === 'edit') {
        const t = templates.find(x => x.id === id);
        document.getElementById('templateId').value = t.id;
        document.getElementById('templateTitle').value = t.title;
        document.getElementById('templateCategory').value = t.category;
        document.getElementById('templateMessage').value = t.message;
        currentKeywords = [...t.keywords];
        document.getElementById('templateModalTitle').innerText = 'Edit Template';
    } else {
        document.getElementById('templateForm').reset();
        document.getElementById('templateId').value = '';
        document.getElementById('templateModalTitle').innerText = 'Create Template';
    }
    renderKeywords();
}

function closeTemplateModal() { document.getElementById('templateModal').style.display = 'none'; }

function addKeyword() {
    const val = document.getElementById('keywordInput').value.trim();
    if (val && !currentKeywords.includes(val)) {
        currentKeywords.push(val);
        document.getElementById('keywordInput').value = '';
        renderKeywords();
    }
}

function renderKeywords() {
    document.getElementById('keywordList').innerHTML = currentKeywords.map(k => `
        <span class="keyword-tag">${k} <button type="button" onclick="removeKeyword('${k}')">×</button></span>
    `).join('');
}

function removeKeyword(k) {
    currentKeywords = currentKeywords.filter(x => x !== k);
    renderKeywords();
}

async function handleTemplateSubmit(e) {
    e.preventDefault();
    const id = document.getElementById('templateId').value;
    const title = document.getElementById('templateTitle').value;
    const data = {
        title: title,
        category: document.getElementById('templateCategory').value,
        message: document.getElementById('templateMessage').value,
        keywords: currentKeywords
    };

    const url = id ? `/api/templates/${id}` : '/api/templates';
    const method = id ? 'PUT' : 'POST';
    const isCreate = !id;

    await fetch(url, {
        method: method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });

    closeTemplateModal();
    loadTemplates();

    // Show toast notification
    if (isCreate) {
        showToast(`Template "${title}" created successfully`, 'success');
    } else {
        showToast(`Template "${title}" updated successfully`, 'success');
    }
}

function deleteTemplate(id) {
    const template = templates.find(t => t.id === id);
    const templateTitle = template ? template.title : 'Template';

    const overlay = document.getElementById('confirmOverlay');
    if (!overlay) {
        // Fallback if overlay doesn't exist
        if (confirm("Delete this template?")) {
            executeDeleteTemplate(id, templateTitle);
        }
        return;
    }

    overlay.style.display = 'flex';
    overlay.className = 'confirm-overlay';
    overlay.innerHTML = `
        <div class="confirm-card">
            <h3>🗑️ Delete Template</h3>
            <p>Are you sure you want to delete the template "<strong>${templateTitle}</strong>"? This action cannot be undone.</p>
            <div class="btn-group">
                <button class="btn btn-gray" onclick="document.getElementById('confirmOverlay').style.display='none'">Cancel</button>
                <button class="btn btn-sm" style="background:#dc2626;color:white;" onclick="executeDeleteTemplate(${id}, '${templateTitle.replace(/'/g, "\\'")}')">Delete</button>
            </div>
        </div>
    `;
}

async function executeDeleteTemplate(id, templateTitle) {
    document.getElementById('confirmOverlay').style.display = 'none';
    await fetch(`/api/templates/${id}`, { method: 'DELETE' });
    loadTemplates();
    showToast(`Template "${templateTitle}" deleted successfully`, 'success');
}

// FAQ Modal Logic (Simplified)
function openFAQModal(mode, id = null) {
    const modal = document.getElementById('faqModal');
    modal.style.display = 'flex';
    if (mode === 'edit') {
        const f = faqs.find(x => x.id === id);
        document.getElementById('faqId').value = f.id;
        document.getElementById('faqQuestion').value = f.question;
        document.getElementById('faqAnswer').value = f.answer;
        document.getElementById('faqCategory').value = f.category;
    } else {
        document.getElementById('faqForm').reset();
        document.getElementById('faqId').value = '';
    }
}
function closeFAQModal() { document.getElementById('faqModal').style.display = 'none'; }

async function handleFAQSubmit(e) {
    e.preventDefault();
    const id = document.getElementById('faqId').value;
    const question = document.getElementById('faqQuestion').value;
    const data = {
        question: question,
        answer: document.getElementById('faqAnswer').value,
        category: document.getElementById('faqCategory').value
    };
    const url = id ? `/api/faqs/${id}` : '/api/faqs';
    const method = id ? 'PUT' : 'POST';
    const isCreate = !id;

    await fetch(url, { method: method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
    closeFAQModal();
    loadFAQs();

    // Show toast notification
    if (isCreate) {
        showToast(`FAQ question created successfully`, 'success');
    } else {
        showToast(`FAQ question updated successfully`, 'success');
    }
}

async function deleteFAQ(id) {
    const overlay = document.getElementById('confirmOverlay');
    if (!overlay) {
        // Fallback if overlay doesn't exist
        if (confirm("Delete this FAQ?")) {
            executeDeleteFAQ(id);
        }
        return;
    }

    overlay.style.display = 'flex';
    overlay.className = 'confirm-overlay';
    overlay.innerHTML = `
        <div class="confirm-card">
            <h3>🗑️ Delete FAQ</h3>
            <p>Are you sure you want to delete this FAQ? This action cannot be undone.</p>
            <div class="btn-group">
                <button class="btn btn-gray" onclick="document.getElementById('confirmOverlay').style.display='none'">Cancel</button>
                <button class="btn btn-sm" style="background:#dc2626;color:white;" onclick="executeDeleteFAQ(${id})">Delete</button>
            </div>
        </div>
    `;
}

async function executeDeleteFAQ(id) {
    document.getElementById('confirmOverlay').style.display = 'none';
    await fetch(`/api/faqs/${id}`, { method: 'DELETE' });
    loadFAQs();
    showToast(`FAQ deleted successfully`, 'success');
}

// Global expose for onclick
window.editTemplate = (id) => openTemplateModal('edit', id);
window.deleteTemplate = deleteTemplate;
window.executeDeleteTemplate = executeDeleteTemplate;
window.editFAQ = (id) => openFAQModal('edit', id);
window.deleteFAQ = deleteFAQ;
window.executeDeleteFAQ = executeDeleteFAQ;

// --- STATS ---
function updateStats() {
    // Safely update stats with null checks
    const totalTemplatesEl = document.getElementById('totalTemplates');
    const totalFAQsEl = document.getElementById('totalFAQs');
    const totalUsageEl = document.getElementById('totalUsage');

    console.log('Updating stats - Templates:', templates.length, 'FAQs:', faqs.length);

    if (totalTemplatesEl) {
        totalTemplatesEl.innerText = templates.length || 0;
        console.log('Updated Total Templates to:', templates.length);
    } else {
        console.error('totalTemplates element not found');
    }

    if (totalFAQsEl) {
        totalFAQsEl.innerText = faqs.length || 0;
        console.log('Updated Total FAQs to:', faqs.length);
    } else {
        console.error('totalFAQs element not found');
    }

    if (totalUsageEl) {
        const tUsage = templates.reduce((acc, curr) => acc + (curr.usageCount || 0), 0);
        const fUsage = faqs.reduce((acc, curr) => acc + (curr.clickCount || 0), 0);
        const totalUsage = tUsage + fUsage;
        totalUsageEl.innerText = totalUsage || 0;
        console.log('Updated Total Usage to:', totalUsage);
    } else {
        console.error('totalUsage element not found');
    }
}

// --- CHAT PREVIEW LOGIC ---
function toggleChatFAQ(e) {
    toggleCallCount++;
    const callNum = toggleCallCount;
    const timestamp = new Date().getTime();

    // Prevent event bubbling
    if (e) {
        e.stopPropagation();
        e.preventDefault();
    }

    console.log(`[${callNum}] toggleChatFAQ called at ${timestamp}`);

    const section = document.getElementById('chatFaqSection');
    const btn = document.getElementById('showFaqButton');

    if (!section || !btn) {
        console.error(`[${callNum}] FAQ elements not found`);
        return;
    }

    const wasOpen = section.style.display === 'block';
    console.log(`[${callNum}] wasOpen: ${wasOpen}`);

    // Force toggle directly with inline styles
    if (wasOpen) {
        console.log(`[${callNum}] Closing FAQ section`);
        section.style.display = 'none !important';
        btn.style.display = 'block !important';
        faqSectionOpen = false;
    } else {
        console.log(`[${callNum}] Opening FAQ section`);
        section.style.display = 'block !important';
        btn.style.display = 'none !important';
        faqSectionOpen = true;

        // Render FAQs if they exist
        if (faqs && faqs.length > 0) {
            console.log(`[${callNum}] Rendering FAQs`);
            renderChatFAQs();
        }
    }
}

function renderChatFAQs(cat = 'All', e) {
    if (e) e.stopPropagation();

    console.log('renderChatFAQs called with category:', cat);
    console.log('FAQs available:', faqs);

    // Check if elements exist
    const filterContainer = document.getElementById('chatFaqFilters');
    const listContainer = document.getElementById('chatFaqList');

    console.log('Filter container:', filterContainer);
    console.log('List container:', listContainer);

    if (!filterContainer || !listContainer) {
        console.warn('Chat FAQ containers not found - elements may not be rendered yet');
        return;
    }

    // Guard check for faqs data
    if (!faqs || !Array.isArray(faqs)) {
        console.warn('FAQs data is not an array:', faqs);
        listContainer.innerHTML = '<p class="text-muted">No FAQs available</p>';
        return;
    }

    // 1. Render Filters
    const cats = ['All', ...new Set(faqs.map(f => f.category))];
    console.log('Categories found:', cats);

    filterContainer.innerHTML = cats.map(c => `
        <button class="filter-btn ${c === cat ? 'active' : ''}" onclick="renderChatFAQs('${c}', event); event.stopPropagation();">${c}</button>
    `).join('');

    // 2. Render List
    const filtered = cat === 'All' ? faqs : faqs.filter(f => f.category === cat);
    console.log('Filtered FAQs:', filtered);

    if (filtered.length === 0) {
        listContainer.innerHTML = '<p class="text-muted">No FAQs in this category</p>';
    } else {
        listContainer.innerHTML = filtered.map(f => `
            <div class="customer-faq-item" id="chat-faq-${f.id}" onclick="event.stopPropagation();">
                <div class="customer-faq-question" onclick="toggleChatFAQItem(${f.id}, event)">
                    <span>${f.question}</span>
                    <small>▼</small>
                </div>
                <div class="customer-faq-answer">${f.answer}</div>
            </div>
        `).join('');
    }

    console.log('Chat FAQs rendered successfully');
}

function toggleChatFAQItem(id, e) {
    if (e) e.stopPropagation();

    console.log('toggleChatFAQItem called with id:', id);

    // Find the FAQ object
    const f = faqs.find(x => x.id === id);
    if (!f) {
        console.error('FAQ not found in local data:', id);
        return;
    }

    // 1. Simulate user ask
    addMsg(f.question, 'user');

    // 2. Hide FAQ list
    const section = document.getElementById('chatFaqSection');
    const btn = document.getElementById('showFaqButton');

    if (section) {
        section.style.display = 'none';
        // Force the inline style override
        section.setAttribute('style', 'display: none !important; background:#f8f9fa;');
    }
    if (btn) {
        btn.style.display = 'block';
        btn.setAttribute('style', 'display: block !important; cursor: pointer;');
    }
    faqSectionOpen = false;

    // 3. Simulate bot answer
    setTimeout(() => {
        addMsg(f.answer, 'bot', 'FAQ');
    }, 500);

    // 4. Increment stats
    fetch(`/api/faqs/${id}/click`, { method: 'POST' }).then(() => {
        console.log('FAQ click count incremented');
        loadFAQs(); // Reload FAQs to update stats
    }).catch(err => {
        console.error('Error incrementing FAQ click count:', err);
    });
}

async function sendMessage() {
    const input = document.getElementById('chatInput');
    const txt = input.value.trim();
    if (!txt) return;

    input.value = '';
    addMsg(txt, 'user');

    try {
        // Send to backend
        const res = await fetch('/api/auto-reply', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: txt })
        });
        const data = await res.json();

        if (data.replies && data.replies.length > 0) {
            data.replies.forEach(r => addMsg(r, 'bot', data.source));
        } else {
            addMsg("Sorry, I couldn't find a suitable response.", 'bot');
        }

        // Reload templates and FAQs to update usage counts in real-time
        await loadTemplates();
        await loadFAQs();
    } catch (error) {
        addMsg("Sorry, there was an error processing your message.", 'bot');
    }
}

function addMsg(txt, sender, source = '') {
    const div = document.createElement('div');
    const classes = sender === 'user' ? 'bg-white border ms-auto' : 'bg-light';
    const align = sender === 'user' ? 'align-self-end' : 'align-self-start';

    div.className = `message-bubble ${classes} ${align} rounded p-2 mb-2`;
    div.style.maxWidth = '80%';
    div.innerHTML = `
        <div class="message-content">${txt}</div>
        ${source ? `<div class="message-meta"><span class="response-source">${source}</span></div>` : ''}
    `;
    document.getElementById('chatMessages').appendChild(div);
    document.getElementById('chatMessages').scrollTop = 9999;
}