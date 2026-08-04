async function loadTradeData() {
  const container = document.getElementById('trades-container');
  const statusLabel = document.getElementById('last-updated');

  try {
    // Fetch trades.json with timestamp to prevent caching
    const response = await fetch('./data/trades.json?t=' + Date.now());
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const trades = await response.json();

    // Clear loading state
    container.innerHTML = '';

    if (!Array.isArray(trades) || trades.length === 0) {
      container.innerHTML = '<div class="empty-state">No single-item trades recorded yet.</div>';
      if (statusLabel) statusLabel.textContent = 'Updated (No records found)';
      return;
    }

    // Build container grid
    const grid = document.createElement('div');
    grid.className = 'grid';

    // Render each trade card
    trades.forEach(trade => {
      const card = document.createElement('div');
      card.className = 'trade-card';

      card.innerHTML = `
        <div class="item-title">${escapeHtml(trade.item || 'Unknown Item')}</div>
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

// Sanitize output strings
function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// Automatically run on load and repeat every 30 seconds
document.addEventListener('DOMContentLoaded', loadTradeData);
setInterval(loadTradeData, 30000);
