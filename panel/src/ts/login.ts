/**
 * Точка входа для страницы входа.
 */

import { initLoginFaq } from './loginFaq.js';
import { initThemeToggle } from './theme-toggle.js';

document.addEventListener('DOMContentLoaded', () => {
  initLoginFaq();
  initThemeToggle();
});
