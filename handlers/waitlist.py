# handlers/waitlist.py — Лист ожидания

from aiogram import Router, Bot, F
from aiogram.types import CallbackQuery

from database import (
    add_to_waitlist, get_waitlist, clear_waitlist,
    is_in_waitlist, get_days_with_free_slots
)
from keyboards import main_menu_kb

router = Router()


@router.callback_query(F.data.startswith("waitlist_add:"))
async def join_waitlist(callback: CallbackQuery):
    """Добавить пользователя в лист ожидания на дату."""
    date_str = callback.data.split(":")[1]

    if await is_in_waitlist(callback.from_user.id, date_str):
        await callback.answer(
            "✅ Вы уже в листе ожидания на этот день. "
            "Мы уведомим вас, если появится место!",
            show_alert=True
        )
        return

    await add_to_waitlist(callback.from_user.id, date_str)
    await callback.answer(
        "🔔 Отлично! Мы сообщим вам, когда появится свободное место.",
        show_alert=True
    )


async def notify_waitlist(bot: Bot, date: str, date_display: str,
                           user_id: int | None = None):
    """
    Уведомить всех в листе ожидания на дату.
    Если user_id задан — не уведомлять этого пользователя (например, отменившего запись).
    После уведомления очищаем лист.
    """
    waitlist = await get_waitlist(date)
    if not waitlist:
        return

    for uid in waitlist:
        if uid == user_id:
            continue
        try:
            await bot.send_message(
                uid,
                f"🎉 <b>Появилось свободное место!</b>\n\n"
                f"📅 На <b>{date_display}</b> освободился слот.\n"
                f"Нажмите «Записаться», чтобы успеть!",
                parse_mode="HTML",
                reply_markup=main_menu_kb(user_id=uid)
            )
        except Exception as e:
            print(f"[Waitlist] Ошибка уведомления пользователя {uid}: {e}")

    await clear_waitlist(date)
