# handlers/booking.py — Обработчики процесса записи

from datetime import datetime

from aiogram import Router, Bot, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from config import ADMIN_ID, CHANNEL_ID
from states import BookingStates
from keyboards import (
    calendar_kb, time_slots_kb, confirm_booking_kb, main_menu_kb
)
from database import (
    get_days_with_free_slots, get_available_slots, has_active_booking,
    book_slot, create_booking, get_work_days_list
)
from scheduler import schedule_reminder, schedule_review_request, schedule_session_start_notification
from handlers.start import check_subscription

router = Router()


@router.callback_query(F.data == "book")
async def start_booking(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Начало процесса записи — показать календарь."""
    # Проверяем подписку
    is_subscribed = await check_subscription(bot, callback.from_user.id)
    if not is_subscribed:
        from keyboards import subscription_kb
        await callback.message.edit_text(
            "📢 Для записи необходимо подписаться на наш канал",
            parse_mode="HTML",
            reply_markup=subscription_kb()
        )
        return

    # Проверяем, нет ли уже записи
    if await has_active_booking(callback.from_user.id):
        await callback.answer(
            "❗ У вас уже есть активная запись. Сначала отмените её.",
            show_alert=True
        )
        return

    # Показываем календарь
    now = datetime.now()
    work_days = await get_work_days_list()
    available = await get_days_with_free_slots()
    await state.set_state(BookingStates.choosing_date)
    await state.update_data(cal_year=now.year, cal_month=now.month)

    text = (
        "📅 <b>Выберите дату записи</b>\n\n"
        "Числа — доступные даты\n"
        "🔴 — мест нет (лист ожидания)"
    )
    markup = calendar_kb(now.year, now.month, work_days, available)

    try:
        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=markup
        )
    except Exception:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(
            text,
            parse_mode="HTML",
            reply_markup=markup
        )


@router.callback_query(F.data.startswith("cal_nav:"), BookingStates.choosing_date)
async def calendar_navigate(callback: CallbackQuery, state: FSMContext):
    """Навигация по календарю (вперёд/назад)."""
    _, year, month = callback.data.split(":")
    year, month = int(year), int(month)
    work_days = await get_work_days_list()
    available = await get_days_with_free_slots()

    await state.update_data(cal_year=year, cal_month=month)

    await callback.message.edit_reply_markup(
        reply_markup=calendar_kb(year, month, work_days, available)
    )


@router.callback_query(F.data.startswith("cal_day:"), BookingStates.choosing_date)
async def select_date(callback: CallbackQuery, state: FSMContext):
    """Выбор даты — показать доступные слоты."""
    date_str = callback.data.split(":")[1]
    slots = await get_available_slots(date_str)

    if not slots:
        from keyboards import waitlist_kb
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        date_display = date_obj.strftime("%d.%m.%Y")
        await callback.message.edit_text(
            f"😔 На <b>{date_display}</b> свободных мест нет.\n\n"
            f"Вы хотите присоединиться к листу ожидания?",
            parse_mode="HTML",
            reply_markup=waitlist_kb(date_str)
        )
        return

    await state.set_state(BookingStates.choosing_time)
    await state.update_data(selected_date=date_str)

    # Форматируем дату для отображения
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    date_display = date_obj.strftime("%d.%m.%Y")

    await callback.message.edit_text(
        f"🕐 <b>Доступное время на {date_display}:</b>\n\n"
        f"Выберите удобное время:",
        parse_mode="HTML",
        reply_markup=time_slots_kb(date_str, slots)
    )


@router.callback_query(F.data == "back_to_calendar", BookingStates.choosing_time)
async def back_to_calendar(callback: CallbackQuery, state: FSMContext):
    """Возврат к календарю из списка слотов."""
    data = await state.get_data()
    year = data.get("cal_year", datetime.now().year)
    month = data.get("cal_month", datetime.now().month)
    work_days = await get_work_days_list()
    available = await get_days_with_free_slots()

    await state.set_state(BookingStates.choosing_date)

    await callback.message.edit_text(
        "📅 <b>Выберите дату записи</b>\n\n"
        "Числа — доступные даты\n"
        "🔴 — мест нет (лист ожидания)",
        parse_mode="HTML",
        reply_markup=calendar_kb(year, month, work_days, available)
    )


@router.callback_query(F.data.startswith("slot:"), BookingStates.choosing_time)
async def select_time(callback: CallbackQuery, state: FSMContext):
    """Выбор времени — запрос имени."""
    parts = callback.data.split(":", maxsplit=2)
    date_str = parts[1]
    time_str = parts[2]

    today_str = datetime.now().strftime("%Y-%m-%d")
    if date_str == today_str:
        current_time_str = datetime.now().strftime("%H:%M")
        if time_str <= current_time_str:
            await callback.answer(
                "⏳ Извините, но это время уже прошло. "
                "Пожалуйста, выберите другой слот или дату.",
                show_alert=True
            )
            return

    await state.update_data(selected_date=date_str, selected_time=time_str)
    await state.set_state(BookingStates.entering_name)

    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    date_display = date_obj.strftime("%d.%m.%Y")

    await callback.message.edit_text(
        f"📝 <b>Запись на {date_display} в {time_str}</b>\n\n"
        f"Введите ваше <b>имя</b>:\n\n"
        f"<i>Для отмены введите /cancel</i>",
        parse_mode="HTML"
    )


@router.message(BookingStates.entering_name)
async def enter_name(message: Message, state: FSMContext):
    """Получение имени — запрос телефона."""
    name = message.text.strip()
    
    if name == "/cancel":
        await state.clear()
        await message.answer(
            "❌ Запись отменена.\n\n"
            "💅 <b>Главное меню</b>\n\n"
            "Выберите нужный пункт:",
            parse_mode="HTML",
            reply_markup=main_menu_kb(user_id=message.from_user.id)
        )
        return

    if not name or len(name) < 2:
        await message.answer(
            "❌ Пожалуйста, введите корректное имя (минимум 2 символа):"
        )
        return

    await state.update_data(client_name=name)
    await state.set_state(BookingStates.entering_phone)

    await message.answer(
        f"👤 <b>{name}</b>, отлично!\n\n"
        f"Теперь введите ваш <b>номер телефона</b>:\n\n"
        f"<i>Для отмены введите /cancel</i>",
        parse_mode="HTML"
    )


@router.message(BookingStates.entering_phone)
async def enter_phone(message: Message, state: FSMContext):
    """Получение телефона — показать подтверждение."""
    phone = message.text.strip()
    
    if phone == "/cancel":
        await state.clear()
        await message.answer(
            "❌ Запись отменена.\n\n"
            "💅 <b>Главное меню</b>\n\n"
            "Выберите нужный пункт:",
            parse_mode="HTML",
            reply_markup=main_menu_kb(user_id=message.from_user.id)
        )
        return

    if not phone or len(phone) < 6:
        await message.answer(
            "❌ Пожалуйста, введите корректный номер телефона:"
        )
        return

    await state.update_data(client_phone=phone)
    await state.set_state(BookingStates.confirming)

    data = await state.get_data()
    date_obj = datetime.strptime(data["selected_date"], "%Y-%m-%d")
    date_display = date_obj.strftime("%d.%m.%Y")

    await message.answer(
        f"📋 <b>Проверьте данные записи:</b>\n\n"
        f"📅 Дата: <b>{date_display}</b>\n"
        f"🕐 Время: <b>{data['selected_time']}</b>\n"
        f"👤 Имя: <b>{data['client_name']}</b>\n"
        f"📞 Телефон: <b>{phone}</b>\n\n"
        f"Всё верно?",
        parse_mode="HTML",
        reply_markup=confirm_booking_kb()
    )


@router.callback_query(F.data == "confirm_booking", BookingStates.confirming)
async def confirm_booking(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Подтверждение записи — сохранение в БД."""
    data = await state.get_data()
    date_str = data["selected_date"]
    time_str = data["selected_time"]
    name = data["client_name"]
    phone = data["client_phone"]
    user_id = callback.from_user.id

    # Повторная проверка, нет ли уже записи
    if await has_active_booking(user_id):
        await callback.message.edit_text(
            "❗ У вас уже есть активная запись!",
            parse_mode="HTML",
            reply_markup=main_menu_kb(user_id=callback.from_user.id)
        )
        await state.clear()
        return

    # Бронируем слот
    if not await book_slot(date_str, time_str):
        await callback.message.edit_text(
            "😔 К сожалению, это время уже занято.\n"
            "Пожалуйста, выберите другое время.",
            parse_mode="HTML",
            reply_markup=main_menu_kb(user_id=callback.from_user.id)
        )
        await state.clear()
        return

    # Сохраняем запись
    booking_id = await create_booking(user_id, date_str, time_str, name, phone)

    # Планируем напоминание за 24ч
    schedule_reminder(bot, booking_id, user_id, date_str, time_str)
    # Планируем уведомление о начале сеанса
    schedule_session_start_notification(bot, booking_id, user_id, date_str, time_str)
    # Планируем запрос отзыва через 12ч после визита
    schedule_review_request(bot, booking_id, user_id, date_str, time_str)

    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    date_display = date_obj.strftime("%d.%m.%Y")

    # Уведомляем клиента
    await callback.message.edit_text(
        f"✅ <b>Запись подтверждена!</b>\n\n"
        f"📅 Дата: <b>{date_display}</b>\n"
        f"🕐 Время: <b>{time_str}</b>\n"
        f"👤 Имя: <b>{name}</b>\n"
        f"📞 Телефон: <b>{phone}</b>\n\n"
        f"Для отмены записи нажмите «📋 Мои записи» в меню.\n"
        f"За 24 часа до визита вам придёт напоминание 🔔",
        parse_mode="HTML",
        reply_markup=main_menu_kb(user_id=callback.from_user.id)
    )

    # Уведомляем администратора
    try:
        await bot.send_message(
            ADMIN_ID,
            f"🔔 <b>Новая запись!</b>\n\n"
            f"📅 Дата: <b>{date_display}</b>\n"
            f"🕐 Время: <b>{time_str}</b>\n"
            f"👤 Имя: <b>{name}</b>\n"
            f"📞 Телефон: <b>{phone}</b>\n"
            f"🆔 Telegram ID: <code>{user_id}</code>",
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"Ошибка отправки уведомления админу: {e}")

    # Публикуем в канал
    try:
        await bot.send_message(
            CHANNEL_ID,
            f"📝 <b>Новая запись</b>\n\n"
            f"📅 {date_display} в {time_str}\n"
            f"Слот занят ✅",
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"Ошибка отправки в канал: {e}")

    await state.clear()


@router.callback_query(F.data == "cancel_process")
async def cancel_booking_process(callback: CallbackQuery, state: FSMContext):
    """Отмена процесса записи."""
    await state.clear()
    await callback.message.edit_text(
        "❌ Запись отменена.\n\n"
        "💅 <b>Главное меню</b>\n"
        "Выберите нужный пункт:",
        parse_mode="HTML",
        reply_markup=main_menu_kb(user_id=callback.from_user.id)
    )
