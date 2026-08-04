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

    // Clear loading state
    container.innerHTML = '';

    // Filter out any entries missing item names or showing placeholders like '—'
    const trades = Array.isArray(rawTrades) 
      ? rawTrades.filter(t => t.item && t.item.trim() !== '' && t.item.trim() !== '—' && t.item.trim() !== '-')
      : [];

    if (trades.length === 0) {
      container.innerHTML = '<div class="empty-state">No single-item trades recorded yet.</div>';
      if (statusLabel) statusLabel.textContent = 'Updated (No valid records found)';
      return;
    }

    // Build grid container
    const grid = document.createElement('div');
    grid.className = 'grid';

    // Render cards
    trades.forEach(trade => {
      const card = document.createElement('div');
      card.className = 'trade-card';

      card.innerHTML = `
        <div class="item-title">${escapeHtml(trade.item)}</div>
        <div class="shard-amount">Shards: <strong>${escapeHtml(trade.shards || 'N/A')}</strong></div>
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

// Sanitize strings
function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// Auto load and interval refresh
document.addEventListener('DOMContentLoaded', loadTradeData);
setInterval(loadTradeData, 30000);
