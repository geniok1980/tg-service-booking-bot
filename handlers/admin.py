# handlers/admin.py — Админ-панель

from datetime import datetime

from aiogram import Router, Bot, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from config import ADMIN_ID
from states import AdminStates
from keyboards import (
    admin_menu_kb, admin_calendar_kb, admin_slots_kb,
    admin_bookings_kb, main_menu_kb,
    admin_portfolio_menu_kb, admin_portfolio_categories_kb, admin_portfolio_photos_kb,
    admin_location_menu_kb, admin_broadcast_confirm_kb, admin_stats_kb,
    admin_prices_menu_kb, admin_user_mgmt_kb
)
from database import (
    add_work_day, close_work_day, add_time_slot, remove_time_slot,
    get_all_slots, get_bookings_by_date, cancel_booking, unbook_slot,
    cancel_all_bookings_on_date, get_work_days_list, get_days_with_free_slots,
    # Портфолио
    get_portfolio_categories, add_portfolio_category, delete_portfolio_category,
    get_portfolio_photos, add_portfolio_photo, delete_portfolio_photo, get_portfolio_photo_count,
    # Геолокация
    get_location_settings, set_location_setting,
    # Рассылка
    get_all_client_ids, get_all_users_ids,
    # Статистика
    get_monthly_stats,
    # Пользователи
    set_user_block_status,
)
from scheduler import cancel_booking_notifications

router = Router()


def is_admin(user_id: int) -> bool:
    """Проверить, является ли пользователь администратором."""
    return user_id == ADMIN_ID


async def _get_admin_calendar_data() -> tuple[list[str], list[str]]:
    """Получить данные для админ-календаря (рабочие дни и дни со свободными слотами)."""
    work_days = await get_work_days_list()
    free_days = await get_days_with_free_slots()
    return work_days, free_days


# ===================== Вход в админ-панель =====================

