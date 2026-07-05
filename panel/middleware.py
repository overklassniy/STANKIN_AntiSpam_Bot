"""Кастомные middleware для веб-панели."""

from base64 import b64decode, b64encode
import json

from itsdangerous import BadSignature
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import HTTPConnection
from starlette.types import ASGIApp, Message, Receive, Scope, Send
from starlette.datastructures import MutableHeaders


class RememberSessionMiddleware(SessionMiddleware):
    """Расширение SessionMiddleware с поддержкой «Запомнить меня».

    При установленном флаге ``remember`` в сессии использует
    ``remember_max_age`` вместо базового ``max_age`` — cookie сессии
    живёт дольше. При чтении cookie пробует оба ``max_age``.

    Аргументы:
        app (ASGIApp): ASGI-приложение.
        secret_key (str | Secret): Ключ подписи сессии.
        max_age (int | None): Базовое время жизни сессии в секундах.
        remember_max_age (int | None): Продлённое время жизни сессии
            в секундах при установленном флаге ``remember``.
        **kwargs: Остальные параметры SessionMiddleware.
    """

    def __init__(
        self,
        app: ASGIApp,
        secret_key: str,
        max_age: int | None,
        remember_max_age: int | None,
        **kwargs,
    ) -> None:
        super().__init__(app, secret_key, max_age=max_age, **kwargs)
        self.remember_max_age = remember_max_age

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        connection = HTTPConnection(scope)
        initial_session_was_empty = True

        if self.session_cookie in connection.cookies:
            data = connection.cookies[self.session_cookie].encode("utf-8")
            try:
                data = self.signer.unsign(data, max_age=self.max_age)
                scope["session"] = self._decode_session(data)
                initial_session_was_empty = False
            except BadSignature:
                # Пробуем продлённый max_age для сессий «Запомнить меня»
                try:
                    data = self.signer.unsign(data, max_age=self.remember_max_age)
                    scope["session"] = self._decode_session(data)
                    initial_session_was_empty = False
                except BadSignature:
                    scope["session"] = self._empty_session()
        else:
            scope["session"] = self._empty_session()

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                session = scope["session"]
                headers = MutableHeaders(scope=message)
                if session.accessed:
                    headers.add_vary_header("Cookie")
                if session.modified and session:
                    data = b64encode(json.dumps(session).encode("utf-8"))
                    data = self.signer.sign(data)
                    # Продлённый max_age, если в сессии установлен флаг remember
                    effective_max_age = (
                        self.remember_max_age
                        if session.get("remember")
                        else self.max_age
                    )
                    header_value = "{session_cookie}={data}; path={path}; {max_age}{security_flags}".format(
                        session_cookie=self.session_cookie,
                        data=data.decode("utf-8"),
                        path=self.path,
                        max_age=f"Max-Age={effective_max_age}; " if effective_max_age else "",
                        security_flags=self.security_flags,
                    )
                    headers.append("Set-Cookie", header_value)
                elif session.modified and not initial_session_was_empty:
                    header_value = "{session_cookie}={data}; path={path}; {expires}{security_flags}".format(
                        session_cookie=self.session_cookie,
                        data="null",
                        path=self.path,
                        expires="expires=Thu, 01 Jan 1970 00:00:00 GMT; ",
                        security_flags=self.security_flags,
                    )
                    headers.append("Set-Cookie", header_value)
            await send(message)

        await self.app(scope, receive, send_wrapper)

    def _decode_session(self, data: bytes):
        """Декодирует данные сессии из подписанного payload.

        Аргументы:
            data (bytes): Расшифрованные данные сессии.

        Возвращаемое значение:
            session (Session): Объект сессии.
        """
        from starlette.middleware.sessions import Session
        return Session(json.loads(b64decode(data)))

    def _empty_session(self):
        """Создаёт пустую сессию.

        Возвращаемое значение:
            session (Session): Пустой объект сессии.
        """
        from starlette.middleware.sessions import Session
        return Session()
