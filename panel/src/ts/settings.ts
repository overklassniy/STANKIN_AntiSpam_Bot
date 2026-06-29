/**
 * Управление настройками через REST API.
 */

import { api, type Setting, type ChatInfo } from './api.js';
import { showToast } from './toast.js';

/**
 * Инициализирует форму глобальных настроек: отправку данных и отображение уведомлений.
 */
export function initSettings(): void {
  const form = document.querySelector<HTMLFormElement>('#settings-form');
  const notification = document.querySelector<HTMLElement>('#settings-notification');

  if (!form) {
    return;
  }

  form.addEventListener('submit', async (e: Event) => {
    e.preventDefault();

    const formData = new FormData(form);
    const settings: Record<string, unknown> = {};

    // Чекбоксы: unchecked не попадают в FormData, добавляем явно
    form.querySelectorAll<HTMLInputElement>('input[type="checkbox"]').forEach((cb) => {
      settings[cb.name] = cb.checked;
    });

    for (const [key, value] of formData.entries()) {
      if (key === 'save') {
        continue;
      }

      // Чекбоксы уже обработаны выше
      if (settings[key] !== undefined) {
        continue;
      }

      const strValue = value.toString();
      if (strValue.toLowerCase() === 'true') {
        settings[key] = true;
      } else if (strValue.toLowerCase() === 'false') {
        settings[key] = false;
      } else if (strValue.replace('.', '').match(/^\d+$/)) {
        settings[key] = strValue.includes('.') ? parseFloat(strValue) : parseInt(strValue, 10);
      } else {
        settings[key] = strValue;
      }
    }

    const chatPk = form.dataset.chatPk;
    try {
      if (chatPk) {
        await api.updateChatSettings(parseInt(chatPk, 10), settings);
      } else {
        await api.updateGlobalSettings(settings);
      }

      if (notification) {
        notification.textContent = 'Настройки сохранены.';
        notification.style.display = 'block';
        setTimeout(() => {
          notification.style.display = 'none';
        }, 3000);
      }
    } catch (err) {
      if (notification) {
        notification.textContent = 'Ошибка сохранения настроек.';
        notification.style.display = 'block';
      }
      console.error('Ошибка сохранения:', err);
    }
  });
}

/**
 * Загружает настройки через REST API.
 *
 * @param chatPk PK чата для загрузки per-chat настроек. Если не указан, загружаются глобальные настройки.
 * @returns Массив настроек или пустой массив при ошибке.
 */
export async function loadSettings(chatPk?: number): Promise<{ items: Setting[] }> {
  try {
    return await api.getSettings(chatPk);
  } catch (err) {
    console.error('Ошибка загрузки настроек:', err);
    return { items: [] };
  }
}

/**
 * Инициализирует переключение вкладок на странице настроек.
 */
export function initSettingsTabs(): void {
  const tabs = document.querySelectorAll<HTMLButtonElement>('.settings-tab');
  const panels = document.querySelectorAll<HTMLElement>('.settings-panel');

  if (tabs.length === 0) {
    return;
  }

  tabs.forEach((tab) => {
    tab.addEventListener('click', () => {
      const target = tab.dataset.tab;

      tabs.forEach((t) => {
        t.classList.remove('active');
        t.setAttribute('aria-selected', 'false');
      });
      tab.classList.add('active');
      tab.setAttribute('aria-selected', 'true');

      panels.forEach((p) => {
        p.classList.toggle('active', p.dataset.panel === target);
      });

      if (target === 'chats') {
        loadChatList();
      }
    });
  });

  const activeChatsPanel = document.querySelector<HTMLElement>('.settings-panel[data-panel="chats"].active');
  if (activeChatsPanel) {
    loadChatList();
  }
}

/**
 * Инициализирует форму добавления чата по Telegram ID.
 */
