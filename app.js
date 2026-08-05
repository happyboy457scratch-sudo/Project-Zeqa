/**
 * ZeqaValues - Complete Standalone Single-File Engine & Trade Tracker Integration
 * Self-contained Single Page Application (SPA) for Mineville PvP Cosmetics.
 */

/* ==========================================================================
   1. GLOBAL STATE, LOCAL STORAGE & DATA PROCESSING
   ========================================================================== */

let cosmeticsData = [];
let tradesData = [];
let tradeStatsMap = {}; // Item key -> { avgValue, totalTradeCount, recentTrades7DaysCount, trades }

let currentPage = localStorage.getItem('lastPage') || 'home';

// Filter & Sort state for Value Page
let valueSearchQuery = '';
let valueCurrentCategory = 'All';
let valueCurrentSort = 'value-desc';

// Compare Page trade slots state
let compareLeftItems = [];
let compareRightItems = [];
let compareActiveSide = 'left';

// Collection View tab state
let collectionActiveTab = 'inventory';

const app = document.getElementById('app');

// Helper to normalize item names for clean cross-file matching
function cleanName(str) {
  return str ? str.toLowerCase().replace(/[^a-z0-9]/g, '') : '';
}

// Helper to convert shorthand values like '10k', '1.5k', '2m' into numbers
function parseShards(val) {
  if (typeof val === 'number') return val;
  if (!val) return 0;

  let str = String(val).trim().toLowerCase().replace(/,/g, '');

  let multiplier = 1;
  if (str.endsWith('k')) {
    multiplier = 1000;
    str = str.slice(0, -1);
  } else if (str.endsWith('m')) {
    multiplier = 1000000;
    str = str.slice(0, -1);
  }

  const num = parseFloat(str);
  return isNaN(num) ? 0 : Math.round(num * multiplier);
}

// Helper to format values nicely for display (e.g., 5000 -> 5k, 10000 -> 10k)
function formatShardsDisplay(val) {
  const num = parseShards(val);
  if (num >= 1000) {
    const kVal = num / 1000;
    return Number.isInteger(kVal) ? `${kVal}k` : `${kVal.toFixed(1)}k`;
  }
  return num.toLocaleString();
}

async function loadData() {
  try {
    const [cosmeticsRes, tradesRes] = await Promise.all([
      fetch('./data/cosmetics.json?t=' + Date.now()),
      fetch('./data/trades.json?t=' + Date.now()).catch(() => null)
    ]);

    if (!cosmeticsRes.ok) throw new Error(`HTTP ${cosmeticsRes.status}`);
    cosmeticsData = await cosmeticsRes.json();

    if (tradesRes && tradesRes.ok) {
      tradesData = await tradesRes.json();
      processTradeStats();
    }
  } catch (err) {
    console.warn('Could not fetch external data, utilizing fallback dataset:', err);
    if (cosmeticsData.length === 0) {
      cosmeticsData = [
        { id: 1, name: 'Dragon Cape', category: 'Capes', rarity: 'Legendary', value: 25000, demand: 9, salesExistingRatio: 85, imageUrl: '' },
        { id: 2, name: 'Ancient Relic', category: 'Artifacts', rarity: 'Mythic', value: 42000, demand: 10, salesExistingRatio: 92, imageUrl: '' },
        { id: 3, name: 'Fireball Projectile', category: 'Projectiles', rarity: 'Rare', value: 8500, demand: 6, salesExistingRatio: 45, imageUrl: '' },
        { id: 4, name: 'Golden Key', category: 'Items', rarity: 'Epic', value: 16000, demand: 8, salesExistingRatio: 70, imageUrl: '' }
      ];
    }
  }
  renderApp();
}

/**
 * Calculates trade statistics per item from trades.json
 */
function processTradeStats() {
  if (!Array.isArray(tradesData) || tradesData.length === 0) return;

  const sevenDaysAgo = Date.now() - (7 * 24 * 60 * 60 * 1000);
  const groupedTrades = {};

  tradesData.forEach(trade => {
    if (!trade.item || trade.item.startsWith('—')) return;

    const cleanedTradeTitle = cleanName(trade.item);
    const matchedCosmetic = cosmeticsData.find(c => {
      const cName = cleanName(c.name);
      return cName.length > 2 && cleanedTradeTitle.includes(cName);
    });

    if (!matchedCosmetic) return;

    const itemKey = cleanName(matchedCosmetic.name);
    if (!groupedTrades[itemKey]) groupedTrades[itemKey] = [];

    const shardsPaid = parseShards(trade.shards);
    const qty = parseInt(trade.quantity, 10) || 1;
    const unitPrice = qty > 0 ? Math.round(shardsPaid / qty) : shardsPaid;
    const tradeTimestamp = trade.timestamp ? new Date(trade.timestamp).getTime() : Date.now();

    groupedTrades[itemKey].push({
      rawText: trade.raw_trade || `${trade.item} -> ${trade.shards}`,
      shardsPaid: shardsPaid,
      unitPrice: unitPrice,
      qty: qty,
      timestamp: tradeTimestamp
    });
  });

  Object.keys(groupedTrades).forEach(itemKey => {
    const trades = groupedTrades[itemKey];
    const totalShards = trades.reduce((sum, t) => sum + t.unitPrice, 0);
    const avgValue = Math.round(totalShards / trades.length);

    const recentTrades7Days = trades
      .filter(t => t.timestamp >= sevenDaysAgo)
      .sort((a, b) => b.timestamp - a.timestamp);

    const displayTrades = recentTrades7Days.length > 0 
      ? recentTrades7Days 
      : [...trades].sort((a, b) => b.timestamp - a.timestamp);

    tradeStatsMap[itemKey] = {
      avgValue: avgValue,
      totalTradeCount: trades.length,
      recentTrades7DaysCount: recentTrades7Days.length,
      trades: displayTrades
    };
  });
}

