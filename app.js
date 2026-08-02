/**
 * ZeqaValues - Main Application Entry Point & SPA Router
 * Coordinates page navigation, authentication state, data loading, and component popups.
 */

import { navbar } from './components/navbar.js';
import { login } from './components/login.js';
import { itemCard } from './components/itemCard.js';
import { statCard } from './components/statCard.js';
import { Popup } from './components/popup.js';
import { ValuePage } from './pages/value.js';
import { compare } from './js/compareEngine.js';
import { loadCollection, saveCollection } from './js/storage.js';

// Application State
let cosmeticsData = [];
let currentPage = localStorage.getItem('lastPage') || 'home';

const app = document.getElementById('app');

/**
 * Fetches cosmetics data payload.
 */
async function loadData() {
  try {
    const response = await fetch('./data/cosmetics.json');
    if (!response.ok) throw new Error('Network response was not ok');
    cosmeticsData = await response.json();
  } catch (error) {
    console.error('Failed to load cosmetics dataset:', error);
    cosmeticsData = [];
  }
}

/**
 * Main application router renderer.
 */
function renderApp() {
  // Authentication Gatekeeper
  if (localStorage.getItem('loggedIn') !== '1') {
    renderLogin();
    return;
  }

  // Render Persistent Top Navigation Bar + Main Page View Container
  app.innerHTML = navbar() + `<main id="page-content" style="padding-bottom: 40px;"></main>`;

  // Bind Navigation Links
  bindNavbarEvents();

  // Route to Selected Page
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
    case 'home':
    default:
      renderHomePage(content);
      break;
  }
}

/**
 * Navigation bar event binding.
 */
function bindNavbarEvents() {
  const navLinks = document.querySelectorAll('.topbar nav a');
  navLinks.forEach(link => {
    link.style.cursor = 'pointer';
    link.onclick = (e) => {
      e.preventDefault();
      const pageName = link.textContent.trim().toLowerCase();
      currentPage = pageName;
      localStorage.setItem('lastPage', pageName);
      renderApp();
    };
  });
}

/**
 * Login View Handler
 */
function renderLogin() {
  app.innerHTML = login();
  const loginBtn = document.getElementById('b');
  if (loginBtn) {
    loginBtn.onclick = () => {
      const user = document.getElementById('u')?.value;
      const pass = document.getElementById('p')?.value;
      const msg = document.getElementById('m');

      if (user === 'happyboy457' && pass === 'admin') {
        localStorage.setItem('loggedIn', '1');
        renderApp();
      } else if (msg) {
        msg.textContent = 'Invalid credentials. Use happyboy457 / admin';
        msg.style.color = '#ff5555';
      }
    };
  }
}

/**
 * Home View Handler
 */
function renderHomePage(container) {
  const totalValue = cosmeticsData.reduce((acc, i) => acc + (i.value || 0), 0);
  const highestItem = [...cosmeticsData].sort((a, b) => (b.value || 0) - (a.value || 0))[0];

  container.innerHTML = `
    <div style="max-width: 1200px; margin: 0 auto; padding: 24px;">
      <div style="margin-bottom: 32px; text-align: center;">
        <h1 style="font-size: 32px; margin-bottom: 8px; color:#fff;">Welcome to <span style="color:#5EF2B6;">ZeqaValues</span></h1>
        <p style="color:#aaaaaa; margin:0;">Mineville PvP Cosmetic Valuation & Market Trading Index</p>
      </div>

      <div class="stat-grid">
        ${statCard('Total Cosmetics', cosmeticsData.length)}
        ${statCard('Highest Value Item', highestItem ? highestItem.name : 'N/A')}
        ${statCard('Market Capitalization', totalValue.toLocaleString() + ' coins')}
      </div>

      <h2 style="margin-top: 40px; color: #5EF2B6; font-size: 20px;">Top Valued Cosmetics</h2>
      <div id="home-items-grid" style="display:grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 16px; margin-top: 16px;">
        ${cosmeticsData.slice(0, 6).map(item => itemCard(item)).join('')}
      </div>
    </div>
  `;

  bindCardPopupClicks(container, '#home-items-grid .item-card');
}

/**
 * Value View Handler (Part 7 Integration)
 */
function renderValuePage(container) {
  const valuePage = new ValuePage(cosmeticsData);
  container.innerHTML = valuePage.render();
  valuePage.bindEvents(container);
}