@router.callback_query(F.data == "admin_panel")
async def admin_panel(callback: CallbackQuery, state: FSMContext):
    """Возврат в админ-панель (через inline-кнопку или навигацию)."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    await state.clear()
    await state.clear()
    
    text = (
        "🔧 <b>Админ-панель</b>\n\n"
        "Выберите действие:"
    )
    try:
        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=admin_menu_kb()
        )
    except Exception:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(
            text,
            parse_mode="HTML",
            reply_markup=admin_menu_kb()
        )


# ===================== Добавление рабочего дня =====================

@router.callback_query(F.data == "admin_add_day")
async def admin_add_day(callback: CallbackQuery, state: FSMContext):
    """Показать календарь для добавления рабочего дня."""
    if not is_admin(callback.from_user.id):
        return

    now = datetime.now()
    work_days = await get_work_days_list()
    await state.set_state(AdminStates.adding_day)
    await callback.message.edit_text(
        "📅 <b>Добавление рабочего дня</b>\n\n"
        "✅ — уже рабочие дни\n"
        "Выберите дату:",
        parse_mode="HTML",
        reply_markup=admin_calendar_kb(now.year, now.month, "add_day", work_days=work_days)
    )


@router.callback_query(
    F.data.startswith("adm_cal:add_day:"),
    AdminStates.adding_day
)
async def admin_add_day_select(callback: CallbackQuery, state: FSMContext):
    """Добавить выбранный день как рабочий."""
    date_str = callback.data.split(":")[2]
    result = await add_work_day(date_str)

    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    date_display = date_obj.strftime("%d.%m.%Y")

    if result:
        await callback.answer(f"✅ День {date_display} добавлен!", show_alert=True)
    else:
        await callback.answer(
            f"ℹ️ День {date_display} уже существует.", show_alert=True
        )

    # Остаёмся в календаре для добавления ещё дней
    now = datetime.now()
    work_days = await get_work_days_list()
    await callback.message.edit_text(
        "📅 <b>Добавление рабочего дня</b>\n\n"
        "✅ — уже рабочие дни\n"
        "Выберите дату (можно добавить несколько):",
        parse_mode="HTML",
        reply_markup=admin_calendar_kb(now.year, now.month, "add_day", work_days=work_days)
    )


# ===================== Добавление временного слота =====================

@router.callback_query(F.data == "admin_add_slot")
async def admin_add_slot(callback: CallbackQuery, state: FSMContext):
    """Показать календарь для выбора дня, к которому добавить слот."""
    if not is_admin(callback.from_user.id):
        return

    now = datetime.now()
    work_days, free_days = await _get_admin_calendar_data()
    await state.set_state(AdminStates.adding_slot_date)
    await callback.message.edit_text(
        "🕐 <b>Добавление временного слота</b>\n\n"
        "🔴 — нет свободных слотов\n"
        "Выберите рабочий день:",
        parse_mode="HTML",
        reply_markup=admin_calendar_kb(now.year, now.month, "add_slot",
                                       work_days=work_days,
                                       days_with_free_slots=free_days)
    )


@router.callback_query(
    F.data.startswith("adm_cal:add_slot:"),
    AdminStates.adding_slot_date
)
async def admin_add_slot_select_date(callback: CallbackQuery,
                                     state: FSMContext):
    """Выбор даты для добавления слота — запрос времени."""
    date_str = callback.data.split(":")[2]
    await state.update_data(slot_date=date_str)
    await state.set_state(AdminStates.adding_slot_time)

    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    date_display = date_obj.strftime("%d.%m.%Y")

    # Показываем текущие слоты
    slots = await get_all_slots(date_str)
    slots_text = ""
    if slots:
        slots_text = "\n\n<b>Текущие слоты:</b>\n"
        for s in slots:
            status = "🔴" if s["is_booked"] else "🟢"
            slots_text += f"{status} {s['time']}\n"

    await callback.message.edit_text(
        f"🕐 <b>Добавление слота на {date_display}</b>\n"
        f"{slots_text}\n"
        f"Введите время в формате <b>ЧЧ:ММ</b> (например, 10:00):\n\n"
        f"<i>Для отмены введите /cancel</i>",
        parse_mode="HTML"
    )


@router.message(AdminStates.adding_slot_time)
async def admin_add_slot_time(message: Message, state: FSMContext):
    """Добавление слота с указанным временем."""
    if not is_admin(message.from_user.id):
        return

    time_str = message.text.strip()

    # Валидация формата времени и приведение к ЧЧ:ММ
    try:
        dt = datetime.strptime(time_str, "%H:%M")
        time_str = dt.strftime("%H:%M")
    except ValueError:
        await message.answer(
            "❌ Неверный формат. Введите время в формате <b>ЧЧ:ММ</b> "
            "(например, 09:00):",
            parse_mode="HTML"
        )
        return

    data = await state.get_data()
    date_str = data["slot_date"]

    result = await add_time_slot(date_str, time_str)
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    date_display = date_obj.strftime("%d.%m.%Y")

    if result:
        await message.answer(
            f"✅ Слот <b>{time_str}</b> на <b>{date_display}</b> добавлен!\n\n"
            f"Введите ещё время или вернитесь в админ-панель через меню.",
            parse_mode="HTML",
            reply_markup=admin_menu_kb()
        )
    else:
        await message.answer(
            f"ℹ️ Слот <b>{time_str}</b> на <b>{date_display}</b> уже существует.\n\n"
            f"Введите другое время или вернитесь в админ-панель через меню.",
            parse_mode="HTML",
            reply_markup=admin_menu_kb()
        )


# ===================== Удаление временного слота =====================

@router.callback_query(F.data == "admin_remove_slot")
async def admin_remove_slot(callback: CallbackQuery, state: FSMContext):
    """Показать календарь для выбора дня, из которого удалить слот."""
    if not is_admin(callback.from_user.id):
        return

    now = datetime.now()
    work_days, free_days = await _get_admin_calendar_data()
    await state.set_state(AdminStates.removing_slot_date)
    await callback.message.edit_text(
        "🗑 <b>Удаление временного слота</b>\n\n"
        "🔴 — нет свободных слотов\n"
        "Выберите рабочий день:",
        parse_mode="HTML",
        reply_markup=admin_calendar_kb(now.year, now.month, "remove_slot",
                                       work_days=work_days,
                                       days_with_free_slots=free_days)
    )


@router.callback_query(
    F.data.startswith("adm_cal:remove_slot:"),
    AdminStates.removing_slot_date
)
async def admin_remove_slot_select_date(callback: CallbackQuery,
                                        state: FSMContext):
    """Показать слоты на выбранную дату для удаления."""
    date_str = callback.data.split(":")[2]
    slots = await get_all_slots(date_str)

    if not slots:
        await callback.answer("На эту дату нет слотов.", show_alert=True)
        return

    await state.set_state(AdminStates.removing_slot_time)

    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    date_display = date_obj.strftime("%d.%m.%Y")

    await callback.message.edit_text(
        f"🗑 <b>Удаление слота на {date_display}</b>\n\n"
        f"Выберите слот для удаления:\n"
        f"(🔴 — занятые слоты нельзя удалить)",
        parse_mode="HTML",
        reply_markup=admin_slots_kb(date_str, slots)
    )


@router.callback_query(
    F.data.startswith("adm_del_slot:"),
    AdminStates.removing_slot_time
)
async def admin_delete_slot(callback: CallbackQuery, state: FSMContext):
    """Удалить конкретный слот."""
    parts = callback.data.split(":", maxsplit=2)
    date_str = parts[1]
    time_str = parts[2]

    result = await remove_time_slot(date_str, time_str)

    if result:
        await callback.answer(f"✅ Слот {time_str} удалён!", show_alert=True)
    else:
        await callback.answer(
            f"❌ Не удалось удалить слот {time_str} (возможно, он занят).",
            show_alert=True
        )

    # Обновляем список слотов
    slots = await get_all_slots(date_str)
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    date_display = date_obj.strftime("%d.%m.%Y")

    if slots:
        await callback.message.edit_text(
            f"🗑 <b>Удаление слота на {date_display}</b>\n\n"
            f"Выберите слот для удаления:\n"
            f"(🔴 — занятые слоты нельзя удалить)",
            parse_mode="HTML",
            reply_markup=admin_slots_kb(date_str, slots)
        )
    else:
        await callback.message.edit_text(
            f"📭 На {date_display} больше нет слотов.",
            parse_mode="HTML",
            reply_markup=admin_menu_kb()
        )
        await state.clear()


# ===================== Закрытие дня =====================

@router.callback_query(F.data == "admin_close_day")
async def admin_close_day(callback: CallbackQuery, state: FSMContext):
    """Показать календарь для закрытия дня."""
    if not is_admin(callback.from_user.id):
        return

    now = datetime.now()
    work_days, free_days = await _get_admin_calendar_data()
    await state.set_state(AdminStates.closing_day)
    await callback.message.edit_text(
        "🚫 <b>Закрытие рабочего дня</b>\n\n"
        "🔴 — нет свободных слотов\n"
        "Выберите рабочий день для закрытия\n"
        "(все записи на этот день будут отменены!):",
        parse_mode="HTML",
        reply_markup=admin_calendar_kb(now.year, now.month, "close_day",
                                       work_days=work_days,
                                       days_with_free_slots=free_days)
    )


@router.callback_query(
    F.data.startswith("adm_cal:close_day:"),
    AdminStates.closing_day
)
async def admin_close_day_confirm(callback: CallbackQuery, state: FSMContext,
                                  bot: Bot):
    """Закрыть выбранный день."""
    date_str = callback.data.split(":")[2]

    # Отменяем все записи на этот день
    cancelled = await cancel_all_bookings_on_date(date_str)

    # Закрываем день
    await close_work_day(date_str)

    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    date_display = date_obj.strftime("%d.%m.%Y")

    # Уведомляем клиентов об отмене
    for booking in cancelled:
        cancel_booking_notifications(booking["id"])
        try:
            await bot.send_message(
                booking["user_id"],
                f"😔 <b>Запись отменена мастером</b>\n\n"
                f"К сожалению, ваша запись на <b>{date_display}</b> "
                f"в <b>{booking['time']}</b> была отменена.\n\n"
                f"Пожалуйста, выберите другую дату. Приносим извинения!",
                parse_mode="HTML"
            )
        except Exception:
            pass

    cancelled_count = len(cancelled)
    text = f"✅ <b>День {date_display} закрыт!</b>"
    if cancelled_count > 0:
        text += f"\n\n❌ Отменено записей: {cancelled_count}"
        text += "\nКлиенты уведомлены."

    await callback.message.edit_text(
        text, parse_mode="HTML", reply_markup=admin_menu_kb()
    )
    await state.clear()


# ===================== Отмена записи клиента (админом) =====================

@router.callback_query(F.data == "admin_cancel_booking")
async def admin_cancel_booking(callback: CallbackQuery, state: FSMContext):
    """Показать календарь для выбора даты с записями."""
    if not is_admin(callback.from_user.id):
        return

    now = datetime.now()
    work_days, free_days = await _get_admin_calendar_data()
    await state.set_state(AdminStates.cancelling_booking)
    await callback.message.edit_text(
        "❌ <b>Отмена записи клиента</b>\n\n"
        "🔴 — нет свободных слотов\n"
        "Выберите рабочий день:",
        parse_mode="HTML",
        reply_markup=admin_calendar_kb(now.year, now.month, "cancel_bk",
                                       work_days=work_days,
                                       days_with_free_slots=free_days)
    )


@router.callback_query(
    F.data.startswith("adm_cal:cancel_bk:"),
    AdminStates.cancelling_booking
)
async def admin_cancel_booking_select_date(callback: CallbackQuery,
                                           state: FSMContext):
    """Показать записи на выбранную дату."""
    date_str = callback.data.split(":")[2]
    bookings = await get_bookings_by_date(date_str)

    if not bookings:
        await callback.answer("На эту дату нет записей.", show_alert=True)
        return

    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    date_display = date_obj.strftime("%d.%m.%Y")

    await callback.message.edit_text(
        f"❌ <b>Записи на {date_display}</b>\n\n"
        f"Выберите запись для отмены:",
        parse_mode="HTML",
        reply_markup=admin_bookings_kb(date_str, bookings)
    )


@router.callback_query(
    F.data.startswith("adm_cancel_bk:"),
    AdminStates.cancelling_booking
)
async def admin_cancel_booking_confirm(callback: CallbackQuery,
                                       state: FSMContext, bot: Bot):
    """Отменить конкретную запись (админом)."""
    booking_id = int(callback.data.split(":")[1])

    booking = await cancel_booking(booking_id)
    if not booking:
        await callback.answer("Запись не найдена.", show_alert=True)
        return

    # Освобождаем слот
    await unbook_slot(booking["date"], booking["time"])

    # Отменяем напоминание
    cancel_reminder(booking_id)

    date_obj = datetime.strptime(booking["date"], "%Y-%m-%d")
    date_display = date_obj.strftime("%d.%m.%Y")

    # Уведомляем клиента
    try:
        await bot.send_message(
            booking["user_id"],
            f"😔 <b>Ваша запись отменена</b>\n\n"
            f"Запись на <b>{date_display}</b> в <b>{booking['time']}</b> "
            f"была отменена мастером.\n\n"
            f"Пожалуйста, выберите другое время. Приносим извинения!",
            parse_mode="HTML"
        )
    except Exception:
        pass

    await callback.message.edit_text(
        f"✅ <b>Запись отменена</b>\n\n"
        f"👤 {booking['name']}\n"
        f"📅 {date_display} в {booking['time']}\n"
        f"Клиент уведомлён.",
        parse_mode="HTML",
        reply_markup=admin_menu_kb()
    )
    await state.clear()


# ===================== Просмотр расписания =====================

@router.callback_query(F.data == "admin_view_schedule")
async def admin_view_schedule(callback: CallbackQuery, state: FSMContext):
    """Показать календарь для просмотра расписания."""
    if not is_admin(callback.from_user.id):
        return

    now = datetime.now()
    work_days = await get_work_days_list()
    await state.set_state(AdminStates.viewing_schedule)
    await callback.message.edit_text(
        "📊 <b>Просмотр расписания</b>\n\n"
        "🗓 — ваши рабочие дни\n"
        "Выберите дату:",
        parse_mode="HTML",
        reply_markup=admin_calendar_kb(now.year, now.month, "view_sched", work_days=work_days)
    )


@router.callback_query(
    F.data.startswith("adm_cal:view_sched:"),
    AdminStates.viewing_schedule
)
async def admin_view_schedule_date(callback: CallbackQuery,
                                   state: FSMContext):
    """Показать расписание на выбранную дату."""
    date_str = callback.data.split(":")[2]
    slots = await get_all_slots(date_str)
    bookings = await get_bookings_by_date(date_str)

    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    date_display = date_obj.strftime("%d.%m.%Y")

    text = f"📊 <b>Расписание на {date_display}</b>\n\n"

    if not slots:
        text += "📭 Слотов нет.\n"
    else:
        # Создаём словарь записей по времени для быстрого поиска
        bookings_by_time = {b["time"]: b for b in bookings}

        for slot in slots:
            if slot["is_booked"] and slot["time"] in bookings_by_time:
                b = bookings_by_time[slot["time"]]
                text += (
                    f"🔴 <b>{slot['time']}</b> — {b['name']} "
                    f"({b['phone']})\n"
                )
            elif slot["is_booked"]:
                text += f"🔴 <b>{slot['time']}</b> — занято\n"
            else:
                text += f"🟢 <b>{slot['time']}</b> — свободно\n"

    text += f"\n📋 Всего записей: {len(bookings)}"

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")]
    ])

    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)


# ===================== Навигация в админ-календаре =====================

@router.callback_query(F.data.startswith("adm_nav:"))
async def admin_calendar_navigate(callback: CallbackQuery):
    """Навигация по календарю в админ-панели."""
    parts = callback.data.split(":")
    action = parts[1]
    year = int(parts[2])
    month = int(parts[3])

    # Для действий с фильтрацией или выделением — подгружаем данные о рабочих днях
    if action in ("add_slot", "remove_slot", "close_day", "cancel_bk", "add_day", "view_sched"):
        work_days, free_days = await _get_admin_calendar_data()
        await callback.message.edit_reply_markup(
            reply_markup=admin_calendar_kb(year, month, action,
                                           work_days=work_days,
                                           days_with_free_slots=free_days)
        )
    else:
        await callback.message.edit_reply_markup(
            reply_markup=admin_calendar_kb(year, month, action)
        )


# ===================== Портфолио (управление) =====================

@router.callback_query(F.data == "admin_portfolio")
async def admin_portfolio(callback: CallbackQuery, state: FSMContext):
    """Меню управления портфолио."""
    if not is_admin(callback.from_user.id):
        return
    await state.clear()
    await callback.message.edit_text(
        "🖼 <b>Управление портфолио</b>\n\nВыберите действие:",
        parse_mode="HTML",
        reply_markup=admin_portfolio_menu_kb()
    )


@router.callback_query(F.data == "adm_portfolio_add_cat")
async def admin_portfolio_add_cat_start(callback: CallbackQuery, state: FSMContext):
    """Ввод названия новой категории."""
    if not is_admin(callback.from_user.id):
        return
    await state.set_state(AdminStates.portfolio_add_category)
    await callback.message.edit_text(
        "🖼 <b>Добавление категории</b>\n\nВведите название новой категории:",
        parse_mode="HTML"
    )


@router.message(AdminStates.portfolio_add_category)
async def admin_portfolio_add_cat_done(message: Message, state: FSMContext):
    """Сохранить новую категорию."""
    if not is_admin(message.from_user.id):
        return
    name = message.text.strip()
    result = await add_portfolio_category(name)
    if result:
        await message.answer(f"✅ Категория «{name}» добавлена!", reply_markup=admin_portfolio_menu_kb())
    else:
        await message.answer(f"ℹ️ Категория «{name}» уже существует.", reply_markup=admin_portfolio_menu_kb())
    await state.clear()


@router.callback_query(F.data == "adm_portfolio_del_cat")
async def admin_portfolio_del_cat_list(callback: CallbackQuery, state: FSMContext):
    """Показать список категорий для удаления."""
    if not is_admin(callback.from_user.id):
        return
    categories = await get_portfolio_categories()
    if not categories:
        await callback.answer("Категорий ещё нет.", show_alert=True)
        return
    # Добавляем кол-во фото к каждой категории
    for cat in categories:
        cat["photo_count"] = await get_portfolio_photo_count(cat["id"])
    await state.set_state(AdminStates.portfolio_del_category)
    await callback.message.edit_text(
        "🗑 <b>Удаление категории</b>\n\n"
        "⚠️ Вместе с категорией удалятся все её фото!\n"
        "Выберите категорию для удаления:",
        parse_mode="HTML",
        reply_markup=admin_portfolio_categories_kb(categories, "del")
    )


@router.callback_query(F.data.startswith("adm_pcat:del:"), AdminStates.portfolio_del_category)
async def admin_portfolio_del_cat_confirm(callback: CallbackQuery, state: FSMContext):
    """Удалить категорию."""
    category_id = int(callback.data.split(":")[2])
    await delete_portfolio_category(category_id)
    await state.clear()
    await callback.answer("✅ Категория удалена.", show_alert=True)
    await callback.message.edit_text(
        "🖼 <b>Управление портфолио</b>\n\nВыберите действие:",
        parse_mode="HTML",
        reply_markup=admin_portfolio_menu_kb()
    )


@router.callback_query(F.data == "adm_portfolio_add_photo")
async def admin_portfolio_add_photo_select_cat(callback: CallbackQuery, state: FSMContext):
    """Выбор категории для добавления фото."""
    if not is_admin(callback.from_user.id):
        return
    categories = await get_portfolio_categories()
    if not categories:
        await callback.answer("Сначала добавьте хотя бы одну категорию.", show_alert=True)
        return
    await state.set_state(AdminStates.portfolio_select_cat)
    await callback.message.edit_text(
        "📷 <b>Добавление фото</b>\n\nВыберите категорию:",
        parse_mode="HTML",
        reply_markup=admin_portfolio_categories_kb(categories, "add_photo")
    )


@router.callback_query(F.data.startswith("adm_pcat:add_photo:"), AdminStates.portfolio_select_cat)
async def admin_portfolio_add_photo_request(callback: CallbackQuery, state: FSMContext):
    """Запросить фото для загрузки."""
    category_id = int(callback.data.split(":")[2])
    await state.update_data(photo_cat_id=category_id)
    await state.set_state(AdminStates.portfolio_add_photo)
    await callback.message.edit_text(
        "📷 <b>Загрузка фото</b>\n\n"
        "Отправьте фото (можно с подписью).\n"
        "Для отмены введите /cancel или вернитесь через меню.",
        parse_mode="HTML"
    )


@router.message(AdminStates.portfolio_add_photo, F.photo)
async def admin_portfolio_save_photo(message: Message, state: FSMContext):
    """Сохранить загруженное фото."""
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    category_id = data.get("photo_cat_id")
    file_id = message.photo[-1].file_id
    caption = message.caption or ""
    await add_portfolio_photo(category_id, file_id, caption)
    await message.answer(
        "✅ Фото добавлено в портфолио!\n\nОтправьте ещё фото или вернитесь в меню.",
        reply_markup=admin_portfolio_menu_kb()
    )
    # Остаёмся в состоянии для добавления следующего фото
    await state.set_state(AdminStates.portfolio_add_photo)


@router.callback_query(F.data == "adm_portfolio_del_photo")
async def admin_portfolio_del_photo_select_cat(callback: CallbackQuery, state: FSMContext):
    """Выбор категории для удаления фото."""
    if not is_admin(callback.from_user.id):
        return
    categories = await get_portfolio_categories()
    if not categories:
        await callback.answer("Категорий и фото ещё нет.", show_alert=True)
        return
    for cat in categories:
        cat["photo_count"] = await get_portfolio_photo_count(cat["id"])
    await state.set_state(AdminStates.portfolio_del_photo)
    await callback.message.edit_text(
        "❌ <b>Удаление фото</b>\n\nВыберите категорию:",
        parse_mode="HTML",
        reply_markup=admin_portfolio_categories_kb(categories, "del_photo")
    )


@router.callback_query(F.data.startswith("adm_pcat:del_photo:"), AdminStates.portfolio_del_photo)
async def admin_portfolio_del_photo_list(callback: CallbackQuery, state: FSMContext):
    """Показать фото категории для удаления."""
    category_id = int(callback.data.split(":")[2])
    photos = await get_portfolio_photos(category_id)
    if not photos:
        await callback.answer("В этой категории нет фото.", show_alert=True)
        return
    await callback.message.edit_text(
        "❌ <b>Удаление фото</b>\n\nВыберите фото для удаления:",
        parse_mode="HTML",
        reply_markup=admin_portfolio_photos_kb(photos, category_id)
    )


@router.callback_query(F.data.startswith("adm_del_photo:"))
async def admin_portfolio_del_photo_confirm(callback: CallbackQuery, state: FSMContext):
    """Удалить конкретное фото."""
    photo_id = int(callback.data.split(":")[1])
    await delete_portfolio_photo(photo_id)
    await state.clear()
    await callback.answer("✅ Фото удалено.", show_alert=True)
    await callback.message.edit_text(
        "🖼 <b>Управление портфолио</b>\n\nВыберите действие:",
        parse_mode="HTML",
        reply_markup=admin_portfolio_menu_kb()
    )


# ===================== Геолокация (управление) =====================

@router.callback_query(F.data == "admin_location")
async def admin_location(callback: CallbackQuery, state: FSMContext):
    """Меню редактирования адреса."""
    if not is_admin(callback.from_user.id):
        return
    await state.clear()
    settings = await get_location_settings()
    address = settings.get("address", "Не задан")
    lat = settings.get("lat", "—")
    lon = settings.get("lon", "—")
    await callback.message.edit_text(
        f"📍 <b>Настройки адреса</b>\n\n"
        f"<b>Текущий адрес:</b> {address}\n"
        f"<b>Координаты:</b> {lat}, {lon}",
        parse_mode="HTML",
        reply_markup=admin_location_menu_kb()
    )


@router.callback_query(F.data == "adm_loc_coords")
async def admin_location_coords_start(callback: CallbackQuery, state: FSMContext):
    """Запросить новые координаты."""
    if not is_admin(callback.from_user.id):
        return
    await state.set_state(AdminStates.location_edit_lat)
    await callback.message.edit_text(
        "🗺 <b>Изменение координат</b>\n\n"
        "Введите координаты в формате:\n"
        "<code>55.7558, 37.6176</code>\n"
        "(широта, долгота через запятую)\n\n"
        "<i>Для отмены введите /cancel</i>",
        parse_mode="HTML"
    )


@router.message(AdminStates.location_edit_lat)
async def admin_location_coords_save(message: Message, state: FSMContext):
    """Сохранить новые координаты."""
    if not is_admin(message.from_user.id):
        return
    try:
        parts = message.text.replace(" ", "").split(",")
        lat = float(parts[0])
        lon = float(parts[1])
        assert -90 <= lat <= 90 and -180 <= lon <= 180
    except Exception:
        await message.answer(
            "❌ Неверный формат. Введите координаты через запятую:\n"
            "<code>55.7558, 37.6176</code>",
            parse_mode="HTML"
        )
        return
    await set_location_setting("lat", str(lat))
    await set_location_setting("lon", str(lon))
    await state.clear()
    await message.answer(
        f"✅ Координаты обновлены: {lat}, {lon}",
        reply_markup=admin_location_menu_kb()
    )


@router.callback_query(F.data == "adm_loc_address")
async def admin_location_address_start(callback: CallbackQuery, state: FSMContext):
    """Запросить текстовый адрес."""
    if not is_admin(callback.from_user.id):
        return
    await state.set_state(AdminStates.location_edit_address)
    await callback.message.edit_text(
        "📝 <b>Изменение адреса</b>\n\n"
        "Введите текстовый адрес студии:\n\n"
        "<i>Для отмены введите /cancel</i>",
        parse_mode="HTML"
    )


@router.message(AdminStates.location_edit_address)
async def admin_location_address_save(message: Message, state: FSMContext):
    """Сохранить текстовый адрес."""
    if not is_admin(message.from_user.id):
        return
    await set_location_setting("address", message.text.strip())
    await state.clear()
    await message.answer(
        f"✅ Адрес обновлён:\n{message.text.strip()}",
        reply_markup=admin_location_menu_kb()
    )


@router.callback_query(F.data == "adm_loc_photo")
async def admin_location_photo_start(callback: CallbackQuery, state: FSMContext):
    """Запросить фото-инструкцию для маршрута."""
    if not is_admin(callback.from_user.id):
        return
    await state.set_state(AdminStates.location_edit_photo)
    await callback.message.edit_text(
        "🖼 <b>Фото-инструкция</b>\n\n"
        "Отправьте фото с пояснением, как добраться.\n"
        "Оно будет показано всем клиентам при нажатии «Как добраться».\n\n"
        "<i>Для отмены введите /cancel</i>",
        parse_mode="HTML"
    )


@router.message(AdminStates.location_edit_photo, F.photo)
async def admin_location_photo_save(message: Message, state: FSMContext):
    """Сохранить фото-инструкцию."""
    if not is_admin(message.from_user.id):
        return
    file_id = message.photo[-1].file_id
    await set_location_setting("directions_file_id", file_id)
    await state.clear()
    await message.answer(
        "✅ Фото-инструкция обновлена!",
        reply_markup=admin_location_menu_kb()
    )


@router.callback_query(F.data == "adm_loc_del_photo")
async def admin_location_photo_delete(callback: CallbackQuery):
    """Удалить фото-инструкцию для маршрута."""
    if not is_admin(callback.from_user.id):
        return
    await set_location_setting("directions_file_id", "")
    await callback.answer("✅ Фото-инструкция удалена.", show_alert=True)
    
    settings = await get_location_settings()
    address = settings.get("address", "Не задан")
    lat = settings.get("lat", "—")
    lon = settings.get("lon", "—")
    await callback.message.edit_text(
        f"📍 <b>Настройки адреса</b>\n\n"
        f"<b>Текущий адрес:</b> {address}\n"
        f"<b>Координаты:</b> {lat}, {lon}",
        parse_mode="HTML",
        reply_markup=admin_location_menu_kb()
    )


# ===================== Рассылка =====================

@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_start(callback: CallbackQuery, state: FSMContext):
    """Начать рассылку — запросить текст."""
    if not is_admin(callback.from_user.id):
        return
    user_ids = await get_all_users_ids()
    if not user_ids:
        await callback.answer(
            "Нет пользователей для рассылки.",
            show_alert=True
        )
        return
    await state.set_state(AdminStates.broadcasting)
    await callback.message.edit_text(
        f"📢 <b>Рассылка</b>\n\n"
        f"Получателей: <b>{len(user_ids)}</b> (все, кто когда-либо писал боту)\n\n"
        f"Введите текст сообщения (поддерживается HTML):\n\n"
        f"<i>Для отмены введите /cancel</i>",
        parse_mode="HTML"
    )


@router.message(AdminStates.broadcasting)
async def admin_broadcast_preview(message: Message, state: FSMContext):
    """Показать превью сообщения рассылки и запросить подтверждение."""
    if not is_admin(message.from_user.id):
        return
    
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Рассылка отменена.", reply_markup=admin_menu_kb())
        return

    await state.update_data(broadcast_text=message.text)
    await state.set_state(AdminStates.broadcast_confirm)
    await message.answer(
        f"📋 <b>Превью сообщения:</b>\n\n{message.text}\n\n"
        f"Отправить это сообщение всем пользователям?",
        parse_mode="HTML",
        reply_markup=admin_broadcast_confirm_kb()
    )


@router.callback_query(F.data == "adm_broadcast_confirm", AdminStates.broadcast_confirm)
async def admin_broadcast_send(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Выполнить рассылку."""
    import asyncio
    data = await state.get_data()
    text = data.get("broadcast_text", "")
    user_ids = await get_all_users_ids()

    await state.clear()
    await callback.message.edit_text(
        f"📤 Отправка... 0/{len(user_ids)}",
        parse_mode="HTML"
    )

    sent, failed = 0, 0
    for i, uid in enumerate(user_ids):
        try:
            await bot.send_message(uid, text, parse_mode="HTML")
            sent += 1
        except Exception:
            failed += 1
        
        # Обновляем прогресс каждые 10 сообщений
        if (i + 1) % 10 == 0:
            try:
                await callback.message.edit_text(
                    f"📤 Отправка... {i+1}/{len(user_ids)}",
                    parse_mode="HTML"
                )
            except Exception:
                pass
        
        await asyncio.sleep(0.05)  # Защита от лимитов Telegram

    await callback.message.edit_text(
        f"✅ <b>Рассылка завершена!</b>\n\n"
        f"Успешно: <b>{sent}</b>\n"
        f"Ошибок: <b>{failed}</b>",
        parse_mode="HTML",
        reply_markup=admin_menu_kb()
    )

    await callback.message.edit_text(
        f"✅ <b>Рассылка завершена!</b>\n\n"
        f"Отправлено: {sent}\n"
        f"Не доставлено: {failed}",
        parse_mode="HTML",
        reply_markup=admin_menu_kb()
    )


