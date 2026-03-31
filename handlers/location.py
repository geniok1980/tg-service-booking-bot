# handlers/location.py — Показ геолокации и инструкции ("Как добраться")

from aiogram import Router, Bot, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext

from database import get_location_settings

router = Router()


def back_to_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🏠 В меню", callback_data="back_to_menu"))
    return builder.as_markup()


@router.callback_query(F.data == "how_to_find")
async def show_location(callback: CallbackQuery, bot: Bot, state: FSMContext):
    """Показать геолокацию и фото-инструкцию."""
    settings = await get_location_settings()

    lat = float(settings.get("lat", 55.7558))
    lon = float(settings.get("lon", 37.6176))
    address = settings.get("address", "Адрес не указан")
    directions_file_id = settings.get("directions_file_id", "")

    # Удаляем старое сообщение, чтобы отправить геоточку
    try:
        await callback.message.delete()
    except Exception:
        pass

    # Отправляем локацию
    loc_msg = await bot.send_location(
        chat_id=callback.from_user.id,
        latitude=lat,
        longitude=lon
    )
    
    # Сохраняем message_id локации, чтобы удалить её при возврате "Назад"
    await state.update_data(location_msg_id=loc_msg.message_id)

    # Текстовое описание адреса
    text = (
        f"📍 <b>Как добраться</b>\n\n"
        f"<b>Адрес:</b> {address}\n\n"
        f"Нажмите на метку на карте, чтобы открыть маршрут к нам."
    )

    if directions_file_id:
        # Есть фото-инструкция
        await bot.send_photo(
            chat_id=callback.from_user.id,
            photo=directions_file_id,
            caption=text,
            parse_mode="HTML",
            reply_markup=back_to_menu_kb()
        )
    else:
        await bot.send_message(
            chat_id=callback.from_user.id,
            text=text,
            parse_mode="HTML",
            reply_markup=back_to_menu_kb()
        )

    await callback.answer()
