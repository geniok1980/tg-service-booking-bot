<div align="center">
  <h1>💅 Telegram-бот для мастера маникюра</h1>
  <p>Бот для автоматической записи клиентов на процедуры с админ-панелью, расписанием и интеграцией с Telegram-каналом.</p>

  ![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
  ![Aiogram](https://img.shields.io/badge/aiogram-3.15-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white)
  ![SQLite](https://img.shields.io/badge/sqlite-%2307405e.svg?style=for-the-badge&logo=sqlite&logoColor=white)
</div>

---


## 📋 Функции

### Клиент
- 📝 Запись на процедуру (выбор даты и времени через inline-календарь)
- 📋 Просмотр и отмена своей записи
- 💅 Прайс-лист
- 📸 Портфолио (ссылка на Pinterest)
- 🔔 Автоматическое напоминание за 24 часа до визита

### Администратор (`/admin`)
- 📅 Добавление рабочих дней
- 🕐 Добавление/удаление временных слотов
- 🚫 Закрытие дня (с уведомлением клиентов)
- ❌ Отмена записей клиентов
- 📊 Просмотр расписания на дату

---

## 🚀 Установка и запуск

### 1. Клонирование / копирование проекта

Скопируйте папку `manicure_bot` на сервер.

### 2. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 3. Настройка

Откройте файл `config.py` и заполните:

```python
BOT_TOKEN = "ваш_токен_бота"          # Получить у @BotFather
ADMIN_ID = 123456789                    # Ваш Telegram ID (узнать: @userinfobot)
CHANNEL_ID = "@your_channel"            # Username или ID вашего канала
CHANNEL_LINK = "https://t.me/your_channel"  # Ссылка на канал
```

> ⚠️ **Важно:** Бот должен быть администратором канала, чтобы проверять подписку и публиковать сообщения.

### 4. Запуск

```bash
python bot.py
```

---

## 📁 Структура проекта

```
manicure_bot/
├── bot.py              # Точка входа
├── config.py           # Настройки (токен, ID админа, канал)
├── database.py         # Работа с SQLite (aiosqlite)
├── keyboards.py        # Inline-клавиатуры
├── states.py           # FSM-состояния
├── scheduler.py        # Напоминания (APScheduler)
├── handlers/
│   ├── __init__.py
│   ├── start.py        # /start, проверка подписки, главное меню
│   ├── booking.py      # Процесс записи (FSM)
│   ├── cancel.py       # Отмена записи клиентом
│   ├── prices.py       # Прайс-лист
│   ├── portfolio.py    # Портфолио
│   └── admin.py        # Админ-панель
├── requirements.txt
└── README.md
```

---

## ⚙️ Технологии

| Компонент | Технология |
|-----------|-----------|
| Фреймворк | aiogram 3.15 |
| База данных | SQLite (aiosqlite) |
| Планировщик | APScheduler |
| Состояния | FSM (aiogram) |
| Интерфейс | Inline-кнопки |