function getItemCalculatedValue(item) {
  const key = cleanName(item.name);
  const stats = tradeStatsMap[key];
  if (stats && stats.avgValue > 0) return stats.avgValue;
  return parseShards(item.value || item.shards);
}

function getInventory() {
  try { return JSON.parse(localStorage.getItem('zv_user_inventory')) || {}; }
  catch { return {}; }
}

function saveInventory(inv) {
  localStorage.setItem('zv_user_inventory', JSON.stringify(inv));
}

function getWishlist() {
  try { return JSON.parse(localStorage.getItem('zv_user_wishlist')) || []; }
  catch { return []; }
}

function saveWishlist(wl) {
  localStorage.setItem('zv_user_wishlist', JSON.stringify(wl));
}

/* ==========================================================================
   2. HELPER RENDERING FUNCTIONS (CARDS & MODALS)
   ========================================================================== */

function getRarityBadgeColor(rarity = '') {
  const r = rarity.toLowerCase();
  switch (r) {
    case 'rare': return '#1f6feb';
    case 'epic': return '#8957e5';
    case 'legendary': return '#d29922';
    case 'limited': return '#da3633';
    case 'exotic': return '#09b43a';
    case 'partner': return '#f0883e';
    default: return '#6e7681';
  }
}

function renderItemCardHtml(item) {
  const imgUrl = item.imageUrl || item.image || 'https://via.placeholder.com/150?text=No+Image';
  const badgeBg = getRarityBadgeColor(item.rarity);
  const calculatedVal = getItemCalculatedValue(item);
  const valDisplay = calculatedVal > 0 ? `${formatShardsDisplay(calculatedVal)} shards` : 'Unlisted';

  return `
    <div class="item-card" data-id="${item.id || item.name}" style="background: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 14px; display: flex; flex-direction: column; align-items: center; cursor: pointer; transition: transform 0.2s, border-color 0.2s;">
      <div style="width: 100%; height: 120px; background: #0d1117; border-radius: 8px; display: flex; align-items: center; justify-content: center; margin-bottom: 12px; overflow: hidden;">
        <img src="${imgUrl}" alt="${escapeHtml(item.name)}" loading="lazy" style="max-width: 85%; max-height: 85%; object-fit: contain;" onerror="this.src='https://via.placeholder.com/150?text=No+Image';">
      </div>
      <h3 style="margin: 0 0 6px 0; color: #fff; font-size: 15px; text-align: center; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; width: 100%;">${escapeHtml(item.name)}</h3>
      <div style="display: flex; gap: 6px; align-items: center; margin-bottom: 8px;">
        <span style="background: ${badgeBg}; color: #fff; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 700; text-transform: uppercase;">${escapeHtml(item.rarity || 'Common')}</span>
        <span style="color: #8b949e; font-size: 11px;">${escapeHtml(item.category || item.type || 'Cosmetic')}</span>
      </div>
      <div style="color: #5EF2B6; font-weight: 700; font-size: 13px;">${valDisplay}</div>
    </div>
  `;
}

function bindCardClickEvents(container) {
  container.querySelectorAll('.item-card').forEach(card => {
    card.onclick = () => {
      const id = card.dataset.id;
      const item = cosmeticsData.find(i => String(i.id || i.name) === String(id));
      if (item) openItemModal(item);
    };
  });
}

