const API_URL = "http://localhost:8000";

// --- Elements ---
const views = {
    login: document.getElementById('login-view'),
    main: document.getElementById('main-view')
};
const loginForm = document.getElementById('login-form');
const logoutBtn = document.getElementById('logout-btn');

// --- State ---
let userToken = null;
let userInfo = null;

// --- Init ---
document.addEventListener('DOMContentLoaded', async () => {
    const data = await chrome.storage.local.get(['token', 'user']);
    if (data.token) {
        userToken = data.token;
        userInfo = data.user;

        // Check if patient role
        if (userInfo.role !== 'patient') {
            await chrome.storage.local.clear();
            showLoginView();
            setStatus('Extension is for patients only', 'error');
            return;
        }

        showMainView();
    } else {
        showLoginView();
    }

    setupTabs();
});

// --- Auth ---
loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;

    try {
        const res = await fetch(`${API_URL}/api/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });

        if (!res.ok) throw new Error('Login failed');

        const data = await res.json();

        // Check if patient
        if (data.user_info.role !== 'patient') {
            document.getElementById('login-error').innerText = 'Extension is for patients only';
            return;
        }

        userToken = data.access_token;
        userInfo = data.user_info;

        await chrome.storage.local.set({
            token: userToken,
            user: userInfo
        });

        showMainView();
    } catch (err) {
        document.getElementById('login-error').innerText = err.message;
    }
});

logoutBtn.addEventListener('click', async () => {
    await chrome.storage.local.clear();
    userToken = null;
    userInfo = null;
    showLoginView();
});

function showLoginView() {
    views.login.classList.remove('hidden');
    views.main.classList.add('hidden');
}

function showMainView() {
    views.login.classList.add('hidden');
    views.main.classList.remove('hidden');
    document.querySelector('.user-info').innerHTML = `<span>👤 ${userInfo.full_name}</span>`;
}

// --- Tabs ---
function setupTabs() {
    const tabs = document.querySelectorAll('.tab-btn');
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.tab-btn').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

            tab.classList.add('active');
            const targetTab = document.getElementById(`${tab.dataset.tab}-tab`);
            targetTab.classList.add('active');

            // Load memories when switching to recall tab
            if (tab.dataset.tab === 'recall') {
                loadMemories();
            }
        });
    });
}

// --- Capture ---
document.getElementById('save-note-btn').addEventListener('click', async () => {
    const note = document.getElementById('note-input').value;
    const tags = document.getElementById('tags-input').value;
    const location = document.getElementById('location-input').value;

    if (!note) {
        setStatus('Please enter a note', 'error');
        return;
    }

    try {
        const data = {
            content: note,
            patient_id: userInfo.patient_id || userInfo.username
        };

        if (tags) data.tags = tags;
        if (location) {
            // Simple location text for now
            data.location_text = location;
        }

        await saveMemory(data);
        document.getElementById('note-input').value = '';
        document.getElementById('tags-input').value = '';
        document.getElementById('location-input').value = '';
        setStatus('Note saved!', 'success');
    } catch (err) {
        setStatus(err.message, 'error');
    }
});

async function saveMemory(data) {
    const res = await fetch(`${API_URL}/api/memory/create`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${userToken}`
        },
        body: JSON.stringify(data)
    });
    if (!res.ok) throw new Error('Failed to save');
    return res.json();
}

// --- Audio Removed ---

// --- Recall / Memory Lane ---
async function loadMemories() {
    const container = document.getElementById('memory-list');
    container.innerHTML = '<div class="loading">Loading memories...</div>';

    try {
        const patientId = userInfo.patient_id || userInfo.username;
        const res = await fetch(`${API_URL}/api/memories/${patientId}?limit=20`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${userToken}`
            }
        });

        if (!res.ok) throw new Error('Failed to load');

        const data = await res.json();
        renderMemories(data.memories || []);
    } catch (err) {
        container.innerHTML = `<div class="error">Failed to load memories: ${err.message}</div>`;
    }
}

function renderMemories(memories) {
    const container = document.getElementById('memory-list');

    if (!memories || memories.length === 0) {
        container.innerHTML = '<div class="empty">No memories yet. Start capturing!</div>';
        return;
    }

    container.innerHTML = '';

    memories.forEach(mem => {
        const div = document.createElement('div');
        div.className = 'memory-item';

        let content = mem.content || mem.caption || mem.transcript || mem.analysis || 'No content';
        let icon = '📝';

        if (mem.type === 'image') icon = '🖼️';
        else if (mem.type === 'audio') icon = '🎤';
        else if (mem.type === 'video') icon = '📹';

        const date = new Date(mem.timestamp * 1000).toLocaleDateString();
        const time = new Date(mem.timestamp * 1000).toLocaleTimeString();

        div.innerHTML = `
            <div class="memory-header">
                <span class="memory-icon">${icon}</span>
                <span class="memory-type">${mem.type}</span>
            </div>
            <div class="memory-content">${content.substring(0, 150)}${content.length > 150 ? '...' : ''}</div>
            <div class="memory-meta">
                <span>📅 ${date} ${time}</span>
                ${mem.person_tags ? `<span>👤 ${mem.person_tags}</span>` : ''}
                ${mem.location ? `<span>📍 ${mem.location.name || 'Location'}</span>` : ''}
            </div>
        `;

        container.appendChild(div);
    });
}

// --- Search ---
document.getElementById('search-btn').addEventListener('click', async () => {
    const query = document.getElementById('search-input').value;

    if (!query) {
        setStatus('Please enter a search query', 'error');
        return;
    }

    const container = document.getElementById('memory-list');
    container.innerHTML = '<div class="loading">Searching...</div>';

    try {
        const res = await fetch(`${API_URL}/api/search`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${userToken}`
            },
            body: JSON.stringify({
                query,
                patient_id: userInfo.patient_id || userInfo.username,
                top_k: 10
            })
        });

        if (!res.ok) throw new Error('Search failed');

        const data = await res.json();

        // Show AI answer if available
        if (data.answer) {
            const answerDiv = document.createElement('div');
            answerDiv.className = 'ai-answer';
            answerDiv.innerHTML = `<strong>💡 AI Answer:</strong><br>${data.answer}`;
            container.innerHTML = '';
            container.appendChild(answerDiv);
        }

        renderMemories(data.memories || []);
    } catch (err) {
        container.innerHTML = `<div class="error">Search failed: ${err.message}</div>`;
    }
});

// --- Helpers ---
function setStatus(msg, type) {
    const el = document.getElementById('status-msg');
    el.innerText = msg;
    el.className = 'status-msg ' + type;
    setTimeout(() => { el.innerText = ''; el.className = 'status-msg'; }, 3000);
}

let timerInterval;
function startTimer() {
    let sec = 0;
    const el = document.getElementById('timer');
    el.innerText = '00:00';
    timerInterval = setInterval(() => {
        sec++;
        const m = Math.floor(sec / 60).toString().padStart(2, '0');
        const s = (sec % 60).toString().padStart(2, '0');
        el.innerText = `${m}:${s}`;
    }, 1000);
}
function stopTimer() { clearInterval(timerInterval); }
