/**
 * ZeqaValues - Compare Page Directory Controller
 * Interactive 2-sided trade evaluation board with dynamic item additions, removals, and outcome state calculations.
 */

import { compare } from '../js/compareEngine.js';
import { Popup } from '../components/popup.js';

export class ComparePage {
  constructor(cosmeticsData = []) {
    this.data = cosmeticsData;
    this.leftItems = cosmeticsData.length > 0 ? [cosmeticsData[0]] : [];
    this.rightItems = cosmeticsData.length > 1 ? [cosmeticsData[1]] : [];
    this.activeSide = 'left'; // 'left' or 'right'
  }

  /**
   * Renders the complete Compare view.
   * @returns {string} HTML string
   */
  render() {
    const result = compare(this.leftItems, this.rightItems);
    
    return `
      <div class="zv-compare-container">
        <div class="zv-compare-header">
          <h1 class="zv-compare-title">Trade Comparison Engine</h1>
          <p class="zv-compare-subtitle">Add cosmetics to both sides to compute trade fairness and valuation differences.</p>
        </div>

        <div class="zv-outcome-banner">
          ${this.renderOutcomeBadge(result)}
          <div class="zv-outcome-diff">
            Difference: <span>${Math.abs(result.difference).toLocaleString()} coins</span> 
            (${result.percentageDifference}% variation)
          </div>
        </div>

        <div class="zv-compare-grid">
          <div class="zv-trade-box" id="zv-box-left">
            <div class="zv-trade-box-header">
              <h3 class="zv-player-name">happyboy457's Offer</h3>
              <button class="zv-box-clear-btn" id="zv-clear-left">Clear</button>
            </div>
            <div class="zv-slots-list" id="zv-slots-left">
              ${this.renderSlots(this.leftItems, 'left')}
            </div>
            <button class="zv-add-slot-btn" id="zv-add-left">+ Add Cosmetic</button>
            <div class="zv-trade-box-footer">
              <span class="zv-total-label">Total Value</span>
              <span class="zv-total-value">${result.leftTotal.toLocaleString()} coins</span>
            </div>
          </div>

          <div class="zv-trade-box" id="zv-box-right">
            <div class="zv-trade-box-header">
              <h3 class="zv-player-name">Trader's Offer</h3>
              <button class="zv-box-clear-btn" id="zv-clear-right">Clear</button>
            </div>
            <div class="zv-slots-list" id="zv-slots-right">
              ${this.renderSlots(this.rightItems, 'right')}
            </div>
            <button class="zv-add-slot-btn" id="zv-add-right">+ Add Cosmetic</button>
            <div class="zv-trade-box-footer">
              <span class="zv-total-label">Total Value</span>
              <span class="zv-total-value">${result.rightTotal.toLocaleString()} coins</span>
            </div>
          </div>
        </div>
      </div>

      <div class="zv-picker-overlay" id="zv-picker-overlay">
        <div class="zv-picker-modal">
          <div class="zv-picker-header">
            <h3 class="zv-picker-title">Select Cosmetic to Add</h3>
            <button class="zv-box-clear-btn" id="zv-close-picker">X</button>
          </div>
          <input type="text" class="zv-picker-search" id="zv-picker-search" placeholder="Type to search cosmetics...">
          <div class="zv-picker-list" id="zv-picker-list">
            ${this.renderPickerItems('')}
          </div>
        </div>
      </div>
    `;
  }

  /**
   * Formats outcome status pill.
   */
  renderOutcomeBadge(result) {
    let badgeClass = 'fair';
    let label = 'Fair Trade';

    if (result.outcome === 'Win for Left') {
      badgeClass = 'win';
      label = 'Win for happyboy457';
    } else if (result.outcome === 'Win for Right') {
      badgeClass = 'loss';
      label = 'Win for Trader';
    }

    return `<div class="zv-outcome-badge ${badgeClass}">${label}</div>`;
  }

