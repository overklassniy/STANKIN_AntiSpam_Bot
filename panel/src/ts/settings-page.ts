/**
 * Точка входа для страницы настроек.
 */

import { initHamburger } from './hamburger.js';
import { initSettings, initSettingsTabs, initAddChatForm, initChatSettingsForm } from './settings.js';
import { initThemeToggle } from './theme-toggle.js';

document.addEventListener('DOMContentLoaded', () => {
  initHamburger();
  initSettings();
  initSettingsTabs();
  initAddChatForm();
  initChatSettingsForm();
  initThemeToggle();
});
