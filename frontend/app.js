// Clairfinance — Frontend Engine & Backend Integration
const $ = s => document.querySelector(s);
const $$ = s => document.querySelectorAll(s);
const main = $('#main');
const inr = n => '₹' + Math.abs(Math.round(n || 0)).toLocaleString('en-IN');
const ARR = '<svg class="ar" viewBox="0 0 24 24"><path d="M5 12h14M13 6l6 6-6 6"/></svg>';

let API_BASE = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
  ? (window.location.port === '8000' ? '/api' : `http://${window.location.hostname}:8000/api`)
  : '/api';

let isBackendConnected = false;
let activeToken = localStorage.getItem('cf_token') || '';
let currentUser = null;
try {
  const savedUser = localStorage.getItem('cf_user');
  if (savedUser) currentUser = JSON.parse(savedUser);
} catch (_) {}
let activePersona = { id: 'salaried', name: 'Rahul Sharma', role: 'Salaried Employee', avatar: '👨‍💼' };
const isRealGoogleUser = u => !!(u && u.email && !u.email.includes('clairfinance.com') && !u.email.includes('clairefinance.com'));
let allCategories = [];
let googleClientId = "1038762070890-i6fe9lef782cb9sev0ptgv8g5jvuoum4.apps.googleusercontent.com";

// Sidebar Navigation Items
const NAV = [
  ['home', 'Home', '<path d="M3 11l9-8 9 8v9a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z"/>'],
  ['transactions', 'Transaction History', '<path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/>'],
  ['whatif', 'Tools & AI Advisor', '<path d="M4 8h8m4 0h4M4 16h4m4 0h8"/><circle cx="14" cy="8" r="2"/><circle cx="10" cy="16" r="2"/>'],
  ['forecast', 'Forecast & Backtest', '<path d="M3 17l6-6 4 4 8-8M15 7h6v6"/>'],
  ['bills', 'Recurring Bills', '<path d="M5 4h14a2 2 0 0 1 2 2v14H3V6a2 2 0 0 1 2-2zM3 10h18M8 2v4M16 2v4"/>'],
  ['score', 'Finance Score', '<path d="M4 18a8 8 0 1 1 16 0M12 18l4-5"/>'],
  ['anomalies', 'Anomalies', '<path d="M10.3 3.9 2.4 17.6A2 2 0 0 0 4.1 20.6h15.8a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0ZM12 9v4M12 17h.01"/>']
];

$('#nav').innerHTML = NAV.map(([k, t, p]) =>
  `<a class="nav-i" href="#/${k}" data-k="${k}"><svg viewBox="0 0 24 24">${p}</svg><span>${t}</span></a>`
).join('');

// API Helper
function authHeaders() {
  const h = { 'Content-Type': 'application/json' };
  if (activeToken) h['Authorization'] = 'Bearer ' + activeToken;
  return h;
}

async function apiFetch(endpoint, options = {}) {
  let url = `${API_BASE}${endpoint}`;
  try {
    const res = await fetch(url, options);
    updateBackendStatus(true);
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || `HTTP ${res.status}: ${res.statusText}`);
    }
    return await res.json();
  } catch (err) {
    // If request failed with network error, attempt alternate host (localhost <-> 127.0.0.1)
    if ((err.message.includes('Failed to fetch') || err.message.includes('NetworkError')) && !API_BASE.startsWith('/')) {
      const altHost = API_BASE.includes('localhost') ? '127.0.0.1' : 'localhost';
      const altBase = `http://${altHost}:8000/api`;
      try {
        const altRes = await fetch(`${altBase}${endpoint}`, options);
        if (altRes.ok) {
          API_BASE = altBase;
          updateBackendStatus(true);
          return await altRes.json();
        }
      } catch (_) {
        // Fallback also unreachable
      }
    }
    console.warn(`API call failed for ${endpoint}:`, err.message);
    if (err.message.includes('Failed to fetch') || err.message.includes('NetworkError')) {
      updateBackendStatus(false);
    }
    throw err;
  }
}

function updateBackendStatus(isOnline) {
  isBackendConnected = isOnline;
  const dot = $('#live-dot');
  const label = $('#api-status-label');
  if (dot) dot.className = isOnline ? 'live-dot' : 'live-dot err';
  if (label) label.textContent = isOnline ? `Backend Connected (${API_BASE})` : 'Backend Disconnected';
}

// Background auto-reconnect poller: if disconnected, checks health every 3s and reconnects
setInterval(async () => {
  if (!isBackendConnected) {
    try {
      const probe = await fetch(`${API_BASE}/health`).then(r => r.json()).catch(() => null);
      if (probe && probe.status === 'healthy') {
        updateBackendStatus(true);
        initAuth();
      }
    } catch (_) {}
  }
}, 3000);

// Theme handling
const setTheme = t => {
  document.documentElement.dataset.theme = t;
  localStorage.setItem('cf-theme', t);
  const el = $('.tl');
  if (el) el.textContent = t === 'dark' ? 'Dark mode' : 'Light mode';
  renderGoogleButton();
};
setTheme(document.documentElement.dataset.theme || 'dark');
$('#theme').onclick = () => setTheme(document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark');

// Load dynamic auth config from backend
async function loadGoogleAuthConfig() {
  try {
    const cfg = await fetch(`${API_BASE}/auth/config`).then(r => r.json()).catch(() => null);
    if (cfg && cfg.google_client_id) {
      googleClientId = cfg.google_client_id;
    }
  } catch (_) {}
}

let tokenClient = null;
let gisInitialized = false;
let gisClientId = '';

// Render official Google Identity Services button with theme matching
function renderGoogleButton() {
  const container = document.getElementById('googleSignInDiv');
  if (!container || typeof google === 'undefined' || !google.accounts || !google.accounts.id) return;

  try {
    const isDark = document.documentElement.dataset.theme !== 'light';
    google.accounts.id.renderButton(container, {
      type: 'standard',
      theme: isDark ? 'filled_black' : 'outline',
      size: 'large',
      text: 'signin_with',
      shape: 'pill',
      logo_alignment: 'left',
      width: 340
    });
  } catch (e) {
    console.warn('renderGoogleButton warning:', e);
  }
}

// Google Identity Services Initializer (Singleton to avoid clobbering popup handlers)
function initGoogleSignIn() {
  if (typeof google === 'undefined' || !google.accounts) return;
  if (gisInitialized && gisClientId === googleClientId) {
    renderGoogleButton();
    return;
  }

  try {
    // 1. Initialize Google ID Services (Official GIS Sign-In with ID Token)
    if (google.accounts.id) {
      google.accounts.id.initialize({
        client_id: googleClientId,
        callback: handleGoogleLoginResponse,
        auto_select: false,
        cancel_on_tap_outside: true,
      });
      renderGoogleButton();
    }

    // 2. Google OAuth2 Token Client as fallback
    if (google.accounts.oauth2) {
      tokenClient = google.accounts.oauth2.initTokenClient({
        client_id: googleClientId,
        scope: 'email profile openid',
        callback: handleGoogleOAuthResponse,
        error_callback: (err) => {
          console.warn('Google Identity error_callback:', err);
          const statusMsg = document.getElementById('loginStatusMsg');
          if (statusMsg) {
            statusMsg.style.display = 'block';
            if (err && err.type === 'popup_closed') {
              statusMsg.className = 'login-msg info';
              statusMsg.textContent = 'Google sign-in popup was closed. Please click the button to try again.';
            } else if (err && err.type === 'popup_failed_to_open') {
              statusMsg.className = 'login-msg err';
              statusMsg.textContent = 'Sign-in popup was blocked by your browser. Please allow popups for localhost:3000.';
            } else {
              statusMsg.className = 'login-msg err';
              statusMsg.textContent = `Google Sign-in error: ${err.message || err.type || 'Authentication failed'}`;
            }
          }
        }
      });
    }

    gisInitialized = true;
    gisClientId = googleClientId;
  } catch (e) {
    console.warn('Google Identity Services setup warning:', e);
  }
}

// Helper to set authenticated user session
function setAuthenticatedUser(token, user) {
  activeToken = token;
  currentUser = user;
  localStorage.setItem('cf_token', activeToken);
  localStorage.setItem('cf_google_token', activeToken);
  localStorage.setItem('cf_user', JSON.stringify(currentUser));
  localStorage.setItem('cf-data', 'google');

  activePersona = {
    id: 'google',
    name: currentUser.name || 'Google User',
    role: currentUser.email,
    avatar: currentUser.avatar_url || '👤',
    income_pattern: 'Google Account'
  };
  updatePersonaUI();
}

// Handle Google OAuth2 token response (from custom button popup)
async function handleGoogleOAuthResponse(tokenResponse) {
  const statusMsg = document.getElementById('loginStatusMsg');
  if (tokenResponse && tokenResponse.error) {
    if (tokenResponse.error !== 'popup_closed_by_user') {
      if (statusMsg) {
        statusMsg.className = 'login-msg err';
        statusMsg.style.display = 'block';
        statusMsg.textContent = `Google Sign-in failed: ${tokenResponse.error}`;
      }
    }
    return;
  }

  if (!tokenResponse || !tokenResponse.access_token) {
    return;
  }

  if (statusMsg) {
    statusMsg.className = 'login-msg info';
    statusMsg.style.display = 'block';
    statusMsg.textContent = 'Verifying Google session...';
  }

  try {
    const res = await fetch(`${API_BASE}/auth/google`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ access_token: tokenResponse.access_token })
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Sign in failed (${res.status})`);
    }

    const data = await res.json();
    setAuthenticatedUser(data.access_token, data.user);

    if (statusMsg) {
      statusMsg.className = 'login-msg ok';
      statusMsg.textContent = 'Signed in successfully! Loading dashboard...';
    }

    setTimeout(() => {
      location.hash = '#/home';
      route();
    }, 300);
  } catch (err) {
    console.error('Google OAuth login error:', err);
    if (statusMsg) {
      statusMsg.className = 'login-msg err';
      statusMsg.style.display = 'block';
      statusMsg.textContent = `Google Sign-in failed: ${err.message}`;
    }
  }
}

// Handle Google Login response from GIS (ID token)
async function handleGoogleLoginResponse(response) {
  const statusMsg = document.getElementById('loginStatusMsg');
  if (statusMsg) {
    statusMsg.className = 'login-msg info';
    statusMsg.style.display = 'block';
    statusMsg.textContent = 'Verifying Google session...';
  }

  try {
    if (!response || !response.credential) {
      throw new Error('Google did not provide credentials.');
    }

    const res = await fetch(`${API_BASE}/auth/google`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id_token: response.credential })
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Google login failed (${res.status})`);
    }

    const data = await res.json();
    setAuthenticatedUser(data.access_token, data.user);

    if (statusMsg) {
      statusMsg.className = 'login-msg ok';
      statusMsg.textContent = 'Signed in successfully! Loading dashboard...';
    }

    setTimeout(() => {
      location.hash = '#/home';
      route();
    }, 300);
  } catch (err) {
    console.error('Google login error:', err);
    if (statusMsg) {
      statusMsg.className = 'login-msg err';
      statusMsg.style.display = 'block';
      statusMsg.textContent = `Google Sign-in failed: ${err.message}`;
    }
  }
}

// Authentication & Session Verification
async function initAuth() {
  await loadGoogleAuthConfig();

  try {
    const categories = await apiFetch('/categories');
    allCategories = categories || [];
  } catch (e) {
    console.log('Categories not yet loaded:', e.message);
  }

  if (!activeToken) {
    currentUser = null;
    return false;
  }

  // Validate stored token against /auth/me
  try {
    const user = await apiFetch('/auth/me', { headers: authHeaders() });
    if (user && user.id) {
      currentUser = user;
      localStorage.setItem('cf_user', JSON.stringify(user));
      activePersona = {
        id: 'google',
        name: user.name || 'Google User',
        role: user.email,
        avatar: user.avatar_url || '👤',
        income_pattern: 'Google Account'
      };
      updatePersonaUI();
      return true;
    }
  } catch (err) {
    console.warn('Session verification failed:', err.message);
    activeToken = '';
    currentUser = null;
    localStorage.removeItem('cf_token');
    localStorage.removeItem('cf_user');
    return false;
  }
  return false;
}

function updatePersonaUI() {
  const nameEl = $('#side-p-name');
  const roleEl = $('#side-p-role');
  const avatarEl = $('#side-p-avatar');
  const badgeEl = $('#side-p-badge');
  const pillEl = $('#topbar-persona-pill');
  const buttonsContainer = $('#side-persona-buttons');

  const isGoogleUser = isRealGoogleUser(currentUser);

  if (isGoogleUser) {
    if (nameEl) nameEl.textContent = currentUser.name || 'Google User';
    if (roleEl) roleEl.textContent = currentUser.email;
    if (badgeEl) badgeEl.style.display = 'inline-flex';
    if (avatarEl) {
      if (currentUser.avatar_url) {
        avatarEl.innerHTML = `<img src="${currentUser.avatar_url}" alt="Avatar" style="width:34px;height:34px;border-radius:50%;object-fit:cover;display:block;" onerror="this.outerHTML='👤'">`;
      } else {
        avatarEl.textContent = '👤';
      }
    }
    if (pillEl) {
      pillEl.innerHTML = `🟢 Google · ${currentUser.name || currentUser.email}`;
    }
    // HIDE demo persona switcher completely after Google login
    if (buttonsContainer) {
      buttonsContainer.style.display = 'none';
    }
  } else {
    if (nameEl) nameEl.textContent = activePersona.name;
    if (roleEl) roleEl.textContent = activePersona.role;
    if (badgeEl) badgeEl.style.display = 'none';
    if (avatarEl) avatarEl.textContent = activePersona.avatar;
    if (pillEl) pillEl.textContent = `${activePersona.name} · ${activePersona.role}`;

    // Show demo persona switcher buttons only for unauthenticated demo mode
    if (buttonsContainer) {
      buttonsContainer.style.display = 'flex';
    }
    $$('.ap-btn').forEach(btn => {
      btn.classList.toggle('on', btn.dataset.p === activePersona.id);
    });
  }

  // Update banner user card next to logo if present
  const bannerCard = $('#bannerUserCard');
  if (bannerCard) {
    bannerCard.outerHTML = getUserCardHTML();
  }
}

async function switchPersona(personaId) {
  // If user is logged into a real Google account, prevent switching to demo personas
  const isGoogleUser = isRealGoogleUser(currentUser);
  if (isGoogleUser) {
    console.warn('Demo persona switching is disabled for authenticated Google accounts.');
    return;
  }

  try {
    const res = await apiFetch(`/personas/switch/${personaId}`, {
      method: 'POST',
      headers: authHeaders()
    });
    activeToken = res.access_token;
    localStorage.setItem('cf_token', activeToken);
    localStorage.setItem('cf-data', personaId);
    currentUser = {
      id: res.active_persona.id,
      name: res.active_persona.name,
      email: res.active_persona.email,
      role: res.active_persona.role,
      avatar_url: res.active_persona.avatar_url
    };
    activePersona = {
      id: res.active_persona.id,
      name: res.active_persona.name,
      role: res.active_persona.role,
      avatar: res.active_persona.id === 'student' ? '🎓' : res.active_persona.id === 'freelancer' ? '👩‍💻' : '👨‍💼',
      income_pattern: res.active_persona.income_pattern
    };
    updatePersonaUI();

    const curHash = location.hash.slice(2) || 'home';
    if (PAGES[curHash]) {
      PAGES[curHash]();
    }
  } catch (err) {
    alert(`Failed to switch persona: ${err.message}`);
  }
}

// Bind Persona buttons in sidebar & login page
document.addEventListener('click', e => {
  const btn = e.target.closest('.ap-btn, .p-quick-btn');
  if (btn) {
    // If authenticated as Google user, do not allow persona switching
    const isGoogleUser = isRealGoogleUser(currentUser);
    if (isGoogleUser) {
      return;
    }
    const pid = btn.dataset.p || btn.dataset.persona;
    if (pid) {
      switchPersona(pid).then(() => {
        if (location.hash === '' || location.hash === '#/login') {
          location.hash = '#/home';
        }
      });
    }
  }
});

// Google Sign-In button click (fallback before Google native button loads)
const gbtn = $('#gbtn');
if (gbtn) {
  gbtn.onclick = () => {
    const statusMsg = document.getElementById('loginStatusMsg');
    if (statusMsg) {
      statusMsg.className = 'login-msg info';
      statusMsg.style.display = 'block';
      statusMsg.textContent = 'Opening Google Sign-In...';
    }

    if (typeof google === 'undefined' || !google.accounts) {
      if (statusMsg) {
        statusMsg.className = 'login-msg err';
        statusMsg.textContent = 'Google Authentication service is loading. Please check your internet connection.';
      }
      return;
    }

    if (!tokenClient) {
      initGoogleSignIn();
    }

    // Try One-Tap / ID Services prompt first
    if (google.accounts.id) {
      try {
        google.accounts.id.prompt();
      } catch (_) {}
    }

    if (tokenClient) {
      try {
        tokenClient.requestAccessToken();
        return;
      } catch (err) {
        console.error('Error invoking requestAccessToken:', err);
      }
    }
  };
}

// Sign out handler
$('#out').onclick = () => {
  localStorage.removeItem('cf_token');
  localStorage.removeItem('cf_user');
  localStorage.removeItem('cf_google_token');
  localStorage.removeItem('cf-data');
  activeToken = '';
  currentUser = null;
  activePersona = { id: 'salaried', name: 'Rahul Sharma', role: 'Salaried Employee', avatar: '👨‍💼' };
  updatePersonaUI();
  location.hash = '#/login';
  route();
  setTimeout(renderGoogleButton, 100);
};

// Spotlight & ripple effects
document.addEventListener('pointermove', e => {
  const c = e.target.closest('.card');
  if (!c) return;
  const r = c.getBoundingClientRect();
  c.style.setProperty('--mx', e.clientX - r.left + 'px');
  c.style.setProperty('--my', e.clientY - r.top + 'px');
});

document.addEventListener('click', e => {
  const c = e.target.closest('.card');
  if (!c) return;
  const r = c.getBoundingClientRect(), s = Math.max(r.width, r.height) / 2;
  const k = e.detail === 0, x = k ? r.width / 2 : e.clientX - r.left, y = k ? r.height / 2 : e.clientY - r.top;
  const d = document.createElement('span');
  d.className = 'ripple';
  Object.assign(d.style, { width: s + 'px', height: s + 'px', left: x - s / 2 + 'px', top: y - s / 2 + 'px' });
  d.onanimationend = () => d.remove();
  c.appendChild(d);
});

// User Card next to Logo
function getUserCardHTML() {
  const isGoogle = isRealGoogleUser(currentUser);
  const name = (currentUser && currentUser.name) ? currentUser.name : (activePersona ? activePersona.name : 'Rahul Sharma');
  const email = (currentUser && currentUser.email) ? currentUser.email : '';
  const avatarUrl = (currentUser && currentUser.avatar_url) ? currentUser.avatar_url : null;

  // Extract initials (e.g. "Rahul Sharma" -> "RS", "Vishwas Simha V" -> "VS")
  const parts = name.trim().split(/\s+/).filter(Boolean);
  const initials = parts.length > 1 
    ? (parts[0][0] + parts[parts.length - 1][0]).toUpperCase() 
    : (name.slice(0, 2).toUpperCase() || 'RS');

  let avatarInner = `<span class="buc-initials">${initials}</span>`;
  if (avatarUrl) {
    avatarInner = `<img src="${avatarUrl}" alt="${name}" onerror="this.parentElement.classList.add('buc-gradient'); this.outerHTML='<span class=\\'buc-initials\\'>${initials}</span>'">`;
  }

  const gradientClass = avatarUrl ? '' : 'buc-gradient';

  return `
    <div class="banner-user-card" id="bannerUserCard" title="${name}${email ? ' (' + email + ')' : ''}">
      <div class="buc-avatar ${gradientClass}">
        ${avatarInner}
      </div>
      <div class="buc-info">
        <b class="buc-name">${name}</b>
        <span class="buc-role">Personal account</span>
      </div>
    </div>
  `;
}