# ===================== Статистика =====================

@router.callback_query(F.data == "admin_stats")
async def admin_stats_select(callback: CallbackQuery):
    """Выбор периода для статистики."""
    if not is_admin(callback.from_user.id):
        return
    await callback.message.edit_text(
        "📈 <b>Статистика</b>\n\nВыберите период:",
        parse_mode="HTML",
        reply_markup=admin_stats_kb()
    )


@router.callback_query(F.data.startswith("adm_stats:"))
async def admin_stats_show(callback: CallbackQuery):
    """Показать статистику за выбранный месяц."""
    if not is_admin(callback.from_user.id):
        return
    _, year_str, month_str = callback.data.split(":")
    year, month = int(year_str), int(month_str)

    stats = await get_monthly_stats(year, month)
    month_names = [
        "", "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
        "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
    ]
    month_name = month_names[month]

    rating_text = (
        f"⭐ {stats['avg_rating']}/5 ({stats['review_count']} отзывов)"
        if stats["avg_rating"]
        else "— отзывов нет"
    )

    await callback.message.edit_text(
        f"📈 <b>Итоги: {month_name} {year}</b>\n\n"
        f"📝 Записей: <b>{stats['total_bookings']}</b>\n"
        f"👥 Новых клиентов: <b>{stats['new_clients']}</b>\n"
        f"📅 Рабочих дней: <b>{stats['work_days']}</b>\n"
        f"Средний рейтинг: <b>{rating_text}</b>",
        parse_mode="HTML",
        reply_markup=admin_stats_kb()
    )


