/**
 * Catalog Analytics Worker
 * Collects search queries and page views from my-catalog
 * Stores in KV and provides admin API
 */

const CORS_HEADERS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, POST, DELETE, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type, Authorization',
};

// Simple hash for password
async function sha256(str) {
  const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(str));
  return [...new Uint8Array(buf)].map(b => b.toString(16).padStart(2, '0')).join('');
}

export default {
  async fetch(request, env) {
    try {
      if (request.method === 'OPTIONS') {
        return new Response(null, { headers: CORS_HEADERS });
      }

      const url = new URL(request.url);
      const path = url.pathname;

      // Public endpoints
      if (path === '/track' && request.method === 'POST') {
        return await handleTrack(request, env);
      }

      // Admin endpoints
      if (path === '/admin/login' && request.method === 'POST') {
        return await handleLogin(request, env);
      }
      if (path.startsWith('/admin/')) {
        const auth = await verifyAuth(request, env);
        if (!auth) return json({ error: 'Unauthorized' }, 401);

        if (path === '/admin/searches') return await handleSearches(request, env);
        if (path === '/admin/analytics') return await handleAnalytics(request, env);
        if (path === '/admin/settings') return await handleSettings(request, env);
        if (path === '/admin/export') return await handleExport(request, env);
        if (path === '/admin/clear') return await handleClear(request, env);
      }

      // Health check
      if (path === '/' || path === '/health') {
        return json({ status: 'ok', service: 'catalog-analytics' });
      }

      return json({ error: 'Not found' }, 404);
    } catch (e) {
      return json({ error: e.message || 'Internal error' }, 500);
    }
  }
};

// === Track search/pageview ===
async function handleTrack(request, env) {
  let data;
  try {
    const text = await request.text();
    data = JSON.parse(text);
  } catch (e) {
    return json({ error: 'Invalid JSON' }, 400);
  }
  const { type, query, page } = data;

  // Get IP-based location from CF headers
  const country = request.headers.get('cf-ipcountry') || 'XX';
  const cf = request.cf || {};
  const city = cf.city || '';
  const region = cf.region || '';

  const entry = {
    type: type || 'search', // search | pageview | click
    query: query || '',
    page: page || '/',
    country,
    city,
    region,
    timestamp: Date.now(),
    ua: (request.headers.get('user-agent') || '').substring(0, 100),
    referrer: data.referrer || '',
  };

  // Get existing logs
  let logs = [];
  try {
    const raw = await env.CATALOG_KV.get('search_logs', 'json');
    if (raw) logs = raw;
  } catch (e) {}

  // Add new entry, keep last 5000
  logs.unshift(entry);
  if (logs.length > 5000) logs = logs.slice(0, 5000);

  await env.CATALOG_KV.put('search_logs', JSON.stringify(logs));

  // Update daily stats
  const today = new Date().toISOString().split('T')[0];
  let dailyStats = {};
  try {
    const raw = await env.CATALOG_KV.get('daily_stats', 'json');
    if (raw) dailyStats = raw;
  } catch (e) {}

  if (!dailyStats[today]) dailyStats[today] = { views: 0, searches: 0, clicks: 0, shares: 0, installs: 0 };
  if (type === 'search') dailyStats[today].searches++;
  else if (type === 'click') dailyStats[today].clicks++;
  else if (type === 'share') dailyStats[today].shares++;
  else if (type === 'install') dailyStats[today].installs++;
  else dailyStats[today].views++;

  // Keep last 90 days
  const keys = Object.keys(dailyStats).sort().reverse();
  if (keys.length > 90) {
    keys.slice(90).forEach(k => delete dailyStats[k]);
  }

  await env.CATALOG_KV.put('daily_stats', JSON.stringify(dailyStats));

  return json({ ok: true }, 200);
}

// === Admin Login ===
async function handleLogin(request, env) {
  const { password } = await request.json();
  const settings = await getSettings(env);
  const hash = await sha256(password);

  if (hash === settings.passwordHash) {
    // Generate simple token
    const token = crypto.randomUUID();
    await env.CATALOG_KV.put('admin_token', token, { expirationTtl: 86400 }); // 24h
    return json({ token });
  }
  return json({ error: 'Wrong password' }, 401);
}