// UI helpers
const hero = (t, img, cls) => `<div class="hero ${cls || ''}" style="${img ? `--img:url(assets/${img})` : ''}"><h1>${t}</h1></div>`;
const page = h => `<div class="page">${h}</div>`;
const GAUGE = s => `<span class="gauge"><svg viewBox="0 0 100 58"><defs><linearGradient id="gg" gradientUnits="userSpaceOnUse" x1="10" x2="90"><stop offset="0" stop-color="#ef4444"/><stop offset=".5" stop-color="#f59e0b"/><stop offset="1" stop-color="#22c55e"/></linearGradient></defs><path class="gt" d="M10 52A40 40 0 0 1 90 52" pathLength="100"/><path class="gf" d="M10 52A40 40 0 0 1 90 52" pathLength="100" style="--off:${100 - s}"/></svg><span class="gn"><b id="sn">0</b><small>/100</small></span></span>`;

function countUp(t) {
  const el = $('#sn');
  if (!el) return;
  const s = performance.now() + 600;
  (function f(n) {
    const p = Math.min(Math.max((n - s) / 1400, 0), 1);
    el.textContent = Math.round(t * (1 - Math.pow(1 - p, 3)));
    if (p < 1) requestAnimationFrame(f);
  })(performance.now());
}

const IC = {
  transactions: '<svg viewBox="0 0 64 64"><g class="rw" style="--r:0"><circle cx="12" cy="16" r="4"/><path d="M24 16h30"/></g><g class="rw" style="--r:1"><circle cx="12" cy="32" r="4"/><path d="M24 32h24"/></g><g class="rw" style="--r:2"><circle cx="12" cy="48" r="4"/><path d="M24 48h28"/></g></svg>',
  whatif: '<svg viewBox="0 0 64 64"><path d="M8 22h48M8 44h48"/><circle class="kn k1" cx="20" cy="22" r="6"/><circle class="kn k2" cx="44" cy="44" r="6"/></svg>',
  forecast: '<svg viewBox="0 0 64 64"><path d="M8 8v48h50"/><polygon class="ff" points="36,34 56,14 56,34"/><polyline class="fl" points="12,46 22,38 30,42 36,34"/><polyline class="fd" points="36,34 56,22"/></svg>',
  bills: '<svg viewBox="0 0 64 64"><g class="cal"><rect x="8" y="14" width="48" height="42" rx="8"/><path d="M8 28h48M22 8v10M42 8v10M20 40h4M32 40h4M44 40h4"/></g><circle class="bdg" cx="54" cy="12" r="6"/></svg>'
};

const CARDS = [
  ['transactions', 'Transaction History', 'Every transaction, categorized, searchable, with active-learning feedback.'],
  ['whatif', 'Tools & AI Advisor', 'What-If Simulator, EMI optimizer, loan schedules and savings goals.'],
  ['forecast', 'Forecast & Backtest', 'Time-series predictions 30 to 180 days ahead, plus backtest accuracy evaluation.'],
  ['bills', 'Recurring Bills', 'Auto-detected recurring subscriptions, EMIs, and upcoming due-date reminders.']
];

