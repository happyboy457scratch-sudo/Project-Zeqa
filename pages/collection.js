/**
 * ZeqaValues - Collection & Wishlist Directory Controller
 * Handles user portfolio calculation, local inventory quantities, and wishlist tracking.
 */

import { Popup } from '../components/popup.js';

export class CollectionPage {
  constructor(cosmeticsData = []) {
    this.data = cosmeticsData;
    this.activeTab = 'inventory'; // 'inventory' or 'wishlist'
  }

  /**
   * Retrieves owned inventory map from localStorage: { [itemId]: quantity }
   */
  getInventory() {
    try {
      return JSON.parse(localStorage.getItem('zv_user_inventory')) || {};
    } catch {
      return {};
    }
  }

  /**
   * Saves updated inventory map.
   */
  saveInventory(inv) {
    localStorage.setItem('zv_user_inventory', JSON.stringify(inv));
  }

  /**
   * Retrieves wishlist item IDs array from localStorage.
   */
  getWishlist() {
    try {
      return JSON.parse(localStorage.getItem('zv_user_wishlist')) || [];
    } catch {
      return [];
    }
  }

  /**
   * Saves updated wishlist array.
   */
  saveWishlist(wl) {
    localStorage.setItem('zv_user_wishlist', JSON.stringify(wl));
  }

  /**
   * Renders the complete Collection view.
   * @returns {string} HTML string
   */
  render() {
    const inv = this.getInventory();
    const wl = this.getWishlist();

    // Calculate metrics
    let totalNetWorth = 0;
    let totalItemCount = 0;

    Object.entries(inv).forEach(([id, qty]) => {
      const item = this.data.find(i => String(i.id) === String(id));
      if (item) {
        totalNetWorth += (item.value || 0) * qty;
        totalItemCount += qty;
      }
    });

    return `
      <div class="zv-collection-container">
        <div class="zv-collection-header">
          <h1 class="zv-collection-title">Cosmetic Portfolio</h1>
          <p class="zv-collection-subtitle">Track owned inventory value, quantities, and desired wishlist items.</p>
        </div>

        <div class="zv-portfolio-summary">
          <div class="zv-stat-card">
            <div class="zv-stat-label">Total Portfolio Net Worth</div>
            <div class="zv-stat-val mint">${totalNetWorth.toLocaleString()} coins</div>
          </div>
          <div class="zv-stat-card">
            <div class="zv-stat-label">Total Cosmetics Owned</div>
            <div class="zv-stat-val">${totalItemCount} items</div>
          </div>
          <div class="zv-stat-card">
            <div class="zv-stat-label">Wishlist Items</div>
            <div class="zv-stat-val">${wl.length} items</div>
          </div>
        </div>

        <div class="zv-collection-tabs">
          <button class="zv-tab-link ${this.activeTab === 'inventory' ? 'active' : ''}" id="zv-tab-inv">
            My Inventory (${Object.keys(inv).length})
          </button>
          <button class="zv-tab-link ${this.activeTab === 'wishlist' ? 'active' : ''}" id="zv-tab-wl">
            Wishlist (${wl.length})
          </button>
        </div>

        <div class="zv-inventory-grid" id="zv-collection-grid">
          ${this.activeTab === 'inventory' ? this.renderInventoryGrid(inv) : this.renderWishlistGrid(wl)}
        </div>
      </div>
    `;
  }

  /**
   * Renders owned inventory items with quantity controls.
   */
  renderInventoryGrid(inv) {
    const entries = Object.entries(inv).filter(([_, qty]) => qty > 0);

    if (entries.length === 0) {
      return `
        <div class="zv-collection-empty" style="grid-column: 1 / -1;">
          <h3>No Cosmetics in Inventory</h3>
          <p>Inspect items in the Value Directory and click "Add to Collection" to start building your portfolio.</p>
        </div>
      `;
    }

    return entries.map(([id, qty]) => {
      const item = this.data.find(i => String(i.id) === String(id));
      if (!item) return '';

      const totalVal = (item.value || 0) * qty;

      return `
        <div class="zv-inventory-card" data-id="${item.id}">
          <div class="zv-card-top">
            <div class="zv-card-name">${item.name}</div>
            <div class="zv-card-meta">
              <span>${item.category || 'Cosmetic'}</span>
              <span>${item.rarity || 'Common'}</span>
            </div>
            <div class="zv-card-price">${totalVal.toLocaleString()} coins</div>
          </div>
          <div class="zv-qty-controls">
            <button class="zv-qty-btn zv-btn-minus" data-id="${item.id}">-</button>
            <span class="zv-qty-display">Qty: ${qty}</span>
            <button class="zv-qty-btn zv-btn-plus" data-id="${item.id}">+</button>
          </div>
        </div>
      `;
    }).join('');
  }