function openItemModal(item) {
  const modalRoot = document.getElementById('zv-modal-root');
  if (!modalRoot) return;

  const imgUrl = item.imageUrl || item.image || 'https://via.placeholder.com/150?text=No+Image';
  const badgeBg = getRarityBadgeColor(item.rarity);
  const inv = getInventory();
  const wl = getWishlist();
  const itemId = item.id || item.name;
  const isWishlisted = wl.includes(String(itemId));
  const currentQty = inv[itemId] || 0;

  const calculatedVal = getItemCalculatedValue(item);
  const valDisplay = calculatedVal > 0 ? `${formatShardsDisplay(calculatedVal)} shards` : 'Unlisted';

  // Recent Trades HTML Generator
  const key = cleanName(item.name);
  const stats = tradeStatsMap[key];
  let tradesHtml = '';

  if (stats && stats.trades.length > 0) {
    const visibleTrades = stats.trades.slice(0, 3);
    const hasMore = stats.trades.length > 3 || stats.recentTrades7DaysCount > 3;

    tradesHtml = `
      <div style="margin-top: 16px; text-align: left; width: 100%; border-top: 1px solid #30363d; padding-top: 12px;">
        <div style="font-size: 11px; font-weight: 700; color: #8b949e; margin-bottom: 8px; text-transform: uppercase;">
          Recent Trades (${stats.recentTrades7DaysCount} in last 7 days)
        </div>
        <div style="display: flex; flex-direction: column; gap: 6px;">
          ${visibleTrades.map(t => `
            <div style="background: #0d1117; padding: 6px 10px; border-radius: 6px; font-size: 12px; color: #c9d1d9; border: 1px solid #21262d;">
              <strong style="color: #5EF2B6;">${formatShardsDisplay(t.shardsPaid)} Shards</strong> — <span style="color: #8b949e;">${escapeHtml(t.rawText)}</span>
            </div>
          `).join('')}
        </div>
        ${hasMore ? `
          <a href="trades.html?search=${encodeURIComponent(item.name)}" 
             style="display: block; margin-top: 10px; font-size: 12px; color: #38bdf8; text-decoration: none; font-weight: 600; text-align: center;">
            Read More (${stats.trades.length - 3} more trades) →
          </a>
        ` : ''}
      </div>
    `;
  } else {
    tradesHtml = `
      <div style="margin-top: 16px; font-size: 12px; color: #6e7681; border-top: 1px solid #30363d; padding-top: 12px;">
        No recent recorded trades in the last 7 days.
      </div>
    `;
  }

  modalRoot.innerHTML = `
    <div id="zv-modal-backdrop" style="position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.8); z-index: 1000; display: flex; align-items: center; justify-content: center;">
      <div style="background: #161b22; border: 1px solid #30363d; border-radius: 14px; padding: 24px; max-width: 420px; width: 90%; text-align: center; position: relative;">
        <button id="zv-modal-close" style="position: absolute; top: 12px; right: 16px; background: none; border: none; color: #8b949e; font-size: 20px; cursor: pointer;">✕</button>
        <div style="width: 100%; height: 140px; background: #0d1117; border-radius: 10px; display: flex; align-items: center; justify-content: center; margin-bottom: 16px;">
          <img src="${imgUrl}" alt="${escapeHtml(item.name)}" style="max-width: 85%; max-height: 85%; object-fit: contain;">
        </div>
        <h2 style="color: #fff; margin: 0 0 6px 0;">${escapeHtml(item.name)}</h2>
        <div style="margin-bottom: 12px;">
          <span style="background: ${badgeBg}; color: #fff; padding: 4px 10px; border-radius: 12px; font-size: 12px; font-weight: 700;">${escapeHtml(item.rarity || 'Common')}</span>
          <span style="color: #8b949e; font-size: 12px; margin-left: 8px;">${escapeHtml(item.category || item.type || 'Cosmetic')}</span>
        </div>
        <div style="color: #5EF2B6; font-size: 18px; font-weight: 800; margin-bottom: 16px;">
          ${valDisplay}
        </div>
        <div style="display: flex; gap: 10px; margin-bottom: 8px;">
          <button id="zv-modal-inv-btn" style="flex: 1; background: #21262d; border: 1px solid #30363d; color: #fff; padding: 10px; border-radius: 8px; font-weight: 600; cursor: pointer;">
            Add to Inv (${currentQty})
          </button>
          <button id="zv-modal-wl-btn" style="flex: 1; background: ${isWishlisted ? 'rgba(231,76,60,0.2)' : '#21262d'}; border: 1px solid ${isWishlisted ? '#e74c3c' : '#30363d'}; color: ${isWishlisted ? '#ff6b6b' : '#fff'}; padding: 10px; border-radius: 8px; font-weight: 600; cursor: pointer;">
            ${isWishlisted ? 'Wishlisted' : '+ Wishlist'}
          </button>
        </div>

        ${tradesHtml}
      </div>
    </div>
  `;

  document.getElementById('zv-modal-close').onclick = () => modalRoot.innerHTML = '';
  document.getElementById('zv-modal-backdrop').onclick = (e) => {
    if (e.target.id === 'zv-modal-backdrop') modalRoot.innerHTML = '';
  };

  document.getElementById('zv-modal-inv-btn').onclick = () => {
    const curInv = getInventory();
    curInv[itemId] = (curInv[itemId] || 0) + 1;
    saveInventory(curInv);
    openItemModal(item);
  };

  document.getElementById('zv-modal-wl-btn').onclick = () => {
    let curWl = getWishlist();
    if (curWl.includes(String(itemId))) {
      curWl = curWl.filter(id => String(id) !== String(itemId));
    } else {
      curWl.push(String(itemId));
    }
    saveWishlist(curWl);
    openItemModal(item);
  };
}

/* ==========================================================================
   3. MAIN SPA ROUTER & LAYOUT RENDERER
   ========================================================================== */