  /**
   * Renders trade slot items for a given player side.
   */
  renderSlots(items, side) {
    if (items.length === 0) {
      return `<div style="text-align:center; color:#666666; padding-top:80px; font-size:13px;">No items added yet.</div>`;
    }

    return items.map((item, index) => `
      <div class="zv-slot-item">
        <div class="zv-slot-item-info">
          <div>
            <div class="zv-slot-item-name">${item.name}</div>
            <div class="zv-slot-item-val">${(item.value || 0).toLocaleString()} coins</div>
          </div>
        </div>
        <button class="zv-slot-remove-btn" data-side="${side}" data-index="${index}">✕</button>
      </div>
    `).join('');
  }

  /**
   * Renders item list inside selector modal.
   */
  renderPickerItems(query) {
    const q = query.toLowerCase().trim();
    const filtered = this.data.filter(i => i.name.toLowerCase().includes(q));

    if (filtered.length === 0) {
      return `<div style="text-align:center; color:#888; padding:20px;">No matching cosmetics found.</div>`;
    }

    return filtered.map(i => `
      <div class="zv-picker-item" data-id="${i.id}">
        <span style="font-weight:600; color:#fff;">${i.name}</span>
        <span style="color:#5EF2B6; font-weight:700;">${(i.value || 0).toLocaleString()} coins</span>
      </div>
    `).join('');
  }

  /**
   * Binds interactive click and keyboard events.
   * @param {HTMLElement} container 
   */
  bindEvents(container) {
    const root = container || document;

    // Add buttons
    const addLeft = root.querySelector('#zv-add-left');
    const addRight = root.querySelector('#zv-add-right');
    const pickerOverlay = root.querySelector('#zv-picker-overlay');
    const closePicker = root.querySelector('#zv-close-picker');
    const pickerSearch = root.querySelector('#zv-picker-search');
    const pickerList = root.querySelector('#zv-picker-list');

    if (addLeft) {
      addLeft.onclick = () => {
        this.activeSide = 'left';
        pickerOverlay.classList.add('active');
      };
    }

    if (addRight) {
      addRight.onclick = () => {
        this.activeSide = 'right';
        pickerOverlay.classList.add('active');
      };
    }

    if (closePicker) {
      closePicker.onclick = () => pickerOverlay.classList.remove('active');
    }

    // Search inside picker
    if (pickerSearch && pickerList) {
      pickerSearch.oninput = (e) => {
        pickerList.innerHTML = this.renderPickerItems(e.target.value);
        this.bindPickerSelect(pickerList, pickerOverlay, container);
      };
    }

    this.bindPickerSelect(pickerList, pickerOverlay, container);

    // Clear Buttons
    const clearLeft = root.querySelector('#zv-clear-left');
    const clearRight = root.querySelector('#zv-clear-right');

    if (clearLeft) {
      clearLeft.onclick = () => {
        this.leftItems = [];
        this.reRender(container);
      };
    }

    if (clearRight) {
      clearRight.onclick = () => {
        this.rightItems = [];
        this.reRender(container);
      };
    }

    // Item Removal Buttons
    root.querySelectorAll('.zv-slot-remove-btn').forEach(btn => {
      btn.onclick = (e) => {
        const side = e.target.dataset.side;
        const idx = parseInt(e.target.dataset.index, 10);
        if (side === 'left') {
          this.leftItems.splice(idx, 1);
        } else {
          this.rightItems.splice(idx, 1);
        }
        this.reRender(container);
      };
    });
  }

  /**
   * Binds selection inside item picker modal.
   */
  bindPickerSelect(pickerList, pickerOverlay, container) {
    if (!pickerList) return;
    pickerList.querySelectorAll('.zv-picker-item').forEach(itemEl => {
      itemEl.onclick = () => {
        const id = itemEl.dataset.id;
        const selected = this.data.find(i => String(i.id) === String(id));
        if (selected) {
          if (this.activeSide === 'left') {
            this.leftItems.push(selected);
          } else {
            this.rightItems.push(selected);
          }
          pickerOverlay.classList.remove('active');
          this.reRender(container);
        }
      };
    });
  }

  /**
   * Re-renders the component and re-binds listeners.
   */
  reRender(container) {
    if (!container) return;
    container.innerHTML = this.render();
    this.bindEvents(container);
  }
}
