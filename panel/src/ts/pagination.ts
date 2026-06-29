/**
 * Клиентская пагинация через REST API.
 */

import { type PaginationMeta } from './api.js';

interface PaginatedTableOptions {
  tableBodySelector: string;
  paginationSelector: string;
  pageHeaderSelector: string;
  fetchFn: (page: number) => Promise<{ items: unknown[]; pagination: PaginationMeta }>;
  renderRow: (item: unknown) => string;
  headerTemplate: (total: number, perPage: number) => string;
}

/**
 * Инициализирует клиентскую пагинацию для таблицы.
 *
 * @param options Конфигурация пагинации: селекторы элементов, функция загрузки данных, функция рендеринга строк.
 */
export function initPagination(options: PaginatedTableOptions): void {
  const tableBody = document.querySelector<HTMLElement>(options.tableBodySelector);
  const paginationContainer = document.querySelector<HTMLElement>(options.paginationSelector);
  const header = document.querySelector<HTMLElement>(options.pageHeaderSelector);

  if (!tableBody || !paginationContainer) {
    return;
  }

  let currentPage = 1;

  async function loadPage(page: number): Promise<void> {
    try {
      const { items, pagination } = await options.fetchFn(page);
      currentPage = pagination.current_page;

      tableBody!.innerHTML = items.map(options.renderRow).join('');

      if (header) {
        header.textContent = options.headerTemplate(pagination.total, pagination.per_page);
      }

      renderPagination(pagination);
    } catch (err) {
      console.error('Ошибка загрузки страницы:', err);
    }
  }

  function renderPagination(pagination: PaginationMeta): void {
    const links: string[] = [];
    const visibleCount = 5;

    if (pagination.current_page > 1) {
      links.push(
        `<a href="#" class="pagination-link prev" data-page="${pagination.current_page - 1}">
          <span class="btn-text">Предыдущая</span>
          <span class="btn-mobile">&lt;</span>
        </a>`
      );
    }

    const total = pagination.total_pages;
    let start = Math.max(1, pagination.current_page - Math.floor(visibleCount / 2));
    let end = Math.min(total, start + visibleCount - 1);
    if (end - start + 1 < visibleCount) {
      start = Math.max(1, end - visibleCount + 1);
    }

    for (let i = start; i <= end; i++) {
      links.push(
        `<a href="#" class="pagination-link ${i === pagination.current_page ? 'active' : ''}" data-page="${i}">${i}</a>`
      );
    }

    if (pagination.current_page < pagination.total_pages) {
      links.push(
        `<a href="#" class="pagination-link next" data-page="${pagination.current_page + 1}">
          <span class="btn-text">Следующая</span>
          <span class="btn-mobile">&gt;</span>
        </a>`
      );
    }

    paginationContainer!.innerHTML = links.join('');

    paginationContainer!.querySelectorAll<HTMLAnchorElement>('.pagination-link').forEach((link) => {
      link.addEventListener('click', (e: Event) => {
        e.preventDefault();
        const page = parseInt(link.dataset.page || '1', 10);
        loadPage(page);
      });
    });
  }

  loadPage(currentPage);
}