function renderApp() {
  if (sessionStorage.getItem('loggedIn') !== '1') {
    renderLogin();
    return;
  }

  const activeUser = localStorage.getItem('zv_active_user') || 'happyboy457';

  app.innerHTML = `
    <div class="topbar" style="background: #14181f; border-bottom: 1px solid #282e38; padding: 14px 24px; display: flex; justify-content: space-between; align-items: center; position: sticky; top: 0; z-index: 100;">
      <div style="font-weight: 800; font-size: 18px; color: #ffffff;">
        Zeqa<span style="color: #5EF2B6;">Values</span>
      </div>
      <nav style="display: flex; gap: 18px; align-items: center;">
        <a class="nav-btn ${currentPage === 'home' ? 'active' : ''}" data-page="home">Home</a>
        <a class="nav-btn ${currentPage === 'value' ? 'active' : ''}" data-page="value">Value</a>
        <a class="nav-btn ${currentPage === 'compare' ? 'active' : ''}" data-page="compare">Compare</a>
        <a class="nav-btn ${currentPage === 'collection' ? 'active' : ''}" data-page="collection">Collection</a>
        <a class="nav-btn ${currentPage === 'settings' ? 'active' : ''}" data-page="settings">Settings</a>
        <a href="trades.html" style="color: #38bdf8; font-weight: 600; text-decoration: none; padding: 4px 10px; border: 1px solid rgba(56, 189, 248, 0.3); border-radius: 6px; background: rgba(56, 189, 248, 0.1);">Trade Tracker ↗</a>
      </nav>
      <div style="font-size: 13px; color: #5EF2B6; font-weight: bold; background: rgba(94,242,182,0.1); padding: 4px 10px; border-radius: 6px; border: 1px solid rgba(94,242,182,0.2);">
        ${escapeHtml(activeUser)}
      </div>
    </div>
    <main id="page-content" style="padding-bottom: 60px;"></main>
    <div id="zv-modal-root"></div>
  `;

  bindNavbar();

  const content = document.getElementById('page-content');
  switch (currentPage) {
    case 'value':
      renderValuePage(content);
      break;
    case 'compare':
      renderComparePage(content);
      break;
    case 'collection':
      renderCollectionPage(content);
      break;
    case 'settings':
      renderSettingsPage(content);
      break;
    case 'home':
    default:
      renderHomePage(content);
      break;
  }
}

function bindNavbar() {
  const links = document.querySelectorAll('.nav-btn');
  links.forEach(link => {
    link.style.cursor = 'pointer';
    link.style.color = link.classList.contains('active') ? '#5EF2B6' : '#aaaaaa';
    link.style.fontWeight = '600';
    link.style.textDecoration = 'none';

    link.onclick = (e) => {
      e.preventDefault();
      const page = link.dataset.page;
      currentPage = page;
      localStorage.setItem('lastPage', page);
      renderApp();
    };
  });
}

/* ==========================================================================
   4. LOGIN VIEW
   ========================================================================== */

function renderLogin() {
  app.innerHTML = `
    <div style="max-width: 360px; margin: 80px auto; background: #14181f; border: 1px solid #282e38; border-radius: 14px; padding: 28px; text-align: center;">
      <h2 style="margin: 0 0 8px 0; color: #ffffff;">ZeqaValues</h2>
      <p style="color: #aaaaaa; font-size: 13px; margin-bottom: 20px;">Sign in to access Mineville PvP cosmetic analytics.</p>
      <input id="u" placeholder="Username" style="width: 100%; padding: 10px; margin-bottom: 12px; background: #0d1117; border: 1px solid #30363d; color: #fff; border-radius: 8px; box-sizing: border-box;">
      <input id="p" type="password" placeholder="Password" style="width: 100%; padding: 10px; margin-bottom: 16px; background: #0d1117; border: 1px solid #30363d; color: #fff; border-radius: 8px; box-sizing: border-box;">
      <button id="b" style="width: 100%; background: #5EF2B6; border: none; color: #111; padding: 12px; border-radius: 8px; font-weight: 700; cursor: pointer;">Sign In</button>
      <p id="m" style="text-align: center; font-size: 13px; margin-top: 12px;"></p>
    </div>
  `;

  document.getElementById('b').onclick = () => {
    const u = document.getElementById('u')?.value.trim();
    const p = document.getElementById('p')?.value.trim();
    const m = document.getElementById('m');

    if (u === 'happyboy457' && p === 'admin') {
      sessionStorage.setItem('loggedIn', '1');
      localStorage.setItem('zv_active_user', u);
      renderApp();
    } else if (m) {
      m.textContent = 'Invalid credentials';
      m.style.color = '#e74c3c';
    }
  };
}

/* ==========================================================================
   5. HOME PAGE VIEW
   ========================================================================== */

function renderHomePage(container) {
  const totalValue = cosmeticsData.reduce((acc, i) => acc + getItemCalculatedValue(i), 0);
  const highestItem = [...cosmeticsData].sort((a, b) => getItemCalculatedValue(b) - getItemCalculatedValue(a))[0];
  const mostTraded = [...cosmeticsData].sort((a, b) => (b.salesExistingRatio || 0) - (a.salesExistingRatio || 0))[0];

  container.innerHTML = `
    <div style="max-width: 1200px; margin: 0 auto; padding: 24px;">
      <div style="text-align: center; margin-bottom: 32px;">
        <h1 style="font-size: 32px; font-weight: 800; color: #fff; margin-bottom: 8px;">
          Mineville <span style="color: #5EF2B6;">ZeqaValues</span> Analytics
        </h1>
        <p style="color: #aaaaaa; font-size: 15px; margin: 0;">Real-time trade evaluations, historical graphs, and market insights.</p>
      </div>

      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px;">
        <div style="background: #14181f; border: 1px solid #282e38; border-radius: 12px; padding: 16px;">
          <div style="font-size: 12px; color: #aaa;">Total Cosmetics</div>
          <div style="font-size: 22px; font-weight: 800; color: #fff; margin-top: 4px;">${cosmeticsData.length}</div>
        </div>
        <div style="background: #14181f; border: 1px solid #282e38; border-radius: 12px; padding: 16px;">
          <div style="font-size: 12px; color: #aaa;">Highest Value</div>
          <div style="font-size: 18px; font-weight: 700; color: #5EF2B6; margin-top: 4px;">${highestItem ? escapeHtml(highestItem.name) : 'N/A'}</div>
        </div>
        <div style="background: #14181f; border: 1px solid #282e38; border-radius: 12px; padding: 16px;">
          <div style="font-size: 12px; color: #aaa;">Most Traded</div>
          <div style="font-size: 18px; font-weight: 700; color: #fff; margin-top: 4px;">${mostTraded ? escapeHtml(mostTraded.name) : 'N/A'}</div>
        </div>
        <div style="background: #14181f; border: 1px solid #282e38; border-radius: 12px; padding: 16px;">
          <div style="font-size: 12px; color: #aaa;">Market Capitalization</div>
          <div style="font-size: 18px; font-weight: 700; color: #5EF2B6; margin-top: 4px;">${formatShardsDisplay(totalValue)} shards</div>
        </div>
      </div>

      <div style="margin-top: 32px; background: #14181f; border: 1px solid #282e38; border-radius: 14px; padding: 20px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 16px;">
        <div>
          <h3 style="margin: 0 0 4px 0; color: #ffffff;">Explore Full Valuation Directory</h3>
          <p style="margin: 0; color: #aaaaaa; font-size: 13px;">Filter through Artifacts, Capes, Projectiles, and Items.</p>
        </div>
        <button id="zv-launch-value" style="background: #5EF2B6; border: none; color: #111111; padding: 12px 24px; border-radius: 8px; font-weight: 700; cursor: pointer;">
          Open Directory →
        </button>
      </div>

      <h2 style="margin-top: 36px; color: #ffffff; font-size: 20px;">Featured Market Items</h2>
      <div id="home-featured-grid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 16px; margin-top: 16px;">
        ${cosmeticsData.slice(0, 8).map(item => renderItemCardHtml(item)).join('')}
      </div>
    </div>
  `;

  container.querySelector('#zv-launch-value').onclick = () => {
    currentPage = 'value';
    localStorage.setItem('lastPage', 'value');
    renderApp();
  };

  bindCardClickEvents(container);
}