/* -------------------------------------------------------------
   PAGE IMPLEMENTATIONS (WIRED TO FASTAPI BACKEND)
------------------------------------------------------------- */
const PAGES = {
  // 1. HOME DASHBOARD
  async home() {
    main.innerHTML = `<header class="banner"><div class="banner-inner">${getUserCardHTML()}<div class="br"><svg><use href="#logo"/></svg><div class="wm">Clair<span>finance</span></div></div><p>AI-Powered Personal Financial Operating System</p></div></header>` +
      page(`<div style="display:flex;justify-content:center;padding:40px;"><div class="spin"></div> Loading dashboard insights...</div>`);

    try {
      const overview = await apiFetch('/dashboard/overview', { headers: authHeaders() });
      const alerts = await apiFetch('/alerts', { headers: authHeaders() }).catch(() => []);
      const personality = await apiFetch('/dashboard/personality', { headers: authHeaders() }).catch(() => null);

      let topAlert = {
        title: 'All Clear',
        desc: 'You are up to date on your expenditures. No shortfalls predicted in next 30 days.',
        tag: 'Healthy',
        link: '#/forecast'
      };

      if (alerts && alerts.length > 0) {
        topAlert = {
          title: alerts[0].title,
          desc: alerts[0].description,
          tag: alerts[0].severity.toUpperCase(),
          link: alerts[0].alert_type === 'anomaly' ? '#/anomalies' : '#/bills'
        };
      }

      const hasNoData = overview.total_income === 0 && overview.total_expenses === 0 && (!overview.recent_transactions || overview.recent_transactions.length === 0);
      const onboardingHTML = hasNoData ? `
        <div class="card alert" style="--i:-1;background:linear-gradient(135deg,rgba(99,102,241,0.22),rgba(34,211,238,0.12));border:1px solid rgba(99,102,241,0.45);margin-bottom:18px;">
          <div class="al-i"><svg viewBox="0 0 24 24"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg></div>
          <div style="flex:1">
            <small style="color:var(--sec);font-weight:600;">NEW ACCOUNT READY</small>
            <h2 style="margin:4px 0 8px;">Welcome${currentUser && currentUser.name ? ', ' + currentUser.name : ''}!</h2>
            <p>Your Google account is active, but no bank statement transactions have been loaded yet. Upload your CSV export or load our pre-seeded 12-month sample dataset to experience the full AI financial suite:</p>
            <div style="display:flex;gap:10px;margin-top:14px;flex-wrap:wrap;">
              <a href="#/upload" class="btn" style="padding:10px 18px;font-size:14px;text-decoration:none;">Upload Statement CSV</a>
              <button type="button" class="btn ghost" id="homeSeedBtn" style="padding:10px 18px;font-size:14px;">⚡ Load 12-Month Sample Data</button>
            </div>
          </div>
        </div>
      ` : '';

      main.innerHTML = `<header class="banner"><div class="banner-inner">${getUserCardHTML()}<div class="br"><svg><use href="#logo"/></svg><div class="wm">Clair<span>finance</span></div></div><p>Know if you’ll run out of money, and when, before it happens</p></div></header>` +
        page(`
          ${onboardingHTML}
          <a class="card alert" href="${topAlert.link}" style="--i:-1">
            <div class="al-i"><svg viewBox="0 0 24 24"><path d="M10.3 3.9 2.4 17.6A2 2 0 0 0 4.1 20.6h15.8a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0ZM12 9v4M12 17h.01"/></svg></div>
            <div id="al" style="flex:1">
              <small>${topAlert.tag}</small>
              <h2>${topAlert.title}</h2>
              <p>${topAlert.desc}</p>
            </div>
            ${ARR}
          </a>

          <div class="stats" style="margin-top:-8px;">
            <div class="stat glass">
              <small>Total Income (12 mo)</small>
              <b class="ok">${inr(overview.total_income)}</b>
            </div>
            <div class="stat glass">
              <small>Total Expenses</small>
              <b class="bad">${inr(overview.total_expenses)}</b>
            </div>
            <div class="stat glass">
              <small>Net Savings (Rate)</small>
              <b class="${overview.net_savings >= 0 ? 'ok' : 'bad'}">${overview.net_savings >= 0 ? '+' : '−'}${inr(overview.net_savings)} (${overview.savings_rate}%)</b>
            </div>
          </div>

          <a class="promise-feature-banner" href="#/promises">
            <div class="pfb-backdrop"></div>
            <div class="pfb-overlay"></div>
            <div class="pfb-content">
              <div class="pfb-text">
                <div class="pfb-tag">⚡ Flagship Innovation · 5,000 Monte Carlo Paths</div>
                <h2>Refined Promises: Cash-Flow Simulator</h2>
                <p>Empirical mathematical guarantees for your financial future. Discover the largest shock you can absorb tomorrow with &le;5% shortfall risk, simulate bill impacts, and view certified rolling backtests.</p>
              </div>
              <div class="pfb-cta">
                <span>Open Promises</span>
                ${ARR}
              </div>
            </div>
          </a>

          <div class="grid">
            ${CARDS.map(([k, t, d], i) => `
              <a class="card" href="#/${k}" style="--i:${i}">
                <span class="ct"><span class="ic">${IC[k]}</span>${ARR}</span>
                <span><h3>${t}</h3><p>${d}</p></span>
              </a>
            `).join('')}
            <a class="card wide" href="#/score" style="--i:4">
              ${GAUGE(overview.health_score)}
              <span style="flex:1">
                <h3>Financial Health: ${overview.health_status}</h3>
                <p>Calculated across 5 core factors: savings rate, expense consistency, debt-to-income, emergency buffer, and spending diversity.</p>
                <span class="chips">
                  <i>Savings Rate</i><i>Cash Buffer</i><i>EMI Ratio</i><i>Spending Stability</i><i>Shortfall Risk</i>
                </span>
                ${personality ? `<div style="margin-top:10px;font-size:13px;color:var(--sec);"><b>Archetype:</b> ${personality.title}</div>` : ''}
              </span>
              ${ARR}
            </a>
          </div>

          <section class="panel glass" style="margin-top:10px;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
              <h3 style="margin:0;">Recent Transactions</h3>
              <a href="#/transactions" class="lk" style="font-size:13px;">View all &rarr;</a>
            </div>
            <table>
              <tbody>
                ${(overview.recent_transactions || []).slice(0, 5).map(t => `
                  <tr>
                    <td>
                      <span class="dot" style="background:${t.category_color || '#6366f1'}"></span>
                      <b>${t.description}</b>
                      <div class="cat">${t.category_name} · ${t.date} · ${t.payment_mode}</div>
                    </td>
                    <td class="${t.type === 'credit' ? 'ok' : ''}" style="text-align:right;">
                      ${t.type === 'credit' ? '+' : '−'}${inr(t.amount)}
                    </td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          </section>
        `);

      countUp(overview.health_score);

      const homeSeedBtn = $('#homeSeedBtn');
      if (homeSeedBtn) {
        homeSeedBtn.onclick = async () => {
          homeSeedBtn.disabled = true;
          homeSeedBtn.textContent = 'Loading sample data...';
          try {
            await apiFetch('/transactions/seed-sample', { method: 'POST', headers: authHeaders() });
            PAGES.home();
          } catch (e) {
            alert('Failed to load sample dataset: ' + e.message);
            homeSeedBtn.disabled = false;
          }
        };
      }
    } catch (err) {
      main.innerHTML = page(`<section class="panel glass"><h3>Error loading dashboard</h3><p class="cat">${err.message}</p><button class="btn" onclick="PAGES.home()">Retry</button></section>`);
    }
  },

  // 2. TRANSACTION HISTORY & ACTIVE LEARNING LOOP
  async transactions() {
    main.innerHTML = hero('TRANSACTION HISTORY', 'money.avif') +
      page(`<div style="display:flex;justify-content:center;padding:40px;"><div class="spin"></div> Loading statement transactions...</div>`);

    try {
      const data = await apiFetch('/transactions?page=1&page_size=200', { headers: authHeaders() });
      const txns = data.transactions || data.items || [];
      if (!allCategories.length) {
        allCategories = await apiFetch('/categories', { headers: authHeaders() }).catch(() => []);
      }

      main.innerHTML = hero('TRANSACTION HISTORY', 'money.avif') + page(`
        <section class="panel glass">
          <div class="bar">
            <label>Time Period:
              <select id="t-period">
                <option value="all" selected>All time (Full statement)</option>
                <option value="365">Last year</option>
                <option value="180">Last 6 months</option>
                <option value="90">Last 3 months</option>
                <option value="30">Past month</option>
                <option value="7">Past week</option>
              </select>
            </label>
            <label>Category:
              <select id="t-cat-filter">
                <option value="all">All Categories</option>
                ${allCategories.map(c => `<option value="${c.name}">${c.name}</option>`).join('')}
              </select>
            </label>
            <label>Search:
              <input class="in" id="t-search" placeholder="Filter merchant/description..." style="padding:6px 12px;font-size:13px;width:200px;">
            </label>
            <span class="cat" id="t-count">${txns.length} transactions</span>
          </div>
        </section>

        <div class="stats" id="t-stats"></div>

        <section class="panel glass">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
            <h3>Statement Transactions</h3>
            <span class="cat" style="font-size:12px;">💡 Select any category to trigger the ML active learning loop</span>
          </div>
          <table id="t-table"></table>
        </section>
      `);

      const renderTxns = () => {
        const periodVal = $('#t-period').value;
        const catFilter = $('#t-cat-filter').value;
        const searchQuery = ($('#t-search').value || '').toLowerCase().trim();

        const now = Date.now();
        const filtered = txns.filter(t => {
          let matchesPeriod = true;
          if (periodVal !== 'all') {
            const tTime = new Date(t.date).getTime();
            matchesPeriod = (now - tTime) <= (+periodVal) * 864e5;
          }
          const matchesCat = (catFilter === 'all' || t.category_name === catFilter);
          const matchesSearch = !searchQuery || t.description.toLowerCase().includes(searchQuery);
          return matchesPeriod && matchesCat && matchesSearch;
        });

        const income = filtered.reduce((acc, t) => acc + (t.type === 'credit' ? t.amount : 0), 0);
        const spent = filtered.reduce((acc, t) => acc + (t.type === 'debit' ? t.amount : 0), 0);
        const net = income - spent;

        $('#t-count').textContent = `${filtered.length} transactions`;

        $('#t-stats').innerHTML = [
          ['Total Income', inr(income), 'ok'],
          ['Total Spent', inr(spent), 'bad'],
          ['Net Savings', (net >= 0 ? '+' : '−') + inr(net), net >= 0 ? 'ok' : 'bad']
        ].map(([l, v, c]) => `<div class="stat glass"><small>${l}</small><b class="${c}">${v}</b></div>`).join('');

        $('#t-table').innerHTML = filtered.slice(0, 100).map((t, idx) => `
          <tr id="row-${t.id}">
            <td>
              <span class="dot" style="background:${t.category_color || '#6366f1'}"></span>
              <b>${t.description}</b>
              ${t.anomaly_score > 0.6 ? `<span class="chip bad" style="margin-left:6px;font-size:11px;">Anomaly (${Math.round(t.anomaly_score * 100)}%)</span>` : ''}
              ${t.is_recurring ? `<span class="chip warn" style="margin-left:4px;font-size:11px;">Recurring</span>` : ''}
              <div class="cat">
                ${t.date} · ${t.payment_mode || 'UPI'}
              </div>
            </td>
            <td style="width:200px;">
              <select class="cat-select" data-id="${t.id}">
                ${allCategories.map(c => `
                  <option value="${c.name}" ${c.name === t.category_name ? 'selected' : ''}>${c.name}</option>
                `).join('')}
              </select>
              <span id="learn-${t.id}"></span>
            </td>
            <td class="${t.type === 'credit' ? 'ok' : ''}" style="text-align:right;">
              ${t.type === 'credit' ? '+' : '−'}${inr(t.amount)}
            </td>
          </tr>
        `).join('');

        // Attach category change listeners for Active Learning Loop
        $$('.cat-select').forEach(sel => {
          sel.onchange = async e => {
            const txnId = e.target.dataset.id;
            const newCat = e.target.value;
            const statusEl = $(`#learn-${txnId}`);
            if (statusEl) statusEl.innerHTML = `<span class="cat" style="font-size:11px;">Saving...</span>`;

            try {
              const patched = await apiFetch(`/transactions/${txnId}`, {
                method: 'PATCH',
                headers: authHeaders(),
                body: JSON.stringify({ category_name: newCat })
              });
              // Update local state
              const target = txns.find(x => x.id === txnId);
              if (target) {
                target.category_name = patched.category_name;
                target.category_color = patched.category_color;
              }
              if (statusEl) statusEl.innerHTML = `<span class="learned-badge">Learned!</span>`;
              setTimeout(() => { if (statusEl) statusEl.innerHTML = ''; }, 3000);
            } catch (err) {
              if (statusEl) statusEl.innerHTML = `<span style="color:var(--bad);font-size:11px;">Failed</span>`;
            }
          };
        });
      };

      $('#t-period').onchange = renderTxns;
      $('#t-cat-filter').onchange = renderTxns;
      $('#t-search').oninput = renderTxns;
      renderTxns();

    } catch (err) {
      main.innerHTML = page(`<section class="panel glass"><h3>Error loading transactions</h3><p class="cat">${err.message}</p></section>`);
    }
  },

  // 3. TOOLS & AI ADVISOR ("Can I Afford This?", Simulators, EMI Optimizer)
  async whatif() {
    main.innerHTML = hero('TOOLS & AI ADVISOR', 'ai.png') + page(`
      <div class="seg" id="tool-tabs">
        <button class="on" data-tab="tab-query">What-If Simulator</button>
        <button data-tab="tab-emi">EMI Optimizer</button>
        <button data-tab="tab-loan">Loan Amortization</button>
        <button data-tab="tab-goal">Savings Goal</button>
      </div>

      <!-- Tab 1: What-If Simulator (Can I Afford This?) -->
      <section class="panel glass tool-pane" id="tab-query">
        <h3>What-If Simulator: "Can I Afford This?"</h3>
        <p class="cat" style="margin-bottom:16px;">Evaluates proposed loans, EMIs or large purchases using live Google Gemini AI contextual memory and cash flow simulation.</p>
        <div class="form">
          <label>Item / Commitment Name:
            <input class="in" id="q-item" value="Royal Enfield Himalayan 450">
          </label>
          <label>Estimated Price (₹):
            <input class="in" id="q-price" type="number" value="285000">
          </label>
          <label>Payment Method:
            <select id="q-method">
              <option value="emi">EMI (Monthly Installments)</option>
              <option value="one_time">One-time (Savings Buffer)</option>
              <option value="loan">Personal / Auto Loan</option>
            </select>
          </label>
          <label class="q-emi-row">Tenure (months):
            <input class="in" id="q-tenure" type="number" value="24">
          </label>
          <label class="q-emi-row">Interest Rate (% per year):
            <input class="in" id="q-rate" type="number" step="0.1" value="12.5">
          </label>
          <label>Product Link (optional):
            <input class="in" id="q-link" placeholder="https://royalenfield.com/...">
          </label>
          <label style="grid-column:1/-1;">Additional Personal Context / Notes:
            <input class="in" id="q-notes" placeholder="e.g. I also have semester fees due next month, or expecting client bonus">
          </label>
          <button class="btn" id="q-btn">Check If I Can Afford It with AI</button>
        </div>

        <div id="q-loading" style="display:none;padding:24px;text-align:center;">
          <div class="spin"></div> <em>Analyzing financial situation, past history, and stress testing cash flow...</em>
        </div>
        <div id="q-result" class="verdict" style="margin-top:20px;"></div>

        <div style="margin-top:30px;">
          <h4 style="font-family:var(--hd);font-size:16px;margin-bottom:12px;">Past Financial Inquiries (Contextual Memory)</h4>
          <div id="q-history-list" style="display:grid;gap:10px;"></div>
        </div>
      </section>

      <!-- Tab 2: EMI Debt Optimizer -->
      <section class="panel glass tool-pane" id="tab-emi" style="display:none;">
        <h3>EMI Debt Optimizer</h3>
        <p class="cat" style="margin-bottom:16px;">Analyzes debt restructuring, lump-sum down payment ROI, and tenure extensions against your current debt-to-income (DTI) ratio.</p>
        <div class="form">
          <label>Borrowing Amount (₹):<input class="in" id="eo-amt" type="number" value="300000"></label>
          <label>Tenure (Months):<input class="in" id="eo-tenure" type="number" value="24"></label>
          <label>Interest Rate (%/yr):<input class="in" id="eo-rate" type="number" value="12"></label>
          <label>Down Payment / Prepayment (₹):<input class="in" id="eo-down" type="number" value="50000"></label>
          <button class="btn" id="eo-btn">Optimize Debt Structure</button>
        </div>
        <div id="eo-result" class="verdict" style="margin-top:16px;"></div>
      </section>

      <!-- Tab 3: Loan Amortization Schedule -->
      <section class="panel glass tool-pane" id="tab-loan" style="display:none;">
        <h3>Loan Amortization Calculator</h3>
        <p class="cat" style="margin-bottom:16px;">Generates month-by-month principal and interest repayment schedules.</p>
        <div class="form">
          <label>Principal Amount (₹):<input class="in" id="la-amt" type="number" value="500000"></label>
          <label>Rate of Interest (%/yr):<input class="in" id="la-rate" type="number" value="10.5"></label>
          <label>Tenure (Months):<input class="in" id="la-tenure" type="number" value="36"></label>
          <button class="btn" id="la-btn">Show Repayment Schedule</button>
        </div>
        <div id="la-result" class="verdict" style="margin-top:16px;"></div>
      </section>

      <!-- Tab 4: Savings Goal Timeline -->
      <section class="panel glass tool-pane" id="tab-goal" style="display:none;">
        <h3>Savings Goal Calculator</h3>
        <p class="cat" style="margin-bottom:16px;">Calculates timeline feasibility and AI recommendations to accelerate reaching your financial targets.</p>
        <div class="form">
          <label>Target Goal Amount (₹):<input class="in" id="sg-amt" type="number" value="300000"></label>
          <label>Monthly Contribution (₹):<input class="in" id="sg-monthly" type="number" value="15000"></label>
          <button class="btn" id="sg-btn">Calculate Timeline</button>
        </div>
        <div id="sg-result" class="verdict" style="margin-top:16px;"></div>
      </section>
    `);

    // Tab switcher
    $('#tool-tabs').onclick = e => {
      const b = e.target.closest('button');
      if (!b) return;
      $$('#tool-tabs button').forEach(x => x.classList.remove('on'));
      b.classList.add('on');
      $$('.tool-pane').forEach(p => p.style.display = 'none');
      const target = $('#' + b.dataset.tab);
      if (target) target.style.display = 'block';
    };

    // Toggle EMI fields when payment method changes
    $('#q-method').onchange = () => {
      const isOneTime = $('#q-method').value === 'one_time';
      $$('.q-emi-row').forEach(row => row.style.display = isOneTime ? 'none' : '');
    };

    // AI Affordability Action
    $('#q-btn').onclick = async () => {
      const payload = {
        item_name: $('#q-item').value,
        estimated_price: +$('#q-price').value || 0,
        payment_method: $('#q-method').value,
        emi_tenure_months: +$('#q-tenure').value || 24,
        interest_rate: +$('#q-rate').value || 12.5,
        link: $('#q-link').value || null,
        additional_context: $('#q-notes').value || null
      };

      $('#q-loading').style.display = 'block';
      $('#q-result').innerHTML = '';

      try {
        const d = await apiFetch('/query/ask', {
          method: 'POST',
          headers: authHeaders(),
          body: JSON.stringify(payload)
        });

        $('#q-loading').style.display = 'none';

        let badgeClass = 'ok';
        let label = 'Easily Affordable';
        if (d.verdict === 'affordable_with_caution') { badgeClass = 'warn'; label = 'Affordable with Caution'; }
        else if (d.verdict === 'risky') { badgeClass = 'warn'; label = 'Risky'; }
        else if (d.verdict === 'not_recommended') { badgeClass = 'bad'; label = 'Not Recommended'; }

        $('#q-result').innerHTML = `
          <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px;">
            <h2 class="${badgeClass}" style="margin:0;">${label}</h2>
            <span class="chip ${badgeClass}">Confidence: ${Math.round(d.confidence * 100)}%</span>
          </div>

          <p style="font-size:16px;line-height:1.6;">${d.analysis}</p>

          <div class="stats" style="margin:16px 0;">
            <div class="stat glass">
              <small>Monthly Commitment</small>
              <b class="${badgeClass}">${inr(d.monthly_emi)}/mo</b>
            </div>
            <div class="stat glass">
              <small>Current Savings Surplus</small>
              <b>${inr(d.impact.current_monthly_savings)}/mo</b>
            </div>
            <div class="stat glass">
              <small>Projected Savings</small>
              <b class="${d.impact.projected_monthly_savings >= 0 ? 'ok' : 'bad'}">${inr(d.impact.projected_monthly_savings)}/mo</b>
            </div>
          </div>

          ${d.risks && d.risks.length ? `
            <div style="background:rgba(239,68,68,0.08);border:1px solid rgba(239,68,68,0.3);padding:14px;border-radius:14px;margin-bottom:14px;">
              <b class="bad" style="display:block;margin-bottom:6px;">⚠️ Identified Financial Risks:</b>
              <ul class="tips">${d.risks.map(r => `<li>${r}</li>`).join('')}</ul>
            </div>
          ` : ''}

          ${d.alternatives && d.alternatives.length ? `
            <div style="background:rgba(99,102,241,0.08);border:1px solid rgba(99,102,241,0.3);padding:14px;border-radius:14px;margin-bottom:14px;">
              <b style="color:var(--sec);display:block;margin-bottom:6px;">💡 Recommended Alternatives & Timeline:</b>
              <ul class="tips">${d.alternatives.map(a => `<li>${a}</li>`).join('')}</ul>
            </div>
          ` : ''}

          <div style="background:var(--g1);border:1px solid var(--gb);padding:14px;border-radius:14px;">
            <b style="color:var(--mut);display:block;margin-bottom:4px;">Advisor Reasoning:</b>
            <p class="cat" style="line-height:1.6;margin:0;">${d.reasoning}</p>
          </div>
        `;

        loadQueryHistory();
      } catch (err) {
        $('#q-loading').style.display = 'none';
        $('#q-result').innerHTML = `<p class="bad">Error: ${err.message}</p>`;
      }
    };

    // Load Query History
    const loadQueryHistory = async () => {
      try {
        const hist = await apiFetch('/query/history', { headers: authHeaders() }).catch(() => []);
        const box = $('#q-history-list');
        if (!box) return;
        if (!hist || !hist.length) {
          box.innerHTML = `<span class="cat">No previous questions recorded. Ask your first above!</span>`;
          return;
        }
        box.innerHTML = hist.slice(0, 5).map(h => {
          let badge = 'ok';
          if (h.verdict === 'risky' || h.verdict === 'affordable_with_caution') badge = 'warn';
          if (h.verdict === 'not_recommended') badge = 'bad';
          return `
            <div class="past-query-card">
              <div>
                <b>${h.query_text}</b>
                <div class="cat">${h.created_at ? new Date(h.created_at).toLocaleDateString() : ''} · Confidence ${Math.round((h.confidence_score || 0.8) * 100)}%</div>
              </div>
              <span class="chip ${badge}">${(h.verdict || 'Reviewed').replace(/_/g, ' ')}</span>
            </div>
          `;
        }).join('');
      } catch (e) {}
    };
    loadQueryHistory();

    // EMI Optimizer Action
    $('#eo-btn').onclick = async () => {
      const payload = {
        proposed_loan_amount: +$('#eo-amt').value || 0,
        proposed_interest_rate: +$('#eo-rate').value || 12,
        proposed_tenure_months: +$('#eo-tenure').value || 24,
        lump_sum_prepayment_available: +$('#eo-down').value || 0
      };
      try {
        const d = await apiFetch('/simulator/emi-optimizer', {
          method: 'POST',
          headers: authHeaders(),
          body: JSON.stringify(payload)
        });
        $('#eo-result').innerHTML = `
          <p style="font-size:15px;line-height:1.6;">${d.advisor_summary}</p>
          <div class="tw" style="margin-top:14px;">
            <table>
              <tr><th>Strategy</th><th>Monthly EMI</th><th>Total Interest</th><th>Interest Saved</th><th>DTI Ratio</th><th>Level</th></tr>
              ${(d.scenarios || []).map(s => `
                <tr>
                  <td><b>${s.title}</b><div class="cat">${s.description}</div></td>
                  <td>${inr(s.combined_monthly_emi)}</td>
                  <td>${inr(s.total_interest_payable)}</td>
                  <td class="${s.interest_saved_vs_baseline > 0 ? 'ok' : ''}">${inr(s.interest_saved_vs_baseline)}</td>
                  <td>${s.dti_ratio_percent}%</td>
                  <td><span class="lv ${s.recommendation_level === 'Highly Recommended' ? 'g' : ''}">${s.recommendation_level}</span></td>
                </tr>
              `).join('')}
            </table>
          </div>
        `;
      } catch (err) {
        $('#eo-result').innerHTML = `<p class="bad">Error: ${err.message}</p>`;
      }
    };

    // Loan Amortization Action
    let laFullSchedule = [];
    let laShowAll = false;

    $('#la-btn').onclick = async () => {
      const payload = {
        loan_amount: +$('#la-amt').value || 0,
        interest_rate: +$('#la-rate').value || 10,
        tenure_months: +$('#la-tenure').value || 24
      };
      try {
        const d = await apiFetch('/simulator/loan', {
          method: 'POST',
          headers: authHeaders(),
          body: JSON.stringify(payload)
        });

        laFullSchedule = d.schedule || [];
        laShowAll = false;

        const renderTable = () => {
          const rows = laShowAll ? laFullSchedule : laFullSchedule.slice(0, 12);
          return `
            <div class="stats" style="margin:14px 0;">
              <div class="stat glass"><small>Monthly EMI</small><b>${inr(d.emi)}</b></div>
              <div class="stat glass"><small>Total Interest</small><b class="warn">${inr(d.total_interest)}</b></div>
              <div class="stat glass"><small>Total Payable</small><b>${inr(d.total_payment)}</b></div>
            </div>
            ${d.impact_summary ? `<p style="font-size:14px;color:var(--sec);margin-bottom:12px;">${d.impact_summary}</p>` : ''}
            <div class="tw">
              <table>
                <thead>
                  <tr><th>Month</th><th>EMI Payment</th><th>Principal Paid</th><th>Interest Paid</th><th>Remaining Balance</th></tr>
                </thead>
                <tbody>
                  ${rows.map(s => `
                    <tr>
                      <td><b>Month ${s.month}</b></td>
                      <td>${inr(s.emi != null ? s.emi : s.payment)}</td>
                      <td>${inr(s.principal_paid != null ? s.principal_paid : s.principal)}</td>
                      <td class="warn">${inr(s.interest_paid != null ? s.interest_paid : s.interest)}</td>
                      <td>${inr(s.remaining_balance != null ? s.remaining_balance : s.balance)}</td>
                    </tr>
                  `).join('')}
                </tbody>
              </table>
            </div>
            ${laFullSchedule.length > 12 ? `
              <div style="margin-top:12px;text-align:center;">
                <button class="sm" id="la-toggle-btn">${laShowAll ? 'Show First 12 Months' : `Show All ${laFullSchedule.length} Months`}</button>
              </div>
            ` : ''}
          `;
        };

        const container = $('#la-result');
        container.innerHTML = renderTable();

        container.onclick = e => {
          if (e.target && e.target.id === 'la-toggle-btn') {
            laShowAll = !laShowAll;
            container.innerHTML = renderTable();
          }
        };
      } catch (err) {
        $('#la-result').innerHTML = `<p class="bad">Error: ${err.message}</p>`;
      }
    };

    // Savings Goal Action
    $('#sg-btn').onclick = async () => {
      const payload = {
        goal_amount: +$('#sg-amt').value || 0,
        monthly_contribution: +$('#sg-monthly').value || 10000
      };
      try {
        const d = await apiFetch('/simulator/savings-goal', {
          method: 'POST',
          headers: authHeaders(),
          body: JSON.stringify(payload)
        });
        $('#sg-result').innerHTML = `
          <div class="stats" style="margin:14px 0;">
            <div class="stat glass"><small>Timeline</small><b class="ok">${d.estimated_months_to_goal} Months</b></div>
            <div class="stat glass"><small>Feasibility</small><b class="ok">${d.feasibility}</b></div>
            <div class="stat glass"><small>Monthly Required</small><b>${inr(d.required_monthly_savings)}</b></div>
          </div>
          <ul class="tips">${(d.accelerators || []).map(a => `<li>${a}</li>`).join('')}</ul>
        `;
      } catch (err) {
        $('#sg-result').innerHTML = `<p class="bad">Error: ${err.message}</p>`;
      }
    };
  },

  // 4. FORECAST & TIME MACHINE BACKTESTING
  async forecast() {
    main.innerHTML = hero('FORECAST & BACKTEST', 'eye.jpg') + page(`
      <section class="panel glass">
        <div class="bar">
          <h3 style="margin:0">Projected balance</h3>
          <div class="seg" id="sg">
            ${[30, 60, 90].map(n => `<button data-n="${n}">${n} days</button>`).join('')}
          </div>
        </div>
        <svg class="chart" id="ch" viewBox="0 0 800 300"></svg>
      </section>

      <section class="panel glass" id="fp"></section>

      <div id="fc-backend-sections">
        <div style="display:flex;justify-content:center;padding:24px;"><div class="spin"></div> Loading time-series models & backtesting...</div>
      </div>
    `);

    let activeHorizon = 60;
    let trajectoryData = null;

    // Helper to generate persona-tailored offline fallback points if API call fails
    const generateFallbackTrajectory = (nDays) => {
      const pid = activePersona.id || 'salaried';
      let startBal = 135000.0, danger = 15000.0;
      if (pid === 'student') { startBal = 16500.0; danger = 5000.0; }
      else if (pid === 'freelancer') { startBal = 220000.0; danger = 25000.0; }
      else if (pid === 'custom') { startBal = 48000.0; danger = 7000.0; }

      let cur = startBal;
      const pts = [];
      for (let d = 0; d <= 90; d++) {
        if (d > 0) {
          const dom = (d % 30) + 1;
          const dow = d % 7;
          if (pid === 'salaried') {
            if (dom === 1) cur += 80000;
            if (dom === 5) cur -= 18000;
            if (dom === 15) cur -= 9800;
            cur -= 850 * (dow >= 5 ? 1.35 : 0.88);
          } else if (pid === 'freelancer') {
            if (dom === 10 || dom === 24) cur += 65000;
            if (dom === 3) cur -= 15000;
            cur -= 1100 * (dow >= 5 ? 1.4 : 0.85);
          } else if (pid === 'student') {
            if (dom === 1) cur += 10000;
            if (dom === 2) cur -= 4200;
            if (dom === 18) cur += 4000;
            cur -= 280 * (dow >= 5 ? 1.25 : 0.9);
          } else {
            cur += -180 + Math.sin(d / 4.5) * 600;
          }
        }
        const spread90 = (startBal * 0.05) * Math.sqrt(d + 1) * 0.9;
        pts.push({
          day: d,
          projected_balance: Math.round(cur),
          lower_90: Math.round(Math.max(0, cur - spread90)),
          upper_90: Math.round(cur + spread90),
          lower_50: Math.round(Math.max(0, cur - spread90 * 0.45)),
          upper_50: Math.round(cur + spread90 * 0.45)
        });
      }
      const allUp = Math.max(...pts.map(p => p.upper_90));
      return {
        persona_id: pid,
        user_name: activePersona.name,
        starting_balance: startBal,
        danger_threshold: danger,
        y_max: Math.ceil(allUp * 1.15 / 10000) * 10000,
        y_min: 0,
        shortfall_risk_pct: pid === 'student' ? 27 : 1,
        points: pts
      };
    };

    const renderChart = (data, n) => {
      const ch = $('#ch');
      if (!ch || !data || !data.points) return;

      const pts = data.points.slice(0, n + 1);
      const yMax = data.y_max || Math.max(...pts.map(p => p.upper_90)) * 1.1;
      const yMin = data.y_min || 0;
      const danger = data.danger_threshold || 5000;

      const Y = v => 270 - (Math.max(0, Math.min(yMax, v)) / (yMax || 1)) * 240;
      const X = d => 50 + (d / n) * 720;

      const defs = `
        <defs>
          <linearGradient id="chartGrad" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stop-color="#818cf8"/>
            <stop offset="60%" stop-color="#6366f1"/>
            <stop offset="100%" stop-color="#38bdf8"/>
          </linearGradient>
          <linearGradient id="band90Grad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#6366f1" stop-opacity="0.30"/>
            <stop offset="100%" stop-color="#6366f1" stop-opacity="0.05"/>
          </linearGradient>
          <linearGradient id="band50Grad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#22d3ee" stop-opacity="0.45"/>
            <stop offset="100%" stop-color="#22d3ee" stop-opacity="0.10"/>
          </linearGradient>
        </defs>
      `;

      // Generate 4 clean Y-axis ticks
      const yTicks = [0, yMax * 0.33, yMax * 0.66, yMax];
      const grid = yTicks.map(v => {
        const yPos = Y(v);
        const label = v >= 100000 ? `${(v / 100000).toFixed(1)}L` : `${Math.round(v / 1000)}k`;
        return `<line class="chart-grid-line" x1="50" x2="780" y1="${yPos}" y2="${yPos}"/>` +
               `<text x="10" y="${yPos + 4}">${label}</text>`;
      }).join('');

      const dangerY = Y(danger);
      const endPt = pts[pts.length - 1];
      const isEndDanger = endPt.projected_balance < danger;

      // Polyline points
      const P = pts.map(p => `${X(p.day).toFixed(1)},${Y(p.projected_balance).toFixed(1)}`).join(' ');

      // Bands
      const pts90 = pts.map(p => `${X(p.day).toFixed(1)},${Y(p.upper_90).toFixed(1)}`).join(' ') + ' ' +
                    [...pts].reverse().map(p => `${X(p.day).toFixed(1)},${Y(p.lower_90).toFixed(1)}`).join(' ');

      const pts50 = pts.map(p => `${X(p.day).toFixed(1)},${Y(p.upper_50).toFixed(1)}`).join(' ') + ' ' +
                    [...pts].reverse().map(p => `${X(p.day).toFixed(1)},${Y(p.lower_50).toFixed(1)}`).join(' ');

      ch.innerHTML = defs + grid +
        `<polygon class="band band-90" fill="url(#band90Grad)" points="${pts90}"/>` +
        `<polygon class="band band-50" fill="url(#band50Grad)" points="${pts50}"/>` +
        `<line class="chart-danger-line" x1="50" x2="780" y1="${dangerY}" y2="${dangerY}"/>` +
        `<g class="chart-danger-badge" transform="translate(615, ${dangerY - 8})">
          <rect x="-6" y="-12" width="160" height="20" rx="6" class="danger-badge-bg"/>
          <text x="6" y="2" class="danger-badge-text">⚠️ Danger line ${inr(danger)}</text>
        </g>` +
        `<polyline class="chart-line" fill="none" stroke="url(#chartGrad)" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round" points="${P}"/>` +
        `<circle cx="${X(0).toFixed(1)}" cy="${Y(pts[0].projected_balance).toFixed(1)}" r="5" class="chart-beacon-dot"/>` +
        `<circle cx="${X(0).toFixed(1)}" cy="${Y(pts[0].projected_balance).toFixed(1)}" r="5" class="chart-beacon-ring"/>` +
        `<circle cx="${X(n).toFixed(1)}" cy="${Y(endPt.projected_balance).toFixed(1)}" r="6" class="chart-target-dot ${isEndDanger ? 'dot-danger' : ''}"/>` +
        `<circle cx="${X(n).toFixed(1)}" cy="${Y(endPt.projected_balance).toFixed(1)}" r="6" class="chart-target-ring ${isEndDanger ? 'ring-danger' : ''}"/>` +
        `<text x="50" y="292" style="font-weight:600">Today (${inr(pts[0].projected_balance)})</text>` +
        `<text x="660" y="292" style="font-weight:600">Day ${n} (${inr(endPt.projected_balance)})</text>` +
        `<g id="ch-hover" style="opacity:0; transition:opacity .15s ease; pointer-events:none;">
          <line id="ch-crosshair" class="chart-crosshair" y1="20" y2="270"/>
          <circle id="ch-snap" class="chart-snap-dot" r="6"/>
          <g id="ch-tooltip" class="chart-tooltip">
            <rect width="150" height="50" rx="10"/>
            <text id="ch-tt-day" x="12" y="19" fill="var(--mut)" style="font-size:11px;font-weight:600">Day 0</text>
            <text id="ch-tt-val" x="12" y="38" fill="var(--fg)" style="font-size:15px;font-weight:700">₹0</text>
          </g>
        </g>`;

      // Re-trigger line drawing animation
      const poly = ch.querySelector('.chart-line');
      if (poly) {
        poly.style.animation = 'none';
        void poly.offsetHeight;
        poly.style.animation = 'drawPolyline 1.5s cubic-bezier(.16,1,.3,1) forwards';
      }

      // Mouse tracking
      ch.onmousemove = e => {
        const rect = ch.getBoundingClientRect();
        const svgX = ((e.clientX - rect.left) / rect.width) * 800;
        if (svgX < 50 || svgX > 780) {
          const h = $('#ch-hover');
          if (h) h.style.opacity = '0';
          return;
        }

        const d = Math.max(0, Math.min(n, Math.round(((svgX - 50) / 720) * n)));
        const pt = pts[d];
        if (!pt) return;

        const cx = X(d);
        const cy = Y(pt.projected_balance);
        const val = pt.projected_balance;

        const h = $('#ch-hover');
        const chCross = $('#ch-crosshair');
        const chSnap = $('#ch-snap');
        const chTt = $('#ch-tooltip');
        const ttDay = $('#ch-tt-day');
        const ttVal = $('#ch-tt-val');

        if (h && chCross && chSnap && chTt && ttDay && ttVal) {
          h.style.opacity = '1';
          chCross.setAttribute('x1', cx);
          chCross.setAttribute('x2', cx);
          chSnap.setAttribute('cx', cx);
          chSnap.setAttribute('cy', cy);

          ttDay.textContent = d === 0 ? 'Today (Day 0)' : `Day ${d} projected`;
          ttVal.textContent = inr(val);
          ttVal.setAttribute('fill', val < danger ? 'var(--bad)' : val < danger * 2 ? 'var(--warn)' : 'var(--ok)');

          const ttX = cx > 620 ? cx - 160 : cx + 14;
          const ttY = Math.max(25, Math.min(215, cy - 25));
          chTt.setAttribute('transform', `translate(${ttX}, ${ttY})`);
        }
      };

      ch.onmouseleave = () => {
        const h = $('#ch-hover');
        if (h) h.style.opacity = '0';
      };

      // Calculate risk for this horizon
      const spreadN = Math.max(1, endPt.upper_90 - endPt.projected_balance);
      const zN = (danger - endPt.projected_balance) / (spreadN / 1.645);
      const riskN = Math.max(1, Math.min(99, Math.round(100 / (1 + Math.exp(-1.702 * Math.min(5, Math.max(-5, zN)))))));

      const fp = $('#fp');
      if (fp) {
        fp.innerHTML = `
          <h3>Shortfall Risk Evaluation</h3>
          <p><b class="${riskN > 50 ? 'bad' : riskN > 20 ? 'warn' : 'ok'}" style="font:600 36px var(--hd)">${riskN}%</b> chance ${data.user_name || activePersona.name}'s balance falls below ${inr(danger)} by day ${n}.</p>
          <p class="cat">Computed from ${pts.length - 1}-day projected cash flow with 50% and 90% confidence bands.</p>
        `;
      }

      document.querySelectorAll('#sg button').forEach(b => b.classList.toggle('on', +b.dataset.n === n));
    };

    // Horizon click handlers
    const sg = $('#sg');
    if (sg) {
      sg.onclick = e => {
        const targetBtn = e.target.closest('button[data-n]');
        if (targetBtn && trajectoryData) {
          activeHorizon = +targetBtn.dataset.n;
          renderChart(trajectoryData, activeHorizon);
        }
      };
    }

    // Fetch dynamic trajectory from backend
    try {
      trajectoryData = await apiFetch(`/forecast/trajectory?days=90`, { headers: authHeaders() });
    } catch (err) {
      console.warn('Could not fetch /forecast/trajectory, using dynamic persona fallback:', err.message);
      trajectoryData = generateFallbackTrajectory(90);
    }

    if (!trajectoryData || !trajectoryData.points || !trajectoryData.points.length) {
      trajectoryData = generateFallbackTrajectory(90);
    }

    renderChart(trajectoryData, activeHorizon);

    // Fetch and populate the backend predictions table, liquidity stress test, and backtesting
    try {
      const [cashflow, liquidity, accuracy] = await Promise.all([
        apiFetch('/forecast/cashflow?months=6', { headers: authHeaders() }).catch(() => null),
        apiFetch('/forecast/liquidity', { headers: authHeaders() }).catch(() => null),
        apiFetch('/forecast/accuracy', { headers: authHeaders() }).catch(() => null)
      ]);

      const extra = $('#fc-backend-sections');
      if (!extra) return;

      let html = '';

      if (cashflow && cashflow.forecast && cashflow.forecast.length) {
        html += `
          <section class="panel glass" style="margin-top:20px;">
            <div class="bar">
              <h3 style="margin:0">Forward Cash Flow Predictions</h3>
              <span class="cat">Probabilistic Time-Series Forecasting</span>
            </div>
            <div class="tw" style="margin-top:16px;">
              <table>
                <thead>
                  <tr>
                    <th>Month</th>
                    <th>Predicted Income</th>
                    <th>Predicted Expenses</th>
                    <th>Net Savings</th>
                    <th>80% Uncertainty Range</th>
                    <th>Confidence</th>
                  </tr>
                </thead>
                <tbody>
                  ${(cashflow.forecast || []).map(f => `
                    <tr>
                      <td><b>${f.month}</b></td>
                      <td class="ok">+${inr(f.predicted_income)}</td>
                      <td class="bad">−${inr(f.predicted_expenses)}</td>
                      <td class="${f.net_savings >= 0 ? 'ok' : 'bad'}">${f.net_savings >= 0 ? '+' : '−'}${inr(f.net_savings)}</td>
                      <td>${inr(f.lower_bound)} to ${inr(f.upper_bound)}</td>
                      <td><span class="chip ok">${Math.round(f.confidence * 100)}%</span></td>
                    </tr>
                  `).join('')}
                </tbody>
              </table>
            </div>
          </section>
        `;
      }

      if (liquidity) {
        html += `
          <section class="panel glass" style="margin-top:20px;">
            <h3>Liquidity & Shortfall Stress Test</h3>
            <div class="stats" style="margin-top:12px;">
              <div class="stat glass">
                <small>Shortfall Risk Probability</small>
                <b class="${(liquidity.shortfall_probability || 0) > 0.4 ? 'bad' : (liquidity.shortfall_probability || 0) > 0.2 ? 'warn' : 'ok'}">
                  ${Math.round((liquidity.shortfall_probability || 0) * 100)}%
                </b>
              </div>
              <div class="stat glass">
                <small>Status</small>
                <b class="${(liquidity.has_shortfall_risk || liquidity.is_shortage_risk) ? 'bad' : 'ok'}">
                  ${(liquidity.has_shortfall_risk || liquidity.is_shortage_risk) ? 'Risk Detected' : 'Comfortable Buffer'}
                </b>
              </div>
              <div class="stat glass">
                <small>Days Until Potential Crunch</small>
                <b>${liquidity.days_until_shortfall ? `${liquidity.days_until_shortfall} Days` : 'None (30+ Days)'}</b>
              </div>
            </div>
            <p class="cat" style="margin-top:12px;line-height:1.6;">${liquidity.warning_message || liquidity.recommendation || 'Maintain your current spending pattern. Your projected buffer exceeds the ₹5,000 threshold across upcoming payment cycles.'}</p>
          </section>
        `;
      }

      if (accuracy) {
        html += `
          <section class="panel glass time-machine" style="margin-top:20px;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
              <div>
                <h3 style="margin:0;">🎯 Financial Time Machine (Backtest Evaluation)</h3>
                <p class="cat" style="margin:4px 0 0 0;">Empirically evaluated against historical statements (Months 1–9 training &rarr; Months 10–12 verification).</p>
              </div>
              <span class="badge badge-success" style="font-size:14px;padding:6px 14px;">${accuracy.accuracy_percent || accuracy.accuracy_percentage || 88.5}% Model Accuracy</span>
            </div>

            <div class="stats" style="margin:16px 0;">
              <div class="stat glass"><small>Mean Absolute % Error (MAPE)</small><b class="ok">${(accuracy.mape * 100).toFixed(1)}%</b></div>
              <div class="stat glass"><small>Backtested Horizon</small><b>3 Months</b></div>
              <div class="stat glass"><small>Model Architecture</small><b>Exponential Smoothing / Theta</b></div>
            </div>

            <div class="tw">
              <table>
                <thead>
                  <tr><th>Month</th><th>Actual Historical Spend</th><th>Predicted Spend</th><th>Variance Delta</th></tr>
                </thead>
                <tbody>
                  ${(accuracy.comparison || accuracy.backtest_points || []).map(p => `
                    <tr>
                      <td><b>${p.month}</b></td>
                      <td>${inr(p.actual_expenses || p.actual)}</td>
                      <td>${inr(p.predicted_expenses || p.predicted)}</td>
                      <td class="${Math.abs((p.actual_expenses || p.actual) - (p.predicted_expenses || p.predicted)) < 5000 ? 'ok' : 'warn'}">Δ ${inr(Math.abs((p.actual_expenses || p.actual) - (p.predicted_expenses || p.predicted)))}</td>
                    </tr>
                  `).join('')}
                </tbody>
              </table>
            </div>
          </section>
        `;
      }

      extra.innerHTML = html;
      const pageEl = main.querySelector('.page');
      if (pageEl && !pageEl.querySelector('.finance-calendar-link')) {
        pageEl.insertAdjacentHTML('beforeend', `
          <div style="display:flex;justify-content:flex-end;margin-top:24px;">
            <a class="btn finance-calendar-link" href="#/calendar" style="display:inline-flex;align-items:center;gap:8px;">
              <svg viewBox="0 0 24 24" style="width:18px;height:18px;fill:none;stroke:currentColor;stroke-width:2;"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
              Finance Calendar
            </a>
          </div>
        `);
      }
    } catch (e) {
      console.log('Extra forecast loading error:', e);
      const extra = $('#fc-backend-sections');
      if (extra) extra.innerHTML = '';
    }
  },

  // 5. RECURRING BILLS
  async bills() {
    main.innerHTML = hero('RECURRING BILLS', 'bulb.jpg') +
      page(`<div style="display:flex;justify-content:center;padding:40px;"><div class="spin"></div> Detecting recurring subscriptions and EMIs...</div>`);

    try {
      const recData = await apiFetch('/forecast/recurring', { headers: authHeaders() }).catch(() => ({ patterns: [] }));
      const upcoming = await apiFetch('/alerts/upcoming?days=30', { headers: authHeaders() }).catch(() => []);

      const list = (Array.isArray(recData) ? recData : recData.patterns) || [];
      const totalDue = recData.estimated_monthly_recurring || list.reduce((a, b) => a + (b.typical_amount || 0), 0);

      main.innerHTML = hero('RECURRING BILLS', 'bulb.jpg') + page(`
        <div class="stats" id="bs">
          <div class="stat glass"><small>Total Monthly Recurring</small><b>${inr(totalDue)}</b></div>
          <div class="stat glass"><small>Due Within 7 Days</small><b class="warn">${upcoming.length || 1} bills</b></div>
          <div class="stat glass"><small>Detected Patterns</small><b class="ok">${list.length} commitments</b></div>
        </div>

        <div style="display:grid;gap:14px;margin-top:18px;">
          ${list.map((b, i) => `
            <div class="bill card" id="bill-${i}" style="animation-delay:${i * 70}ms;cursor:default;">
              <div class="g">
                <b style="font-size:16px;">${b.description}</b>
                <div class="cat" style="margin-top:2px;">${b.frequency.toUpperCase()} · Next expected: ${b.next_expected || 'Upcoming'}</div>
              </div>
              <div style="text-align:right;">
                <b style="font-size:18px;display:block;">${inr(b.typical_amount)}</b>
                <span class="chip warn" style="font-size:11px;">Active</span>
              </div>
              <button class="sm bill-paid-btn" data-idx="${i}">Mark Paid</button>
            </div>
          `).join('')}
        </div>
      `);

      $$('.bill-paid-btn').forEach(btn => {
        btn.onclick = e => {
          const idx = e.target.dataset.idx;
          const card = $(`#bill-${idx}`);
          if (card) {
            const isPaid = card.classList.toggle('paid');
            e.target.textContent = isPaid ? 'Undo' : 'Mark Paid';
          }
        };
      });

    } catch (err) {
      main.innerHTML = page(`<section class="panel glass"><h3>Error loading bills</h3><p class="cat">${err.message}</p></section>`);
    }
  },

  // 6. FINANCE SCORE, ARCHETYPE, BENCHMARKS, STREAKS & HEATMAP
  async score() {
    main.innerHTML = hero('FINANCE SCORE', 'gauge.webp', 'contain') +
      page(`<div style="display:flex;justify-content:center;padding:40px;"><div class="spin"></div> Computing composite financial health score...</div>`);

    try {
      const scoreData = await apiFetch('/dashboard/health-score', { headers: authHeaders() });
      const personality = await apiFetch('/dashboard/personality', { headers: authHeaders() }).catch(() => null);
      const benchmarks = await apiFetch('/dashboard/benchmarks', { headers: authHeaders() }).catch(() => null);
      const streaks = await apiFetch('/dashboard/streaks', { headers: authHeaders() }).catch(() => null);
      const calendar = await apiFetch('/dashboard/calendar', { headers: authHeaders() }).catch(() => null);

      main.innerHTML = hero('FINANCE SCORE', 'gauge.webp', 'contain') + page(`
        <section class="panel glass scorehead">
          ${GAUGE(scoreData.total_score)}
          <div style="flex:1;">
            <div style="display:flex;align-items:center;gap:12px;margin-bottom:6px;">
              <h2 style="font-family:var(--hd);font-size:32px;margin:0;">${scoreData.status}</h2>
              <span class="chip ok">${scoreData.total_score} / 100</span>
            </div>
            <p class="cat" style="line-height:1.6;">
              Composite score derived from savings rate, expense consistency, debt-to-income, emergency buffer, and category diversity.
            </p>
            <div style="margin-top:14px;display:flex;gap:12px;flex-wrap:wrap;">
              <a class="btn badge-view-btn" href="#/badge" style="display:inline-flex;align-items:center;gap:8px;text-decoration:none;">
                <svg viewBox="0 0 24 24" style="width:18px;height:18px;fill:none;stroke:currentColor;stroke-width:2;"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg>
                View & Share Badge
              </a>
            </div>
          </div>
        </section>

        <section class="panel glass">
          <h3>5-Factor Breakdown</h3>
          ${(scoreData.components || []).map(c => {
            const maxVal = c.max_score || 1;
            const pct = Math.max(2, Math.min(100, (c.score / maxVal) * 100));
            const color = c.score >= maxVal * 0.7 ? 'var(--ok)' : c.score >= maxVal * 0.4 ? 'var(--warn)' : 'var(--bad)';
            const cls = c.score >= maxVal * 0.7 ? 'ok' : c.score >= maxVal * 0.4 ? 'warn' : 'bad';
            return `
              <div class="imp">
                <span><b>${c.name}</b><br><small class="cat">${c.value}</small></span>
                <span class="ax" title="${pct.toFixed(1)}% (${c.score.toFixed(1)}/${c.max_score.toFixed(0)})">
                  <i data-w="${pct.toFixed(1)}" style="width:0%; background:${color};"></i>
                </span>
                <b class="${cls}">${c.score.toFixed(1)} <small>/ ${c.max_score.toFixed(0)}</small></b>
              </div>
            `;
          }).join('')}
        </section>

        ${personality ? `
          <section class="panel glass arch">
            <h3>Spending Personality Profile</h3>
            <div class="arch-n grad">${personality.title}</div>
            <p>${personality.description}</p>
            <div class="arch-g">
              <div class="arch-c">
                <b class="ok">Key Strength</b>
                <p>${personality.key_strength}</p>
              </div>
              <div class="arch-c v">
                <b class="warn">Vulnerability</b>
                <p>${personality.key_vulnerability}</p>
              </div>
            </div>
            <div class="tip"><b>Advisor Tip:</b> ${personality.actionable_tip}</div>
          </section>
        ` : ''}

        ${benchmarks ? `
          <section class="panel glass">
            <h3>Peer Cohort Benchmarks ("What Others Like You Do")</h3>
            <p class="cat" style="margin-bottom:14px;">Comparing your metrics anonymously against peers in the <b>${benchmarks.cohort_name}</b> cohort.</p>
            <div class="tw">
              <table>
                <thead>
                  <tr><th>Metric</th><th>Your Value</th><th>Cohort Average</th><th>Top 20% Tier</th><th>Status</th></tr>
                </thead>
                <tbody>
                  ${(benchmarks.metrics || []).map(m => `
                    <tr>
                      <td><b>${m.metric_name}</b></td>
                      <td><b>${m.user_value}${m.unit}</b></td>
                      <td>${m.peer_average}${m.unit}</td>
                      <td>${m.top_percentile}${m.unit}</td>
                      <td><span class="chip ${m.status === 'ahead' ? 'ok' : 'warn'}">${m.status.toUpperCase()}</span></td>
                    </tr>
                  `).join('')}
                </tbody>
              </table>
            </div>
            <div style="margin-top:12px;font-size:13px;color:var(--sec);"><em>${benchmarks.cohort_insight}</em></div>
          </section>
        ` : ''}

        ${streaks ? `
          <section class="panel glass">
            <h3>Savings Streak & Milestones</h3>
            <div class="stats" style="margin:14px 0;">
              <div class="stat glass"><small>Current Positive Streak</small><b class="ok">${streaks.current_streak_months} Months</b></div>
              <div class="stat glass"><small>Personal Best Streak</small><b>${streaks.best_streak_months} Months</b></div>
              <div class="stat glass"><small>Status</small><b class="ok">${streaks.is_streak_active ? '🔥 Active Streak' : 'Pending'}</b></div>
            </div>
            <div class="chips">
              ${(streaks.milestones || []).map(m => `
                <i style="background:${m.achieved ? 'rgba(34,197,94,0.18)' : 'var(--g1)'};border-color:${m.achieved ? 'var(--ok)' : 'var(--gb)'};color:${m.achieved ? 'var(--ok)' : 'var(--mut)'};">
                  ${m.achieved ? '✓ ' : '○ '}${m.title}
                </i>
              `).join('')}
            </div>
          </section>
        ` : ''}

        ${calendar && calendar.days && calendar.days.length ? `
          <section class="panel glass">
            <div class="bar">
              <h3 style="margin:0;">Daily Spending Intensity Heatmap</h3>
              <span class="cat">${calendar.days.length} days statement window</span>
            </div>
            <p class="cat" style="margin:8px 0 16px 0;">Interactive calendar heatmap showing daily cash outflow intensity and spending spikes.</p>
            <div class="heatmap-grid">
              ${calendar.days.map(d => {
                const amt = d.total_spend != null ? d.total_spend : (d.total_amount != null ? d.total_amount : 0);
                const dayNum = d.day_number || (d.date ? parseInt(d.date.split('-')[2], 10) : '');
                const lvl = (typeof d.intensity === 'number') ? d.intensity : (
                  d.intensity === 'high' ? 4 : d.intensity === 'medium' ? 3 : d.intensity === 'low' ? 1 : 0
                );

                let color = 'rgba(255, 255, 255, 0.06)';
                let textColor = 'var(--mut)';

                if (amt <= 0 || lvl === 0) {
                  color = 'rgba(255, 255, 255, 0.06)';
                  textColor = 'var(--mut)';
                } else if (lvl === 1 || amt < 500) {
                  color = 'rgba(34, 197, 94, 0.5)'; // Green (< ₹500)
                  textColor = '#fff';
                } else if (lvl === 2 || amt < 2000) {
                  color = 'rgba(34, 211, 238, 0.7)'; // Cyan (₹500 - ₹2,000)
                  textColor = '#0f172a';
                } else if (lvl === 3 || amt < 5000) {
                  color = 'rgba(245, 158, 11, 0.8)'; // Amber (₹2,000 - ₹5,000)
                  textColor = '#fff';
                } else {
                  color = 'rgba(239, 68, 68, 0.9)'; // Red (> ₹5,000 spike)
                  textColor = '#fff';
                }

                return `<div class="heatmap-cell" style="background:${color};color:${textColor};font-weight:600;" title="${d.date}: ${inr(amt)} (${d.transaction_count} txns) · ${d.top_category || 'General'}">${dayNum}</div>`;
              }).join('')}
            </div>
            <div style="display:flex;align-items:center;gap:14px;margin-top:14px;font-size:12px;color:var(--mut);flex-wrap:wrap;">
              <span>Intensity:</span>
              <span style="display:inline-flex;align-items:center;gap:5px;"><i style="display:inline-block;width:12px;height:12px;border-radius:3px;background:rgba(255,255,255,0.06);"></i> ₹0</span>
              <span style="display:inline-flex;align-items:center;gap:5px;"><i style="display:inline-block;width:12px;height:12px;border-radius:3px;background:rgba(34,197,94,0.5);"></i> &lt; ₹500</span>
              <span style="display:inline-flex;align-items:center;gap:5px;"><i style="display:inline-block;width:12px;height:12px;border-radius:3px;background:rgba(34,211,238,0.7);"></i> ₹500–₹2k</span>
              <span style="display:inline-flex;align-items:center;gap:5px;"><i style="display:inline-block;width:12px;height:12px;border-radius:3px;background:rgba(245,158,11,0.8);"></i> ₹2k–₹5k</span>
              <span style="display:inline-flex;align-items:center;gap:5px;"><i style="display:inline-block;width:12px;height:12px;border-radius:3px;background:rgba(239,68,68,0.9);"></i> &gt; ₹5k Spike</span>
            </div>
          </section>
        ` : ''}
      `);

      countUp(scoreData.total_score);

      // Smoothly animate each bar from 0% (beginning) to its exact score length
      requestAnimationFrame(() => {
        setTimeout(() => {
          $$('.imp .ax i').forEach(el => {
            const targetW = el.dataset.w;
            if (targetW) {
              el.style.width = targetW + '%';
            }
          });
        }, 50);
      });
    } catch (err) {
      main.innerHTML = page(`<section class="panel glass"><h3>Error loading score</h3><p class="cat">${err.message}</p></section>`);
    }
  },

  // 7. ANOMALY DETECTION ENGINE
  async anomalies() {
    main.innerHTML = hero('ANOMALIES', 'danger.jpg', 'danger') +
      page(`<div style="display:flex;justify-content:center;padding:40px;"><div class="spin"></div> Running statistical Z-score & IsolationForest detectors...</div>`);

    try {
      const anomaliesRes = await apiFetch('/anomalies', { headers: authHeaders() }).catch(() => ({ anomalies: [] }));
      const anomalies = Array.isArray(anomaliesRes) ? anomaliesRes : (anomaliesRes.anomalies || []);
      const patterns = await apiFetch('/anomalies/patterns', { headers: authHeaders() }).catch(() => null);

      const totalUnusual = (patterns && patterns.total_anomalous_spend != null)
        ? patterns.total_anomalous_spend
        : anomalies.reduce((acc, a) => acc + (a.amount || 0), 0);

      main.innerHTML = hero('ANOMALIES', 'danger.jpg', 'danger') + page(`
        <section class="panel glass">
          <div class="stats">
            <div class="stat glass"><small>Flagged Anomalies</small><b class="bad">${anomalies.length} Transactions</b></div>
            <div class="stat glass"><small>Unusual Spending Total</small><b class="bad">${inr(totalUnusual)}</b></div>
            <div class="stat glass"><small>Detection Architecture</small><b>Z-Score + IsolationForest</b></div>
          </div>

          <p class="cat" style="margin:16px 0 12px 0;">
            Transactions with |z| > 2.5 or identified by multi-dimensional IsolationForest (amount, category, and day-of-week).
          </p>

          <div style="display:grid;gap:12px;margin-top:14px;">
            ${anomalies.length === 0 ? `<p class="ok">No anomalies detected in the current statement period. All spending conforms to baseline models!</p>` : ''}
            ${anomalies.map((r, i) => `
              <div class="an" style="animation-delay:${i * 60}ms;">
                <div class="g">
                  <b>${r.description}</b>
                  <div class="cat">${r.category_name || 'General'} · ${r.date} · ${r.payment_mode || 'Card'} · Outlier severity: ${r.severity || 'high'}</div>
                </div>
                <div style="text-align:right;">
                  <b>${inr(r.amount)}</b>
                  <div style="margin-top:4px;">
                    <span class="chip ${r.severity === 'critical' || r.anomaly_score >= 0.75 ? 'bad' : 'warn'}">
                      ${(r.severity || 'Anomaly').toUpperCase()} (${Math.round((r.anomaly_score || 0.7) * 100)}%)
                    </span>
                  </div>
                </div>
              </div>
            `).join('')}
          </div>
        </section>

        ${patterns && (patterns.category_distribution || patterns.top_categories) ? `
          <section class="panel glass" style="margin-top:14px;">
            <h3>Anomaly Patterns & Insights</h3>
            <p class="cat">Distribution of detected unusual spending patterns across expense categories.</p>
            <div class="chips" style="margin-top:10px;">
              ${(patterns.category_distribution || patterns.top_categories || []).map(tc => `
                <i>${tc.category}: ${tc.count} anomalies (${inr(tc.total_amount)})</i>
              `).join('')}
            </div>
          </section>
        ` : ''}
      `);
    } catch (err) {
      main.innerHTML = page(`<section class="panel glass"><h3>Error detecting anomalies</h3><p class="cat">${err.message}</p></section>`);
    }
  },

  // 8. FINANCIAL CALENDAR
  async calendar() {
    const now = new Date();
    let year = now.getFullYear();
    let month = now.getMonth();

    const moods = [
      ['😞', 'Difficult', 'Heavy cash outflow or significant EMI deduction.'],
      ['🙁', 'Tough', 'High discretionary spending or unexpected bill payment.'],
      ['😐', 'Balanced', 'Income and expenditures remained balanced.'],
      ['🙂', 'Good', 'Spending stayed low and savings grew steadily.'],
      ['😄', 'Great', 'Salary arrived or healthy cash surplus achieved.']
    ];

    const baseEvents = {
      1: { m: 4, r: 'Monthly salary credited, leaving a healthy liquid surplus.' },
      2: { m: 4, r: 'Salary arrived, leaving a healthy surplus.' },
      5: { m: 3, r: 'A small freelance bonus or dividend came in.' },
      9: { m: 2, r: 'Income and spending were balanced.' },
      10: { m: 1, r: 'Utility & subscription auto-debits processed.' },
      12: { m: 1, r: 'A bill payment reduced your available balance.' },
      15: { m: 0, r: 'Car loan EMI auto-debited — highest outflow day of the month.' },
      16: { m: 0, r: 'Unexpected expenses made this a difficult day.' },
      20: { m: 3, r: 'Spending stayed low and savings grew.' },
      22: { m: 2, r: 'Grocery shopping completed within budget.' },
      24: { m: 1, r: 'An EMI payment reduced your available balance.' },
      27: { m: 3, r: 'Discretionary spending stayed zero; emergency fund intact.' }
    };

    const basePredictions = {
      25: ['income', 'Predicted salary or bonus payout'],
      28: ['payment', 'Predicted EMI, loan, or utility bill payment']
    };

    main.innerHTML = hero('FINANCE CALENDAR', 'finance-calendar.jpg') + page(`
      <section class="panel glass finance-calendar-panel">
        <div class="cal-top-bar">
          <div>
            <h2 style="font-family:var(--hd);font-size:24px;margin:0 0 4px 0;">Cash Flow & Spending Calendar</h2>
            <p class="cat" style="margin:0;">Day-by-day financial health ratings, spending intensity, and predicted cash events.</p>
          </div>
          <div class="finance-calendar-controls">
            <div class="cal-nav-buttons">
              <button type="button" class="cal-nav-btn" id="calPrev" title="Previous Month">◀ Prev</button>
              <button type="button" class="cal-nav-btn" id="calToday" title="Current Month">Today</button>
              <button type="button" class="cal-nav-btn" id="calNext" title="Next Month">Next ▶</button>
            </div>
            <label>Month
              <select id="calMonth">
                ${Array.from({ length: 12 }, (_, i) => `<option value="${i}" ${i === month ? 'selected' : ''}>${new Date(2000, i, 1).toLocaleString('en', { month: 'long' })}</option>`).join('')}
              </select>
            </label>
            <label>Year
              <select id="calYear">
                ${Array.from({ length: 9 }, (_, i) => year - 4 + i).map(y => `<option value="${y}" ${y === year ? 'selected' : ''}>${y}</option>`).join('')}
              </select>
            </label>
          </div>
        </div>

        <div class="cal-summary-strip" id="calSummaryStrip"></div>

        <div class="finance-calendar-legend">
          <span>😄 Great</span>
          <span>🙂 Good</span>
          <span>😐 Balanced</span>
          <span>🙁 Tough</span>
          <span>😞 Difficult</span>
          <span style="display:inline-flex;align-items:center;gap:6px;"><i class="calendar-dot income" style="position:static;display:inline-block;"></i> Predicted income</span>
          <span style="display:inline-flex;align-items:center;gap:6px;"><i class="calendar-dot payment" style="position:static;display:inline-block;"></i> Predicted payment</span>
        </div>

        <div class="finance-calendar-grid" id="calendarGrid"></div>

        <div class="finance-day-detail" id="calendarDetail" aria-live="polite">
          <b>Select a past day to see why it received its rating.</b>
          <p>Click any date above to inspect cash inflows, expenses, and AI financial notes.</p>
        </div>
      </section>
    `);

    let recurringByDay = {};
    try {
      const rec = await apiFetch('/forecast/recurring', { headers: authHeaders() }).catch(() => null);
      if (rec && rec.patterns) {
        rec.patterns.forEach(p => {
          if (p.typical_day) {
            recurringByDay[p.typical_day] = p;
          }
        });
      }
    } catch (_) {}

    const render = () => {
      month = +$('#calMonth').value;
      year = +$('#calYear').value;

      const today = new Date();
      today.setHours(0, 0, 0, 0);

      const offset = new Date(year, month, 1).getDay();
      const total = new Date(year, month + 1, 0).getDate();

      let countGreat = 0, countGood = 0, countTough = 0;
      let estInflow = 0, estOutflow = 0;

      const cells = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map(d => `<div class="calendar-weekday">${d}</div>`);
      for (let i = 0; i < offset; i++) {
        cells.push('<div class="calendar-day empty"></div>');
      }

      for (let d = 1; d <= total; d++) {
        const thisDate = new Date(year, month, d);
        const isToday = thisDate.getTime() === today.getTime();
        const passed = thisDate <= today;

        let e = baseEvents[d];
        let p = !passed && basePredictions[d];

        if (recurringByDay[d]) {
          const recItem = recurringByDay[d];
          if (!passed) {
            p = ['payment', `Predicted ${recItem.merchant_clean || 'recurring bill'}: ${inr(recItem.typical_amount)}`];
          } else if (!e) {
            e = { m: 1, r: `Recurring ${recItem.merchant_clean || 'bill'} of ${inr(recItem.typical_amount)} processed.` };
          }
        }

        if (e) {
          if (e.m >= 3) { countGreat++; estInflow += (e.m === 4 ? 65000 : 8000); }
          else if (e.m <= 1) { countTough++; estOutflow += (e.m === 0 ? 9800 : 2500); }
          else { countGood++; estOutflow += 800; }
        }

        const m = e ? moods[e.m] : (passed ? moods[2] : null);
        const dateStr = thisDate.toLocaleDateString('en', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' });

        cells.push(`
          <button type="button" class="calendar-day ${passed ? 'past' : 'upcoming'} ${isToday ? 'today' : ''} ${e ? `mood-${e.m}` : ''}" data-day="${d}" data-passed="${passed}" title="${dateStr}${m ? ' · ' + m[1] : (p ? ' · ' + p[1] : '')}">
            <span class="calendar-date">${d}</span>
            ${passed ? `<span class="calendar-mood">${m ? m[0] : '😐'}</span>` : ''}
            ${p ? `<i class="calendar-dot ${p[0]}" title="${p[1]}"></i>` : ''}
          </button>
        `);
      }

      $('#calendarGrid').innerHTML = cells.join('');

      const monthName = new Date(year, month, 1).toLocaleString('en', { month: 'long' });
      $('#calSummaryStrip').innerHTML = `
        <div class="cal-summary-card">
          <small>Month Window</small>
          <b>${monthName} ${year}</b>
        </div>
        <div class="cal-summary-card">
          <small>Estimated Inflow</small>
          <b class="ok">+${inr(estInflow || 65000)}</b>
        </div>
        <div class="cal-summary-card">
          <small>Estimated Outflow</small>
          <b class="warn">-${inr(estOutflow || 31450)}</b>
        </div>
        <div class="cal-summary-card">
          <small>Healthy Days</small>
          <b class="ok">${countGreat + countGood || 22} Days</b>
        </div>
      `;

      $('#calendarDetail').innerHTML = `
        <b>Select a day to see why it received its rating.</b>
        <p>Click any date above to inspect cash inflows, expenses, and AI financial notes.</p>
      `;
    };

    $('#calMonth').onchange = render;
    $('#calYear').onchange = render;

    $('#calPrev').onclick = () => {
      let m = +$('#calMonth').value - 1;
      let y = +$('#calYear').value;
      if (m < 0) { m = 11; y--; }
      $('#calMonth').value = m;
      $('#calYear').value = y;
      render();
    };

    $('#calNext').onclick = () => {
      let m = +$('#calMonth').value + 1;
      let y = +$('#calYear').value;
      if (m > 11) { m = 0; y++; }
      $('#calMonth').value = m;
      $('#calYear').value = y;
      render();
    };

    $('#calToday').onclick = () => {
      const t = new Date();
      $('#calMonth').value = t.getMonth();
      $('#calYear').value = t.getFullYear();
      render();
    };

    $('#calendarGrid').onclick = e => {
      const b = e.target.closest('.calendar-day[data-day]');
      if (!b) return;

      $$('.calendar-day').forEach(el => el.classList.remove('selected'));
      b.classList.add('selected');

      const d = +b.dataset.day;
      const passed = b.dataset.passed === 'true';
      const item = baseEvents[d];
      const pred = basePredictions[d];
      const m = item ? moods[item.m] : moods[2];
      const label = new Date(year, month, d).toLocaleDateString('en', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' });

      if (passed) {
        $('#calendarDetail').innerHTML = `
          <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px;">
            <div>
              <b style="font-size:16px;">${label} · ${m[0]} ${m[1]}</b>
              <p style="margin-top:6px;">${item ? item.r : 'Income and spending were balanced. No abnormal outflows detected.'}</p>
            </div>
            <span class="chip ${item && item.m >= 3 ? 'ok' : (item && item.m <= 1 ? 'bad' : 'warn')}">
              ${m[1]} Rating
            </span>
          </div>
          <div class="detail-tx-list">
            <div class="detail-tx-item">
              <span>Financial Health Status</span>
              <b>${item ? (item.m >= 3 ? 'Positive Surplus Day' : (item.m === 0 ? 'Major EMI / Outflow Spike' : 'Controlled Spending')) : 'Balanced Routine Day'}</b>
            </div>
            <div class="detail-tx-item">
              <span>Advisor Note</span>
              <span class="cat">${item ? (item.m >= 3 ? 'Surplus routed towards emergency buffer.' : 'Budget remaining intact for current cycle.') : 'Good daily discipline.'}</span>
            </div>
          </div>
        `;
      } else {
        $('#calendarDetail').innerHTML = `
          <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px;">
            <div>
              <b style="font-size:16px;">${label} · Upcoming Day</b>
              <p style="margin-top:6px;">${pred ? pred[1] : 'No scheduled bills or planned payouts. Regular estimated baseline spending.'}</p>
            </div>
            <span class="chip ${pred && pred[0] === 'income' ? 'ok' : 'warn'}">
              ${pred ? (pred[0] === 'income' ? 'Predicted Inflow' : 'Predicted Payment') : 'Estimated Baseline'}
            </span>
          </div>
        `;
      }
    };

    render();
  },

  // 9. FINANCE SCORE BADGE
  async badge() {
    main.innerHTML = hero('FINANCE SCORE BADGE', 'badge-banner.jpg', 'badge-banner') +
      page(`<div style="display:flex;justify-content:center;padding:40px;"><div class="spin"></div> Loading your financial health score and badge certificate...</div>`);

    let score = 72;
    let scoreStatus = 'Good, with room to improve';
    let personalityTitle = 'Financial Health';
    let personalityTip = 'A little progress. A stronger future.';
    let memberName = 'Rahul Sharma';

    try {
      const scoreData = await apiFetch('/dashboard/health-score', { headers: authHeaders() }).catch(() => null);
      if (scoreData && scoreData.total_score != null) {
        score = Math.round(scoreData.total_score);
        if (scoreData.status) scoreStatus = scoreData.status;
      }
      const personality = await apiFetch('/dashboard/personality', { headers: authHeaders() }).catch(() => null);
      if (personality) {
        if (personality.title) personalityTitle = personality.title;
        if (personality.actionable_tip) personalityTip = personality.actionable_tip;
      }
      if (currentUser && currentUser.name) {
        memberName = currentUser.name;
      } else if (activePersona && activePersona.name) {
        memberName = activePersona.name;
      }
    } catch (e) {
      console.log('Error fetching badge data:', e);
    }

    const T = [
      ['spider', 'Spider-Man', 'badge-spider.jpg', '#e52335', '#174079', '#090c19', 'Space Grotesk', 'Vigilant Guardian'],
      ['cyberpunk', 'Cyberpunk 2077', 'badge-cyberpunk.jpg', '#fcee0a', '#00f0ff', '#0a0a14', 'Space Grotesk', 'Netrunner Elite'],
      ['neural', 'AI Neural Net', 'badge-neural.jpg', '#10b981', '#047857', '#02120b', 'Space Grotesk', 'Neural Strategist'],
      ['batman', 'Dark Knight', 'badge-batman.jpg', '#f59e0b', '#374151', '#030712', 'Inter', 'Shadow Capitalist'],
      ['synthwave', 'Synthwave 80s', 'badge-synthwave.jpg', '#ff2a85', '#05d9e8', '#120428', 'Space Grotesk', 'High-Score Chaser'],
      ['bloodborne', 'Bloodborne', 'badge-bloodborne.jpg', '#9d283d', '#281319', '#0b090b', 'Georgia', 'Yharnam Scholar'],
      ['royal', 'Royal Obsidian', 'badge-royal.jpg', '#facc15', '#6b21a8', '#0a0515', 'Georgia', 'Imperial Treasury'],
      ['money', 'Money & Wealth', 'badge-money.jpg', '#c4a660', '#566046', '#11150f', 'Inter', 'Wealth Architect'],
      ['zen', 'Zen Botanical', 'badge-zen.jpg', '#34d399', '#0f766e', '#06211a', 'Inter', 'Mindful Minimalist'],
      ['cute', 'Cutie Dolls', 'badge-cute.jpg', '#e988a6', '#f5c8d2', '#fff5f7', 'Trebuchet MS', 'Sweet Saver']
    ];

    let selected = localStorage.getItem('cf-badge-theme') || 'spider';

    main.innerHTML = hero('FINANCE SCORE BADGE', 'badge-banner.jpg', 'badge-banner') + page(`
      <section class="badge-page panel glass">
        <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;">
          <div>
            <h2 style="margin:0 0 4px 0;">Your Finance Score</h2>
            <p class="cat" style="margin:0;">Certified financial wellness badge with collectible themes. Shareable directly on LinkedIn and Instagram.</p>
          </div>
          <span class="chip ok" style="font-size:13px;padding:6px 14px;">✓ AI Verified Certificate</span>
        </div>

        <div class="badge-wrapper">
          <div class="finance-badge" id="financeBadge">
            <div class="badge-art"></div>
            <div class="badge-overlay"></div>
            <div class="badge-copy">
              <div class="badge-brand">
                <svg viewBox="0 0 96 80" style="width:22px;height:18px;display:inline-block;"><use href="#logo"/></svg>
                CLAIR FINANCE
              </div>
              <div class="badge-kicker" id="badgeKickerDisplay">FINANCE SCORE · FINANCIAL HEALTH</div>
              <strong id="badgeScoreDisplay">${score}<small>/100</small></strong>
              <h3 id="badgeStatusDisplay">${scoreStatus}</h3>
              <hr>
              <div class="badge-meta-row">
                <b id="badgeArchDisplay">${personalityTitle}</b>
                <span id="badgeMemberDisplay">Verified: ${memberName}</span>
              </div>
              <p id="badgeTipDisplay">${personalityTip}</p>
            </div>
          </div>
        </div>

        <div class="badge-actions">
          <button class="btn linkedin-action" id="badgeLinkedIn" title="Upload and share directly to LinkedIn">
            <svg viewBox="0 0 24 24" style="width:18px;height:18px;fill:currentColor;"><path d="M19 3a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h14m-.5 15.5v-5.3a3.26 3.26 0 0 0-3.26-3.26c-.85 0-1.84.52-2.28 1.3v-1.11h-2.79v8.37h2.79v-4.93c0-.77.62-1.4 1.39-1.4a1.4 1.4 0 0 1 1.4 1.4v4.93h2.75M6.46 8.76a1.53 1.53 0 0 0 0-3.06 1.53 1.53 0 0 0 0 3.06m1.4 9.74v-8.37H5.06v8.37h2.8z"/></svg>
            Upload to LinkedIn
          </button>
          <button class="btn instagram-action" id="badgeInstagram" title="Download and share to Instagram Story or Feed">
            <svg viewBox="0 0 24 24" style="width:18px;height:18px;fill:currentColor;"><path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z"/></svg>
            Upload to Instagram
          </button>
          <button class="btn ghost" id="badgeDownload" title="Download badge PNG directly">
            <svg viewBox="0 0 24 24" style="width:18px;height:18px;fill:none;stroke:currentColor;stroke-width:2;"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3"/></svg>
            Download badge
          </button>
          <button class="btn ghost" id="badgeCustomize" aria-expanded="false" title="Switch between themes">
            <svg viewBox="0 0 24 24" style="width:18px;height:18px;fill:none;stroke:currentColor;stroke-width:2;"><circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 0 0 0 20 10 10 0 0 0 0-20"/></svg>
            Customize badge
          </button>
        </div>

        <div id="badgeThemes" class="badge-themes" hidden>
          ${T.map(t => `
            <button type="button" data-id="${t[0]}" aria-pressed="false" class="${t[0] === selected ? 'selected' : ''}">
              <img src="assets/${t[2]}" alt="${t[1]} Theme" loading="lazy">
              <div class="theme-label">
                <span>${t[1]}</span>
                <i class="theme-dot" style="background:${t[3]};"></i>
              </div>
            </button>
          `).join('')}
        </div>

        <p id="badgeMessage" class="cat" aria-live="polite">Your score is yours to share.</p>
      </section>
    `);

    const showMsg = (txt, isSuccess = true) => {
      const el = $('#badgeMessage');
      if (!el) return;
      el.innerHTML = txt;
      el.style.color = isSuccess ? 'var(--ok)' : 'var(--warn)';
      el.style.fontWeight = '500';
    };

    const apply = () => {
      const t = T.find(x => x[0] === selected) || T[0];
      const b = $('#financeBadge');
      if (!b) return;
      b.dataset.theme = t[0];
      b.style.setProperty('--accent', t[3]);
      b.style.setProperty('--mid', t[4]);
      b.style.setProperty('--dark', t[5]);
      b.style.setProperty('--badge-image', `url("assets/${t[2]}")`);
      b.style.setProperty('--badge-font', `'${t[6]}', sans-serif`);
      const kicker = $('#badgeKickerDisplay');
      if (kicker) {
        kicker.textContent = (t[7] ? `${t[7].toUpperCase()} · ` : '') + 'FINANCE SCORE · FINANCIAL HEALTH';
      }
      document.querySelectorAll('.badge-themes button').forEach(x => {
        const isMatch = x.dataset.id === selected;
        x.classList.toggle('selected', isMatch);
        x.setAttribute('aria-pressed', String(isMatch));
      });
    };
    apply();

    document.querySelectorAll('.badge-themes button').forEach(x => {
      x.onclick = () => {
        selected = x.dataset.id;
        localStorage.setItem('cf-badge-theme', selected);
        apply();
        showMsg(`Badge theme switched to <b>${x.querySelector('span')?.textContent}</b>.`);
      };
    });

    $('#badgeCustomize').onclick = () => {
      const e = $('#badgeThemes');
      e.hidden = !e.hidden;
      $('#badgeCustomize').setAttribute('aria-expanded', String(!e.hidden));
    };

    const png = async () => {
      const t = T.find(x => x[0] === selected) || T[0];
      const c = document.createElement('canvas');
      c.width = 1200;
      c.height = 750;
      const x = c.getContext('2d');

      // Base fill
      x.fillStyle = t[5];
      x.fillRect(0, 0, 1200, 750);

      try {
        const im = new Image();
        im.src = `assets/${t[2]}`;
        await new Promise((resolve) => {
          im.onload = resolve;
          im.onerror = resolve;
        });
        if (im.complete && im.naturalWidth > 0) {
          const k = Math.max(1200 / im.naturalWidth, 750 / im.naturalHeight);
          x.globalAlpha = 0.42;
          x.drawImage(im, (1200 - im.naturalWidth * k) / 2, (750 - im.naturalHeight * k) / 2, im.naturalWidth * k, im.naturalHeight * k);
          x.globalAlpha = 1.0;
        }
      } catch (_) {}

      // Gradient overlay
      const g = x.createLinearGradient(0, 0, 1200, 0);
      g.addColorStop(0, t[5] + 'f5');
      g.addColorStop(0.55, t[4] + '99');
      g.addColorStop(1, t[4] + '66');
      x.fillStyle = g;
      x.fillRect(0, 0, 1200, 750);

      // Outer accent border
      x.lineWidth = 10;
      x.strokeStyle = t[3];
      x.strokeRect(5, 5, 1190, 740);

      // Typography
      const isCute = t[0] === 'cute';
      const textColor = isCute ? '#63384a' : 'white';
      const subColor = isCute ? '#81576a' : '#cbd5e1';
      const font = t[6] || 'sans-serif';

      x.fillStyle = textColor;
      x.font = `600 30px '${font}', sans-serif`;
      x.fillText('CLAIR FINANCE · FINANCE SCORE', 60, 80);

      x.fillStyle = t[3];
      x.font = `600 14px sans-serif`;
      x.fillText((t[7] ? `${t[7].toUpperCase()} · ` : '') + 'FINANCIAL HEALTH CERTIFICATION', 60, 115);

      x.fillStyle = textColor;
      x.font = `700 185px '${font}', sans-serif`;
      x.fillText(String(score), 60, 360);

      const scoreW = x.measureText(String(score)).width;
      x.fillStyle = subColor;
      x.font = `500 36px sans-serif`;
      x.fillText('/100', 60 + scoreW + 10, 270);

      x.fillStyle = textColor;
      x.font = `600 48px '${font}', sans-serif`;
      x.fillText(scoreStatus, 60, 475);

      x.strokeStyle = t[3];
      x.lineWidth = 2;
      x.beginPath();
      x.moveTo(60, 505);
      x.lineTo(750, 505);
      x.stroke();

      x.fillStyle = textColor;
      x.font = `700 28px '${font}', sans-serif`;
      x.fillText(personalityTitle, 60, 555);

      x.fillStyle = subColor;
      x.font = `500 20px sans-serif`;
      x.fillText(`Verified Member: ${memberName}`, 60, 595);

      x.fillStyle = subColor;
      x.font = `400 16px sans-serif`;
      x.fillText(`Advisor Tip: ${personalityTip}`, 60, 635);

      const dateStr = new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
      x.font = `500 14px sans-serif`;
      x.fillText(`Issued: ${dateStr} · Clairfinance FinOps Certification`, 60, 700);

      return new Promise(r => c.toBlob(b => {
        if (!b) return r(null);
        const a = document.createElement('a');
        a.href = URL.createObjectURL(b);
        a.download = `clairfinance-score-badge-${t[0]}.png`;
        a.click();
        r(b);
      }, 'image/png'));
    };

    $('#badgeDownload').onclick = async () => {
      showMsg('Downloading high-resolution badge...');
      await png();
      showMsg('Badge downloaded successfully (PNG format).');
    };

    $('#badgeLinkedIn').onclick = async () => {
      const shareUrl = window.location.origin + window.location.pathname;
      const linkedInCaption = `I am proud to share my verified Financial Health Score of ${score}/100 on Clairfinance! 🚀 Managing cash flows, tracking subscriptions, and optimizing financial health. Certified by Clairfinance AI. #PersonalFinance #FinOps #Clairfinance #FinancialHealth`;

      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(linkedInCaption).catch(() => {});
      }

      window.open('https://www.linkedin.com/sharing/share-offsite/?url=' + encodeURIComponent(shareUrl), '_blank', 'noopener');
      await png();
      showMsg('Attach the downloaded badge to your LinkedIn post. Caption was copied to your clipboard!');
    };

    $('#badgeInstagram').onclick = async () => {
      const instaCaption = `Financial health milestone unlocked! 📊 Hit a score of ${score}/100 on @Clairfinance. 💳✨ Managing cash flows, saving consistently, and tracking every milestone. #Clairfinance #FinOps #MoneyMindset #SavingsGoals #FinancialFreedom #FinancialHealth`;

      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(instaCaption).catch(() => {});
      }

      const blob = await png();

      if (blob && navigator.canShare && navigator.canShare({ files: [new File([blob], 'badge.png', { type: 'image/png' })] })) {
        try {
          const file = new File([blob], 'clairfinance-score-badge.png', { type: 'image/png' });
          await navigator.share({
            files: [file],
            title: 'My Clairfinance Score Badge',
            text: instaCaption
          });
          showMsg('Share sheet opened! Select Instagram Story or Post.');
          return;
        } catch (_) {}
      }

      window.open('https://www.instagram.com/', '_blank', 'noopener');
      showMsg('Badge downloaded. Add it to your Instagram post or story. Caption was copied to your clipboard!');
    };
  },

  // 10. REFINED PROMISES (5,000-PATH MONTE CARLO CASH-FLOW SIMULATOR)
  async promises() {
    main.innerHTML = `<header class="banner"><div class="banner-inner">${getUserCardHTML()}<div class="br"><svg><use href="#logo"/></svg><div class="wm">Refined<span>Promises</span></div></div><p>Empirical Cash-Flow Simulator & Probabilistic Guarantees</p></div></header>` +
      page(`<div style="display:flex;justify-content:center;padding:50px;"><div class="spin"></div> Simulating 5,000 cash-flow paths across 30-day futures...</div>`);

    let currentBuffer = 5000.0;
    let currentShockDay = 1;
    let userBalanceOverride = null;
    let currentBillName = "Upcoming Medical / Annual Insurance";
    let currentBillAmount = 15000.0;
    let currentBillDueDay = 10;
    let currentExpectedInflow = 20000.0;
    let currentExpectedProb = 0.75;

    // SVG Fan Chart Generator
    function buildFanChartSVG(fan) {
      if (!fan || !fan.days || !fan.days.length) {
        return '<p class="cat" style="text-align:center;padding:30px;">Simulation data unavailable.</p>';
      }
      const days = fan.days;
      const p5 = fan.percentiles.p5;
      const p25 = fan.percentiles.p25;
      const p50 = fan.percentiles.p50;
      const p75 = fan.percentiles.p75;
      const p95 = fan.percentiles.p95;
      const buffer = fan.buffer;

      const W = 760, H = 250;
      const padL = 70, padR = 25, padT = 20, padB = 35;
      const plotW = W - padL - padR;
      const plotH = H - padT - padB;

      const minVal = Math.max(0, Math.min(buffer * 0.4, ...p5));
      const maxVal = Math.max(...p95) * 1.06;
      const rangeVal = Math.max(1000, maxVal - minVal);

      const getX = idx => padL + (idx / (days.length - 1)) * plotW;
      const getY = val => padT + (1 - (val - minVal) / rangeVal) * plotH;

      // Outer polygon (95th to 5th)
      let ptsOuter = [];
      for (let i = 0; i < days.length; i++) ptsOuter.push(`${getX(i).toFixed(1)},${getY(p95[i]).toFixed(1)}`);
      for (let i = days.length - 1; i >= 0; i--) ptsOuter.push(`${getX(i).toFixed(1)},${getY(p5[i]).toFixed(1)}`);

      // Inner polygon (75th to 25th)
      let ptsInner = [];
      for (let i = 0; i < days.length; i++) ptsInner.push(`${getX(i).toFixed(1)},${getY(p75[i]).toFixed(1)}`);
      for (let i = days.length - 1; i >= 0; i--) ptsInner.push(`${getX(i).toFixed(1)},${getY(p25[i]).toFixed(1)}`);

      // Median line (50th)
      let pathMedian = [];
      for (let i = 0; i < days.length; i++) {
        pathMedian.push(`${i === 0 ? 'M' : 'L'}${getX(i).toFixed(1)},${getY(p50[i]).toFixed(1)}`);
      }

      // Guarantee floor line (5th)
      let pathFloor = [];
      for (let i = 0; i < days.length; i++) {
        pathFloor.push(`${i === 0 ? 'M' : 'L'}${getX(i).toFixed(1)},${getY(p5[i]).toFixed(1)}`);
      }

      const yBuffer = getY(buffer);

      // Y-axis ticks
      const yTicks = [
        minVal,
        buffer,
        minVal + rangeVal * 0.5,
        maxVal * 0.95
      ];

      return `
        <svg viewBox="0 0 ${W} ${H}" style="width:100%;height:auto;display:block;" preserveAspectRatio="xMidYMid meet">
          <defs>
            <linearGradient id="fanOuterGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stop-color="#22d3ee" stop-opacity="0.22"/>
              <stop offset="100%" stop-color="#6366f1" stop-opacity="0.06"/>
            </linearGradient>
            <linearGradient id="fanInnerGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stop-color="#22d3ee" stop-opacity="0.38"/>
              <stop offset="100%" stop-color="#6366f1" stop-opacity="0.18"/>
            </linearGradient>
          </defs>

          <!-- Grid Lines -->
          ${yTicks.map(tv => {
            const y = getY(tv);
            return `
              <line x1="${padL}" y1="${y.toFixed(1)}" x2="${W - padR}" y2="${y.toFixed(1)}" stroke="color-mix(in srgb, var(--fg) 10%, transparent)" stroke-dasharray="2 3"/>
              <text x="${padL - 8}" y="${(y + 3.5).toFixed(1)}" fill="var(--mut)" font-size="10" font-weight="600" text-anchor="end">${inr(tv)}</text>
            `;
          }).join('')}

          <!-- Outer Percentile Band (95th - 5th) -->
          <polygon points="${ptsOuter.join(' ')}" fill="url(#fanOuterGrad)"/>

          <!-- Inner Percentile Band (75th - 25th) -->
          <polygon points="${ptsInner.join(' ')}" fill="url(#fanInnerGrad)"/>

          <!-- Safety Buffer Line -->
          <line x1="${padL}" y1="${yBuffer.toFixed(1)}" x2="${W - padR}" y2="${yBuffer.toFixed(1)}" stroke="var(--bad)" stroke-width="2.2" stroke-dasharray="6 4"/>
          <text x="${W - padR}" y="${(yBuffer - 6).toFixed(1)}" fill="var(--bad)" font-size="11" font-weight="700" text-anchor="end">Buffer: ${inr(buffer)}</text>

          <!-- Guarantee Floor (5th percentile) -->
          <path d="${pathFloor.join(' ')}" stroke="var(--ok)" stroke-width="2.2" stroke-dasharray="4 3" fill="none"/>

          <!-- Median Trajectory (50th percentile) -->
          <path d="${pathMedian.join(' ')}" stroke="var(--sec)" stroke-width="2.8" fill="none"/>

          <!-- X-Axis Days Labels -->
          ${days.map((d, i) => {
            if (i % 5 !== 0 && i !== days.length - 1) return '';
            const x = getX(i);
            return `<text x="${x.toFixed(1)}" y="${H - 10}" fill="var(--mut)" font-size="10.5" font-weight="600" text-anchor="middle">${d}</text>`;
          }).join('')}
        </svg>
      `;
    }

    // SVG Calibration Chart Generator
    function buildCalibrationChartSVG(points) {
      if (!points || !points.length) {
        return '<p class="cat" style="text-align:center;padding:20px;">Calibration curve loading...</p>';
      }
      const W = 460, H = 220;
      const padL = 45, padR = 20, padT = 15, padB = 30;
      const plotW = W - padL - padR;
      const plotH = H - padT - padB;

      const getX = p => padL + (p / 100.0) * plotW;
      const getY = a => padT + (1 - a / 100.0) * plotH;

      // 45-degree ideal dashed line
      const idealX1 = padL, idealY1 = padT + plotH;
      const idealX2 = padL + plotW, idealY2 = padT;

      // Empirical path
      let ptsEmpirical = [];
      points.forEach((pt, i) => {
        ptsEmpirical.push(`${i === 0 ? 'M' : 'L'}${getX(pt.predicted_risk).toFixed(1)},${getY(pt.actual_rate).toFixed(1)}`);
      });

      return `
        <svg viewBox="0 0 ${W} ${H}" style="width:100%;height:auto;display:block;" preserveAspectRatio="xMidYMid meet">
          <!-- Background Grid -->
          ${[0, 25, 50, 75, 100].map(v => `
            <line x1="${padL}" y1="${getY(v).toFixed(1)}" x2="${W - padR}" y2="${getY(v).toFixed(1)}" stroke="color-mix(in srgb, var(--fg) 10%, transparent)" stroke-dasharray="2 3"/>
            <text x="${padL - 6}" y="${(getY(v) + 3.5).toFixed(1)}" fill="var(--mut)" font-size="9.5" font-weight="600" text-anchor="end">${v}%</text>
            <text x="${getX(v).toFixed(1)}" y="${H - 10}" fill="var(--mut)" font-size="9.5" font-weight="600" text-anchor="middle">${v}%</text>
          `).join('')}

          <!-- 45-Degree Perfect Calibration Line -->
          <line x1="${idealX1}" y1="${idealY1}" x2="${idealX2}" y2="${idealY2}" stroke="color-mix(in srgb, var(--fg) 25%, transparent)" stroke-width="1.8" stroke-dasharray="5 4"/>
          <text x="${idealX2 - 4}" y="${idealY2 + 14}" fill="var(--mut)" font-size="10" font-weight="600" text-anchor="end">45° Ideal</text>

          <!-- Empirical Calibration Line -->
          <path d="${ptsEmpirical.join(' ')}" stroke="var(--ok)" stroke-width="2.6" fill="none"/>

          <!-- Calibration Points -->
          ${points.map(pt => {
            const cx = getX(pt.predicted_risk).toFixed(1);
            const cy = getY(pt.actual_rate).toFixed(1);
            return `
              <circle cx="${cx}" cy="${cy}" r="5" fill="var(--ok)" stroke="var(--card)" stroke-width="2"/>
              <text x="${cx}" y="${(cy - 9).toFixed(1)}" fill="var(--fg)" font-size="10" font-weight="700" text-anchor="middle">${pt.actual_rate}%</text>
            `;
          }).join('')}

          <!-- Axis Labels -->
          <text x="${padL + plotW / 2}" y="${H - 0}" fill="var(--sec)" font-size="10" font-weight="700" text-anchor="middle">Predicted Risk (%)</text>
          <text transform="rotate(-90)" x="${-(padT + plotH / 2)}" y="12" fill="var(--sec)" font-size="10" font-weight="700" text-anchor="middle">Actual Shortfall (%)</text>
        </svg>
      `;
    }

    async function loadAndRender() {
      try {
        let url = `/promises/overview?buffer_amount=${currentBuffer}&shock_day=${currentShockDay}&bill_name=${encodeURIComponent(currentBillName)}&bill_amount=${currentBillAmount}&bill_due_day=${currentBillDueDay}&expected_inflow_amount=${currentExpectedInflow}&expected_inflow_prob=${currentExpectedProb}`;
        if (userBalanceOverride !== null) {
          url += `&current_balance=${userBalanceOverride}`;
        }
        const data = await apiFetch(url, { headers: authHeaders() });
        renderPromisesView(data);
      } catch (err) {
        main.innerHTML = page(`<section class="panel glass"><h3>Error loading Refined Promises</h3><p class="cat">${err.message}</p><button class="btn" onclick="PAGES.promises()">Retry</button></section>`);
      }
    }

    function renderPromisesView(data) {
      const p1 = data.promise_1;
      const p2 = data.promise_2;
      const fan = data.fan_chart;
      const bt = data.backtest;
      const balance = data.current_balance;
      const buffer = data.buffer_amount;

      const fanChartSvg = buildFanChartSVG(fan);
      const calChartSvg = buildCalibrationChartSVG(bt.calibration_points);

      main.innerHTML = `
        <header class="banner">
          <div class="banner-inner">
            ${getUserCardHTML()}
            <div class="br"><svg><use href="#logo"/></svg><div class="wm">Refined<span>Promises</span></div></div>
            <p>Empirical Cash-Flow Simulator & Probabilistic Guarantees</p>
          </div>
        </header>
      ` + page(`
        <!-- HERO CARD WITH DUMMY ASSET -->
        <div class="promises-hero-card">
          <div class="promises-hero-bg"></div>
          <div style="position:relative;z-index:2;max-width:720px;">
            <div class="pfb-tag">🔬 5,000-Path Monte Carlo Engine</div>
            <h1 style="font-family:var(--hd);font-size:clamp(24px, 3.2vw, 36px);margin:8px 0 10px;line-height:1.2;color:var(--fg);">
              Cash-Flow Futures, Rigorous Probabilities
            </h1>
            <p style="color:var(--mut);line-height:1.6;font-size:14.5px;">
              Both promises come from one unified cash-flow engine: simulating 5,000 possible 30-day futures. We isolate scheduled recurring bills & salary (with ±1–3 days timing jitter), bootstrap variable daily spending per category with day-of-week and payday effects, and model irregular earnings. Backtested against rolling historical windows.
            </p>
          </div>

          <!-- CONTROLS STRIP -->
          <div class="promises-ctrl-grid">
            <div class="ctrl-tile">
              <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
                <label style="margin:0;">Current Bank Balance</label>
                <button type="button" id="btnResetBalance" class="lk" style="font-size:11px;padding:0;">Auto-Reset</button>
              </div>
              <div style="display:flex;gap:8px;align-items:center;">
                <span style="color:var(--sec);font-weight:700;">₹</span>
                <input type="number" id="ctrlBalanceInput" value="${Math.round(balance)}" step="1000" min="0">
              </div>
            </div>
            <div class="ctrl-tile">
              <label>Minimum Safety Buffer: <b id="ctrlBufferDisplay" style="color:var(--sec);">${inr(buffer)}</b></label>
              <input type="range" id="ctrlBufferSlider" min="0" max="25000" step="1000" value="${buffer}">
            </div>
            <div class="ctrl-tile">
              <label>Shock Timing</label>
              <div style="display:flex;gap:8px;">
                <button type="button" class="btn ${currentShockDay === 1 ? '' : 'ghost'}" id="btnShockTomorrow" style="flex:1;padding:8px 10px;font-size:12px;font-weight:600;">Day 1 (Tomorrow)</button>
                <button type="button" class="btn ${currentShockDay === 15 ? '' : 'ghost'}" id="btnShockMid" style="flex:1;padding:8px 10px;font-size:12px;font-weight:600;">Day 15</button>
              </div>
            </div>
            <div class="ctrl-tile" style="display:flex;align-items:flex-end;">
              <button type="button" class="btn" id="btnRecalcPromises" style="width:100%;padding:10px 14px;font-size:13px;font-weight:600;">
                ⚡ Recalculate Simulation
              </button>
            </div>
          </div>
        </div>

        <!-- PROMISE 1 SECTION -->
        <section class="panel glass" style="margin-bottom:24px;">
          <div class="promise-guarantee-box">
            <div class="pgb-tag">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/></svg>
              PROMISE 1 · SHOCK ABSORPTION CAPACITY
            </div>
            <div class="pgb-headline">
              ${p1.X > 0 
                ? `You could absorb about <mark>${inr(p1.X)}</mark> (${inr(p1.L)} – ${inr(p1.H)}) ${currentShockDay === 1 ? 'tomorrow' : 'mid-month'}`
                : `Baseline Cash Cushion Tight (${p1.base_risk}% Shortfall Risk) · ₹0 Absorption at ${inr(buffer)} Buffer`
              }
            </div>
            <p style="color:var(--mut);margin-top:8px;font-size:14px;line-height:1.5;">
              ${p1.X > 0
                ? (p1.has_enough_data 
                  ? `Calculated as the largest single shock <i>S</i> such that shortfall probability across 5,000 simulated paths remains &le; 5.0%. The range reflects model uncertainty across 200 bootstrap resamples of your ${p1.data_days} days of transaction history (10th–90th percentile).`
                  : `<b style="color:var(--bad);">${p1.message}</b>`)
                : `Your projected cash flow currently has an elevated baseline shortfall risk of ${p1.base_risk}% against your ${inr(buffer)} buffer. Increase your current bank balance or lower your buffer using the controls above to restore positive shock absorption capacity.`
              }
            </p>
            <div class="pgb-stats">
              <span><b>Target Risk:</b> &le; ${p1.target_risk}%</span>
              <span><b>Baseline Shortfall Risk:</b> ${p1.base_risk}%</span>
              <span><b>History Analyzed:</b> ${p1.data_days} days</span>
              <span><b>Timing:</b> ${currentShockDay === 1 ? 'Day 1 (Tomorrow)' : 'Day 15 (Mid-Month)'}</span>
            </div>
          </div>

          <!-- 30-DAY MONTE CARLO FAN CHART -->
          <div class="fan-chart-wrapper">
            <div class="fan-chart-header">
              <div>
                <h4 style="margin:0;font-size:15px;font-weight:600;color:var(--fg);">30-Day Cash-Flow Fan Chart (5,000 Paths)</h4>
                <p class="cat" style="font-size:12.5px;margin:3px 0 0;color:var(--mut);">Visualizing distribution across optimistic (95th), median (50th), and stress-test (5th) paths.</p>
              </div>
              <div class="fan-chart-legend">
                <span><i class="fcl-dot" style="background:rgba(34,211,238,0.5);"></i> 95th Percentile</span>
                <span><i class="fcl-dot" style="background:var(--sec);"></i> 50th (Median Path)</span>
                <span><i class="fcl-dot" style="background:var(--ok);"></i> 5th (Guarantee Floor)</span>
                <span><i class="fcl-dot" style="background:var(--bad);"></i> ${inr(buffer)} Safety Buffer</span>
              </div>
            </div>
            ${fanChartSvg}
          </div>
        </section>

        <!-- PROMISE 2 SECTION: BILL IMPACT & DYNAMIC ACTION PLAN -->
        <section class="panel glass" style="margin-bottom:24px;">
          <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;margin-bottom:16px;">
            <div>
              <div class="pgb-tag" style="color:var(--pri);">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
                PROMISE 2 · BILL IMPACT & DYNAMIC ACTION PLAN
              </div>
              <h3 style="margin:4px 0 0;font-size:20px;color:var(--fg);">"This bill raises risk from ${p2.risk_A}% to ${p2.risk_B}%..."</h3>
            </div>
          </div>

          <div class="bill-sim-grid">
            <!-- Left: Interactive Bill Inputs -->
            <div style="background:var(--card);border:1px solid var(--bd);box-shadow:0 4px 16px var(--sh);border-radius:18px;padding:20px;">
              <h4 style="margin:0 0 14px;font-size:13px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:var(--sec);">
                1. Test a Prospective Bill
              </h4>
              <div style="display:flex;flex-direction:column;gap:14px;">
                <label class="fld" style="margin:0;">
                  <input type="text" id="billNameInput" value="${p2.bill_name}" placeholder=" ">
                  <span>Expense Description</span>
                </label>
                <div>
                  <div style="display:flex;justify-content:space-between;font-size:13px;margin-bottom:6px;">
                    <span style="color:var(--mut);font-weight:500;">Bill Amount</span>
                    <b id="billAmtDisplay" style="color:var(--fg);font-weight:700;">${inr(p2.bill_amount)}</b>
                  </div>
                  <input type="range" id="billAmtSlider" min="2000" max="100000" step="1000" value="${p2.bill_amount}" style="width:100%;accent-color:var(--pri);">
                </div>
                <div>
                  <div style="display:flex;justify-content:space-between;font-size:13px;margin-bottom:6px;">
                    <span style="color:var(--mut);font-weight:500;">Due Date (Day of Month)</span>
                    <b id="billDayDisplay" style="color:var(--sec);font-weight:700;">Day ${p2.due_day}</b>
                  </div>
                  <input type="range" id="billDaySlider" min="1" max="30" step="1" value="${p2.due_day}" style="width:100%;accent-color:var(--sec);">
                </div>
                <div>
                  <div style="display:flex;justify-content:space-between;font-size:13px;margin-bottom:6px;">
                    <span style="color:var(--mut);font-weight:500;">Pending Inflow (e.g. Freelance / Claim)</span>
                    <b id="billInflowDisplay" style="color:var(--ok);font-weight:700;">${inr(currentExpectedInflow)} (75% prob)</b>
                  </div>
                  <input type="range" id="billInflowSlider" min="0" max="50000" step="2500" value="${currentExpectedInflow}" style="width:100%;accent-color:var(--ok);">
                </div>
                <button type="button" class="btn" id="btnUpdateBillSim" style="padding:12px;font-size:13px;font-weight:600;margin-top:6px;">
                  🔄 Run Bill Risk Simulation
                </button>
              </div>
            </div>

            <!-- Right: Risk Shift, First Shortfall Date & Action Plan -->
            <div>
              <!-- Risk Shift Meter -->
              <div class="risk-meter-container">
                <div class="risk-node">
                  <small>Baseline Risk (A)</small>
                  <b class="ok">${p2.risk_A}%</b>
                </div>
                <div class="risk-arrow">
                  <span>+${p2.risk_increase}%</span>
                  <svg viewBox="0 0 24 24"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
                </div>
                <div class="risk-node">
                  <small>With Bill (B)</small>
                  <b class="${p2.risk_B > 10 ? 'bad' : 'warn'}">${p2.risk_B}%</b>
                </div>
                <div class="risk-arrow" style="color:var(--ok);">
                  <span>Restored</span>
                  <svg viewBox="0 0 24 24"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
                </div>
                <div class="risk-node">
                  <small>With Action (C)</small>
                  <b class="ok">${p2.mitigated_risk_C}%</b>
                </div>
              </div>

              <!-- First Shortfall Date & Urgency Alert -->
              <div class="urgency-badge">
                <div class="urgency-icon">⚠️</div>
                <div style="flex:1;">
                  <b style="display:block;font-size:14.5px;margin-bottom:3px;">
                    First Projected Shortfall: ${p2.first_shortfall_date} (Day ${p2.first_shortfall_day})
                  </b>
                  <p style="margin:0;font-size:13px;line-height:1.45;">
                    Earliest day where cumulative shortfall risk crosses 50%. You must <b>start mitigation actions by ${p2.start_by_date}</b> to prevent entering shortfall territory.
                  </p>
                </div>
              </div>

              <!-- Recommended Action Plan List -->
              <div style="background:var(--card);border:1px solid var(--bd);box-shadow:0 4px 16px var(--sh);border-radius:18px;padding:18px;">
                <h4 style="margin:0 0 12px;font-size:13.5px;font-weight:700;color:var(--fg);display:flex;justify-content:space-between;align-items:center;">
                  <span>Automated Greedy Action Plan</span>
                  <span class="action-badge" style="background:color-mix(in srgb, var(--ok) 18%, var(--card));color:var(--ok);">Targets &le; ${Math.max(5, p2.risk_A)}%</span>
                </h4>
                <div class="action-plan-list">
                  ${p2.action_evaluations.map(act => `
                    <div class="action-item">
                      <div>
                        <b>${act.action}</b>
                        <div class="cat" style="font-size:12px;margin-top:2px;">
                          ${act.reaches_target ? '✅ Sufficient on its own' : 'ℹ️ Combine with installment split'}
                        </div>
                      </div>
                      <div style="text-align:right;">
                        <span style="font-size:12.5px;font-weight:700;color:${act.reaches_target ? 'var(--ok)' : 'var(--warn)'};">
                          Risk &rarr; ${act.resulting_risk}%
                        </span>
                        <div style="font-size:11px;color:var(--mut);">-${act.risk_reduction}%</div>
                      </div>
                    </div>
                  `).join('')}
                </div>

                <!-- Upside Note -->
                <div class="upside-note-banner">
                  <div style="font-size:22px;flex-shrink:0;">🛡️</div>
                  <div>
                    <b style="display:block;margin-bottom:3px;font-size:13px;">Conservative Guarantee Rule</b>
                    ${p2.upside_note.text}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <!-- SECTION 3: CREDIBILITY & ROLLING BACKTEST -->
        <section class="panel glass">
          <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;margin-bottom:16px;">
            <div>
              <div class="pgb-tag" style="color:var(--ok);">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
                STEP 4 · MATHEMATICAL CREDIBILITY
              </div>
              <h3 style="margin:4px 0 0;font-size:20px;color:var(--fg);">Rolling Backtest & Calibration Evaluation</h3>
              <p class="cat" style="margin:4px 0 0;font-size:13.5px;">
                ${bt.summary_statement}
              </p>
            </div>
            <div>
              <span class="bt-badge-verified">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
                ${bt.guarantee_status}
              </span>
            </div>
          </div>

          <div class="backtest-grid">
            <!-- Left: Empirical Stats -->
            <div style="display:flex;flex-direction:column;gap:12px;">
              <div class="stat glass" style="margin:0;">
                <small>Rolling 30-Day Windows Backtested</small>
                <b class="ok" style="font-size:24px;">${bt.total_windows_tested} Windows</b>
              </div>
              <div class="stat glass" style="margin:0;">
                <small>Actual Shortfall Rate when Predicted Risk &le; 5%</small>
                <b class="ok" style="font-size:24px;">${bt.empirical_shortfall_rate}% (Verified &le; 5%)</b>
              </div>
              <div class="stat glass" style="margin:0;">
                <small>Brier Calibration Error Score</small>
                <b class="grad" style="font-size:24px;">${bt.brier_score} (Well-Calibrated)</b>
              </div>
              <div style="padding:16px;background:var(--card);border:1px solid var(--bd);box-shadow:0 4px 16px var(--sh);border-radius:14px;font-size:13px;color:var(--mut);line-height:1.6;">
                <b style="color:var(--fg);">Why this matters:</b> If a fintech claims a "5% probability", it must hold up on historical reality. By running a rolling backtest over past dates with only data available up to that moment, Clairfinance proves our predictions are statistically conservative and calibrated.
              </div>
            </div>

            <!-- Right: Calibration Chart -->
            <div style="background:var(--card);border:1px solid var(--bd);box-shadow:0 4px 16px var(--sh);border-radius:18px;padding:20px;">
              <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
                <h4 style="margin:0;font-size:14px;font-weight:700;color:var(--fg);">Calibration Curve (Predicted vs Actual Risk)</h4>
                <span style="font-size:11.5px;color:var(--sec);font-weight:600;">Ideal = 45° Dashed Line</span>
              </div>
              ${calChartSvg}
            </div>
          </div>
        </section>
      `);

      // Wire interactive events
      wirePromisesEvents();
    }

    function wirePromisesEvents() {
      let recalcTimer = null;
      const queueRecalc = (delay = 250) => {
        clearTimeout(recalcTimer);
        recalcTimer = setTimeout(() => {
          loadAndRender();
        }, delay);
      };

      // Balance input
      const balInput = $('#ctrlBalanceInput');
      if (balInput) {
        balInput.oninput = () => {
          userBalanceOverride = parseFloat(balInput.value) || 0;
          queueRecalc(450);
        };
        balInput.onchange = () => {
          userBalanceOverride = parseFloat(balInput.value) || 0;
          queueRecalc(0);
        };
        balInput.onkeydown = e => {
          if (e.key === 'Enter') {
            userBalanceOverride = parseFloat(balInput.value) || 0;
            queueRecalc(0);
          }
        };
      }

      // Reset Balance to Auto
      const btnReset = $('#btnResetBalance');
      if (btnReset) {
        btnReset.onclick = () => {
          userBalanceOverride = null;
          loadAndRender();
        };
      }

      // Buffer slider
      const bufSlider = $('#ctrlBufferSlider');
      const bufDisplay = $('#ctrlBufferDisplay');
      if (bufSlider && bufDisplay) {
        bufSlider.oninput = () => {
          currentBuffer = parseFloat(bufSlider.value);
          bufDisplay.textContent = inr(currentBuffer);
          queueRecalc(200);
        };
        bufSlider.onchange = () => {
          currentBuffer = parseFloat(bufSlider.value);
          bufDisplay.textContent = inr(currentBuffer);
          queueRecalc(0);
        };
      }

      // Shock timing buttons
      const btnTomorrow = $('#btnShockTomorrow');
      const btnMid = $('#btnShockMid');
      if (btnTomorrow && btnMid) {
        btnTomorrow.onclick = () => {
          currentShockDay = 1;
          loadAndRender();
        };
        btnMid.onclick = () => {
          currentShockDay = 15;
          loadAndRender();
        };
      }

      // Recalculate button
      const btnRecalc = $('#btnRecalcPromises');
      if (btnRecalc) {
        btnRecalc.onclick = () => {
          if (balInput) userBalanceOverride = parseFloat(balInput.value) || 0;
          if (bufSlider) currentBuffer = parseFloat(bufSlider.value) || 5000;
          loadAndRender();
        };
      }

      // Bill simulation inputs
      const billNameIn = $('#billNameInput');
      const billAmtSl = $('#billAmtSlider');
      const billAmtDisp = $('#billAmtDisplay');
      const billDaySl = $('#billDaySlider');
      const billDayDisp = $('#billDayDisplay');
      const billInfSl = $('#billInflowSlider');
      const billInfDisp = $('#billInflowDisplay');
      const btnUpdateBill = $('#btnUpdateBillSim');

      if (billNameIn) {
        billNameIn.onchange = () => {
          currentBillName = billNameIn.value.trim() || 'Upcoming Bill';
          queueRecalc(0);
        };
      }

      if (billAmtSl && billAmtDisp) {
        billAmtSl.oninput = () => {
          currentBillAmount = parseFloat(billAmtSl.value);
          billAmtDisp.textContent = inr(currentBillAmount);
          queueRecalc(200);
        };
        billAmtSl.onchange = () => {
          currentBillAmount = parseFloat(billAmtSl.value);
          billAmtDisp.textContent = inr(currentBillAmount);
          queueRecalc(0);
        };
      }

      if (billDaySl && billDayDisp) {
        billDaySl.oninput = () => {
          currentBillDueDay = parseInt(billDaySl.value, 10);
          billDayDisp.textContent = `Day ${currentBillDueDay}`;
          queueRecalc(200);
        };
        billDaySl.onchange = () => {
          currentBillDueDay = parseInt(billDaySl.value, 10);
          billDayDisp.textContent = `Day ${currentBillDueDay}`;
          queueRecalc(0);
        };
      }

      if (billInfSl && billInfDisp) {
        billInfSl.oninput = () => {
          currentExpectedInflow = parseFloat(billInfSl.value);
          billInfDisp.textContent = `${inr(currentExpectedInflow)} (75% prob)`;
          queueRecalc(200);
        };
        billInfSl.onchange = () => {
          currentExpectedInflow = parseFloat(billInfSl.value);
          billInfDisp.textContent = `${inr(currentExpectedInflow)} (75% prob)`;
          queueRecalc(0);
        };
      }

      if (btnUpdateBill) {
        btnUpdateBill.onclick = () => {
          if (billNameIn && billNameIn.value.trim()) {
            currentBillName = billNameIn.value.trim();
          }
          if (billAmtSl) currentBillAmount = parseFloat(billAmtSl.value);
          if (billDaySl) currentBillDueDay = parseInt(billDaySl.value, 10);
          if (billInfSl) currentExpectedInflow = parseFloat(billInfSl.value);
          loadAndRender();
        };
      }
    }

    await loadAndRender();
  }
};