/**
 * Compare View Handler (Trade Comparison Engine)
 */
function renderComparePage(container) {
  // Default mock comparison between items if present
  const leftItem = cosmeticsData[0] ? [cosmeticsData[0]] : [];
  const rightItem = cosmeticsData[2] ? [cosmeticsData[2]] : [];
  const result = compare(leftItem, rightItem);

  container.innerHTML = `
    <div style="max-width: 1000px; margin: 0 auto; padding: 24px;">
      <h1 style="color:#fff; margin-bottom: 8px;">Trade Comparison Engine</h1>
      <p style="color:#aaaaaa; margin-bottom: 24px;">Analyze equality and profit margin between item trades.</p>

      <div style="display:grid; grid-template-columns: 1fr 1fr; gap: 20px;">
        <div style="background:#161b22; border:1px solid #30363d; border-radius:12px; padding:20px;">
          <h3 style="color:#5EF2B6; margin-top:0;">happyboy457's Offer</h3>
          <div>${leftItem.map(i => itemCard(i)).join('')}</div>
          <div style="margin-top:16px; font-size:18px; font-weight:bold;">Total: ${result.leftTotal.toLocaleString()} coins</div>
        </div>

        <div style="background:#161b22; border:1px solid #30363d; border-radius:12px; padding:20px;">
          <h3 style="color:#5EF2B6; margin-top:0;">Trader's Offer</h3>
          <div>${rightItem.map(i => itemCard(i)).join('')}</div>
          <div style="margin-top:16px; font-size:18px; font-weight:bold;">Total: ${result.rightTotal.toLocaleString()} coins</div>
        </div>
      </div>

      <div style="margin-top:24px; background:#111; border:1px solid #282828; border-radius:12px; padding:20px; text-align:center;">
        <h2 style="margin:0 0 8px 0; color:${result.isFair ? '#5EF2B6' : '#ffac33'};">Outcome: ${result.outcome}</h2>
        <div style="color:#aaaaaa;">Value Differential: ${Math.abs(result.difference).toLocaleString()} coins (${result.percentageDifference}%)</div>
      </div>
    </div>
  `;

  bindCardPopupClicks(container, '.item-card');
}

/**
 * Collection View Handler (User Inventory)
 */
function renderCollectionPage(container) {
  const collectionIds = loadCollection();
  const collectionItems = cosmeticsData.filter(i => collectionIds.includes(i.id));
  const collectionValue = collectionItems.reduce((acc, i) => acc + (i.value || 0), 0);

  container.innerHTML = `
    <div style="max-width: 1000px; margin: 0 auto; padding: 24px;">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 24px;">
        <div>
          <h1 style="color:#fff; margin:0 0 4px 0;">My Collection</h1>
          <p style="color:#aaaaaa; margin:0;">Saved user inventory & portfolio tracking</p>
        </div>
        <div style="background:#161b22; border:1px solid #5EF2B6; padding:12px 20px; border-radius:10px; color:#5EF2B6; font-weight:bold;">
          Net Worth: ${collectionValue.toLocaleString()} coins
        </div>
      </div>

      ${collectionItems.length === 0 ? `
        <div style="background:#141414; border:1px dashed #2a2a2a; border-radius:12px; padding:60px; text-align:center; color:#aaaaaa;">
          Your collection is currently empty. Visit the Value Directory to add cosmetics.
        </div>
      ` : `
        <div style="display:grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 16px;">
          ${collectionItems.map(item => itemCard(item)).join('')}
        </div>
      `}
    </div>
  `;

  bindCardPopupClicks(container, '.item-card');
}

/**
 * Utility to attach click handlers to item cards to open the Popup inspection window (Part 6).
 */
function bindCardPopupClicks(container, selector) {
  const cards = container.querySelectorAll(selector);
  cards.forEach(card => {
    card.style.cursor = 'pointer';
    card.onclick = () => {
      const cardTitle = card.querySelector('h3')?.textContent;
      const found = cosmeticsData.find(i => i.name === cardTitle || String(i.id) === String(card.dataset.id));
      if (found) {
        Popup.open(found);
      }
    };
  });
}

/**
 * Application Bootstrap
 */
async function init() {
  await loadData();
  renderApp();
}

init();
