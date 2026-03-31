# handlers/prices.py — Отображение прайса

from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery

from keyboards import main_menu_kb
from database import get_location_settings

router = Router()


@router.callback_query(F.data == "prices")
async def show_prices(callback: CallbackQuery, bot: Bot):
    """Показать прайс-лист (текст и/или фото)."""
    settings = await get_location_settings()
    
    price_text = settings.get("prices_text", "")
    price_photo_id = settings.get("prices_photo_id", "")

    if not price_text and not price_photo_id:
        text = "💅 <b>Прайс-лист</b>\n\nПрайс пока не добавлен. Пожалуйста, обратитесь напрямую к мастеру!"
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
            await bot.send_message(
                chat_id=callback.from_user.id,
                text=text,
                parse_mode="HTML",
                reply_markup=main_menu_kb(user_id=callback.from_user.id)
            )
        return

    # Если есть только текст
    if price_text and not price_photo_id:
        try:
            await callback.message.edit_text(
                price_text,
                parse_mode="HTML",
                reply_markup=main_menu_kb(user_id=callback.from_user.id)
            )
        except Exception:
            try:
                await callback.message.delete()
            except Exception:
                pass
            await bot.send_message(
                chat_id=callback.from_user.id,
                text=price_text,
                parse_mode="HTML",
                reply_markup=main_menu_kb(user_id=callback.from_user.id)
            )
        return

    # Если есть фото (с текстом или без)
    try:
        await callback.message.delete()
    except Exception:
        pass
    
    await bot.send_photo(
        chat_id=callback.from_user.id,
        photo=price_photo_id,
        caption=price_text,
        parse_mode="HTML",
        reply_markup=main_menu_kb(user_id=callback.from_user.id)
    )
    await callback.answer()
