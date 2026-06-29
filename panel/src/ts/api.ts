/**
 * Типы и обёртки для REST API.
 */

const API_BASE = '/api/v1';

interface PaginationMeta {
  current_page: number;
  total_pages: number;
  total: number;
  per_page: number;
}

interface ApiResponse<T> {
  items: T[];
  pagination: PaginationMeta;
}

interface ErrorResponse {
  error: string;
  message: string;
}

interface SpamMessage {
  id: number;
  chat_id: number;
  message_id: number;
  timestamp: number;
  author_id: number;
  author_username: string | null;
  message_text: string;
  has_reply_markup: boolean | null;
  cas: boolean | null;
  lols: boolean | null;
  chatgpt_prediction: number | null;
  bert_prediction: number | null;
}

interface MutedUser {
  id: number;
  chat_pk: number;
  user_id: number;
  username: string | null;
  timestamp: number;
  muted_till_timestamp: number | null;
  relapse_number: number;
}

interface Setting {
  key: string;
  value: string | number | boolean;
  description: string;
  is_global: boolean;
  chat_pk: number | null;
}

interface ChatUser {
  id: number;
  name: string;
  telegram_id: number;
  is_superadmin: boolean;
}

interface ChatInfo {
  pk: number;
  chat_id: number;
  title: string;
  is_active: boolean;
  users: ChatUser[];
}

interface UserInfo {
  id: number;
  username: string;
  is_superadmin: boolean;
}

/**
 * Выполняет HTTP-запрос и возвращает JSON.
 *
 * @param url URL эндпоинта.
 * @param options Опции запроса fetch.
 * @returns Разобранный JSON-ответ.
 * @throws Error Если сервер вернул ошибку.
 */
async function fetchJson<T>(
  url: string,
  options?: RequestInit
): Promise<T> {
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const error: ErrorResponse = await response.json().catch(() => ({
      error: 'unknown',
      message: `HTTP ${response.status}`,
    }));
    throw new Error(error.message || error.error || `HTTP ${response.status}`);
  }

  return response.json();
}

/**
 * Объект с методами для работы с REST API.
 */
export const api = {
  async getSpam(page: number = 1): Promise<ApiResponse<SpamMessage>> {
    return fetchJson(`${API_BASE}/spam?page=${page}`);
  },

  async getMuted(page: number = 1): Promise<ApiResponse<MutedUser>> {
    return fetchJson(`${API_BASE}/muted?page=${page}`);
  },

  async getSettings(chatPk?: number): Promise<{ items: Setting[] }> {
    const url = chatPk
      ? `${API_BASE}/settings/chat/${chatPk}`
      : `${API_BASE}/settings`;
    return fetchJson(url);
  },

  async updateGlobalSettings(settings: Record<string, unknown>): Promise<void> {
    await fetchJson(`${API_BASE}/settings/global`, {
      method: 'PUT',
      body: JSON.stringify({ settings }),
    });
  },

  async updateChatSettings(
    chatPk: number,
    settings: Record<string, unknown>
  ): Promise<void> {
    await fetchJson(`${API_BASE}/settings/chat/${chatPk}`, {
      method: 'PUT',
      body: JSON.stringify({ settings }),
    });
  },

  async getChats(): Promise<{ items: ChatInfo[] }> {
    return fetchJson(`${API_BASE}/chats`);
  },

  async getModels(): Promise<{ items: string[] }> {
    return fetchJson(`${API_BASE}/models`);
  },

  async addChat(chatId: number): Promise<ChatInfo> {
    return fetchJson(`${API_BASE}/chats`, {
      method: 'POST',
      body: JSON.stringify({ chat_id: chatId }),
    });
  },

  async getCurrentUser(): Promise<UserInfo | null> {
    try {
      return await fetchJson(`${API_BASE}/auth/me`);
    } catch {
      return null;
    }
  },

  async login(username: string, password: string, remember: boolean): Promise<void> {
    await fetchJson(`${API_BASE}/auth/login`, {
      method: 'POST',
      body: JSON.stringify({ username, password, remember }),
    });
  },

  async logout(): Promise<void> {
    await fetchJson(`${API_BASE}/auth/logout`, {
      method: 'POST',
    });
  },
};

export type {
  PaginationMeta,
  ApiResponse,
  ErrorResponse,
  SpamMessage,
  MutedUser,
  Setting,
  ChatInfo,
  ChatUser,
  UserInfo,
};
