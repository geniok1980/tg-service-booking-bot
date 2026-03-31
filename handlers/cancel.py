# handlers/cancel.py — Отмена записи клиентом

from datetime import datetime

from aiogram import Router, Bot, F
from aiogram.types import CallbackQuery

from config import ADMIN_ID, CHANNEL_ID
from keyboards import cancel_booking_kb, main_menu_kb
from database import get_user_booking, cancel_booking, unbook_slot
from scheduler import cancel_booking_notifications
from handlers.waitlist import notify_waitlist

router = Router()


@router.callback_query(F.data == "my_bookings")
async def show_my_bookings(callback: CallbackQuery):
    """Показать активную запись пользователя."""
    booking = await get_user_booking(callback.from_user.id)

    if not booking:
        text = (
            "📋 <b>Мои записи</b>\n\n"
            "У вас нет активных записей."
        )
        try:
            await callback.message.edit_text(
                text,
                parse_mode="HTML",
                reply_markup=main_menu_kb(user_id=callback.from_user.id)
            )
        except Exception:
            try:
                await callback.message.delete()
            except Exception:
                pass
            await callback.message.answer(
                text,
                parse_mode="HTML",
                reply_markup=main_menu_kb(user_id=callback.from_user.id)
            )
        return

    date_obj = datetime.strptime(booking["date"], "%Y-%m-%d")
    date_display = date_obj.strftime("%d.%m.%Y")
    
    text = (
        f"📋 <b>Ваша активная запись:</b>\n\n"
        f"📅 Дата: <b>{date_display}</b>\n"
        f"🕐 Время: <b>{booking['time']}</b>\n"
        f"👤 Имя: <b>{booking['name']}</b>\n"
        f"📞 Телефон: <b>{booking['phone']}</b>"
    )
    
    try:
        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=cancel_booking_kb(booking["id"])
        )
    except Exception:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(
            text,
            parse_mode="HTML",
            reply_markup=cancel_booking_kb(booking["id"])
        )


@router.callback_query(F.data.startswith("cancel_my_booking:"))
async def cancel_my_booking(callback: CallbackQuery, bot: Bot):
    """Отмена записи клиентом."""
    booking_id = int(callback.data.split(":")[1])

    # Отменяем запись
    booking = await cancel_booking(booking_id)

    if not booking:
        await callback.answer("❌ Запись не найдена.", show_alert=True)
        return

    # Освобождаем слот
    await unbook_slot(booking["date"], booking["time"])

    # Отменяем напоминание
    cancel_booking_notifications(booking_id)

    date_obj = datetime.strptime(booking["date"], "%Y-%m-%d")
    date_display = date_obj.strftime("%d.%m.%Y")

    # Уведомляем лист ожидания (освободился слот)
    await notify_waitlist(bot, booking["date"], date_display,
                          user_id=callback.from_user.id)

    # Уведомляем клиента
    await callback.message.edit_text(
        f"✅ <b>Запись отменена!</b>\n\n"
        f"📅 {date_display} в {booking['time']} — теперь свободно.\n\n"
        f"Вы можете записаться снова.",
        parse_mode="HTML",
        reply_markup=main_menu_kb(user_id=callback.from_user.id)
    )

    # Уведомляем администратора
    try:
        await bot.send_message(
            ADMIN_ID,
            f"❌ <b>Запись отменена клиентом</b>\n\n"
            f"📅 Дата: <b>{date_display}</b>\n"
            f"🕐 Время: <b>{booking['time']}</b>\n"
            f"👤 Имя: <b>{booking['name']}</b>\n"
            f"📞 Телефон: <b>{booking['phone']}</b>",
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"Ошибка уведомления админа об отмене: {e}")

    # Публикуем в канал
    try:
        await bot.send_message(
            CHANNEL_ID,
            f"🔓 <b>Слот освободился!</b>\n\n"
            f"📅 {date_display} в {booking['time']}\n"
            f"Записывайтесь! 💅",
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"Ошибка отправки в канал: {e}")