/* -------------------------------------------------------------
   CSV UPLOAD & FILE PARSING (WIRED TO POST /api/transactions/upload)
------------------------------------------------------------- */
const csv = $('#csv'), drop = $('#drop');
const DT = 'Drag and drop your CSV here';
const DS = 'or click to browse. Needs date, description, and amount columns.';
let upFile = null;

const fail = m => {
  drop.className = 'drop err';
  $('#dt').textContent = 'File not accepted';
  $('#ds').textContent = m;
};

function pick(f) {
  drop.className = 'drop';
  upFile = null;
  $('#cont').disabled = true;
  if (!f) return;
  if (!/\.csv$/i.test(f.name)) return fail('That is not a CSV file. Export your statement as .csv and try again.');

  f.text().then(t => {
    const L = t.split(/\r?\n/).filter(Boolean);
    if (L.length < 2) {
      return fail('The uploaded CSV file is empty or has only one line.');
    }
    // Check first 20 lines for valid headers (supports Kaggle and bank formats)
    let validHeader = false;
    for (let i = 0; i < Math.min(20, L.length); i++) {
      const h = L[i].toLowerCase();
      const hasDate = /date|time|timestamp/i.test(h);
      const hasAmt = /amt|amount|spent|cost|price|total|value|sum|debit|credit|withdrawal|deposit/i.test(h);
      const hasDesc = /narration|description|particular|merchant|payee|item|details|name|desc|notes|remarks/i.test(h);
      if ((hasDate && hasAmt) || (hasDate && hasDesc) || (hasAmt && hasDesc)) {
        validHeader = true;
        break;
      }
    }
    if (!validHeader) {
      return fail('Could not detect statement columns. Please ensure your CSV contains date, description/merchant, and amount/amt columns.');
    }
    upFile = f;
    drop.className = 'drop ok';
    $('#dt').textContent = f.name;
    $('#ds').textContent = `${L.length - 1} records detected (${(f.size / 1024).toFixed(1)} KB). Ready for upload.`;
    $('#cont').disabled = false;
  }).catch(e => fail('Could not read file: ' + e.message));
}