/* ==========================================================================
   6. VALUE DIRECTORY PAGE
   ========================================================================== */

function renderValuePage(container) {
  const categories = ['All', 'Artifacts', 'Capes', 'Projectiles', 'Items', 'Cosmetic'];

  container.innerHTML = `
    <div style="max-width: 1200px; margin: 0 auto; padding: 24px;">
      <h1 style="color: #fff; margin: 0 0 6px 0;">Cosmetics Directory</h1>
      <p style="color: #aaa; margin: 0 0 24px 0; font-size: 14px;">Filter and inspect real-time valuations across all cosmetic categories.</p>

      <div style="background: #14181f; border: 1px solid #282e38; border-radius: 12px; padding: 16px; margin-bottom: 24px; display: flex; flex-direction: column; gap: 14px;">
        <div style="display: flex; gap: 12px; flex-wrap: wrap;">
          <input type="text" id="zv-search-field" placeholder="Search cosmetics..." value="${escapeHtml(valueSearchQuery)}" style="flex: 1; min-width: 200px; padding: 10px; background: #0d1117; border: 1px solid #30363d; border-radius: 8px; color: #fff;">
          <select id="zv-sort-field" style="padding: 10px; background: #0d1117; border: 1px solid #30363d; border-radius: 8px; color: #fff;">
            <option value="value-desc" ${valueCurrentSort === 'value-desc' ? 'selected' : ''}>Highest Value</option>
            <option value="value-asc" ${valueCurrentSort === 'value-asc' ? 'selected' : ''}>Lowest Value</option>
            <option value="demand-desc" ${valueCurrentSort === 'demand-desc' ? 'selected' : ''}>Highest Demand</option>
            <option value="demand-asc" ${valueCurrentSort === 'demand-asc' ? 'selected' : ''}>Lowest Demand</option>
            <option value="name-asc" ${valueCurrentSort === 'name-asc' ? 'selected' : ''}>Name (A-Z)</option>
            <option value="name-desc" ${valueCurrentSort === 'name-desc' ? 'selected' : ''}>Name (Z-A)</option>
          </select>
        </div>

        <div id="zv-category-pills" style="display: flex; gap: 8px; flex-wrap: wrap;">
          ${categories.map(cat => `
            <button class="zv-pill ${valueCurrentCategory === cat ? 'active' : ''}" data-category="${cat}" style="padding: 6px 14px; border-radius: 20px; border: 1px solid ${valueCurrentCategory === cat ? '#5EF2B6' : '#30363d'}; background: ${valueCurrentCategory === cat ? 'rgba(94,242,182,0.15)' : '#0d1117'}; color: ${valueCurrentCategory === cat ? '#5EF2B6' : '#aaa'}; font-weight: 600; cursor: pointer;">
              ${cat}
            </button>
          `).join('')}
        </div>
      </div>

      <div id="zv-catalog-grid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 16px;">
        ${renderValueGridItemsHtml()}
      </div>
    </div>
  `;

  const searchInput = container.querySelector('#zv-search-field');
  const sortSelect = container.querySelector('#zv-sort-field');
  const pillsWrap = container.querySelector('#zv-category-pills');
  const gridContainer = container.querySelector('#zv-catalog-grid');

  searchInput.oninput = (e) => {
    valueSearchQuery = e.target.value;
    gridContainer.innerHTML = renderValueGridItemsHtml();
    bindCardClickEvents(gridContainer);
  };

  sortSelect.onchange = (e) => {
    valueCurrentSort = e.target.value;
    gridContainer.innerHTML = renderValueGridItemsHtml();
    bindCardClickEvents(gridContainer);
  };

  pillsWrap.onclick = (e) => {
    const btn = e.target.closest('.zv-pill');
    if (!btn) return;
    valueCurrentCategory = btn.dataset.category;
    renderValuePage(container);
  };

  bindCardClickEvents(gridContainer);
}