# ===================== Прайсы (управление) =====================

@router.callback_query(F.data == "admin_prices")
async def admin_prices(callback: CallbackQuery, state: FSMContext):
    """Меню управления прайсами."""
    if not is_admin(callback.from_user.id):
        return
    await state.clear()
    
    settings = await get_location_settings()
    price_text = settings.get("prices_text", "")
    price_photo_id = settings.get("prices_photo_id", "")
    
    status_text = "❌ Не задан" if not price_text else "✅ Задан"
    status_photo = "❌ Не загружено" if not price_photo_id else "✅ Загружено"

    await callback.message.edit_text(
        f"💅 <b>Настройки прайса</b>\n\n"
        f"<b>Текст прайса:</b> {status_text}\n"
        f"<b>Фото прайса:</b> {status_photo}\n\n"
        f"<i>Вы можете добавить или только текст, или только фото, или и то, и другое.</i>",
        parse_mode="HTML",
        reply_markup=admin_prices_menu_kb()
    )


@router.callback_query(F.data == "adm_price_edit_text")
async def admin_price_edit_text_start(callback: CallbackQuery, state: FSMContext):
    """Запросить новый текст прайса."""
    if not is_admin(callback.from_user.id):
        return
    await state.set_state(AdminStates.prices_edit_text)
    
    settings = await get_location_settings()
    current_text = settings.get("prices_text", "")
    if current_text:
        current_text = f"\n<b>Текущий текст:</b>\n<i>{current_text}</i>\n\n"
    
    await callback.message.edit_text(
        f"📝 <b>Текст прайс-листа</b>\n{current_text}"
        "Введите новый текст прайс-листа:\n\n"
        "<i>Для отмены введите /cancel</i>",
        parse_mode="HTML"
    )


