# keyboards.py — Inline-клавиатуры бота

import calendar
from datetime import datetime, timedelta

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import CHANNEL_LINK, ADMIN_ID


# ===================== Главное меню =====================

def main_menu_kb(user_id: int | None = None) -> InlineKeyboardMarkup:
    """Клавиатура главного меню. Если user_id == ADMIN_ID, показываем кнопку админ-панели."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📝 Записаться", callback_data="book")
    )
    builder.row(
        InlineKeyboardButton(text="📋 Мои записи", callback_data="my_bookings")
    )
    builder.row(
        InlineKeyboardButton(text="💅 Прайсы", callback_data="prices"),
        InlineKeyboardButton(text="📸 Наши работы", callback_data="portfolio_cats")
    )
    builder.row(
        InlineKeyboardButton(text="📍 Как добраться", callback_data="how_to_find")
    )
    # Кнопка админ-панели видна только администратору
    if user_id is not None and user_id == ADMIN_ID:
        builder.row(
            InlineKeyboardButton(text="🔧 Админ-панель", callback_data="admin_panel")
        )
    return builder.as_markup()


# ===================== Проверка подписки =====================

def subscription_kb() -> InlineKeyboardMarkup:
    """Клавиатура проверки подписки на канал."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📢 Подписаться", url=CHANNEL_LINK)
    )
    builder.row(
        InlineKeyboardButton(text="✅ Проверить подписку", callback_data="check_subscription")
    )
    return builder.as_markup()


# ===================== Календарь (клиент) =====================

def calendar_kb(year: int, month: int, work_days: list[str],
                available_days: list[str]) -> InlineKeyboardMarkup:
    """
    Inline-календарь на месяц для клиента.
    work_days — все незакрытые рабочие дни.
    available_days — список дат ('YYYY-MM-DD'), на которых есть свободные (будущие) слоты.
    Рабочие дни со свободными слотами — число (кликабельное).
    Нерабочие / без слотов — «•» (неактивная).
    Занятые полностью дни — «🔴 День».
    Прошедшие — «·».
    """
    builder = InlineKeyboardBuilder()

    # Заголовок: название месяца и год
    month_names = [
        "", "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
        "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
    ]
    builder.row(
        InlineKeyboardButton(
            text=f"📅 {month_names[month]} {year}",
            callback_data="ignore"
        )
    )

    # Дни недели
    week_days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    builder.row(*[
        InlineKeyboardButton(text=d, callback_data="ignore")
        for d in week_days
    ])

    # Дни месяца
    cal = calendar.monthcalendar(year, month)
    today = datetime.now().date()

    for week in cal:
        row_buttons = []
        for day in week:
            if day == 0:
                row_buttons.append(
                    InlineKeyboardButton(text=" ", callback_data="ignore")
                )
            else:
                date_str = f"{year}-{month:02d}-{day:02d}"
                date_obj = datetime(year, month, day).date()

                if date_obj < today:
                    # Прошедшие дни — неактивны
                    row_buttons.append(
                        InlineKeyboardButton(text="·", callback_data="ignore")
                    )
                elif date_str in available_days:
                    # Рабочий день со свободными слотами
                    row_buttons.append(
                        InlineKeyboardButton(
                            text=str(day),
                            callback_data=f"cal_day:{date_str}"
                        )
                    )
                elif date_str in work_days:
                    # Рабочий день, но все слоты заняты или прошли
                    row_buttons.append(
                        InlineKeyboardButton(
                            text=f"🔴 {day}",
                            callback_data=f"cal_day:{date_str}"
                        )
                    )
                else:
                    # Нерабочий день
                    row_buttons.append(
                        InlineKeyboardButton(
                            text="•",
                            callback_data="ignore"
                        )
                    )
        builder.row(*row_buttons)

    # Навигация между месяцами
    nav_buttons = []

    # Кнопка "назад" — только если предыдущий месяц >= текущий
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    if datetime(prev_year, prev_month, 1).date() >= today.replace(day=1):
        nav_buttons.append(
            InlineKeyboardButton(
                text="◀️",
                callback_data=f"cal_nav:{prev_year}:{prev_month}"
            )
        )

    # Кнопка "вперёд" — максимум 1 месяц вперёд от текущего
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1
    max_date = today + timedelta(days=31)
    if datetime(next_year, next_month, 1).date() <= max_date:
        nav_buttons.append(
            InlineKeyboardButton(
                text="▶️",
                callback_data=f"cal_nav:{next_year}:{next_month}"
            )
        )

    if nav_buttons:
        builder.row(*nav_buttons)

    # Кнопка "Назад в меню"
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")
    )

    return builder.as_markup()


# ===================== Временные слоты =====================