function renderValueGridItemsHtml() {
  let filtered = [...cosmeticsData];

  if (valueSearchQuery.trim() !== '') {
    const q = valueSearchQuery.toLowerCase();
    filtered = filtered.filter(item => item.name.toLowerCase().includes(q));
  }

  if (valueCurrentCategory !== 'All') {
    filtered = filtered.filter(item => (item.category || item.type || '').toLowerCase() === valueCurrentCategory.toLowerCase());
  }

  filtered.sort((a, b) => {
    const valA = getItemCalculatedValue(a);
    const valB = getItemCalculatedValue(b);
    switch (valueCurrentSort) {
      case 'value-desc': return valB - valA;
      case 'value-asc': return valA - valB;
      case 'demand-desc': return (b.demand || 0) - (a.demand || 0);
      case 'demand-asc': return (a.demand || 0) - (b.demand || 0);
      case 'name-asc': return a.name.localeCompare(b.name);
      case 'name-desc': return b.name.localeCompare(a.name);
      default: return 0;
    }
  });

  if (filtered.length === 0) {
    return `<div style="grid-column: 1 / -1; text-align: center; color: #888; padding: 40px;">No cosmetics found matching your criteria.</div>`;
  }

  return filtered.map(item => renderItemCardHtml(item)).join('');
}

/* ==========================================================================
   7. COMPARE ENGINE PAGE
   ========================================================================== */

function renderComparePage(container) {
  if (compareLeftItems.length === 0 && cosmeticsData[0]) compareLeftItems = [cosmeticsData[0]];
  if (compareRightItems.length === 0 && cosmeticsData[1]) compareRightItems = [cosmeticsData[1]];

  const leftTotal = compareLeftItems.reduce((acc, i) => acc + getItemCalculatedValue(i), 0);
  const rightTotal = compareRightItems.reduce((acc, i) => acc + getItemCalculatedValue(i), 0);
  const diff = leftTotal - rightTotal;
  const maxTotal = Math.max(leftTotal, rightTotal, 1);
  const pctDiff = Math.round((Math.abs(diff) / maxTotal) * 100);

  let outcomeLabel = 'Fair Trade';
  let badgeBg = '#27ae60';
  if (pctDiff > 5) {
    if (leftTotal > rightTotal) {
      outcomeLabel = 'Win for You';
      badgeBg = '#27ae60';
    } else {
      outcomeLabel = 'Win for Trader';
      badgeBg = '#e74c3c';
    }
  }

  container.innerHTML = `
    <div style="max-width: 1000px; margin: 0 auto; padding: 24px;">
      <h1 style="color: #fff; margin: 0 0 6px 0;">Trade Comparison Engine</h1>
      <p style="color: #aaa; margin: 0 0 20px 0; font-size: 14px;">Evaluate total offer values and trade fairness instantly.</p>

      <div style="background: #14181f; border: 1px solid #282e38; border-radius: 12px; padding: 16px; margin-bottom: 24px; text-align: center;">
        <span style="background: ${badgeBg}; color: #fff; padding: 6px 16px; border-radius: 20px; font-weight: 700; font-size: 14px; display: inline-block;">${outcomeLabel}</span>
        <div style="color: #aaa; font-size: 13px; margin-top: 8px;">
          Difference: <strong style="color: #5EF2B6;">${formatShardsDisplay(Math.abs(diff))} shards</strong> (${pctDiff}% variation)
        </div>
      </div>

      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
        <div style="background: #14181f; border: 1px solid #282e38; border-radius: 12px; padding: 16px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
            <h3 style="margin: 0; color: #fff;">Your Offer</h3>
            <button id="zv-clear-left" style="background: none; border: none; color: #e74c3c; cursor: pointer; font-size: 12px;">Clear</button>
          </div>
          <div style="min-height: 180px;">${renderCompareSlotsHtml(compareLeftItems, 'left')}</div>
          <button id="zv-add-left" style="width: 100%; margin-top: 12px; background: #0d1117; border: 1px dashed #30363d; color: #5EF2B6; padding: 10px; border-radius: 8px; font-weight: 600; cursor: pointer;">+ Add Cosmetic</button>
          <div style="margin-top: 16px; padding-top: 12px; border-top: 1px solid #282e38; display: flex; justify-content: space-between; font-weight: 700;">
            <span style="color: #aaa;">Total Value:</span>
            <span style="color: #5EF2B6;">${formatShardsDisplay(leftTotal)} shards</span>
          </div>
        </div>

        <div style="background: #14181f; border: 1px solid #282e38; border-radius: 12px; padding: 16px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
            <h3 style="margin: 0; color: #fff;">Trader's Offer</h3>
            <button id="zv-clear-right" style="background: none; border: none; color: #e74c3c; cursor: pointer; font-size: 12px;">Clear</button>
          </div>
          <div style="min-height: 180px;">${renderCompareSlotsHtml(compareRightItems, 'right')}</div>
          <button id="zv-add-right" style="width: 100%; margin-top: 12px; background: #0d1117; border: 1px dashed #30363d; color: #5EF2B6; padding: 10px; border-radius: 8px; font-weight: 600; cursor: pointer;">+ Add Cosmetic</button>
          <div style="margin-top: 16px; padding-top: 12px; border-top: 1px solid #282e38; display: flex; justify-content: space-between; font-weight: 700;">
            <span style="color: #aaa;">Total Value:</span>
            <span style="color: #5EF2B6;">${formatShardsDisplay(rightTotal)} shards</span>
          </div>
        </div>
      </div>
    </div>

    <div id="zv-picker-overlay" style="display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.8); z-index: 1000; align-items: center; justify-content: center;">
      <div style="background: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 20px; width: 90%; max-width: 440px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
          <h3 style="margin: 0; color: #fff;">Select Cosmetic</h3>
          <button id="zv-close-picker" style="background: none; border: none; color: #aaa; font-size: 18px; cursor: pointer;">✕</button>
        </div>
        <input type="text" id="zv-picker-search" placeholder="Type to search..." style="width: 100%; padding: 10px; background: #0d1117; border: 1px solid #30363d; border-radius: 8px; color: #fff; box-sizing: border-box; margin-bottom: 12px;">
        <div id="zv-picker-list" style="max-height: 260px; overflow-y: auto;">${renderPickerItemsHtml('')}</div>
      </div>
    </div>
  `;

  const pickerOverlay = container.querySelector('#zv-picker-overlay');
  const closePicker = container.querySelector('#zv-close-picker');
  const searchInput = container.querySelector('#zv-picker-search');
  const pickerList = container.querySelector('#zv-picker-list');

  container.querySelector('#zv-add-left').onclick = () => {
    compareActiveSide = 'left';
    pickerOverlay.style.display = 'flex';
  };

  container.querySelector('#zv-add-right').onclick = () => {
    compareActiveSide = 'right';
    pickerOverlay.style.display = 'flex';
  };

  closePicker.onclick = () => pickerOverlay.style.display = 'none';

  searchInput.oninput = (e) => {
    pickerList.innerHTML = renderPickerItemsHtml(e.target.value);
    bindPickerItemClicks(pickerList, pickerOverlay, container);
  };

  bindPickerItemClicks(pickerList, pickerOverlay, container);

  container.querySelector('#zv-clear-left').onclick = () => { compareLeftItems = []; renderComparePage(container); };
  container.querySelector('#zv-clear-right').onclick = () => { compareRightItems = []; renderComparePage(container); };

  container.querySelectorAll('.zv-slot-remove-btn').forEach(btn => {
    btn.onclick = (e) => {
      const side = e.target.dataset.side;
      const idx = parseInt(e.target.dataset.index, 10);
      if (side === 'left') compareLeftItems.splice(idx, 1);
      else compareRightItems.splice(idx, 1);
      renderComparePage(container);
    };
  });
}