@router.message(AdminStates.prices_edit_text)
async def admin_price_edit_text_save(message: Message, state: FSMContext):
    """Сохранить новый текст прайса."""
    if not is_admin(message.from_user.id):
        return
    await set_location_setting("prices_text", message.text)
    await state.clear()
    await message.answer("✅ Текст прайса обновлён!", reply_markup=admin_prices_menu_kb())


@router.callback_query(F.data == "adm_price_del_text")
async def admin_price_edit_text_delete(callback: CallbackQuery):
    """Удалить текст прайса."""
    if not is_admin(callback.from_user.id):
        return
    await set_location_setting("prices_text", "")
    await callback.answer("✅ Текст прайса удалён.", show_alert=True)
    
    settings = await get_location_settings()
    price_photo_id = settings.get("prices_photo_id", "")
    status_photo = "❌ Не загружено" if not price_photo_id else "✅ Загружено"

    await callback.message.edit_text(
        f"💅 <b>Настройки прайса</b>\n\n"
        f"<b>Текст прайса:</b> ❌ Не задан\n"
        f"<b>Фото прайса:</b> {status_photo}\n\n"
        f"<i>Вы можете добавить или только текст, или только фото, или и то, и другое.</i>",
        parse_mode="HTML",
        reply_markup=admin_prices_menu_kb()
    )