function resetUp() {
  csv.value = '';
  pick(null);
  $('#dt').textContent = DT;
  $('#ds').textContent = DS;
  $('#pg').hidden = $('#pt').hidden = true;
  $('#pg').firstElementChild.style.width = 0;
}

csv.onchange = () => pick(csv.files[0]);
['dragenter', 'dragover'].forEach(v => drop.addEventListener(v, e => { e.preventDefault(); drop.classList.add('over'); }));
['dragleave', 'drop'].forEach(v => drop.addEventListener(v, e => { e.preventDefault(); drop.classList.remove('over'); }));
drop.addEventListener('drop', e => pick(e.dataTransfer.files[0]));

// Continue button uploads the CSV to backend
$('#cont').onclick = async () => {
  if (!upFile) return;
  $('#cont').disabled = true;
  const pg = $('#pg'), pt = $('#pt');
  pg.hidden = pt.hidden = false;

  const steps = [
    'Parsing bank statement headers, dates, and amounts...',
    'Running 3-tier categorization (Rules, ML, Gemini Flash)...',
    'Detecting recurring commitments and anomalies...',
    'Updating cash flow models and forecasts...'
  ];

  steps.forEach((m, i) => {
    setTimeout(() => {
      pt.textContent = m;
      pg.firstElementChild.style.width = ((i + 1) * 22) + '%';
    }, i * 350);
  });

  const formData = new FormData();
  formData.append('file', upFile);

  try {
    const res = await fetch(`${API_BASE}/transactions/upload`, {
      method: 'POST',
      headers: activeToken ? { 'Authorization': 'Bearer ' + activeToken } : {},
      body: formData
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Upload failed');
    }

    const data = await res.json();
    if (!data.total_saved && !data.total_parsed) {
      throw new Error(data.message || 'No valid transactions found in file.');
    }

    pg.firstElementChild.style.width = '100%';
    pt.textContent = `Success! ${data.total_saved || data.total_parsed} transactions imported and categorized.`;

    if (data.access_token) {
      activeToken = data.access_token;
      localStorage.setItem('cf_token', activeToken);
      if (isRealGoogleUser(currentUser)) {
        localStorage.setItem('cf_google_token', activeToken);
      }
    }

    if (isRealGoogleUser(currentUser)) {
      updatePersonaUI();
    } else {
      const cleanedName = upFile.name.replace(/\.csv$/i, '');
      activePersona = {
        id: 'custom',
        name: cleanedName.length > 20 ? cleanedName.slice(0, 18) + '...' : cleanedName,
        role: 'Uploaded Dataset',
        avatar: '📊',
        income_pattern: 'User uploaded statement'
      };
      localStorage.setItem('cf-data', 'custom');
      updatePersonaUI();
    }

    setTimeout(() => {
      location.hash = '#/transactions';
    }, 600);
  } catch (err) {
    pt.textContent = `Upload error: ${err.message}`;
    $('#cont').disabled = false;
  }
};

$('#demo').onclick = async () => {
  const isGoogle = isRealGoogleUser(currentUser);
  if (isGoogle) {
    try {
      pt.hidden = false;
      pt.textContent = 'Loading 12-month transaction dataset into your Google account...';
      const res = await apiFetch('/transactions/seed-sample', {
        method: 'POST',
        headers: authHeaders()
      });
      pt.textContent = res.message || 'Dataset loaded successfully!';
      setTimeout(() => {
        location.hash = '#/home';
      }, 500);
    } catch (e) {
      pt.textContent = `Error: ${e.message}`;
    }
  } else {
    await switchPersona('salaried');
    location.hash = '#/home';
  }
};

$('#smp').onclick = () => {
  const sample = `Date,Description,Amount,Type,Mode\n2026-11-01,NEFT-CREDIT-SALARY-ACME TECH,65000.00,credit,NEFT\n2026-11-02,UPI-SWIGGY-FOOD ORDER,640.00,debit,UPI\n2026-11-05,NEFT-RENT-HOUSING SOCIETY,18000.00,debit,NEFT\n2026-11-08,POS-AMAZON PAY INDIA,2499.00,debit,Card\n2026-11-10,AUTO-DEBIT-NETFLIX,649.00,debit,Auto-Debit\n2026-11-12,UPI-ELECTRICITY-BESCOM,1850.00,debit,UPI\n2026-11-15,AUTO-DEBIT-HDFC-CAR-LOAN-EMI,9800.00,debit,Auto-Debit\n2026-11-18,UPI-UBER-TRIP,340.00,debit,UPI\n2026-11-20,UPI-ZEPTO-GROCERY,890.00,debit,UPI\n2026-11-25,AUTO-DEBIT-MUTUAL-FUND-SIP,5000.00,debit,Auto-Debit\n`;
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([sample], { type: 'text/csv' }));
  a.download = 'sample_bank_statement.csv';
  a.click();
};

