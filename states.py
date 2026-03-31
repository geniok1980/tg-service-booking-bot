# states.py — FSM-состояния для бота

from aiogram.fsm.state import State, StatesGroup


class BookingStates(StatesGroup):
    """Состояния процесса записи клиента."""
    choosing_date = State()    # Выбор даты из календаря
    choosing_time = State()    # Выбор времени
    entering_name = State()    # Ввод имени
    entering_phone = State()   # Ввод номера телефона
    confirming = State()       # Подтверждение записи


class AdminStates(StatesGroup):
    """Состояния админ-панели."""
    adding_day = State()              # Добавление рабочего дня
    adding_slot_date = State()        # Выбор даты для добавления слота
    adding_slot_time = State()        # Ввод времени слота
    removing_slot_date = State()      # Выбор даты для удаления слота
    removing_slot_time = State()      # Выбор слота для удаления
    cancelling_booking = State()      # Отмена записи клиента
    closing_day = State()             # Закрытие дня
    viewing_schedule = State()        # Просмотр расписания
    # Прайсы
    prices_edit_text = State()        # Редактирование текста прайса
    prices_edit_photo = State()       # Загрузка фото прайса
    # Портфолио
    portfolio_add_category = State()  # Ввод названия новой категории
    portfolio_del_category = State()  # Выбор категории для удаления
    portfolio_select_cat = State()    # Выбор категории для добавления фото
    portfolio_add_photo = State()     # Загрузка фото
    portfolio_del_photo = State()     # Выбор фото для удаления
    # Геолокация
    location_edit_lat = State()       # Ввод широты
    location_edit_lon = State()       # Ввод долготы
    location_edit_address = State()   # Ввод текстового адреса
    location_edit_photo = State()     # Загрузка фото-инструкции
    # Рассылка
    broadcasting = State()            # Ввод текста рассылки
    broadcast_confirm = State()       # Подтверждение рассылки
    # Блокировка пользователей
    blocking_user = State()           # Ввод @username для блокировки
    unblocking_user = State()         # Ввод @username для разблокировки
