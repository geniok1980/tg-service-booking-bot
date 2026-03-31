# handlers/review.py — Система отзывов после визита

from aiogram import Router, F
from aiogram.types import CallbackQuery

from config import ADMIN_ID
from database import save_review
from keyboards import main_menu_kb

router = Router()

RATING_ICONS = {1: "⭐", 2: "⭐⭐", 3: "⭐⭐⭐", 4: "⭐⭐⭐⭐", 5: "⭐⭐⭐⭐⭐"}


@router.callback_query(F.data.startswith("review:"))
async def process_review(callback: CallbackQuery):
    """Обработать оценку пользователя."""
    parts = callback.data.split(":")
    booking_id = int(parts[1])
    rating = int(parts[2])

    user_id = callback.from_user.id
    name = callback.from_user.full_name or "Клиент"

    saved = await save_review(booking_id, user_id, name, rating)

    stars = RATING_ICONS.get(rating, "⭐")

    if saved:
        await callback.message.edit_text(
            f"🙏 <b>Спасибо за отзыв!</b>\n\n"
            f"Вы поставили оценку: {stars}\n\n"
            f"Ваше мнение очень важно для нас ❤️",
            parse_mode="HTML",
            reply_markup=main_menu_kb(user_id=user_id)
        )

        # Уведомляем администратора
        try:
            await callback.bot.send_message(
                ADMIN_ID,
                f"⭐ <b>Новый отзыв!</b>\n\n"
                f"👤 Клиент: {name}\n"
                f"Оценка: {stars} ({rating}/5)",
                parse_mode="HTML"
            )
        except Exception as e:
            print(f"[Review] Ошибка уведомления администратора: {e}")
    else:
        await callback.answer("Вы уже оставили отзыв на эту запись.", show_alert=True)