@router.callback_query(F.data == "adm_price_edit_photo")
async def admin_price_edit_photo_start(callback: CallbackQuery, state: FSMContext):
    """Запросить фото прайса."""
    if not is_admin(callback.from_user.id):
        return
    await state.set_state(AdminStates.prices_edit_photo)
    await callback.message.edit_text(
        "🖼 <b>Фото прайс-листа</b>\n\n"
        "Отправьте фото, на котором изображен ваш прайс.\n\n"
        "<i>Для отмены введите /cancel</i>",
        parse_mode="HTML"
    )


@router.message(AdminStates.prices_edit_photo, F.photo)
async def admin_price_edit_photo_save(message: Message, state: FSMContext):
    """Сохранить фото прайса."""
    if not is_admin(message.from_user.id):
        return
    file_id = message.photo[-1].file_id
    await set_location_setting("prices_photo_id", file_id)
    await state.clear()
    await message.answer("✅ Фото прайса загружено!", reply_markup=admin_prices_menu_kb())


@router.callback_query(F.data == "adm_price_del_photo")
async def admin_price_edit_photo_delete(callback: CallbackQuery):
    """Удалить фото прайса."""
    if not is_admin(callback.from_user.id):
        return
    await set_location_setting("prices_photo_id", "")
    await callback.answer("✅ Фото прайса удалено.", show_alert=True)
    
    settings = await get_location_settings()
    price_text = settings.get("prices_text", "")
    status_text = "❌ Не задан" if not price_text else "✅ Задан"

    await callback.message.edit_text(
        f"💅 <b>Настройки прайса</b>\n\n"
        f"<b>Текст прайса:</b> {status_text}\n"
        f"<b>Фото прайса:</b> ❌ Не загружено\n\n"
        f"<i>Вы можете добавить или только текст, или только фото, или и то, и другое.</i>",
        parse_mode="HTML",
        reply_markup=admin_prices_menu_kb()
    )


