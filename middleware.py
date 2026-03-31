# middleware.py — Middleware для отслеживания пользователей и блокировки

from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import Update, Message, CallbackQuery
from database import update_user_data, is_user_blocked
from config import ADMIN_ID

class UserManagementMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any]
    ) -> Any:
        user = None
        if event.message:
            user = event.message.from_user
        elif event.callback_query:
            user = event.callback_query.from_user

        if user:
            # Обновляем данные пользователя в базе (username, имя)
            await update_user_data(
                user_id=user.id,
                username=user.username,
                full_name=user.full_name
            )

            # Проверяем на блокировку (админа блокировать нельзя)
            if user.id != ADMIN_ID:
                if await is_user_blocked(user.id):
                    # Если это сообщение — можно ответить, что доступ закрыт
                    if event.message:
                        await event.message.answer("⛔ <b>Доступ ограничен.</b>\n\nВы были заблокированы администратором.")
                    elif event.callback_query:
                        await event.callback_query.answer("⛔ Доступ ограничен", show_alert=True)
                    return # Прерываем выполнение

        return await handler(event, data)
