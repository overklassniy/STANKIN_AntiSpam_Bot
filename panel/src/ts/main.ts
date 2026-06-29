/**
 * Главная точка входа для авторизованных страниц.
 */

import { initHamburger } from './hamburger.js';
import { initThemeToggle } from './theme-toggle.js';

document.addEventListener('DOMContentLoaded', () => {
  initHamburger();
  initThemeToggle();
});