// === Verify Auth ===
async function verifyAuth(request, env) {
  const auth = request.headers.get('Authorization');
  if (!auth) return false;
  const token = auth.replace('Bearer ', '');
  const stored = await env.CATALOG_KV.get('admin_token');
  return token === stored;
}

// === Get Searches ===
async function handleSearches(request, env) {
  if (request.method === 'DELETE') {
    await env.CATALOG_KV.put('search_logs', '[]');
    return json({ ok: true });
  }

  const logs = await env.CATALOG_KV.get('search_logs', 'json') || [];

  // Aggregate top queries
  const queryCounts = {};
  const countryCounts = {};
  const cityCounts = {};
  let searchCount = 0;
  let viewCount = 0;
  let clickCount = 0;
  let shareCount = 0;
  let installCount = 0;

  logs.forEach(l => {
    if (l.type === 'search') {
      searchCount++;
      const q = (l.query || '').trim().toLowerCase();
      if (q) queryCounts[q] = (queryCounts[q] || 0) + 1;
    } else if (l.type === 'click') {
      clickCount++;
    } else if (l.type === 'share') {
      shareCount++;
      const q = (l.query || '').trim().toLowerCase();
      if (q) queryCounts[q] = (queryCounts[q] || 0) + 1;
    } else if (l.type === 'install') {
      installCount++;
    } else {
      viewCount++;
    }
    if (l.country) countryCounts[l.country] = (countryCounts[l.country] || 0) + 1;
    if (l.city) cityCounts[l.city] = (cityCounts[l.city] || 0) + 1;
  });

  // Sort top queries
  const topQueries = Object.entries(queryCounts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 30)
    .map(([query, count]) => ({ query, count }));

  const topCountries = Object.entries(countryCounts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 20)
    .map(([country, count]) => ({ country, count }));

  const topCities = Object.entries(cityCounts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 20)
    .map(([city, count]) => ({ city, count }));

  return json({
    total: logs.length,
    searchCount,
    viewCount,
    clickCount,
    shareCount,
    installCount,
    topQueries,
    topCountries,
    topCities,
    recent: logs.slice(0, 100),
  });
}

// === Analytics (daily stats) ===
async function handleAnalytics(request, env) {
  const dailyStats = await env.CATALOG_KV.get('daily_stats', 'json') || {};
  return json({ dailyStats });
}

// === Settings ===
async function handleSettings(request, env) {
  if (request.method === 'GET') {
    const settings = await getSettings(env);
    return json({ siteName: settings.siteName });
  }
  if (request.method === 'POST') {
    const data = await request.json();
    const settings = await getSettings(env);

    if (data.newPassword) {
      settings.passwordHash = await sha256(data.newPassword);
    }
    if (data.siteName) {
      settings.siteName = data.siteName;
    }

    await env.CATALOG_KV.put('settings', JSON.stringify(settings));
    return json({ ok: true });
  }
  return json({ error: 'Method not allowed' }, 405);
}

// === Export ===
async function handleExport(request, env) {
  const logs = await env.CATALOG_KV.get('search_logs', 'json') || [];
  const dailyStats = await env.CATALOG_KV.get('daily_stats', 'json') || {};
  return json({ logs, dailyStats, exportedAt: new Date().toISOString() });
}

// === Clear ===
async function handleClear(request, env) {
  if (request.method === 'POST') {
    await env.CATALOG_KV.put('search_logs', '[]');
    await env.CATALOG_KV.put('daily_stats', '{}');
    return json({ ok: true });
  }
  return json({ error: 'Method not allowed' }, 405);
}

// === Helpers ===
async function getSettings(env) {
  const raw = await env.CATALOG_KV.get('settings', 'json');
  return raw || {
    siteName: 'קטלוג מותגים',
    passwordHash: await sha256('admin123'),
  };
}

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json', ...CORS_HEADERS },
  });
}