export function initAddChatForm(): void {
  const form = document.querySelector<HTMLFormElement>('#add-chat-form');
  const notification = document.querySelector<HTMLElement>('#add-chat-notification');

  if (!form) {
    return;
  }

  form.addEventListener('submit', async (e: Event) => {
    e.preventDefault();

    const input = form.querySelector<HTMLInputElement>('#chat-id-input');
    if (!input) {
      return;
    }

    const chatId = parseInt(input.value, 10);
    if (isNaN(chatId)) {
      if (notification) {
        notification.textContent = 'Введите корректный ID чата.';
        notification.style.display = 'block';
      }
      return;
    }

    const submitBtn = form.querySelector<HTMLButtonElement>('button[type="submit"]');
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.textContent = 'Добавление...';
    }

    try {
      const chat = await api.addChat(chatId);
      showToast(`Чат «${chat.title}» добавлен.`, 'success');

      if (notification) {
        notification.textContent = `Чат «${chat.title}» добавлен.`;
        notification.style.display = 'block';
        setTimeout(() => {
          notification.style.display = 'none';
        }, 3000);
      }

      input.value = '';
      await loadChatList();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Ошибка добавления чата.';
      showToast(message, 'error');

      if (notification) {
        notification.textContent = message;
        notification.style.display = 'block';
      }
    } finally {
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Добавить чат';
      }
    }
  });
}

/**
 * Загружает список чатов и отображает их как карточки.
 */
async function loadChatList(): Promise<void> {
  const list = document.querySelector<HTMLElement>('#chat-settings-list');
  if (!list) {
    return;
  }

  list.innerHTML = '<p class="chat-settings-empty">Загрузка списка чатов...</p>';

  try {
    const { items } = await api.getChats();

    if (items.length === 0) {
      list.innerHTML = '<p class="chat-settings-empty">Нет доступных чатов.</p>';
      return;
    }

    list.innerHTML = '';
    for (const chat of items) {
      const card = document.createElement('div');
      card.className = 'chat-card';
      card.dataset.chatPk = String(chat.pk);

      const header = document.createElement('div');
      header.className = 'chat-card-header';

      const title = document.createElement('span');
      title.className = 'chat-card-title';
      title.textContent = chat.title || `ID: ${chat.chat_id}`;

      const id = document.createElement('span');
      id.className = 'chat-card-id';
      id.textContent = `ID: ${chat.chat_id}`;

      header.appendChild(title);
      header.appendChild(id);
      card.appendChild(header);

      if (chat.users && chat.users.length > 0) {
        const usersEl = document.createElement('div');
        usersEl.className = 'chat-card-users';
        const usersLabel = document.createElement('span');
        usersLabel.className = 'chat-card-users-label';
        usersLabel.textContent = 'Пользователи:';
        usersEl.appendChild(usersLabel);
        for (const u of chat.users) {
          const userSpan = document.createElement('span');
          userSpan.className = 'chat-card-user';
          userSpan.textContent = u.is_superadmin
            ? `${u.name} (админ)`
            : u.name;
          usersEl.appendChild(userSpan);
        }
        card.appendChild(usersEl);
      }

      card.addEventListener('click', () => {
        document.querySelectorAll('.chat-card').forEach((c) => c.classList.remove('selected'));
        card.classList.add('selected');
        loadChatSettings(chat);
      });

      list.appendChild(card);
    }
  } catch (err) {
    list.innerHTML = '<p class="chat-settings-empty">Ошибка загрузки списка чатов.</p>';
    console.error('Ошибка загрузки чатов:', err);
  }
}

/**
 * Загружает и отображает настройки конкретного чата.
 *
 * @param chat Информация о чате.
 */
