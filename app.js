/**
 * ZeqaValues - Complete Standalone Single-File Engine
 * Self-contained Single Page Application (SPA) for Mineville PvP Cosmetics.
 */

/* ==========================================================================
   1. GLOBAL STATE & LOCAL STORAGE HANDLERS
   ========================================================================== */

let cosmeticsData = [];
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

async function loadData() {
  try {
    const res = await fetch('./data/cosmetics.json');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    cosmeticsData = await res.json();
  } catch (err) {
    console.warn('Could not fetch cosmetics.json, utilizing fallback dataset:', err);
    cosmeticsData = [
      { id: 1, name: 'Dragon Cape', category: 'Capes', rarity: 'Legendary', value: 25000, demand: 9, salesExistingRatio: 85, priceHistory: [21000, 22500, 23000, 24000, 25000] },
      { id: 2, name: 'Galaxy Halo', category: 'Hats', rarity: 'Mythic', value: 42000, demand: 10, salesExistingRatio: 92, priceHistory: [35000, 38000, 40000, 41500, 42000] },
      { id: 3, name: 'Ruby Trail', category: 'Trails', rarity: 'Rare', value: 8500, demand: 6, salesExistingRatio: 45, priceHistory: [7000, 7500, 8000, 8200, 8500] },
      { id: 4, name: 'Shadow Aura', category: 'Auras', rarity: 'Epic', value: 16000, demand: 8, salesExistingRatio: 70, priceHistory: [14000, 14800, 15200, 15800, 16000] },
      { id: 5, name: 'Emerald Wings', category: 'Wings', rarity: 'Legendary', value: 31000, demand: 9, salesExistingRatio: 88, priceHistory: [28000, 29500, 30000, 30800, 31000] }
    ];
  }
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
   2. MAIN SPA ROUTER & LAYOUT RENDERER
   ========================================================================== */

function renderApp() {
  if (localStorage.getItem('loggedIn') !== '1') {
    renderLogin();
    return;
  }

  const activeUser = localStorage.getItem('zv_active_user') || 'happyboy457';

  app.innerHTML = `
    <div class="topbar" style="background: #14181f; border-bottom: 1px solid #282e38; padding: 14px 24px; display: flex; justify-content: space-between; align-items: center; position: sticky; top: 0; z-index: 100;">
      <div style="font-weight: 800; font-size: 18px; color: #ffffff;">
        Zeqa<span style="color: #5EF2B6;">Values</span>
      </div>
      <nav style="display: flex; gap: 18px;">
        <a class="nav-btn ${currentPage === 'home' ? 'active' : ''}" data-page="home">Home</a>
        <a class="nav-btn ${currentPage === 'value' ? 'active' : ''}" data-page="value">Value</a>
        <a class="nav-btn ${currentPage === 'compare' ? 'active' : ''}" data-page="compare">Compare</a>
        <a class="nav-btn ${currentPage === 'collection' ? 'active' : ''}" data-page="collection">Collection</a>
        <a class="nav-btn ${currentPage === 'settings' ? 'active' : ''}" data-page="settings">Settings</a>
      </nav>
      <div style="font-size: 13px; color: #5EF2B6; font-weight: bold; background: rgba(94,242,182,0.1); padding: 4px 10px; border-radius: 6px; border: 1px solid rgba(94,242,182,0.2);">
        ${activeUser}
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
   3. LOGIN VIEW
   ========================================================================== */

function renderLogin() {
  app.innerHTML = `
    <div style="max-width: 360px; margin: 80px auto; background: #14181f; border: 1px solid #282e38; border-radius: 14px; padding: 28px; text-align: center;">
      <h2 style="margin: 0 0 8px 0; color: #ffffff;">ZeqaValues</h2>
      <p style="color: #aaaaaa; font-size: 13px; margin-bottom: 20px;">Sign in to access Mineville PvP cosmetic analytics.</p>
      <input id="u" placeholder="Username (happyboy457)" style="width: 100%; padding: 10px; margin-bottom: 12px; background: #0d1117; border: 1px solid #30363d; color: #fff; border-radius: 8px; box-sizing: border-box;">
      <input id="p" type="password" placeholder="Password (admin)" style="width: 100%; padding: 10px; margin-bottom: 16px; background: #0d1117; border: 1px solid #30363d; color: #fff; border-radius: 8px; box-sizing: border-box;">
      <button id="b" style="width: 100%; background: #5EF2B6; border: none; color: #111; padding: 12px; border-radius: 8px; font-weight: 700; cursor: pointer;">Sign In</button>
      <p id="m" style="text-align: center; font-size: 13px; margin-top: 12px;"></p>
    </div>
  `;

  document.getElementById('b').onclick = () => {
    const u = document.getElementById('u')?.value.trim();
    const p = document.getElementById('p')?.value.trim();
    const m = document.getElementById('m');

    if (u === 'happyboy457' && p === 'admin') {
      localStorage.setItem('loggedIn', '1');
      localStorage.setItem('zv_active_user', u);
      renderApp();
    } else if (m) {
      m.textContent = 'Invalid credentials. Use happyboy457 / admin';
      m.style.color = '#e74c3c';
    }
  };
}

/* ==========================================================================
   4. HOME PAGE VIEW
   ========================================================================== */

function renderHomePage(container) {
  const totalValue = cosmeticsData.reduce((acc, i) => acc + (i.value || 0), 0);
  const highestItem = [...cosmeticsData].sort((a, b) => (b.value || 0) - (a.value || 0))[0];
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
          <div style="font-size: 18px; font-weight: 700; color: #5EF2B6; margin-top: 4px;">${highestItem ? highestItem.name : 'N/A'}</div>
        </div>
        <div style="background: #14181f; border: 1px solid #282e38; border-radius: 12px; padding: 16px;">
          <div style="font-size: 12px; color: #aaa;">Most Traded</div>
          <div style="font-size: 18px; font-weight: 700; color: #fff; margin-top: 4px;">${mostTraded ? mostTraded.name : 'N/A'}</div>
        </div>
        <div style="background: #14181f; border: 1px solid #282e38; border-radius: 12px; padding: 16px;">
          <div style="font-size: 12px; color: #aaa;">Market Capitalization</div>
          <div style="font-size: 18px; font-weight: 700; color: #5EF2B6; margin-top: 4px;">${totalValue.toLocaleString()} coins</div>
        </div>
      </div>

      <div style="margin-top: 32px; background: #14181f; border: 1px solid #282e38; border-radius: 14px; padding: 20px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 16px;">
        <div>
          <h3 style="margin: 0 0 4px 0; color: #ffffff;">Explore Full Valuation Directory</h3>
          <p style="margin: 0; color: #aaaaaa; font-size: 13px;">Filter through Capes, Hats, Trails, Auras, and Wings with 10 sorting engines.</p>
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
   5. VALUE DIRECTORY PAGE
   ========================================================================== */

function renderValuePage(container) {
  const categories = ['All', 'Capes', 'Hats', 'Trails', 'Auras', 'Wings'];

  container.innerHTML = `
    <div style="max-width: 1200px; margin: 0 auto; padding: 24px;">
      <h1 style="color: #fff; margin: 0 0 6px 0;">Cosmetics Directory</h1>
      <p style="color: #aaa; margin: 0 0 24px 0; font-size: 14px;">Filter and inspect real-time valuations across all cosmetic tiers.</p>

      <div style="background: #14181f; border: 1px solid #282e38; border-radius: 12px; padding: 16px; margin-bottom: 24px; display: flex; flex-direction: column; gap: 14px;">
        <div style="display: flex; gap: 12px; flex-wrap: wrap;">
          <input type="text" id="zv-search-field" placeholder="Search cosmetics..." value="${valueSearchQuery}" style="flex: 1; min-width: 200px; padding: 10px; background: #0d1117; border: 1px solid #30363d; border-radius: 8px; color: #fff;">
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
    filtered = filtered.filter(item => (item.category || '').toLowerCase() === valueCurrentCategory.toLowerCase());
  }

  filtered.sort((a, b) => {
    switch (valueCurrentSort) {
      case 'value-desc': return (b.value || 0) - (a.value || 0);
      case 'value-asc': return (a.value || 0) - (b.value || 0);
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
   6. COMPARE ENGINE PAGE
   ========================================================================== */

function renderComparePage(container) {
  if (compareLeftItems.length === 0 && cosmeticsData[0]) compareLeftItems = [cosmeticsData[0]];
  if (compareRightItems.length === 0 && cosmeticsData[1]) compareRightItems = [cosmeticsData[1]];

  const leftTotal = compareLeftItems.reduce((acc, i) => acc + (i.value || 0), 0);
  const rightTotal = compareRightItems.reduce((acc, i) => acc + (i.value || 0), 0);
  const diff = leftTotal - rightTotal;
  const maxTotal = Math.max(leftTotal, rightTotal, 1);
  const pctDiff = Math.round((Math.abs(diff) / maxTotal) * 100);

  let outcomeLabel = 'Fair Trade';
  let badgeBg = '#27ae60';
  if (pctDiff > 5) {
    if (leftTotal > rightTotal) {
      outcomeLabel = 'Win for happyboy457';
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
          Difference: <strong style="color: #5EF2B6;">${Math.abs(diff).toLocaleString()} coins</strong> (${pctDiff}% variation)
        </div>
      </div>

      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
        <div style="background: #14181f; border: 1px solid #282e38; border-radius: 12px; padding: 16px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
            <h3 style="margin: 0; color: #fff;">happyboy457's Offer</h3>
            <button id="zv-clear-left" style="background: none; border: none; color: #e74c3c; cursor: pointer; font-size: 12px;">Clear</button>
          </div>
          <div style="min-height: 180px;">${renderCompareSlotsHtml(compareLeftItems, 'left')}</div>
          <button id="zv-add-left" style="width: 100%; margin-top: 12px; background: #0d1117; border: 1px dashed #30363d; color: #5EF2B6; padding: 10px; border-radius: 8px; font-weight: 600; cursor: pointer;">+ Add Cosmetic</button>
          <div style="margin-top: 16px; padding-top: 12px; border-top: 1px solid #282e38; display: flex; justify-content: space-between; font-weight: 700;">
            <span style="color: #aaa;">Total Value:</span>
            <span style="color: #5EF2B6;">${leftTotal.toLocaleString()} coins</span>
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
            <span style="color: #5EF2B6;">${rightTotal.toLocaleString()} coins</span>
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
  return items.map((item, index) => `
    <div style="background: #0d1117; border: 1px solid #21262d; border-radius: 8px; padding: 10px; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center;">
      <div>
        <div style="color: #fff; font-weight: 600; font-size: 14px;">${item.name}</div>
        <div style="color: #5EF2B6; font-size: 12px;">${(item.value || 0).toLocaleString()} coins</div>
      </div>
      <button class="zv-slot-remove-btn" data-side="${side}" data-index="${index}" style="background: none; border: none; color: #e74c3c; cursor: pointer; font-size: 16px;">✕</button>
    </div>
  `).join('');
}

function renderPickerItemsHtml(query) {
  const q = query.toLowerCase().trim();
  const filtered = cosmeticsData.filter(i => i.name.toLowerCase().includes(q));

  if (filtered.length === 0) return `<div style="text-align: center; color: #888; padding: 20px;">No items found.</div>`;

  return filtered.map(i => `
    <div class="zv-picker-item" data-id="${i.id}" style="padding: 10px; border-bottom: 1px solid #21262d; display: flex; justify-content: space-between; cursor: pointer;">
      <span style="color: #fff; font-weight: 600;">${i.name}</span>
      <span style="color: #5EF2B6; font-weight: 700;">${(i.value || 0).toLocaleString()} coins</span>
    </div>
  `).join('');
}

function bindPickerItemClicks(pickerList, pickerOverlay, container) {
  pickerList.querySelectorAll('.zv-picker-item').forEach(el => {
    el.onclick = () => {
      const id = el.dataset.id;
      const selected = cosmeticsData.find(i => String(i.id) === String(id));
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
   7. COLLECTION & WISHLIST PAGE
   ========================================================================== */

function renderCollectionPage(container) {
  const inv = getInventory();
  const wl = getWishlist();

  let totalNetWorth = 0;
  let totalItemCount = 0;

  Object.entries(inv).forEach(([id, qty]) => {
    const item = cosmeticsData.find(i => String(i.id) === String(id));
    if (item) {
      totalNetWorth += (item.value || 0) * qty;
      totalItemCount += qty;
    }
  });

  container.innerHTML = `
    <div style="max-width: 1000px; margin: 0 auto; padding: 24px;">
      <h1 style="color: #fff; margin: 0 0 6px 0;">Portfolio & Wishlist</h1>
      <p style="color: #aaa; margin: 0 0 20px 0; font-size: 14px;">Track owned cosmetics inventory value and desired items.</p>

      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 24px;">
        <div style="background: #14181f; border: 1px solid #282e38; border-radius: 12px; padding: 16px;">
          <div style="font-size: 12px; color: #aaa;">Portfolio Net Worth</div>
          <div style="font-size: 20px; font-weight: 800; color: #5EF2B6; margin-top: 4px;">${totalNetWorth.toLocaleString()} coins</div>
        </div>
        <div style="background: #14181f; border: 1px solid #282e38; border-radius: 12px; padding: 16px;">
          <div style="font-size: 12px; color: #aaa;">Total Owned Items</div>
          <div style="font-size: 20px; font-weight: 800; color: #fff; margin-top: 4px;">${totalItemCount} items</div>
        </div>
        <div style="background: #14181f; border: 1px solid #282e38; border-radius: 12px; padding: 16px;">
          <div style="font-size: 12px; color: #aaa;">Wishlist Count</div>
          <div style="font-size: 20px; font-weight: 800; color: #fff; margin-top: 4px;">${wl.length} items</div>
        </div>
      </div>

      <div style="display: flex; gap: 12px; margin-bottom: 20px; border-bottom: 1px solid #282e38; padding-bottom: 12px;">
        <button id="zv-tab-inv" style="background: none; border: none; color: ${collectionActiveTab === 'inventory' ? '#5EF2B6' : '#aaa'}; font-weight: 700; font-size: 15px; cursor: pointer;">
          Inventory (${Object.keys(inv).length})
        </button>
        <button id="zv-tab-wl" style="background: none; border: none; color: ${collectionActiveTab === 'wishlist' ? '#5EF2B6' : '#aaa'}; font-weight: 700; font-size: 15px; cursor: pointer;">
          Wishlist (${wl.length})
        </button>
      </div>

      <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 16px;">
        ${collectionActiveTab === 'inventory' ? renderCollectionInventoryHtml(inv) : renderCollectionWishlistHtml(wl)}
      </div>
    </div>
  `;

  container.querySelector('#zv-tab-inv').onclick = () => { collectionActiveTab = 'inventory'; renderCollectionPage(container); };
  container.querySelector('#zv-tab-wl').onclick = () => { collectionActiveTab = 'wishlist'; renderCollectionPage(container); };

  container.querySelectorAll('.zv-btn-plus').forEach(btn => {
    btn.onclick = (e) => {
      e.stopPropagation();
      const id = btn.dataset.id;
      const curInv = getInventory();
      curInv[id] = (curInv[id] || 0) + 1;
      saveInventory(curInv);
      renderCollectionPage(container);
    };
  });

  container.querySelectorAll('.zv-btn-minus').forEach(btn => {
    btn.onclick = (e) => {
      e.stopPropagation();
      const id = btn.dataset.id;
      const curInv = getInventory();
      if (curInv[id] > 1) curInv[id] -= 1;
      else delete curInv[id];
      saveInventory(curInv);
      renderCollectionPage(container);
    };
  });

  container.querySelectorAll('.zv-wishlist-remove-btn').forEach(btn => {
    btn.onclick = (e) => {
      e.stopPropagation();
      const id = btn.dataset.id;
      let curWl = getWishlist().filter(val => String(val) !== String(id));
      saveWishlist(curWl);
      renderCollectionPage(container);
    };
  });

  bindCardClickEvents(container);
}

function renderCollectionInventoryHtml(inv) {
  const entries = Object.entries(inv).filter(([_, qty]) => qty > 0);
  if (entries.length === 0) {
    return `<div style="grid-column: 1 / -1; text-align: center; color: #888; padding: 40px;">Your collection is empty. Open items in the directory to add them!</div>`;
  }

  return entries.map(([id, qty]) => {
    const item = cosmeticsData.find(i => String(i.id) === String(id));
    if (!item) return '';
    return `
      <div class="item-card" data-id="${item.id}" style="background: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 16px;">
        <h3 style="margin: 0 0 4px 0; color: #fff;">${item.name}</h3>
        <div style="font-size: 12px; color: #aaa; margin-bottom: 10px;">${item.category || 'Cosmetic'}</div>
        <div style="font-size: 14px; font-weight: bold; color: #5EF2B6; margin-bottom: 12px;">${((item.value || 0) * qty).toLocaleString()} coins</div>
        <div style="display: flex; justify-content: space-between; align-items: center; background: #0d1117; padding: 6px; border-radius: 6px;">
          <button class="zv-btn-minus" data-id="${item.id}" style="background: #21262d; border: none; color: #fff; width: 28px; height: 28px; border-radius: 4px; cursor: pointer;">-</button>
          <span style="color: #fff; font-size: 13px; font-weight: bold;">Qty: ${qty}</span>
          <button class="zv-btn-plus" data-id="${item.id}" style="background: #21262d; border: none; color: #fff; width: 28px; height: 28px; border-radius: 4px; cursor: pointer;">+</button>
        </div>
      </div>
    `;
  }).join('');
}

function renderCollectionWishlistHtml(wl) {
  if (wl.length === 0) {
    return `<div style="grid-column: 1 / -1; text-align: center; color: #888; padding: 40px;">Your wishlist is empty.</div>`;
  }

  return wl.map(id => {
    const item = cosmeticsData.find(i => String(i.id) === String(id));
    if (!item) return '';
    return `
      <div class="item-card" data-id="${item.id}" style="background: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 16px;">
        <h3 style="margin: 0 0 4px 0; color: #fff;">${item.name}</h3>
        <div style="font-size: 12px; color: #aaa; margin-bottom: 10px;">${item.category || 'Cosmetic'}</div>
        <div style="font-size: 14px; font-weight: bold; color: #5EF2B6; margin-bottom: 12px;">${(item.value || 0).toLocaleString()} coins</div>
        <button class="zv-wishlist-remove-btn" data-id="${item.id}" style="width: 100%; background: rgba(231,76,60,0.15); border: 1px solid #e74c3c; color: #ff6b6b; padding: 6px; border-radius: 6px; font-size: 12px; cursor: pointer;">Remove Wishlist</button>
      </div>
    `;
  }).join('');
}

/* ==========================================================================
   8. SETTINGS PAGE
   ========================================================================== */

function renderSettingsPage(container) {
  const activeUser = localStorage.getItem('zv_active_user') || 'happyboy457';

  container.innerHTML = `
    <div style="max-width: 600px; margin: 0 auto; padding: 24px;">
      <h1 style="color: #fff; margin: 0 0 6px 0;">Settings</h1>
      <p style="color: #aaa; margin: 0 0 24px 0; font-size: 14px;">Manage session and local storage preferences.</p>

      <div style="background: #14181f; border: 1px solid #282e38; border-radius: 12px; padding: 18px; margin-bottom: 16px; display: flex; justify-content: space-between; align-items: center;">
        <div>
          <div style="color: #fff; font-weight: 600;">Active Account</div>
          <div style="color: #aaa; font-size: 12px;">Signed in username</div>
        </div>
        <span style="color: #5EF2B6; font-weight: 700;">${activeUser}</span>
      </div>

      <div style="background: #14181f; border: 1px solid #282e38; border-radius: 12px; padding: 18px; margin-bottom: 16px; display: flex; justify-content: space-between; align-items: center;">
        <div>
          <div style="color: #fff; font-weight: 600;">Reset Local Portfolio</div>
          <div style="color: #aaa; font-size: 12px;">Clears all saved inventory and wishlist items</div>
        </div>
        <button id="zv-reset-storage" style="background: #e74c3c; border: none; color: #fff; padding: 8px 14px; border-radius: 6px; font-weight: 600; cursor: pointer;">Reset Storage</button>
      </div>

      <div style="background: #14181f; border: 1px solid #282e38; border-radius: 12px; padding: 18px; display: flex; justify-content: space-between; align-items: center;">
        <div>
          <div style="color: #fff; font-weight: 600;">Sign Out</div>
          <div style="color: #aaa; font-size: 12px;">Terminates active session</div>
        </div>
        <button id="zv-sign-out" style="background: #30363d; border: 1px solid #444c56; color: #fff; padding: 8px 14px; border-radius: 6px; font-weight: 600; cursor: pointer;">Log Out</button>
      </div>
    </div>
  `;

  container.querySelector('#zv-reset-storage').onclick = () => {
    if (confirm('Clear local collection and wishlist data?')) {
      localStorage.removeItem('zv_user_inventory');
      localStorage.removeItem('zv_user_wishlist');
      alert('Portfolio reset successfully.');
      renderApp();
    }
  };

  container.querySelector('#zv-sign-out').onclick = () => {
    localStorage.removeItem('loggedIn');
    renderApp();
  };
}

/* ==========================================================================
   9. POPUP INSPECTOR MODAL
   ========================================================================== */

function openPopupModal(item) {
  const modalRoot = document.getElementById('zv-modal-root');
  if (!modalRoot) return;

  const inv = getInventory();
  const wl = getWishlist();
  const isOwned = (inv[item.id] || 0) > 0;
  const isWishlisted = wl.includes(item.id);

  const priceHistory = item.priceHistory || [
    Math.round((item.value || 10000) * 0.85),
    Math.round((item.value || 10000) * 0.90),
    Math.round((item.value || 10000) * 0.95),
    (item.value || 10000)
  ];

  modalRoot.innerHTML = `
    <div id="popup-overlay" style="position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.8); backdrop-filter: blur(8px); display: flex; align-items: center; justify-content: center; z-index: 10000;">
      <div style="background: #161b22; border: 1px solid #30363d; border-radius: 16px; padding: 24px; width: 90%; max-width: 480px; box-shadow: 0 20px 50px rgba(0,0,0,0.8); color: #fff;">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px;">
          <div>
            <h2 style="margin: 0 0 4px 0; font-size: 22px; color: #fff;">${item.name}</h2>
            <div style="font-size: 13px; color: #aaa;">${item.category || 'Cosmetic'} • <span style="color: #5EF2B6;">${item.rarity || 'Common'}</span></div>
          </div>
          <button id="zv-modal-close-btn" style="background: none; border: none; color: #aaa; font-size: 20px; cursor: pointer;">✕</button>
        </div>

        <div style="background: #0d1117; border: 1px solid #21262d; border-radius: 12px; padding: 16px; margin-bottom: 16px; text-align: center;">
          <div style="font-size: 12px; color: #aaa; text-transform: uppercase;">Estimated Market Value</div>
          <div style="font-size: 28px; font-weight: 800; color: #5EF2B6; margin-top: 4px;">${(item.value || 0).toLocaleString()} coins</div>
        </div>

        <div style="margin-bottom: 16px;">
          <div style="font-size: 12px; color: #aaa; margin-bottom: 8px;">Price Trend Graph</div>
          <svg viewBox="0 0 300 80" style="width: 100%; height: 80px; background: #0d1117; border-radius: 8px; padding: 8px; box-sizing: border-box;">
            <path d="${buildSvgPath(priceHistory)}" fill="none" stroke="#5EF2B6" stroke-width="3" />
          </svg>
        </div>

        <div style="display: flex; gap: 12px;">
          <button id="zv-add-inv-btn" style="flex: 1; background: #5EF2B6; border: none; color: #111; padding: 12px; border-radius: 8px; font-weight: 700; cursor: pointer;">
            ${isOwned ? 'In Collection (+1)' : 'Add to Collection'}
          </button>
          <button id="zv-add-wl-btn" style="flex: 1; background: #21262d; border: 1px solid #30363d; color: #fff; padding: 12px; border-radius: 8px; font-weight: 600; cursor: pointer;">
            ${isWishlisted ? 'Wishlisted ★' : 'Add to Wishlist ☆'}
          </button>
        </div>
      </div>
    </div>
  `;

  modalRoot.querySelector('#zv-modal-close-btn').onclick = closePopupModal;
  modalRoot.querySelector('#popup-overlay').onclick = (e) => {
    if (e.target.id === 'popup-overlay') closePopupModal();
  };

  modalRoot.querySelector('#zv-add-inv-btn').onclick = () => {
    const curInv = getInventory();
    curInv[item.id] = (curInv[item.id] || 0) + 1;
    saveInventory(curInv);
    openPopupModal(item);
  };

  modalRoot.querySelector('#zv-add-wl-btn').onclick = () => {
    let curWl = getWishlist();
    if (curWl.includes(item.id)) {
      curWl = curWl.filter(id => id !== item.id);
    } else {
      curWl.push(item.id);
    }
    saveWishlist(curWl);
    openPopupModal(item);
  };
}

function closePopupModal() {
  const modalRoot = document.getElementById('zv-modal-root');
  if (modalRoot) modalRoot.innerHTML = '';
}

function buildSvgPath(prices) {
  if (!prices || prices.length < 2) return "M 0 40 L 300 40";
  const min = Math.min(...prices);
  const max = Math.max(...prices);
  const range = max - min || 1;
  const width = 280;
  const height = 60;

  return prices.map((p, idx) => {
    const x = 10 + (idx / (prices.length - 1)) * width;
    const y = 70 - ((p - min) / range) * height;
    return `${idx === 0 ? 'M' : 'L'} ${x} ${y}`;
  }).join(' ');
}

function renderItemCardHtml(item) {
  return `
    <div class="item-card" data-id="${item.id}" style="background: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 16px; transition: transform 0.2s;">
      <h3 style="margin: 0 0 6px 0; color: #fff; font-size: 16px;">${item.name}</h3>
      <div style="font-size: 12px; color: #aaa; margin-bottom: 10px;">${item.category || 'Cosmetic'}</div>
      <div style="font-size: 14px; font-weight: bold; color: #5EF2B6;">${(item.value || 0).toLocaleString()} coins</div>
    </div>
  `;
}

function bindCardClickEvents(container) {
  const cards = container.querySelectorAll('.item-card');
  cards.forEach(card => {
    card.style.cursor = 'pointer';
    card.onclick = (e) => {
      if (e.target.closest('.zv-btn-plus') || e.target.closest('.zv-btn-minus') || e.target.closest('.zv-wishlist-remove-btn')) return;
      const id = card.dataset.id;
      const found = cosmeticsData.find(i => String(i.id) === String(id));
      if (found) openPopupModal(found);
    };
  });
}

// Global ESC key event
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') closePopupModal();
});

// Application Entry Point
async function init() {
  await loadData();
  renderApp();
}

init();
