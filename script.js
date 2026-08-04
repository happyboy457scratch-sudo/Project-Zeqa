async function loadTradeData() {
  const container = document.getElementById('trades-container');
  const statusLabel = document.getElementById('last-updated');

  try {
    // Fetch trades.json with timestamp to prevent browser caching
    const response = await fetch('./data/trades.json?t=' + Date.now());
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const rawTrades = await response.json();

    container.innerHTML = '';

    // Filter out entries without valid item names
    const trades = Array.isArray(rawTrades) 
      ? rawTrades.filter(t => t.item && t.item.trim() !== '' && t.item.trim() !== '—' && t.item.trim() !== '-')
      : [];

    if (trades.length === 0) {
      container.innerHTML = '<div class="empty-state">No single-item trades recorded yet.</div>';
      if (statusLabel) statusLabel.textContent = 'Updated (No valid records found)';
      return;
    }

    const grid = document.createElement('div');
    grid.className = 'grid';

    trades.forEach(trade => {
      const card = document.createElement('div');
      card.className = 'trade-card';

      // Parse unit shard value or fallback to total division
      const shardDisplay = computeUnitShards(trade);
      const qtyBadge = trade.quantity && trade.quantity > 1 ? ` (x${trade.quantity})` : '';

      card.innerHTML = `
        <div class="item-title">${escapeHtml(trade.item)}${escapeHtml(qtyBadge)}</div>
        <div class="shard-amount">Shards: <strong>${escapeHtml(shardDisplay)}</strong></div>
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
    if (statusLabel) {
      statusLabel.textContent = 'Error loading trades. Ensure data/trades.json exists.';
    }
  }
}

// Client-side fallback to calculate per-unit shard price for existing entries
function computeUnitShards(trade) {
  if (trade.shards && trade.shards !== 'N/A') {
    return trade.shards;
  }

  const raw = trade.raw_trade || '';
  const matchShard = raw.match(/\b(\d+(?:\.\d+)?)(k)?\b/i);
  if (!matchShard) return 'N/A';

  let totalVal = parseFloat(matchShard[1]);
  if (matchShard[2]) totalVal *= 1000;

  const matchQty = raw.match(/(?:x\s*(\d+)|(\d+)\s*x)/i);
  const qty = matchQty ? parseInt(matchQty[1] || matchQty[2], 10) : 1;

  const unitVal = totalVal / qty;
  if (unitVal >= 1000) {
    const kVal = unitVal / 1000;
    return kVal % 1 === 0 ? `${kVal}k` : `${kVal.toFixed(1)}k`;
  }
  return String(Math.round(unitVal));
}

// Sanitize strings
function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// Auto load on page ready & refresh every 30s
document.addEventListener('DOMContentLoaded', loadTradeData);
setInterval(loadTradeData, 30000);