async function loadChatSettings(chat: ChatInfo): Promise<void> {
  const container = document.querySelector<HTMLElement>('#chat-settings-container');
  const titleEl = document.querySelector<HTMLElement>('#chat-settings-title');
  const fieldsEl = document.querySelector<HTMLElement>('#chat-settings-fields');
  const form = document.querySelector<HTMLFormElement>('#chat-settings-form');

  if (!container || !titleEl || !fieldsEl || !form) {
    return;
  }

  titleEl.textContent = `Настройки чата: ${chat.title || `ID: ${chat.chat_id}`}`;
  form.dataset.chatPk = String(chat.pk);
  fieldsEl.innerHTML = '<p class="chat-settings-empty">Загрузка настроек...</p>';
  container.style.display = 'block';

  try {
    const [{ items }, modelsRes] = await Promise.all([
      api.getSettings(chat.pk),
      api.getModels(),
    ]);
    const availableModels = modelsRes.items;

    fieldsEl.innerHTML = '';
    for (const setting of items) {
      const isBool = typeof setting.value === 'boolean';
      const isSelect = setting.key === 'BERT_MODEL';

      if (isBool) {
        const group = document.createElement('div');
        group.className = 'form-group checkbox-group checkbox-wrapper';

        const input = document.createElement('input');
        input.type = 'checkbox';
        input.id = `chat-${setting.key}`;
        input.name = setting.key;
        input.value = 'true';
        input.checked = setting.value === true;

        const label = document.createElement('label');
        label.htmlFor = `chat-${setting.key}`;
        label.textContent = setting.key;
        label.title = setting.description;

        group.appendChild(input);
        group.appendChild(label);
        fieldsEl.appendChild(group);
      } else if (isSelect) {
        const group = document.createElement('div');
        group.className = 'form-group';

        const label = document.createElement('label');
        label.htmlFor = `chat-${setting.key}`;
        label.textContent = setting.key;
        label.title = setting.description;

        const select = document.createElement('select');
        select.className = 'text_input';
        select.id = `chat-${setting.key}`;
        select.name = setting.key;

        for (const model of availableModels) {
          const option = document.createElement('option');
          option.value = model;
          option.textContent = model;
          if (setting.value === model) {
            option.selected = true;
          }
          select.appendChild(option);
        }

        group.appendChild(label);
        group.appendChild(select);
        fieldsEl.appendChild(group);
      } else {
        const group = document.createElement('div');
        group.className = 'form-group';

        const label = document.createElement('label');
        label.htmlFor = `chat-${setting.key}`;
        label.textContent = setting.key;
        label.title = setting.description;

        const input = document.createElement('input');
        input.className = 'text_input';
        input.type = typeof setting.value === 'number' ? 'number' : 'text';
        if (input.type === 'number') {
          input.step = 'any';
        }
        input.id = `chat-${setting.key}`;
        input.name = setting.key;
        input.value = String(setting.value);

        group.appendChild(label);
        group.appendChild(input);
        fieldsEl.appendChild(group);
      }
    }
  } catch (err) {
    fieldsEl.innerHTML = '<p class="chat-settings-empty">Ошибка загрузки настроек чата.</p>';
    console.error('Ошибка загрузки настроек чата:', err);
  }
}

/**
 * Инициализирует форму сохранения per-chat настроек.
 */
export function initChatSettingsForm(): void {
  const form = document.querySelector<HTMLFormElement>('#chat-settings-form');
  const notification = document.querySelector<HTMLElement>('#chat-settings-notification');

  if (!form) {
    return;
  }

  form.addEventListener('submit', async (e: Event) => {
    e.preventDefault();

    const chatPk = form.dataset.chatPk;
    if (!chatPk) {
      return;
    }

    const formData = new FormData(form);
    const settings: Record<string, unknown> = {};

    // Чекбоксы: unchecked не попадают в FormData, добавляем явно
    form.querySelectorAll<HTMLInputElement>('input[type="checkbox"]').forEach((cb) => {
      settings[cb.name] = cb.checked;
    });

    for (const [key, value] of formData.entries()) {
      if (key === 'save') {
        continue;
      }

      // Чекбоксы уже обработаны выше
      if (settings[key] !== undefined) {
        continue;
      }

      const strValue = value.toString();
      if (strValue.toLowerCase() === 'true') {
        settings[key] = true;
      } else if (strValue.toLowerCase() === 'false') {
        settings[key] = false;
      } else if (strValue.replace('.', '').match(/^\d+$/)) {
        settings[key] = strValue.includes('.') ? parseFloat(strValue) : parseInt(strValue, 10);
      } else {
        settings[key] = strValue;
      }
    }

    try {
      await api.updateChatSettings(parseInt(chatPk, 10), settings);

      if (notification) {
        notification.textContent = 'Настройки чата сохранены.';
        notification.style.display = 'block';
        setTimeout(() => {
          notification.style.display = 'none';
        }, 3000);
      }
    } catch (err) {
      if (notification) {
        notification.textContent = 'Ошибка сохранения настроек чата.';
        notification.style.display = 'block';
      }
      console.error('Ошибка сохранения настроек чата:', err);
    }
  });
}
