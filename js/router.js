/**
 * ZeqaValues - SPA Master Router Engine
 * Controls page switching across ['home', 'compare', 'value', 'collection', 'settings']
 */

import { navbar } from '../components/navbar.js';
import { login } from '../components/login.js';
import { HomePage } from '../pages/home.js';
import { ValuePage } from '../pages/value.js';
import { ComparePage } from '../pages/compare.js';
import { CollectionPage } from '../pages/collection.js';
import { SettingsPage } from '../pages/settings.js';

export const pages = ['home', 'compare', 'value', 'collection', 'settings'];

export class Router {
  constructor(appElement, cosmeticsData = []) {
    this.app = appElement;
    this.data = cosmeticsData;
    this.currentPage = localStorage.getItem('lastPage') || 'home';
  }

  setData(data) {
    this.data = data;
  }

  navigate(page) {
    if (!pages.includes(page)) page = 'home';
    this.currentPage = page;
    localStorage.setItem('lastPage', page);
    this.render();
  }

  render() {
    if (localStorage.getItem('loggedIn') !== '1') {
      this.renderLogin();
      return;
    }

    this.app.innerHTML = navbar() + `<main id="page-content"></main>`;
    this.bindNavbar();

    const content = document.getElementById('page-content');
    if (!content) return;

    switch (this.currentPage) {
      case 'value': {
        const page = new ValuePage(this.data);
        content.innerHTML = page.render();
        page.bindEvents(content);
        break;
      }
      case 'compare': {
        const page = new ComparePage(this.data);
        content.innerHTML = page.render();
        page.bindEvents(content);
        break;
      }
      case 'collection': {
        const page = new CollectionPage(this.data);
        content.innerHTML = page.render();
        page.bindEvents(content);
        break;
      }
      case 'settings': {
        const page = new SettingsPage(this);
        content.innerHTML = page.render();
        page.bindEvents(content);
        break;
      }
      case 'home':
      default: {
        const page = new HomePage(this.data, this);
        content.innerHTML = page.render();
        page.bindEvents(content);
        break;
      }
    }
  }

  bindNavbar() {
    const links = document.querySelectorAll('.topbar nav a');
    links.forEach(link => {
      link.style.cursor = 'pointer';
      link.onclick = (e) => {
        e.preventDefault();
        const route = link.textContent.trim().toLowerCase();
        this.navigate(route);
      };
    });
  }

  renderLogin() {
    this.app.innerHTML = login();
    const btn = document.getElementById('b');
    if (btn) {
      btn.onclick = () => {
        const u = document.getElementById('u')?.value;
        const p = document.getElementById('p')?.value;
        const m = document.getElementById('m');

        if (u === 'happyboy457' && p === 'admin') {
          localStorage.setItem('loggedIn', '1');
          localStorage.setItem('zv_active_user', u);
          this.render();
        } else if (m) {
          m.textContent = 'Invalid credentials. Use happyboy457 / admin';
          m.style.color = '#e74c3c';
        }
      };
    }
  }
}