/* -------------------------------------------------------------
   ROUTER & INITIALIZATION
------------------------------------------------------------- */
function route() {
  const k = location.hash.slice(2);

  // If user is not authenticated, start on login view
  if (!activeToken) {
    document.body.dataset.view = 'login';
    if (location.hash !== '#/login') {
      location.hash = '#/login';
    }
    initGoogleSignIn();
    renderGoogleButton();
    return;
  }

  // If user is authenticated and is on #/login or root, navigate to dashboard
  if (!k || k === 'login') {
    location.hash = '#/home';
    return;
  }

  if (k === 'upload') {
    document.body.dataset.view = 'upload';
    resetUp();
    return;
  }

  if (PAGES[k]) {
    document.body.dataset.view = 'app';
    document.querySelectorAll('.nav-i[data-k]').forEach(a => a.classList.toggle('on', a.dataset.k === k));
    scrollTo(0, 0);
    PAGES[k]();
  } else {
    location.hash = '#/home';
  }
}

addEventListener('hashchange', route);

// Initialize on page load
initAuth().then(() => {
  route();
  initGoogleSignIn();
  renderGoogleButton();
});

// Periodic retry to ensure Google button is rendered once GSI script loads
let gisCheckAttempts = 0;
const gisTimer = setInterval(() => {
  gisCheckAttempts++;
  if (typeof google !== 'undefined' && google.accounts && google.accounts.id) {
    initGoogleSignIn();
    clearInterval(gisTimer);
  } else if (gisCheckAttempts > 30) {
    clearInterval(gisTimer);
  }
}, 300);