function renderCompareSlotsHtml(items, side) {
  if (items.length === 0) return `<div style="text-align: center; color: #666; padding-top: 60px; font-size: 13px;">No items added.</div>`;
  return items.map((item, index) => {
    const imgUrl = item.imageUrl || item.image || 'https://via.placeholder.com/150?text=No+Image';
    const val = getItemCalculatedValue(item);
    return `
      <div style="background: #0d1117; border: 1px solid #21262d; border-radius: 8px; padding: 8px 12px; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center;">
        <div style="display: flex; align-items: center; gap: 10px;">
          <img src="${imgUrl}" style="width: 32px; height: 32px; object-fit: contain; border-radius: 4px; background: #161b22;" onerror="this.src='https://via.placeholder.com/150?text=No+Image';">
          <div>
            <div style="color: #fff; font-weight: 600; font-size: 13px;">${escapeHtml(item.name)}</div>
            <div style="color: #5EF2B6; font-size: 11px;">${formatShardsDisplay(val)} shards</div>
          </div>
        </div>
        <button class="zv-slot-remove-btn" data-side="${side}" data-index="${index}" style="background: none; border: none; color: #e74c3c; cursor: pointer; font-size: 16px;">✕</button>
      </div>
    `;
  }).join('');
}

function renderPickerItemsHtml(query) {
  const q = query.toLowerCase().trim();
  const filtered = cosmeticsData.filter(i => i.name.toLowerCase().includes(q));

  if (filtered.length === 0) return `<div style="text-align: center; color: #888; padding: 20px;">No items found.</div>`;

  return filtered.map(i => {
    const imgUrl = i.imageUrl || i.image || 'https://via.placeholder.com/150?text=No+Image';
    const itemKey = i.id || i.name;
    const val = getItemCalculatedValue(i);
    return `
      <div class="zv-picker-item" data-id="${itemKey}" style="padding: 8px; border-bottom: 1px solid #21262d; display: flex; align-items: center; justify-content: space-between; cursor: pointer;">
        <div style="display: flex; align-items: center; gap: 10px;">
          <img src="${imgUrl}" style="width: 28px; height: 28px; object-fit: contain; background: #0d1117; border-radius: 4px;" onerror="this.src='https://via.placeholder.com/150?text=No+Image';">
          <span style="color: #fff; font-weight: 600; font-size: 13px;">${escapeHtml(i.name)}</span>
        </div>
        <span style="color: #5EF2B6; font-weight: 700; font-size: 12px;">${formatShardsDisplay(val)} shards</span>
      </div>
    `;
  }).join('');
}