# ===================== Управление пользователями =====================

@router.callback_query(F.data == "admin_users")
async def admin_users_menu(callback: CallbackQuery):
    """Меню управления пользователями."""
    if not is_admin(callback.from_user.id):
        return
    await callback.message.edit_text(
        "👥 <b>Управление пользователями</b>\n\n"
        "Вы можете заблокировать или разблокировать пользователя по его @username.\n"
        "<i>Примечание: Бот должен был 'видеть' пользователя хотя бы раз, чтобы блок сработал.</i>",
        parse_mode="HTML",
        reply_markup=admin_user_mgmt_kb()
    )


@router.callback_query(F.data == "adm_user_block")
async def admin_user_block_start(callback: CallbackQuery, state: FSMContext):
    """Начало блокировки — запрос username."""
    if not is_admin(callback.from_user.id):
        return
    await state.set_state(AdminStates.blocking_user)
    await callback.message.edit_text(
        "🚫 <b>Блокировка пользователя</b>\n\n"
        "Введите @username пользователя, которого хотите заблокировать:\n\n"
        "<i>Введите /cancel для отмены</i>",
        parse_mode="HTML"
    )


@router.callback_query(F.data == "adm_user_unblock")
async def admin_user_unblock_start(callback: CallbackQuery, state: FSMContext):
    """Начало разблокировки — запрос username."""
    if not is_admin(callback.from_user.id):
        return
    await state.set_state(AdminStates.unblocking_user)
    await callback.message.edit_text(
        "✅ <b>Разблокировка пользователя</b>\n\n"
        "Введите @username пользователя, которого хотите разблокировать:\n\n"
        "<i>Введите /cancel для отмены</i>",
        parse_mode="HTML"
    )