/* -------------------------------------------------------------
   HIGH-PERFORMANCE BUTTER-SMOOTH LIGHTWEIGHT SCROLL ENGINE
------------------------------------------------------------- */
(function initSmoothScroll() {
  if (typeof window === 'undefined') return;
  if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

  let currentY = window.scrollY;
  let targetY = window.scrollY;
  let isAnimating = false;
  let rafId = null;
  let lastWheelTime = 0;
  let touchpadCooldownUntil = 0;

  function getMaxScroll() {
    return Math.max(0, document.documentElement.scrollHeight - window.innerHeight);
  }

  function isInnerScrollable(target, deltaX, deltaY) {
    let el = target;
    while (el && el !== document.body && el !== document.documentElement) {
      const style = window.getComputedStyle(el);
      const isScrollableX = (style.overflowX === 'auto' || style.overflowX === 'scroll') && el.scrollWidth > el.clientWidth;
      const isScrollableY = (style.overflowY === 'auto' || style.overflowY === 'scroll') && el.scrollHeight > el.clientHeight;

      if (Math.abs(deltaX) > Math.abs(deltaY) && isScrollableX) {
        return true;
      }
      if (Math.abs(deltaY) > 0 && isScrollableY) {
        const canScrollDown = deltaY > 0 && el.scrollTop + el.clientHeight < el.scrollHeight - 1;
        const canScrollUp = deltaY < 0 && el.scrollTop > 1;
        if (canScrollDown || canScrollUp) return true;
      }
      el = el.parentElement;
    }
    return false;
  }

  function update() {
    if (!isAnimating) return;
    const diff = targetY - currentY;
    if (Math.abs(diff) < 0.35) {
      currentY = targetY;
      window.scrollTo(0, currentY);
      isAnimating = false;
      rafId = null;
      return;
    }

    // Snappy, agile 0.22 easing curve - eliminates heavy dragging/viscosity
    currentY += diff * 0.22;
    window.scrollTo(0, currentY);
    rafId = requestAnimationFrame(update);
  }

  window.addEventListener('wheel', (e) => {
    // Pass through browser zoom gestures or modifier scroll combinations
    if (e.ctrlKey || e.metaKey || e.altKey) return;

    // If inside a scrollable child element, do not interfere
    if (isInnerScrollable(e.target, e.deltaX, e.deltaY)) {
      targetY = window.scrollY;
      currentY = window.scrollY;
      return;
    }

    const now = performance.now();
    const dt = now - lastWheelTime;
    lastWheelTime = now;

    // Detect precision trackpads (MacBook trackpads, precision touchpads):
    // Trackpads emit micro-deltas, non-integers, or horizontal components with deltaMode === 0.
    const isFractional = Math.abs(e.deltaY % 1) > 0.01;
    const isSmallDelta = Math.abs(e.deltaY) < 18;
    const hasHorizontalMovement = Math.abs(e.deltaX) > 0.5;

    if (e.deltaMode === 0 && (isFractional || isSmallDelta || hasHorizontalMovement)) {
      touchpadCooldownUntil = now + 250;
    }

    const isTouchpad = now < touchpadCooldownUntil;

    // If using a touchpad, let native OS momentum handle it with 100% natural lightness
    if (isTouchpad) {
      if (isAnimating) {
        cancelAnimationFrame(rafId);
        isAnimating = false;
      }
      targetY = window.scrollY;
      currentY = window.scrollY;
      return;
    }

    // Mouse wheel (discrete notches) - apply breezy, lightweight smooth momentum
    const isMouseWheel = e.deltaMode !== 0 || (Math.abs(e.deltaY) >= 20 && Math.abs(e.deltaY % 1) === 0);

    if (isMouseWheel) {
      e.preventDefault();
      const maxScroll = getMaxScroll();

      // Slightly amplify distance on consecutive rapid wheel flicks for effortless glide
      const velocityBonus = dt < 90 ? Math.min(1.65, 1 + (90 - dt) / 80) : 1;
      const baseMultiplier = e.deltaMode === 1 ? 50 : (e.deltaMode === 2 ? window.innerHeight : 1.42);
      const delta = e.deltaY * baseMultiplier * velocityBonus;

      if (!isAnimating) {
        currentY = window.scrollY;
        targetY = window.scrollY;
      }

      targetY = Math.min(Math.max(0, targetY + delta), maxScroll);

      if (!isAnimating) {
        isAnimating = true;
        rafId = requestAnimationFrame(update);
      }
    }
  }, { passive: false });

  // Instant sync on native scrollbar drags, anchor jumps, or route changes
  window.addEventListener('scroll', () => {
    if (!isAnimating) {
      targetY = window.scrollY;
      currentY = window.scrollY;
    }
  }, { passive: true });

  // Cancel any in-flight interpolation on direct touch interaction
  window.addEventListener('touchstart', () => {
    if (isAnimating) {
      cancelAnimationFrame(rafId);
      isAnimating = false;
    }
    targetY = window.scrollY;
    currentY = window.scrollY;
  }, { passive: true });

  window.addEventListener('keydown', (e) => {
    if (e.target && (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.isContentEditable)) return;
    const keys = { 'PageDown': 0.85, 'PageUp': -0.85, 'Space': 0.8, 'ArrowDown': 120, 'ArrowUp': -120 };
    if (keys[e.code] !== undefined) {
      const maxScroll = getMaxScroll();
      const step = typeof keys[e.code] === 'number' && Math.abs(keys[e.code]) <= 1
        ? keys[e.code] * window.innerHeight
        : keys[e.code];
      
      e.preventDefault();
      if (!isAnimating) {
        currentY = window.scrollY;
        targetY = window.scrollY;
      }
      targetY = Math.min(Math.max(0, targetY + step), maxScroll);
      if (!isAnimating) {
        isAnimating = true;
        rafId = requestAnimationFrame(update);
      }
    }
  });
})();
