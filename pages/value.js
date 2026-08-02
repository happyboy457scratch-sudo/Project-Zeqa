/**
 * ZeqaValues - Value Page Directory Controller
 * Multi-criteria sorting engine, instant string filtering, and dynamic item rendering.
 */

import { itemCard } from '../components/itemCard.js';
import { Popup } from '../components/popup.js';

export class ValuePage {
  constructor(cosmeticsData = []) {
    this.data = cosmeticsData;
    this.currentCategory = 'All';
    this.searchQuery = '';
    this.currentSort = 'value-desc';
  }

  /**
   * Renders the complete page template and initializes handlers.
   * @returns {string} HTML string
   */
  render() {
    return `
      <div class="zv-value-container">
        <div class="zv-value-header">
          <h1 class="zv-value-title">Cosmetics Directory</h1>
          <p class="zv-value-subtitle">Explore, filter, and analyze Mineville PvP item valuations in real-time.</p>
        </div>

        <div class="zv-controls-bar">
          <div class="zv-controls-top">
            <div class="zv-search-box">
              <input type="text" id="zv-search-field" placeholder="Search by cosmetic name..." value="${this.searchQuery}">
            </div>
            <select class="zv-sort-select" id="zv-sort-field">
              <option value="value-desc" ${this.currentSort === 'value-desc' ? 'selected' : ''}>Highest Value</option>
              <option value="value-asc" ${this.currentSort === 'value-asc' ? 'selected' : ''}>Lowest Value</option>
              <option value="demand-desc" ${this.currentSort === 'demand-desc' ? 'selected' : ''}>Highest Demand</option>
              <option value="demand-asc" ${this.currentSort === 'demand-asc' ? 'selected' : ''}>Lowest Demand</option>
              <option value="traded-desc" ${this.currentSort === 'traded-desc' ? 'selected' : ''}>Most Traded</option>
              <option value="traded-asc" ${this.currentSort === 'traded-asc' ? 'selected' : ''}>Least Traded</option>
              <option value="name-asc" ${this.currentSort === 'name-asc' ? 'selected' : ''}>Alphabetical (A-Z)</option>
              <option value="name-desc" ${this.currentSort === 'name-desc' ? 'selected' : ''}>Alphabetical (Z-A)</option>
              <option value="newest" ${this.currentSort === 'newest' ? 'selected' : ''}>Newest</option>
              <option value="oldest" ${this.currentSort === 'oldest' ? 'selected' : ''}>Oldest</option>
            </select>
          </div>

          <div class="zv-categories-wrap" id="zv-category-pills">
            ${this.renderCategories()}
          </div>
        </div>

        <div class="zv-catalog-grid" id="zv-catalog-grid">
          ${this.renderGridItems()}
        </div>
      </div>
    `;
  }

  /**
   * Generates category filter pill elements.
   */
  renderCategories() {
    const categories = ['All', 'Capes', 'Hats', 'Trails', 'Auras', 'Wings'];
    return categories.map(cat => `
      <button class="zv-category-pill ${this.currentCategory === cat ? 'active' : ''}" data-category="${cat}">
        ${cat}
      </button>
    `).join('');
  }

  /**
   * Filters and sorts the dataset, returning formatted item cards or empty state.
   */
  renderGridItems() {
    let filtered = [...this.data];

    // Filter by Search Query
    if (this.searchQuery.trim() !== '') {
      const q = this.searchQuery.toLowerCase();
      filtered = filtered.filter(item => item.name.toLowerCase().includes(q));
    }

    // Filter by Category
    if (this.currentCategory !== 'All') {
      filtered = filtered.filter(item => (item.category || '').toLowerCase() === this.currentCategory.toLowerCase());
    }

    // Sort Algorithms
    filtered.sort((a, b) => {
      switch (this.currentSort) {
        case 'value-desc':
          return (b.value || 0) - (a.value || 0);
        case 'value-asc':
          return (a.value || 0) - (b.value || 0);
        case 'demand-desc':
          return (b.demand || 0) - (a.demand || 0);
        case 'demand-asc':
          return (a.demand || 0) - (b.demand || 0);
        case 'traded-desc':
          return (b.salesExistingRatio || 0) - (a.salesExistingRatio || 0);
        case 'traded-asc':
          return (a.salesExistingRatio || 0) - (b.salesExistingRatio || 0);
        case 'name-asc':
          return a.name.localeCompare(b.name);
        case 'name-desc':
          return b.name.localeCompare(a.name);
        case 'newest':
          return (b.id || 0) - (a.id || 0);
        case 'oldest':
          return (a.id || 0) - (b.id || 0);
        default:
          return 0;
      }
    });

    if (filtered.length === 0) {
      return `
        <div class="zv-empty-state">
          <div class="zv-empty-state-title">No Cosmetics Found</div>
          <div>Try adjusting your search query or selecting a different category filter.</div>
        </div>
      `;
    }

    return filtered.map(item => itemCard(item)).join('');
  }

  /**
   * Binds interactive listeners after HTML injection.
   * @param {HTMLElement} containerElement 
   */
  bindEvents(containerElement) {
    const searchInput = containerElement.querySelector('#zv-search-field');
    const sortSelect = containerElement.querySelector('#zv-sort-field');
    const pillsWrap = containerElement.querySelector('#zv-category-pills');
    const gridContainer = containerElement.querySelector('#zv-catalog-grid');

    // Search Input Handler
    if (searchInput) {
      searchInput.oninput = (e) => {
        this.searchQuery = e.target.value;
        this.updateGrid(gridContainer);
      };
    }

    // Sort Dropdown Handler
    if (sortSelect) {
      sortSelect.onchange = (e) => {
        this.currentSort = e.target.value;
        this.updateGrid(gridContainer);
      };
    }

    // Category Pill Buttons Handler
    if (pillsWrap) {
      pillsWrap.onclick = (e) => {
        const btn = e.target.closest('.zv-category-pill');
        if (!btn) return;

        this.currentCategory = btn.dataset.category;
        
        // Update active class state on pills
        pillsWrap.querySelectorAll('.zv-category-pill').forEach(p => p.classList.remove('active'));
        btn.classList.add('active');

        this.updateGrid(gridContainer);
      };
    }

    this.bindCardClicks(gridContainer);
  }

  /**
   * Re-renders only the item grid without destroying filter UI inputs.
   */
  updateGrid(gridContainer) {
    if (!gridContainer) return;
    gridContainer.innerHTML = this.renderGridItems();
    this.bindCardClicks(gridContainer);
  }

  /**
   * Connects item card clicks directly to the Popup Inspection Engine (Part 6).
   */
  bindCardClicks(gridContainer) {
    const cards = gridContainer.querySelectorAll('.item-card');
    cards.forEach(card => {
      card.style.cursor = 'pointer';
      card.onclick = () => {
        const itemId = card.dataset.id || card.getAttribute('data-id');
        const found = this.data.find(i => String(i.id) === String(itemId) || i.name === card.querySelector('h3')?.textContent);
        if (found) {
          Popup.open(found);
        }
      };
    });
  }
}
