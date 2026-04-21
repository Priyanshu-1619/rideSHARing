/* ============================================================
   NEXTRIDE - Global JavaScript Utilities
   ============================================================ */

// ── Theme Management ──────────────────────────────────────────
const Theme = {
  init() {
    const saved = localStorage.getItem('nr_theme') || 'dark';
    document.documentElement.setAttribute('data-theme', saved);
  },
  toggle() {
    const current = document.documentElement.getAttribute('data-theme');
    const next = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('nr_theme', next);
  }
};
Theme.init();

// ── Toast Notifications ──────────────────────────────────────
const Toast = {
  container: null,
  init() {
    this.container = document.createElement('div');
    this.container.className = 'toast-container';
    document.body.appendChild(this.container);
  },
  show(message, type = 'info') {
    if (!this.container) this.init();
    const icons = { success: '✅', error: '❌', info: 'ℹ️', warning: '⚠️' };
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `<span>${icons[type] || '💬'}</span><span>${message}</span>`;
    this.container.appendChild(toast);
    setTimeout(() => toast.remove(), 3500);
  }
};

// ── API Helper ───────────────────────────────────────────────
const API = {
  async request(url, options = {}) {
    try {
      const res = await fetch(url, {
        headers: { 'Content-Type': 'application/json', ...options.headers },
        ...options
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Request failed');
      return data;
    } catch (err) {
      throw err;
    }
  },
  get(url)         { return this.request(url); },
  post(url, body)  { return this.request(url, { method: 'POST',  body: JSON.stringify(body) }); },
  patch(url, body) { return this.request(url, { method: 'PATCH', body: JSON.stringify(body) }); },
  delete(url)      { return this.request(url, { method: 'DELETE' }); },
};

// ── Format Utilities ─────────────────────────────────────────
const Format = {
  date(str) {
    if (!str) return '–';
    const d = new Date(str);
    return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
  },
  time(str) {
    if (!str) return '–';
    const d = new Date(str);
    return d.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
  },
  datetime(str) {
    return `${this.date(str)}, ${this.time(str)}`;
  },
  currency(n) {
    return `₹${parseFloat(n).toFixed(2)}`;
  },
  initials(name) {
    return (name || 'U').split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2);
  },
  timeFromNow(str) {
    if (!str) return '';
    const diff = new Date(str) - new Date();
    if (diff < 0) return 'Past';
    const h = Math.floor(diff / 3600000);
    const m = Math.floor((diff % 3600000) / 60000);
    if (h > 24) return `in ${Math.floor(h/24)}d`;
    if (h > 0)  return `in ${h}h ${m}m`;
    return `in ${m}m`;
  }
};

// ── Badge HTML ───────────────────────────────────────────────
function badge(status) {
  const s = (status || '').toLowerCase();
  const map = {
    open: 'badge-open', full: 'badge-full',
    pending: 'badge-pending', accepted: 'badge-accepted',
    rejected: 'badge-rejected', cancelled: 'badge-cancelled',
    completed: 'badge-open', paid: 'badge-accepted',
    refunded: 'badge-cancelled',
  };
  return `<span class="badge ${map[s] || ''}">${status}</span>`;
}

// ── Ride Card HTML ───────────────────────────────────────────
function rideCardHTML(ride, action = '') {
  return `
    <div class="ride-card fade-in" data-ride-id="${ride.ride_id}">
      <div class="flex items-center justify-between">
        <div class="driver-info">
          <div class="driver-avatar">${Format.initials(ride.driver_name)}</div>
          <span>${ride.driver_name || 'Unknown'}</span>
        </div>
        ${badge(ride.status)}
      </div>
      <div class="ride-route">
        <span>${ride.source}</span>
        <span class="arrow">→</span>
        <span>${ride.destination}</span>
      </div>
      <div class="ride-meta">
        <span class="meta-chip"><span class="chip-icon">🕐</span>${Format.datetime(ride.ride_time)}</span>
        <span class="meta-chip"><span class="chip-icon">⏱</span>${Format.timeFromNow(ride.ride_time)}</span>
        <span class="meta-chip"><span class="chip-icon">💺</span>${ride.available_seats}/${ride.total_seats} seats</span>
      </div>
      <div class="ride-footer">
        <span class="price-tag">${Format.currency(ride.price_per_seat)}/seat</span>
        ${action}
      </div>
    </div>
  `;
}

// ── Logout ───────────────────────────────────────────────────
async function logout() {
  await API.post('/api/logout');
  window.location.href = '/login';
}

// ── Init on DOM ready ────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  // Bind theme toggle
  const toggleBtn = document.getElementById('themeToggle');
  if (toggleBtn) toggleBtn.addEventListener('click', Theme.toggle);

  // Highlight active nav link
  const path = window.location.pathname;
  document.querySelectorAll('.sidebar-nav a, .navbar-links a').forEach(a => {
    if (a.getAttribute('href') === path) a.classList.add('active');
  });
});