function bindPickerItemClicks(pickerList, pickerOverlay, container) {
  pickerList.querySelectorAll('.zv-picker-item').forEach(el => {
    el.onclick = () => {
      const id = el.dataset.id;
      const selected = cosmeticsData.find(i => String(i.id || i.name) === String(id));
      if (selected) {
        if (compareActiveSide === 'left') compareLeftItems.push(selected);
        else compareRightItems.push(selected);
        pickerOverlay.style.display = 'none';
        renderComparePage(container);
      }
    };
  });
}

/* ==========================================================================
   8. COLLECTION & WISHLIST PAGE
   ========================================================================== */

function renderCollectionPage(container) {
  const inv = getInventory();
  const wl = getWishlist();

  let totalNetWorth = 0;
  let totalItemCount = 0;

  Object.entries(inv).forEach(([id, qty]) => {
    const item = cosmeticsData.find(i => String(i.id || i.name) === String(id));
    if (item) {
      totalNetWorth += getItemCalculatedValue(item) * qty;
      totalItemCount += qty;
    }
  });

  const invItems = cosmeticsData.filter(i => (inv[i.id || i.name] || 0) > 0);
  const wlItems = cosmeticsData.filter(i => wl.includes(String(i.id || i.name)));

  container.innerHTML = `
    <div style="max-width: 1000px; margin: 0 auto; padding: 24px;">
      <h1 style="color: #fff; margin: 0 0 6px 0;">Portfolio & Wishlist</h1>
      <p style="color: #aaa; margin: 0 0 20px 0; font-size: 14px;">Track owned cosmetics inventory value and desired items.</p>

      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 24px;">
        <div style="background: #14181f; border: 1px solid #282e38; border-radius: 12px; padding: 16px;">
          <div style="font-size: 12px; color: #aaa;">Total Inventory Value</div>
          <div style="font-size: 22px; font-weight: 800; color: #5EF2B6; margin-top: 4px;">${formatShardsDisplay(totalNetWorth)} shards</div>
        </div>
        <div style="background: #14181f; border: 1px solid #282e38; border-radius: 12px; padding: 16px;">
          <div style="font-size: 12px; color: #aaa;">Items Collected</div>
          <div style="font-size: 22px; font-weight: 800; color: #fff; margin-top: 4px;">${totalItemCount}</div>
        </div>
        <div style="background: #14181f; border: 1px solid #282e38; border-radius: 12px; padding: 16px;">
          <div style="font-size: 12px; color: #aaa;">Wishlisted Items</div>
          <div style="font-size: 22px; font-weight: 800; color: #fff; margin-top: 4px;">${wlItems.length}</div>
        </div>
      </div>

      <div style="display: flex; gap: 12px; border-bottom: 1px solid #282e38; margin-bottom: 20px; padding-bottom: 8px;">
        <button id="zv-tab-inv" style="background: none; border: none; color: ${collectionActiveTab === 'inventory' ? '#5EF2B6' : '#aaa'}; font-weight: 700; cursor: pointer; font-size: 15px;">Inventory (${invItems.length})</button>
        <button id="zv-tab-wl" style="background: none; border: none; color: ${collectionActiveTab === 'wishlist' ? '#5EF2B6' : '#aaa'}; font-weight: 700; cursor: pointer; font-size: 15px;">Wishlist (${wlItems.length})</button>
      </div>

      <div id="zv-collection-grid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 16px;">
        ${collectionActiveTab === 'inventory' 
          ? (invItems.length > 0 ? invItems.map(i => renderItemCardHtml(i)).join('') : '<div style="color: #888;">No items in inventory.</div>')
          : (wlItems.length > 0 ? wlItems.map(i => renderItemCardHtml(i)).join('') : '<div style="color: #888;">No items wishlisted.</div>')
        }
      </div>
    </div>
  `;

  container.querySelector('#zv-tab-inv').onclick = () => { collectionActiveTab = 'inventory'; renderCollectionPage(container); };
  container.querySelector('#zv-tab-wl').onclick = () => { collectionActiveTab = 'wishlist'; renderCollectionPage(container); };

  bindCardClickEvents(container.querySelector('#zv-collection-grid'));
}

/* ==========================================================================
   9. SETTINGS PAGE
   ========================================================================== */

function renderSettingsPage(container) {
  const activeUser = localStorage.getItem('zv_active_user') || 'happyboy457';

  container.innerHTML = `
    <div style="max-width: 600px; margin: 0 auto; padding: 24px;">
      <h1 style="color: #fff; margin: 0 0 6px 0;">Settings</h1>
      <p style="color: #aaa; margin: 0 0 24px 0; font-size: 14px;">Manage user session and application data.</p>

      <div style="background: #14181f; border: 1px solid #282e38; border-radius: 12px; padding: 20px;">
        <div style="margin-bottom: 20px;">
          <label style="color: #aaa; font-size: 12px; display: block; margin-bottom: 6px;">ACTIVE ACCOUNT</label>
          <div style="color: #fff; font-weight: 700; font-size: 16px;">${escapeHtml(activeUser)}</div>
        </div>
        <button id="zv-logout-btn" style="background: #e74c3c; border: none; color: #fff; padding: 10px 18px; border-radius: 8px; font-weight: 700; cursor: pointer;">
          Log Out
        </button>
      </div>
    </div>
  `;

  container.querySelector('#zv-logout-btn').onclick = () => {
    sessionStorage.removeItem('loggedIn');
    renderApp();
  };
}

function escapeHtml(str) {
  return String(str || '')
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

document.addEventListener('DOMContentLoaded', loadData);