def time_slots_kb(date: str, slots: list[str]) -> InlineKeyboardMarkup:
    """Клавиатура доступных временных слотов."""
    builder = InlineKeyboardBuilder()

    for slot in slots:
        builder.row(
            InlineKeyboardButton(
                text=f"🕐 {slot}",
                callback_data=f"slot:{date}:{slot}"
            )
        )

    builder.row(
        InlineKeyboardButton(text="🔙 Назад к календарю", callback_data="back_to_calendar")
    )
    return builder.as_markup()


# ===================== Подтверждение =====================

def confirm_booking_kb() -> InlineKeyboardMarkup:
    """Клавиатура подтверждения записи."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_booking"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_process")
    )
    return builder.as_markup()


def cancel_booking_kb(booking_id: int) -> InlineKeyboardMarkup:
    """Клавиатура отмены записи клиентом."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="❌ Отменить запись",
            callback_data=f"cancel_my_booking:{booking_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")
    )
    return builder.as_markup()


# ===================== Портфолио =====================

def portfolio_kb() -> InlineKeyboardMarkup:
    """Клавиатура с ссылкой на портфолио."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="🖼 Смотреть портфолио",
            url="https://ru.pinterest.com/crystalwithluv/_created/"
        )
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")
    )
    return builder.as_markup()


def admin_calendar_kb(year: int, month: int, action: str,
                      work_days: list[str] | None = None,
                      days_with_free_slots: list[str] | None = None) -> InlineKeyboardMarkup:
    """
    Календарь для админа (выбор даты для различных действий).
    action — тип действия (add_day, add_slot, remove_slot, close_day, cancel_bk, view_sched)
    work_days — список рабочих (незакрытых) дней
    days_with_free_slots — список дней с хотя бы одним свободным слотом

    Логика отображения:
    - add_day: все будущие дни кликабельные (рабочие дни не нужны для фильтрации)
    - add_slot, remove_slot, close_day, cancel_bk: только рабочие дни кликабельные
      - Если слоты закончились (нет свободных), число в скобках: (5)
      - Если свободные есть — обычное число: 5
    - view_sched: все будущие дни кликабельные
    """
    builder = InlineKeyboardBuilder()

    month_names = [
        "", "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
        "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
    ]
    builder.row(
        InlineKeyboardButton(
            text=f"📅 {month_names[month]} {year}",
            callback_data="ignore"
        )
    )

    week_days_header = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    builder.row(*[
        InlineKeyboardButton(text=d, callback_data="ignore")
        for d in week_days_header
    ])

    # Действия, где нужна фильтрация по рабочим дням
    filter_by_work_days = action in ("add_slot", "remove_slot", "close_day", "cancel_bk", "view_sched")

    if work_days is None:
        work_days = []
    if days_with_free_slots is None:
        days_with_free_slots = []

    cal = calendar.monthcalendar(year, month)
    today = datetime.now().date()

    for week in cal:
        row_buttons = []
        for day in week:
            if day == 0:
                row_buttons.append(
                    InlineKeyboardButton(text=" ", callback_data="ignore")
                )
            else:
                date_str = f"{year}-{month:02d}-{day:02d}"
                date_obj = datetime(year, month, day).date()

                if date_obj < today:
                    # Прошедший день
                    row_buttons.append(
                        InlineKeyboardButton(text="·", callback_data="ignore")
                    )
                elif filter_by_work_days:
                    # Фильтруем — показываем только рабочие дни
                    if date_str in work_days:
                        # Если просмотр расписания — эмодзи календарь
                        if action == "view_sched":
                            label = f"{day}🗓"
                        # Если слоты закончились — эмодзи красный круг
                        elif date_str not in days_with_free_slots:
                            label = f"{day}🔴"
                        else:
                            label = str(day)
                            
                        row_buttons.append(
                            InlineKeyboardButton(
                                text=label,
                                callback_data=f"adm_cal:{action}:{date_str}"
                            )
                        )
                    else:
                        # Нерабочий день
                        row_buttons.append(
                            InlineKeyboardButton(text="•", callback_data="ignore")
                        )
                else:
                    # add_day — все будущие дни кликабельные
                    # Но существующие рабочие дни помечаем ✅
                    label = str(day)
                    if date_str in work_days and action == "add_day":
                        label = f"{day}✅"
                    
                    row_buttons.append(
                        InlineKeyboardButton(
                            text=label,
                            callback_data=f"adm_cal:{action}:{date_str}"
                        )
                    )
        builder.row(*row_buttons)

    # Навигация
    nav_buttons = []
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    if datetime(prev_year, prev_month, 1).date() >= today.replace(day=1):
        nav_buttons.append(
            InlineKeyboardButton(
                text="◀️",
                callback_data=f"adm_nav:{action}:{prev_year}:{prev_month}"
            )
        )

    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1
    max_date = today + timedelta(days=62)
    if datetime(next_year, next_month, 1).date() <= max_date:
        nav_buttons.append(
            InlineKeyboardButton(
                text="▶️",
                callback_data=f"adm_nav:{action}:{next_year}:{next_month}"
            )
        )

    if nav_buttons:
        builder.row(*nav_buttons)

    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")
    )

    return builder.as_markup()


def admin_slots_kb(date: str, slots: list[dict]) -> InlineKeyboardMarkup:
    """Клавиатура слотов для удаления (админ)."""
    builder = InlineKeyboardBuilder()
    for s in slots:
        status = "🔴 Занят" if s["is_booked"] else "🟢 Свободен"
        builder.row(
            InlineKeyboardButton(
                text=f"{s['time']} — {status}",
                callback_data=f"adm_del_slot:{date}:{s['time']}"
            )
        )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")
    )
    return builder.as_markup()


def admin_bookings_kb(date: str,
                      bookings: list[dict]) -> InlineKeyboardMarkup:
    """Клавиатура записей на дату для отмены (админ)."""
    builder = InlineKeyboardBuilder()
    for b in bookings:
        builder.row(
            InlineKeyboardButton(
                text=f"❌ {b['time']} — {b['name']}",
                callback_data=f"adm_cancel_bk:{b['id']}"
            )
        )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")
    )
    return builder.as_markup()


# ===================== Портфолио (клиент) =====================

def portfolio_categories_kb(categories: list[dict]) -> InlineKeyboardMarkup:
    """Клавиатура категорий портфолио — выбор категории."""
    builder = InlineKeyboardBuilder()
    for cat in categories:
        builder.row(
            InlineKeyboardButton(
                text=cat["name"],
                callback_data=f"portfolio_view:{cat['id']}:0"
            )
        )
    builder.row(
        InlineKeyboardButton(text="🏠 В меню", callback_data="back_to_menu")
    )
    return builder.as_markup()


def portfolio_nav_kb(category_id: int, page: int, total: int) -> InlineKeyboardMarkup:
    """Навигация по фото внутри категории (страница page из total)."""
    builder = InlineKeyboardBuilder()
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(
            text="◀", callback_data=f"portfolio_view:{category_id}:{page - 1}"
        ))
    nav.append(InlineKeyboardButton(
        text=f"{page + 1}/{total}", callback_data="ignore"
    ))
    if page < total - 1:
        nav.append(InlineKeyboardButton(
            text="▶", callback_data=f"portfolio_view:{category_id}:{page + 1}"
        ))
    builder.row(*nav)
    builder.row(
        InlineKeyboardButton(text="🔙 Категории", callback_data="portfolio_cats"),
        InlineKeyboardButton(text="🏠 Меню", callback_data="back_to_menu")
    )
    return builder.as_markup()


def waitlist_kb(date: str) -> InlineKeyboardMarkup:
    """Кнопка добавления в лист ожидания."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="🔔 Уведомить, если освободится",
            callback_data=f"waitlist_add:{date}"
        )
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="book")
    )
    return builder.as_markup()


