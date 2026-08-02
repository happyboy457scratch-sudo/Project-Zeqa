/**
 * ZeqaValues - Modular Single Page Application Entry Point
 * Loads dataset and delegates routing to SPA Router.
 */

import { Router } from './js/router.js';

let cosmeticsData = [];
const appElement = document.getElementById('app');
const router = new Router(appElement);

/**
 * Initializes application data and triggers initial view render.
 */
async function init() {
  try {
    const response = await fetch('./data/cosmetics.json');
    if (!response.ok) {
      throw new Error(`Failed to fetch cosmetics payload: ${response.statusText}`);
    }
    cosmeticsData = await response.json();
  } catch (err) {
    console.error('Data initialization error:', err);
    cosmeticsData = [];
  }

  router.setData(cosmeticsData);
  router.render();
}

// Bootstrap
init();
