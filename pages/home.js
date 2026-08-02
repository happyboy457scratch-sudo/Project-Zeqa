/**
 * ZeqaValues - Home Dashboard Controller
 * Displays market capitalization metrics, top gainers/popular items, and fast search.
 */

import { statCard } from '../components/statCard.js';
import { itemCard } from '../components/itemCard.js';
import { Popup } from '../components/popup.js';

export class HomePage {
  constructor(cosmeticsData = [], router = null) {
    this.data = cosmeticsData;
    this.router = router;
  }

  render() {
    const totalVal = this.data.reduce((acc, i) => acc + (i.value || 0), 0);
    const topValued = [...this.data].sort((a, b) => (b.value || 0) - (a.value || 0))[0];
    const topTraded = [...this.data].sort((a, b) => (b.salesExistingRatio || 0) - (a.salesExistingRatio || 0))[0];

    return `
      <div style="max-width: 1200px; margin: 0 auto; padding: 24px;">
        <div style="text-align: center; margin-bottom: 32px;">
          <h1 style="font-size: 32px; font-weight: 800; color: #ffffff; margin-bottom: 8px;">
            Mineville <span style="color: #5EF2B6;">ZeqaValues</span> Analytics
          </h1>
          <p style="color: #aaaaaa; font-size: 15px; margin: 0;">Real-time trade evaluations, historical graphs, and cosmetic market insights.</p>
        </div>

        <div class="stat-grid">
          ${statCard('Total Cosmetics Index', this.data.length)}
          ${statCard('Highest Value Item', topValued ? topValued.name : 'N/A')}
          ${statCard('Most Traded Cosmetic', topTraded ? topTraded.name : 'N/A')}
          ${statCard('Market Cap', totalVal.toLocaleString() + ' coins')}
        </div>

        <div style="margin-top: 36px; background: #14181f; border: 1px solid #282e38; border-radius: 14px; padding: 20px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 16px;">
          <div>
            <h3 style="margin: 0 0 4px 0; color: #ffffff;">Explore the Full Valuation Directory</h3>
            <p style="margin: 0; color: #aaaaaa; font-size: 13px;">Filter through Capes, Hats, Trails, Auras, and Wings using 9 distinct sorting engines.</p>
          </div>
          <button id="zv-launch-value" style="background: #5EF2B6; border: none; color: #111111; padding: 12px 24px; border-radius: 8px; font-weight: 700; cursor: pointer;">
            Open Value Page →
          </button>
        </div>

        <h2 style="margin-top: 40px; color: #ffffff; font-size: 20px; letter-spacing: -0.5px;">Featured Market Items</h2>
        <div id="home-featured-grid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 18px; margin-top: 16px;">
          ${this.data.slice(0, 8).map(item => itemCard(item)).join('')}
        </div>
      </div>
    `;
  }

  bindEvents(container) {
    const root = container || document;
    
    // Directory CTA
    const btn = root.querySelector('#zv-launch-value');
    if (btn && this.router) {
      btn.onclick = () => this.router.navigate('value');
    }

    // Modal inspection popup binding
    root.querySelectorAll('#home-featured-grid .item-card').forEach(card => {
      card.style.cursor = 'pointer';
      card.onclick = () => {
        const id = card.dataset.id;
        const name = card.querySelector('h3')?.textContent;
        const found = this.data.find(i => String(i.id) === String(id) || i.name === name);
        if (found) Popup.open(found);
      };
    });
  }
}