def review_kb(booking_id: int) -> InlineKeyboardMarkup:
    """Кнопки оценки маникюра (1–5 звёзд)."""
    builder = InlineKeyboardBuilder()
    builder.row(*[
        InlineKeyboardButton(
            text=f"{i}⭐",
            callback_data=f"review:{booking_id}:{i}"
        )
        for i in range(1, 6)
    ])
    return builder.as_markup()


# ===================== Расширенная админ-панель =====================

def admin_menu_kb() -> InlineKeyboardMarkup:
    """Клавиатура расширенной админ-панели."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📅 Добавить рабочий день", callback_data="admin_add_day")
    )
    builder.row(
        InlineKeyboardButton(text="🕐 Добавить слот", callback_data="admin_add_slot"),
        InlineKeyboardButton(text="🗑 Удалить слот", callback_data="admin_remove_slot")
    )
    builder.row(
        InlineKeyboardButton(text="🚫 Закрыть день", callback_data="admin_close_day")
    )
    builder.row(
        InlineKeyboardButton(text="❌ Отменить запись", callback_data="admin_cancel_booking")
    )
    builder.row(
        InlineKeyboardButton(text="📊 Расписание на дату", callback_data="admin_view_schedule")
    )
    builder.row(
        InlineKeyboardButton(text="💅 Прайсы", callback_data="admin_prices"),
        InlineKeyboardButton(text="🖼 Портфолио", callback_data="admin_portfolio")
    )
    builder.row(
        InlineKeyboardButton(text="📍 Адрес", callback_data="admin_location")
    )
    builder.row(
        InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast"),
        InlineKeyboardButton(text="👤 Пользователи", callback_data="admin_users")
    )
    builder.row(
        InlineKeyboardButton(text="📈 Статистика", callback_data="admin_stats")
    )
    builder.row(
        InlineKeyboardButton(text="🏠 Выйти в меню", callback_data="back_to_menu")
    )
    return builder.as_markup()


def admin_portfolio_menu_kb() -> InlineKeyboardMarkup:
    """Меню управления портфолио в админке."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ Добавить категорию", callback_data="adm_portfolio_add_cat")
    )
    builder.row(
        InlineKeyboardButton(text="🗑 Удалить категорию", callback_data="adm_portfolio_del_cat")
    )
    builder.row(
        InlineKeyboardButton(text="📷 Добавить фото", callback_data="adm_portfolio_add_photo")
    )
    builder.row(
        InlineKeyboardButton(text="❌ Удалить фото", callback_data="adm_portfolio_del_photo")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")
    )
    return builder.as_markup()


