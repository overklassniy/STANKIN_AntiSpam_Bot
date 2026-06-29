/**Переключение тёмной темы.

 * Алгоритм работы:
 *   1. Прочитать сохранённую тему из localStorage.
 *   2. Если тема не сохранена, использовать системную настройку.
 *   3. При клике по кнопке переключить тему и сохранить выбор.
 */

const STORAGE_KEY = 'theme';

/**Переключает тему на противоположную. */
function toggleTheme(): void {
  const html = document.documentElement;
  const current = html.getAttribute('data-theme');
  const isDark = current === 'dark';

  html.classList.add('no-transition');

  if (isDark) {
    html.removeAttribute('data-theme');
    localStorage.setItem(STORAGE_KEY, 'light');
  } else {
    html.setAttribute('data-theme', 'dark');
    localStorage.setItem(STORAGE_KEY, 'dark');
  }

  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      html.classList.remove('no-transition');
    });
  });
}

/**Инициализирует кнопку переключения темы. */
export function initThemeToggle(): void {
  const button = document.getElementById('theme-toggle');
  if (!button) return;

  button.addEventListener('click', toggleTheme);
}
