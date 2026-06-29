/**Toast-уведомления.

 * Алгоритм работы:
 *   1. Создать элемент toast с типом (success, error, info).
 *   2. Добавить в контейнер toast-container.
 *   3. Автоматически скрыть через 4 секунды.
 */

type ToastType = 'success' | 'error' | 'info';

const TOAST_DURATION = 4000;

/**Показывает toast-уведомление.
 *
 * Аргументы:
 *   message (string): Текст уведомления.
 *   type (ToastType): Тип уведомления — success, error или info.
 */
export function showToast(message: string, type: ToastType = 'info'): void {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.textContent = message;

  container.appendChild(toast);

  setTimeout(() => {
    toast.classList.add('toast-hide');
    toast.addEventListener('animationend', () => {
      toast.remove();
    }, { once: true });
  }, TOAST_DURATION);
}