def admin_portfolio_categories_kb(categories: list[dict],
                                   action: str) -> InlineKeyboardMarkup:
    """Список категорий для управления в админке."""
    builder = InlineKeyboardBuilder()
    for cat in categories:
        count_suffix = f" ({cat.get('photo_count', 0)} фото)" if "photo_count" in cat else ""
        builder.row(
            InlineKeyboardButton(
                text=f"{cat['name']}{count_suffix}",
                callback_data=f"adm_pcat:{action}:{cat['id']}"
            )
        )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="admin_portfolio")
    )
    return builder.as_markup()


def admin_portfolio_photos_kb(photos: list[dict], category_id: int) -> InlineKeyboardMarkup:
    """Список фото категории для удаления."""
    builder = InlineKeyboardBuilder()
    for i, photo in enumerate(photos, 1):
        caption = photo.get("caption") or f"Фото #{i}"
        builder.row(
            InlineKeyboardButton(
                text=f"❌ {caption[:30]}",
                callback_data=f"adm_del_photo:{photo['id']}"
            )
        )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="admin_portfolio")
    )
    return builder.as_markup()


def admin_location_menu_kb() -> InlineKeyboardMarkup:
    """Меню редактирования адреса в админке."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🗺 Изменить координаты", callback_data="adm_loc_coords")
    )
    builder.row(
        InlineKeyboardButton(text="📝 Изменить адрес (текст)", callback_data="adm_loc_address")
    )
    builder.row(
        InlineKeyboardButton(text="🖼 Загрузить фото-инструкцию", callback_data="adm_loc_photo")
    )
    builder.row(
        InlineKeyboardButton(text="❌ Удалить фото-инструкцию", callback_data="adm_loc_del_photo")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")
    )
    return builder.as_markup()


def admin_prices_menu_kb() -> InlineKeyboardMarkup:
    """Меню управления прайсами в админке."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📝 Изменить текст", callback_data="adm_price_edit_text")
    )
    builder.row(
        InlineKeyboardButton(text="🗑 Удалить текст", callback_data="adm_price_del_text")
    )
    builder.row(
        InlineKeyboardButton(text="🖼 Загрузить фото прайса", callback_data="adm_price_edit_photo")
    )
    builder.row(
        InlineKeyboardButton(text="❌ Удалить фото прайса", callback_data="adm_price_del_photo")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")
    )
    return builder.as_markup()


def admin_broadcast_confirm_kb() -> InlineKeyboardMarkup:
    """Подтверждение рассылки."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Отправить всем", callback_data="adm_broadcast_confirm"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="admin_panel")
    )
    return builder.as_markup()


def admin_stats_kb() -> InlineKeyboardMarkup:
    """Кнопки выбора периода для статистики."""
    from datetime import datetime
    now = datetime.now()
    prev_month = now.month - 1 if now.month > 1 else 12
    prev_year = now.year if now.month > 1 else now.year - 1
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=f"📅 Текущий месяц ({now.month}/{now.year})",
            callback_data=f"adm_stats:{now.year}:{now.month}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=f"📅 Прошлый месяц ({prev_month}/{prev_year})",
            callback_data=f"adm_stats:{prev_year}:{prev_month}"
        )
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")
    )
    return builder.as_markup()


# ===================== Управление пользователями =====================

def admin_user_mgmt_kb() -> InlineKeyboardMarkup:
    """Клавиатура управления пользователями."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🚫 Заблокировать", callback_data="adm_user_block"),
        InlineKeyboardButton(text="✅ Разблокировать", callback_data="adm_user_unblock")
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_panel")
    )
    return builder.as_markup()
