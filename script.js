/**
 * ZeqaValues - Live Trade Tracker & Shard Value Integration Bridge
 */

let cosmeticsList = [];

// Clean up strings for lower-case matching
function cleanString(str) {
  return str ? str.toLowerCase().replace(/[^a-z0-9]/g, '') : '';
}

// 1. Fetch Cosmetics/Value Database
async function loadCosmeticsData() {
  try {
    // Relative path safe for sub-directory deployments
    const res = await fetch('data/cosmetics.json?t=' + Date.now());
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    cosmeticsList = await res.json();
    console.log(`Loaded ${cosmeticsList.length} cosmetic reference values.`);
  } catch (err) {
    console.warn('Could not fetch cosmetics.json for shard matching:', err);
  }
}

// Helper: Match traded item string to cosmetics database using fuzzy search
function findMatchingCosmetic(tradeItemName) {
  if (!tradeItemName || cosmeticsList.length === 0) return null;

  const cleanedTradeName = cleanString(tradeItemName);

  // 1. Try exact normalized match first
  let match = cosmeticsList.find(c => cleanString(c.name) === cleanedTradeName);
  if (match) return match;

  // 2. Try substring matching (e.g. if scraped title contains "Sweet Headband")
  // Sort by name length descending so longer/more specific names match first
  const sortedCosmetics = [...cosmeticsList].sort((a, b) => b.name.length - a.name.length);
  
  match = sortedCosmetics.find(c => {
    const cleanedCosmeticName = cleanString(c.name);
    return cleanedCosmeticName.length > 2 && cleanedTradeName.includes(cleanedCosmeticName);
  });

  return match || null;
}

// 2. Load Trades and Calculate Shard Difference
async function loadTradeData() {
  const container = document.getElementById('trades-container');
  const statusLabel = document.getElementById('last-updated');

  try {
    const response = await fetch('data/trades.json?t=' + Date.now());
    if (!response.ok) throw new Error(`HTTP status: ${response.status}`);

    const rawTrades = await response.json();
    if (!container) return;
    container.innerHTML = '';

    const trades = Array.isArray(rawTrades) 
      ? rawTrades.filter(t => t.item && t.item.trim() !== '' && !t.item.startsWith('—'))
      : [];

    if (trades.length === 0) {
      container.innerHTML = '<div class="empty-state">No trades recorded yet.</div>';
      if (statusLabel) statusLabel.textContent = 'Updated (No valid records)';
      return;
    }

    const grid = document.createElement('div');
    grid.className = 'grid';

    trades.forEach(trade => {
      const card = document.createElement('div');
      card.className = 'trade-card';

      const qty = trade.quantity || 1;
      const qtyBadge = qty > 1 ? ` (x${qty})` : '';

      // Match item with cosmetic shard value database
      const matchedItem = findMatchingCosmetic(trade.item);
      const shardValPerUnit = matchedItem ? (matchedItem.value || matchedItem.shards || 0) : 0;
      const totalEstimatedShards = shardValPerUnit * qty;
      const shardsPaid = parseInt(trade.shards, 10) || 0;

      // Calculate Shard Profit / Loss
      let evalBadgeHtml = '';
      if (matchedItem && shardValPerUnit > 0 && shardsPaid > 0) {
        const shardDiff = totalEstimatedShards - shardsPaid;
        const pctDiff = Math.abs(shardDiff) / Math.max(shardsPaid, 1);

        if (pctDiff <= 0.05) {
          evalBadgeHtml = `<span style="background: rgba(39, 174, 96, 0.2); color: #27ae60; border: 1px solid #27ae60; padding: 2px 8px; border-radius: 6px; font-size: 11px; font-weight: 700;">Fair Trade</span>`;
        } else if (shardDiff > 0) {
          evalBadgeHtml = `<span style="background: rgba(94, 242, 186, 0.2); color: #5EF2B6; border: 1px solid #5EF2B6; padding: 2px 8px; border-radius: 6px; font-size: 11px; font-weight: 700;">+${shardDiff.toLocaleString()} Shards</span>`;
        } else {
          evalBadgeHtml = `<span style="background: rgba(231, 76, 60, 0.2); color: #e74c3c; border: 1px solid #e74c3c; padding: 2px 8px; border-radius: 6px; font-size: 11px; font-weight: 700;">${shardDiff.toLocaleString()} Shards</span>`;
        }
      }

      const valDisplay = matchedItem && shardValPerUnit > 0 
        ? `<div style="font-size: 0.85rem; color: #5EF2B6; margin-bottom: 6px;">
             Item Value: <strong>${totalEstimatedShards.toLocaleString()} shards</strong> ${qty > 1 ? `(${shardValPerUnit.toLocaleString()}/ea)` : ''}
           </div>`
        : `<div style="font-size: 0.85rem; color: #64748b; margin-bottom: 6px;">Item Value: Unlisted</div>`;

      card.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 6px;">
          <div class="item-title" style="margin: 0;">${escapeHtml(trade.item)}${escapeHtml(qtyBadge)}</div>
          ${evalBadgeHtml}
        </div>
        ${valDisplay}
        <div class="shard-amount">Shards Paid: <strong>${escapeHtml(trade.shards || 'N/A')}</strong></div>
        <div class="raw-text">${escapeHtml(trade.raw_trade || '')}</div>
      `;

      grid.appendChild(card);
    });

    container.appendChild(grid);
    if (statusLabel) {
      statusLabel.textContent = `Loaded ${trades.length} trade(s) at ${new Date().toLocaleTimeString()}`;
    }

  } catch (error) {
    console.error('Error fetching trade data:', error);
    if (statusLabel) statusLabel.textContent = 'Error loading trades.';
  }
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

document.addEventListener('DOMContentLoaded', async () => {
  await loadCosmeticsData();
  await loadTradeData();
});

setInterval(loadTradeData, 30000);