  /**
   * Renders saved wishlist items.
   */
  renderWishlistGrid(wl) {
    if (wl.length === 0) {
      return `
        <div class="zv-collection-empty" style="grid-column: 1 / -1;">
          <h3>Your Wishlist is Empty</h3>
          <p>Save items you are actively hunting for quick access and price tracking.</p>
        </div>
      `;
    }

    return wl.map(id => {
      const item = this.data.find(i => String(i.id) === String(id));
      if (!item) return '';

      return `
        <div class="zv-inventory-card" data-id="${item.id}">
          <div class="zv-card-top">
            <div class="zv-card-name">${item.name}</div>
            <div class="zv-card-meta">
              <span>${item.category || 'Cosmetic'}</span>
              <span>${item.rarity || 'Common'}</span>
            </div>
            <div class="zv-card-price">${(item.value || 0).toLocaleString()} coins</div>
          </div>
          <button class="zv-wishlist-remove-btn" data-id="${item.id}">Remove from Wishlist</button>
        </div>
      `;
    }).join('');
  }

  /**
   * Binds click and state updating events.
   */
  bindEvents(container) {
    const root = container || document;

    // Tab buttons
    const tabInv = root.querySelector('#zv-tab-inv');
    const tabWl = root.querySelector('#zv-tab-wl');

    if (tabInv) {
      tabInv.onclick = () => {
        this.activeTab = 'inventory';
        this.reRender(container);
      };
    }

    if (tabWl) {
      tabWl.onclick = () => {
        this.activeTab = 'wishlist';
        this.reRender(container);
      };
    }

    // Quantity Increment / Decrement
    root.querySelectorAll('.zv-btn-plus').forEach(btn => {
      btn.onclick = (e) => {
        e.stopPropagation();
        const id = btn.dataset.id;
        const inv = this.getInventory();
        inv[id] = (inv[id] || 0) + 1;
        this.saveInventory(inv);
        this.reRender(container);
      };
    });

    root.querySelectorAll('.zv-btn-minus').forEach(btn => {
      btn.onclick = (e) => {
        e.stopPropagation();
        const id = btn.dataset.id;
        const inv = this.getInventory();
        if (inv[id] > 1) {
          inv[id] -= 1;
        } else {
          delete inv[id];
        }
        this.saveInventory(inv);
        this.reRender(container);
      };
    });

    // Wishlist Remove
    root.querySelectorAll('.zv-wishlist-remove-btn').forEach(btn => {
      btn.onclick = (e) => {
        e.stopPropagation();
        const id = btn.dataset.id;
        let wl = this.getWishlist();
        wl = wl.filter(itemVal => String(itemVal) !== String(id));
        this.saveWishlist(wl);
        this.reRender(container);
      };
    });

    // Inspection Modal Card Clicks
    root.querySelectorAll('.zv-inventory-card').forEach(card => {
      card.style.cursor = 'pointer';
      card.onclick = (e) => {
        if (e.target.closest('.zv-qty-controls') || e.target.closest('.zv-wishlist-remove-btn')) return;
        const id = card.dataset.id;
        const found = this.data.find(i => String(i.id) === String(id));
        if (found) {
          Popup.open(found);
        }
      };
    });
  }

  /**
   * Re-renders the component.
   */
  reRender(container) {
    if (!container) return;
    container.innerHTML = this.render();
    this.bindEvents(container);
  }
}
