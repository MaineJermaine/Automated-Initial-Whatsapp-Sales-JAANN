// Global State for Auto-Reply Manager
let templates = [];
let faqs = [];
let currentKeywords = [];

document.addEventListener('DOMContentLoaded', function () {
    // Only run this logic if we are on the templates page
    if (document.body.id !== 'page-templates') return;

    loadTemplates();
    loadFAQs();
    initializeTabs();
});

// --- TABS LOGIC ---
function initializeTabs() {
    document.querySelectorAll('.tab-button').forEach(btn => {
        btn.addEventListener('click', () => {
            // Remove active class from all buttons and contents
            document.querySelectorAll('.tab-button').forEach(b => b.classList.remove('active', 'text-primary', 'fw-bold'));
            document.querySelectorAll('.tab-button').forEach(b => b.classList.add('text-muted'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

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

// --- TEMPLATE MANAGEMENT ---
async function loadTemplates() {
    const res = await fetch('/api/templates');
    templates = await res.json();
    renderTemplates();
    updateStats();
}

function renderTemplates() {
    const search = document.getElementById('searchInput').value.toLowerCase();
    const cat = document.getElementById('categoryFilter').value;
    const container = document.getElementById('templateList');

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
            <div class="small text-muted mt-auto pt-2 border-top d-flex justify-content-between">
                <span>Used: ${t.usageCount} times</span>
            </div>
        </div>
    `).join('');
}

// --- FAQ MANAGEMENT ---
async function loadFAQs() {
    const res = await fetch('/api/faqs');
    faqs = await res.json();
    renderFAQs();
    renderChatFAQs(); // Update chat view too
    updateStats();
}

function renderFAQs() {
    const search = document.getElementById('faqSearchInput').value.toLowerCase();
    const cat = document.getElementById('faqCategoryFilter').value;
    const container = document.getElementById('faqList');

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
            <div class="small text-muted mt-auto pt-2 border-top">
                <span>Clicks: ${f.clickCount}</span>
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
    const data = {
        title: document.getElementById('templateTitle').value,
        category: document.getElementById('templateCategory').value,
        message: document.getElementById('templateMessage').value,
        keywords: currentKeywords
    };

    const url = id ? `/api/templates/${id}` : '/api/templates';
    const method = id ? 'PUT' : 'POST';

    await fetch(url, {
        method: method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });

    closeTemplateModal();
    loadTemplates();
}

async function deleteTemplate(id) {
    if (confirm("Delete this template?")) {
        await fetch(`/api/templates/${id}`, { method: 'DELETE' });
        loadTemplates();
    }
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
    const data = {
        question: document.getElementById('faqQuestion').value,
        answer: document.getElementById('faqAnswer').value,
        category: document.getElementById('faqCategory').value
    };
    const url = id ? `/api/faqs/${id}` : '/api/faqs';
    const method = id ? 'PUT' : 'POST';

    await fetch(url, { method: method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
    closeFAQModal();
    loadFAQs();
}

async function deleteFAQ(id) {
    if (confirm("Delete this FAQ?")) {
        await fetch(`/api/faqs/${id}`, { method: 'DELETE' });
        loadFAQs();
    }
}

// Global expose for onclick
window.editTemplate = (id) => openTemplateModal('edit', id);
window.deleteTemplate = deleteTemplate;
window.editFAQ = (id) => openFAQModal('edit', id);
window.deleteFAQ = deleteFAQ;

// --- STATS ---
function updateStats() {
    document.getElementById('totalTemplates').innerText = templates.length;
    document.getElementById('totalFAQs').innerText = faqs.length;

    const tUsage = templates.reduce((acc, curr) => acc + (curr.usageCount || 0), 0);
    const fUsage = faqs.reduce((acc, curr) => acc + (curr.clickCount || 0), 0);
    document.getElementById('totalUsage').innerText = tUsage + fUsage;
}

// --- CHAT PREVIEW LOGIC ---
function toggleChatFAQ() {
    const section = document.getElementById('chatFaqSection');
    const btn = document.getElementById('showFaqButton');
    if (section.style.display === 'none') {
        section.style.display = 'block';
        btn.style.display = 'none';
        renderChatFAQs();
    } else {
        section.style.display = 'none';
        btn.style.display = 'block';
    }
}

function renderChatFAQs(cat = 'All') {
    // 1. Render Filters
    const cats = ['All', ...new Set(faqs.map(f => f.category))];
    document.getElementById('chatFaqFilters').innerHTML = cats.map(c => `
        <button class="filter-btn ${c === cat ? 'active' : ''}" onclick="renderChatFAQs('${c}')">${c}</button>
    `).join('');

    // 2. Render List
    const list = document.getElementById('chatFaqList');
    const filtered = cat === 'All' ? faqs : faqs.filter(f => f.category === cat);

    list.innerHTML = filtered.map(f => `
        <div class="customer-faq-item" id="chat-faq-${f.id}">
            <div class="customer-faq-question" onclick="toggleChatFAQItem(${f.id})">
                <span>${f.question}</span>
                <small>▼</small>
            </div>
            <div class="customer-faq-answer">${f.answer}</div>
        </div>
    `).join('');
}

function toggleChatFAQItem(id) {
    document.getElementById(`chat-faq-${id}`).classList.toggle('open');
    // Optional: Hit API to increment click count
    fetch(`/api/faqs/${id}/click`, { method: 'POST' });
}

async function sendMessage() {
    const input = document.getElementById('chatInput');
    const txt = input.value.trim();
    if (!txt) return;

    input.value = '';
    addMsg(txt, 'user');

    // Send to backend
    const res = await fetch('/api/auto-reply', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: txt })
    });
    const data = await res.json();

    data.replies.forEach(r => addMsg(r, 'bot', data.source));
    if (data.source === 'template') loadTemplates(); // Update stats
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