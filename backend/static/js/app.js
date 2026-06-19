const TOKEN_KEY = 'dafterdocs_token';
const USER_KEY = 'dafterdocs_user';

function getToken() {
  return window.localStorage.getItem(TOKEN_KEY);
}

function getUser() {
  const raw = window.localStorage.getItem(USER_KEY);
  if (!raw) {
    return null;
  }

  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

function storeSession(payload) {
  window.localStorage.setItem(TOKEN_KEY, payload.token);
  window.localStorage.setItem(USER_KEY, JSON.stringify(payload.user));
}

function clearSession() {
  window.localStorage.removeItem(TOKEN_KEY);
  window.localStorage.removeItem(USER_KEY);
}

function showFeedback(message, tone = 'error') {
  const el = document.getElementById('auth-feedback');
  if (!el) {
    return;
  }

  el.className = `rounded-2xl border px-4 py-3 text-sm ${
    tone === 'success'
      ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
      : 'border-red-200 bg-red-50 text-red-700'
  }`;
  el.textContent = message;
}

function requireAuth(page) {
  const token = getToken();
  if (!token && page === 'workspace') {
    window.location.href = '/';
    return false;
  }

  if (token && page === 'auth') {
    window.location.href = '/workspace';
    return false;
  }

  return true;
}

async function submitAuthForm(event) {
  event.preventDefault();

  const form = event.currentTarget;
  const mode = form.dataset.authMode;
  const endpoint = mode === 'register' ? '/api/auth/register' : '/api/auth/login';
  const formData = new FormData(form);
  const payload = Object.fromEntries(formData.entries());

  try {
    const response = await fetch(endpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || 'Authentication failed.');
    }

    storeSession(data);
    window.location.href = '/workspace';
  } catch (error) {
    showFeedback(error instanceof Error ? error.message : 'Authentication failed.');
  }
}

function setAuthTab(tab) {
  const loginForm = document.getElementById('login-form');
  const registerForm = document.getElementById('register-form');
  const buttons = document.querySelectorAll('[data-auth-tab-target]');

  buttons.forEach((button) => {
    const active = button.dataset.authTabTarget === tab;
    button.className = active
      ? 'rounded-2xl bg-slate px-4 py-3 text-sm font-semibold text-white'
      : 'rounded-2xl border border-slate-200 px-4 py-3 text-sm font-semibold text-slate-700';
  });

  if (loginForm && registerForm) {
    loginForm.classList.toggle('hidden', tab !== 'login');
    registerForm.classList.toggle('hidden', tab !== 'register');
  }
}

function hydrateWorkspaceUser() {
  const user = getUser();
  if (!user) {
    return;
  }

  const name = document.getElementById('workspace-user-name');
  const email = document.getElementById('workspace-user-email');
  const role = document.getElementById('workspace-user-role');

  if (name) {
    name.textContent = user.name || 'Unknown user';
  }

  if (email) {
    email.textContent = user.email || '';
  }

  if (role) {
    role.textContent = user.role || 'member';
  }
}

async function performExportDownload(documentId, format) {
  const token = getToken();
  if (!token) {
    clearSession();
    window.location.href = '/';
    return;
  }

  const response = await fetch(`/api/documents/${documentId}/export?format=${format}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || 'Unable to export document.');
  }

  const binary = atob(data.base64);
  const bytes = Uint8Array.from(binary, (char) => char.charCodeAt(0));
  const blob = new Blob([bytes], { type: 'application/octet-stream' });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = data.fileName || `${documentId}-output.${format}`;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

function logout() {
  clearSession();
  window.location.href = '/';
}

document.body.addEventListener('htmx:configRequest', (event) => {
  const token = getToken();
  if (token) {
    event.detail.headers.Authorization = `Bearer ${token}`;
  }
});

document.body.addEventListener('htmx:responseError', (event) => {
  const xhr = event.detail.xhr;
  if (xhr.status === 401) {
    clearSession();
    window.location.href = '/';
    return;
  }

  const panel = document.getElementById('job-panel');
  if (panel) {
    let message = 'Request failed.';
    try {
      const payload = JSON.parse(xhr.responseText);
      message = payload.detail || message;
    } catch {
      message = xhr.responseText || message;
    }
    panel.innerHTML = `<div class="rounded-3xl border border-red-200 bg-red-50 p-5 text-sm text-red-700">${message}</div>`;
  }
});

document.addEventListener('click', async (event) => {
  const exportButton = event.target.closest('[data-export-document-id][data-export-format]');
  if (!exportButton) {
    return;
  }

  try {
    await performExportDownload(exportButton.dataset.exportDocumentId, exportButton.dataset.exportFormat);
  } catch (error) {
    window.alert(error instanceof Error ? error.message : 'Unable to export document.');
  }
});

document.addEventListener('DOMContentLoaded', () => {
  const page = document.body.dataset.page;
  if (!requireAuth(page)) {
    return;
  }

  document.querySelectorAll('[data-auth-tab-target]').forEach((button) => {
    button.addEventListener('click', () => setAuthTab(button.dataset.authTabTarget));
  });

  document.querySelectorAll('[data-auth-mode]').forEach((form) => {
    form.addEventListener('submit', submitAuthForm);
  });

  if (page === 'workspace') {
    hydrateWorkspaceUser();
  }
});

window.downloadExport = performExportDownload;
window.logout = logout;
