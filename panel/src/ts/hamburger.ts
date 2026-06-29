/**
 * Управление гамбургер-меню.
 */

/**
 * Инициализирует гамбургер-меню: переключение видимости и закрытие по клику вне меню.
 */
export function initHamburger(): void {
  const hamburger = document.querySelector<HTMLElement>('.hamburger');
  const dropdown = document.querySelector<HTMLElement>('.dropdown-menu');

  if (!hamburger || !dropdown) {
    return;
  }

  hamburger.addEventListener('click', (e: Event) => {
    e.stopPropagation();
    const isOpen = dropdown.classList.toggle('show');
    hamburger.setAttribute('aria-expanded', String(isOpen));
  });

  document.addEventListener('click', (e: Event) => {
    const target = e.target as HTMLElement;
    if (!dropdown.contains(target) && !hamburger.contains(target)) {
      dropdown.classList.remove('show');
      hamburger.setAttribute('aria-expanded', 'false');
    }
  });
}