@router.message(AdminStates.blocking_user)
async def admin_process_user_block(message: Message, state: FSMContext):
    """Процесс блокировки."""
    if not is_admin(message.from_user.id):
        return
    
    tag = message.text.strip()
    if tag == "/cancel":
        await state.clear()
        await message.answer("❌ Отменено", reply_markup=admin_menu_kb())
        return

    # Убираем @ для поиска
    clean_tag = tag.lstrip('@')
    
    if await set_user_block_status(clean_tag, 1):
        await message.answer(f"✅ Пользователь <b>{tag}</b> заблокирован.", parse_mode="HTML", reply_markup=admin_menu_kb())
        await state.clear()
    else:
        # Если не найден ИЛИ это админ
        await message.answer(
            f"❌ Не удалось заблокировать <b>{tag}</b>.\n\n"
            "Возможные причины:\n"
            "1. Это ваш собственный аккаунт (админа нельзя забанить).\n"
            "2. Пользователь не найден в базе (он должен был хоть раз написать боту).\n"
            "3. Ошибка в написании @username.\n\n"
            "Попробуйте заново или введите /cancel:",
            parse_mode="HTML"
        )


@router.message(AdminStates.unblocking_user)
async def admin_process_user_unblock(message: Message, state: FSMContext):
    """Процесс разблокировки."""
    if not is_admin(message.from_user.id):
        return
    
    tag = message.text.strip()
    if tag == "/cancel":
        await state.clear()
        await message.answer("❌ Отменено", reply_markup=admin_menu_kb())
        return

    # Убираем @ для поиска
    clean_tag = tag.lstrip('@')
    
    if await set_user_block_status(clean_tag, 0):
        await message.answer(f"✅ Пользователь <b>{tag}</b> разблокирован.", parse_mode="HTML", reply_markup=admin_menu_kb())
        await state.clear()
    else:
        await message.answer(
            f"❌ Пользователь <b>{tag}</b> не найден в базе.\n\n"
            "Попробуйте заново или введите /cancel:",
            parse_mode="HTML"
        )
