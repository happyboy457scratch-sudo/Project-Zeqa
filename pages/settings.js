/**
 * ZeqaValues - Settings Page Controller
 * System configuration, user preferences, and cache clearing.
 */

export class SettingsPage {
  constructor(router = null) {
    this.router = router;
  }

  render() {
    const activeUser = localStorage.getItem('zv_active_user') || 'happyboy457';
    const theme = localStorage.getItem('zv_theme') || 'dark';

    return `
      <div class="zv-settings-container">
        <div class="zv-settings-header">
          <h1 class="zv-settings-title">Application Settings</h1>
          <p class="zv-settings-subtitle">Manage preferences, theme settings, and active session state.</p>
        </div>

        <div class="zv-settings-card">
          <div class="zv-settings-card-title">Session Details</div>
          <div class="zv-setting-row">
            <div class="zv-setting-info">
              <span class="zv-setting-label">Logged In User</span>
              <span class="zv-setting-desc">Active account identity</span>
            </div>
            <span style="font-weight:700; color:#5EF2B6;">${activeUser}</span>
          </div>
        </div>

        <div class="zv-settings-card">
          <div class="zv-settings-card-title">UI Preferences</div>
          <div class="zv-setting-row">
            <div class="zv-setting-info">
              <span class="zv-setting-label">Color Theme</span>
              <span class="zv-setting-desc">Base UI color profile</span>
            </div>
            <select class="zv-select-input" id="zv-theme-select">
              <option value="dark" ${theme === 'dark' ? 'selected' : ''}>Dark (Default)</option>
              <option value="mint" ${theme === 'mint' ? 'selected' : ''}>High-Contrast Mint</option>
            </select>
          </div>
        </div>

        <div class="zv-settings-card">
          <div class="zv-settings-card-title">Data & Maintenance</div>
          <div class="zv-setting-row">
            <div class="zv-setting-info">
              <span class="zv-setting-label">Clear Local Collection Data</span>
              <span class="zv-setting-desc">Resets all saved inventory and wishlist items in storage</span>
            </div>
            <button class="zv-danger-btn" id="zv-reset-storage">Reset Storage</button>
          </div>
          <div class="zv-setting-row" style="margin-top:12px;">
            <div class="zv-setting-info">
              <span class="zv-setting-label">Sign Out</span>
              <span class="zv-setting-desc">Terminates current session</span>
            </div>
            <button class="zv-danger-btn" id="zv-sign-out">Log Out</button>
          </div>
        </div>
      </div>
    `;
  }

  bindEvents(container) {
    const root = container || document;

    const themeSelect = root.querySelector('#zv-theme-select');
    if (themeSelect) {
      themeSelect.onchange = (e) => {
        localStorage.setItem('zv_theme', e.target.value);
      };
    }

    const resetBtn = root.querySelector('#zv-reset-storage');
    if (resetBtn) {
      resetBtn.onclick = () => {
        if (confirm('Are you sure you want to clear your local collection and wishlist?')) {
          localStorage.removeItem('zv_user_inventory');
          localStorage.removeItem('zv_user_wishlist');
          alert('Local collection reset successfully.');
        }
      };
    }

    const signOutBtn = root.querySelector('#zv-sign-out');
    if (signOutBtn) {
      signOutBtn.onclick = () => {
        localStorage.removeItem('loggedIn');
        if (this.router) this.router.render();
      };
    }
  }
}
