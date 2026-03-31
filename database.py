# database.py — Работа с базой данных SQLite

import aiosqlite
from datetime import datetime

DB_PATH = "manicure_bot.db"


async def init_db():
    """Инициализация базы данных и создание таблиц."""
    async with aiosqlite.connect(DB_PATH) as db:
        # Таблица рабочих дней
        await db.execute("""
            CREATE TABLE IF NOT EXISTS work_days (
                date TEXT PRIMARY KEY,
                is_closed INTEGER DEFAULT 0
            )
        """)
        # Таблица временных слотов
        await db.execute("""
            CREATE TABLE IF NOT EXISTS time_slots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                is_booked INTEGER DEFAULT 0,
                UNIQUE(date, time)
            )
        """)
        # Таблица бронирований
        await db.execute("""
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                name TEXT NOT NULL,
                phone TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        # Таблица категорий портфолио
        await db.execute("""
            CREATE TABLE IF NOT EXISTS portfolio_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            )
        """)
        # Таблица фото портфолио (хранится file_id Telegram)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS portfolio_photos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER NOT NULL REFERENCES portfolio_categories(id) ON DELETE CASCADE,
                file_id TEXT NOT NULL,
                caption TEXT DEFAULT ''
            )
        """)
        # Настройки геолокации (редактируются через админку)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS location_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        # Вставляем дефолтные значения геолокации, если их ещё нет
        await db.execute("""
            INSERT OR IGNORE INTO location_settings (key, value)
            VALUES ('lat', '55.7558'), ('lon', '37.6176'),
                   ('address', 'Адрес не задан'), ('directions_file_id', '')
        """)
        # Лист ожидания
        await db.execute("""
            CREATE TABLE IF NOT EXISTS waitlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                UNIQUE(user_id, date)
            )
        """)
        # Отзывы клиентов
        await db.execute("""
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                booking_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                rating INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(booking_id)
            )
        """)
        # Пользователи (для трекинга и блокировки)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                is_blocked INTEGER DEFAULT 0,
                last_seen TEXT NOT NULL
            )
        """)
        await db.commit()


# ===================== Рабочие дни =====================

async def add_work_day(date: str) -> bool:
    """Добавить рабочий день. Возвращает True если добавлен, False если уже существует."""
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute(
                "INSERT INTO work_days (date, is_closed) VALUES (?, 0)", (date,)
            )
            # Автоматически добавляем стандартные слоты
            default_slots = ["08:00", "12:00", "16:00", "20:00"]
            for slot_time in default_slots:
                await db.execute(
                    "INSERT OR IGNORE INTO time_slots (date, time, is_booked) VALUES (?, ?, 0)",
                    (date, slot_time)
                )
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False


async def close_work_day(date: str) -> bool:
    """Закрыть рабочий день. Возвращает True если закрыт."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "UPDATE work_days SET is_closed = 1 WHERE date = ?", (date,)
        )
        await db.commit()
        return cursor.rowcount > 0


async def get_available_days() -> list[str]:
    """Получить список доступных (открытых) рабочих дней."""
    async with aiosqlite.connect(DB_PATH) as db:
        today = datetime.now().strftime("%Y-%m-%d")
        cursor = await db.execute(
            "SELECT date FROM work_days WHERE is_closed = 0 AND date >= ? ORDER BY date",
            (today,)
        )
        rows = await cursor.fetchall()
        return [row[0] for row in rows]


async def is_work_day(date: str) -> bool:
    """Проверить, является ли дата рабочим днём (и не закрыт)."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT 1 FROM work_days WHERE date = ? AND is_closed = 0", (date,)
        )
        return await cursor.fetchone() is not None


async def get_all_work_days() -> list[dict]:
    """Получить все рабочие дни с их статусом."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT date, is_closed FROM work_days ORDER BY date"
        )
        rows = await cursor.fetchall()
        return [{"date": r[0], "is_closed": r[1]} for r in rows]


async def get_work_days_list() -> list[str]:
    """Получить список дат рабочих (незакрытых) дней."""
    async with aiosqlite.connect(DB_PATH) as db:
        today = datetime.now().strftime("%Y-%m-%d")
        cursor = await db.execute(
            "SELECT date FROM work_days WHERE is_closed = 0 AND date >= ? ORDER BY date",
            (today,)
        )
        rows = await cursor.fetchall()
        return [row[0] for row in rows]


async def get_days_with_free_slots() -> list[str]:
    """Получить список дат, на которых есть хотя бы один свободный слот."""
    async with aiosqlite.connect(DB_PATH) as db:
        today = datetime.now().strftime("%Y-%m-%d")
        cursor = await db.execute(
            "SELECT DISTINCT ts.date FROM time_slots ts "
            "JOIN work_days wd ON ts.date = wd.date "
            "WHERE ts.is_booked = 0 AND wd.is_closed = 0 AND ts.date >= ? "
            "ORDER BY ts.date",
            (today,)
        )
        rows = await cursor.fetchall()
        
        days = [row[0] for row in rows]
        valid_days = []
        
        today_str = datetime.now().strftime("%Y-%m-%d")
        for d in days:
            if d == today_str:
                slots = await get_available_slots(d)
                if slots:
                    valid_days.append(d)
            else:
                valid_days.append(d)
                
        return valid_days


# ===================== Временные слоты =====================

async def add_time_slot(date: str, time: str) -> bool:
    """Добавить временной слот. Возвращает True если добавлен."""
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute(
                "INSERT INTO time_slots (date, time, is_booked) VALUES (?, ?, 0)",
                (date, time)
            )
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False


async def remove_time_slot(date: str, time: str) -> bool:
    """Удалить временной слот. Возвращает True если удалён."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM time_slots WHERE date = ? AND time = ? AND is_booked = 0",
            (date, time)
        )
        await db.commit()
        return cursor.rowcount > 0


async def get_available_slots(date: str) -> list[str]:
    """Получить доступные (не забронированные) слоты на дату."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT time FROM time_slots WHERE date = ? AND is_booked = 0 ORDER BY time",
            (date,)
        )
        rows = await cursor.fetchall()
        
        slots = [row[0] for row in rows]
        
        # Фильтрация прошедших слотов, если дата — сегодня
        today_str = datetime.now().strftime("%Y-%m-%d")
        if date == today_str:
            current_time_str = datetime.now().strftime("%H:%M")
            slots = [s for s in slots if s > current_time_str]
            
        return slots


async def get_all_slots(date: str) -> list[dict]:
    """Получить все слоты на дату (для админа)."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT time, is_booked FROM time_slots WHERE date = ? ORDER BY time",
            (date,)
        )
        rows = await cursor.fetchall()
        return [{"time": r[0], "is_booked": r[1]} for r in rows]


async def book_slot(date: str, time: str) -> bool:
    """Забронировать слот. Возвращает True если успешно."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "UPDATE time_slots SET is_booked = 1 WHERE date = ? AND time = ? AND is_booked = 0",
            (date, time)
        )
        await db.commit()
        return cursor.rowcount > 0


async def unbook_slot(date: str, time: str) -> bool:
    """Освободить слот. Возвращает True если успешно."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "UPDATE time_slots SET is_booked = 0 WHERE date = ? AND time = ?",
            (date, time)
        )
        await db.commit()
        return cursor.rowcount > 0


# ===================== Бронирования =====================

async def has_active_booking(user_id: int) -> bool:
    """Проверить, есть ли у пользователя активная запись."""
    async with aiosqlite.connect(DB_PATH) as db:
        today = datetime.now().strftime("%Y-%m-%d")
        current_time = datetime.now().strftime("%H:%M")
        cursor = await db.execute(
            "SELECT 1 FROM bookings WHERE user_id = ? AND (date > ? OR (date = ? AND time > ?))",
            (user_id, today, today, current_time)
        )
        return await cursor.fetchone() is not None


async def create_booking(user_id: int, date: str, time: str,
                         name: str, phone: str) -> int:
    """Создать запись. Возвращает ID бронирования."""
    async with aiosqlite.connect(DB_PATH) as db:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor = await db.execute(
            "INSERT INTO bookings (user_id, date, time, name, phone, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, date, time, name, phone, now)
        )
        await db.commit()
        return cursor.lastrowid


async def get_user_booking(user_id: int) -> dict | None:
    """Получить активную запись пользователя."""
    async with aiosqlite.connect(DB_PATH) as db:
        today = datetime.now().strftime("%Y-%m-%d")
        current_time = datetime.now().strftime("%H:%M")
        cursor = await db.execute(
            "SELECT id, date, time, name, phone FROM bookings "
            "WHERE user_id = ? AND (date > ? OR (date = ? AND time > ?)) ORDER BY date LIMIT 1",
            (user_id, today, today, current_time)
        )
        row = await cursor.fetchone()
        if row:
            return {
                "id": row[0], "date": row[1], "time": row[2],
                "name": row[3], "phone": row[4]
            }
        return None


async def cancel_booking(booking_id: int) -> dict | None:
    """Отменить запись по ID. Возвращает данные отменённой записи."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT id, user_id, date, time, name, phone FROM bookings WHERE id = ?",
            (booking_id,)
        )
        row = await cursor.fetchone()
        if row:
            await db.execute("DELETE FROM bookings WHERE id = ?", (booking_id,))
            await db.commit()
            return {
                "id": row[0], "user_id": row[1], "date": row[2],
                "time": row[3], "name": row[4], "phone": row[5]
            }
        return None


async def cancel_booking_by_user(user_id: int) -> dict | None:
    """Отменить активную запись пользователя."""
    booking = await get_user_booking(user_id)
    if booking:
        return await cancel_booking(booking["id"])
    return None


async def get_bookings_by_date(date: str) -> list[dict]:
    """Получить все записи на дату."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT id, user_id, time, name, phone FROM bookings "
            "WHERE date = ? ORDER BY time",
            (date,)
        )
        rows = await cursor.fetchall()
        return [
            {"id": r[0], "user_id": r[1], "time": r[2],
             "name": r[3], "phone": r[4]}
            for r in rows
        ]


async def get_all_future_bookings() -> list[dict]:
    """Получить все будущие записи (для восстановления напоминаний)."""
    async with aiosqlite.connect(DB_PATH) as db:
        today = datetime.now().strftime("%Y-%m-%d")
        cursor = await db.execute(
            "SELECT id, user_id, date, time, name, phone FROM bookings "
            "WHERE date >= ? ORDER BY date, time",
            (today,)
        )
        rows = await cursor.fetchall()
        return [
            {"id": r[0], "user_id": r[1], "date": r[2],
             "time": r[3], "name": r[4], "phone": r[5]}
            for r in rows
        ]


async def cancel_all_bookings_on_date(date: str) -> list[dict]:
    """Отменить все записи на дату (при закрытии дня). Возвращает список отменённых."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT id, user_id, date, time, name, phone FROM bookings WHERE date = ?",
            (date,)
        )
        rows = await cursor.fetchall()
        bookings = [
            {"id": r[0], "user_id": r[1], "date": r[2],
             "time": r[3], "name": r[4], "phone": r[5]}
            for r in rows
        ]
        if bookings:
            await db.execute("DELETE FROM bookings WHERE date = ?", (date,))
            # Освобождаем все слоты на этот день
            await db.execute(
                "UPDATE time_slots SET is_booked = 0 WHERE date = ?", (date,)
            )
            await db.commit()
        return bookings


# ===================== Портфолио =====================

async def get_portfolio_categories() -> list[dict]:
    """Получить все категории портфолио."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT id, name FROM portfolio_categories ORDER BY name"
        )
        rows = await cursor.fetchall()
        return [{"id": r[0], "name": r[1]} for r in rows]


async def add_portfolio_category(name: str) -> bool:
    """Добавить категорию. Возвращает True если добавлена."""
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute(
                "INSERT INTO portfolio_categories (name) VALUES (?)", (name,)
            )
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False


async def delete_portfolio_category(category_id: int) -> bool:
    """Удалить категорию и все её фото."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        cursor = await db.execute(
            "DELETE FROM portfolio_categories WHERE id = ?", (category_id,)
        )
        await db.commit()
        return cursor.rowcount > 0


async def get_portfolio_photos(category_id: int) -> list[dict]:
    """Получить все фото в категории."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT id, file_id, caption FROM portfolio_photos WHERE category_id = ?",
            (category_id,)
        )
        rows = await cursor.fetchall()
        return [{"id": r[0], "file_id": r[1], "caption": r[2]} for r in rows]


async def add_portfolio_photo(category_id: int, file_id: str, caption: str = "") -> int:
    """Добавить фото в категорию. Возвращает ID фото."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO portfolio_photos (category_id, file_id, caption) VALUES (?, ?, ?)",
            (category_id, file_id, caption)
        )
        await db.commit()
        return cursor.lastrowid


async def delete_portfolio_photo(photo_id: int) -> bool:
    """Удалить фото из портфолио."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM portfolio_photos WHERE id = ?", (photo_id,)
        )
        await db.commit()
        return cursor.rowcount > 0


async def get_portfolio_photo_count(category_id: int) -> int:
    """Получить кол-во фото в категории."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM portfolio_photos WHERE category_id = ?",
            (category_id,)
        )
        row = await cursor.fetchone()
        return row[0] if row else 0


# ===================== Геолокация =====================

async def get_location_settings() -> dict:
    """Получить настройки геолокации."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT key, value FROM location_settings")
        rows = await cursor.fetchall()
        return {r[0]: r[1] for r in rows}


async def set_location_setting(key: str, value: str):
    """Обновить настройку геолокации."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO location_settings (key, value) VALUES (?, ?)",
            (key, value)
        )
        await db.commit()


# ===================== Лист ожидания =====================

async def add_to_waitlist(user_id: int, date: str) -> bool:
    """Добавить пользователя в лист ожидания. Возвращает True если добавлен."""
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute(
                "INSERT INTO waitlist (user_id, date) VALUES (?, ?)",
                (user_id, date)
            )
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False


async def get_waitlist(date: str) -> list[int]:
    """Получить список user_id из листа ожидания на дату."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT user_id FROM waitlist WHERE date = ?", (date,)
        )
        rows = await cursor.fetchall()
        return [r[0] for r in rows]


async def clear_waitlist(date: str):
    """Очистить лист ожидания на дату."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM waitlist WHERE date = ?", (date,))
        await db.commit()


async def is_in_waitlist(user_id: int, date: str) -> bool:
    """Проверить, стоит ли пользователь в листе ожидания."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT 1 FROM waitlist WHERE user_id = ? AND date = ?",
            (user_id, date)
        )
        return await cursor.fetchone() is not None


# ===================== Отзывы =====================

async def save_review(booking_id: int, user_id: int, name: str, rating: int) -> bool:
    """Сохранить отзыв. Возвращает True если сохранён (первый раз)."""
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            await db.execute(
                "INSERT INTO reviews (booking_id, user_id, name, rating, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (booking_id, user_id, name, rating, now)
            )
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False


async def get_all_reviews() -> list[dict]:
    """Получить все отзывы."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT name, rating, created_at FROM reviews ORDER BY created_at DESC"
        )
        rows = await cursor.fetchall()
        return [{"name": r[0], "rating": r[1], "created_at": r[2]} for r in rows]


# ===================== Статистика =====================

async def get_monthly_stats(year: int, month: int) -> dict:
    """Получить статистику за месяц."""
    async with aiosqlite.connect(DB_PATH) as db:
        prefix = f"{year}-{month:02d}"

        # Записей за месяц
        cursor = await db.execute(
            "SELECT COUNT(*) FROM bookings WHERE date LIKE ?", (f"{prefix}%",)
        )
        total_bookings = (await cursor.fetchone())[0]

        # Новых клиентов (впервые записались в этот месяц)
        cursor = await db.execute(
            """SELECT COUNT(DISTINCT user_id) FROM bookings b
               WHERE date LIKE ?
               AND NOT EXISTS (
                   SELECT 1 FROM bookings b2
                   WHERE b2.user_id = b.user_id AND b2.date < ?
               )""",
            (f"{prefix}%", f"{prefix}-01")
        )
        new_clients = (await cursor.fetchone())[0]

        # Средний рейтинг за месяц
        cursor = await db.execute(
            "SELECT AVG(rating), COUNT(*) FROM reviews WHERE created_at LIKE ?",
            (f"{prefix}%",)
        )
        row = await cursor.fetchone()
        avg_rating = round(row[0], 1) if row[0] else None
        review_count = row[1]

        # Рабочих дней за месяц
        cursor = await db.execute(
            "SELECT COUNT(*) FROM work_days WHERE date LIKE ? AND is_closed = 0",
            (f"{prefix}%",)
        )
        work_days_count = (await cursor.fetchone())[0]

        return {
            "total_bookings": total_bookings,
            "new_clients": new_clients,
            "avg_rating": avg_rating,
            "review_count": review_count,
            "work_days": work_days_count,
        }


# ===================== Рассылка =====================

async def get_all_client_ids() -> list[int]:
    """Получить уникальные user_id всех клиентов, которые когда-либо записывались."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT DISTINCT user_id FROM bookings")
        rows = await cursor.fetchall()
        return [r[0] for r in rows]


async def get_all_users_ids() -> list[int]:
    """Получить ID всех пользователей, которых бот когда-либо видел."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT user_id FROM users")
        rows = await cursor.fetchall()
        return [r[0] for r in rows]


# ===================== Управление пользователями =====================

async def update_user_data(user_id: int, username: str, full_name: str):
    """Обновить данные пользователя в базе."""
    async with aiosqlite.connect(DB_PATH) as db:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        await db.execute("""
            INSERT INTO users (user_id, username, full_name, last_seen)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                full_name = excluded.full_name,
                last_seen = excluded.last_seen
        """, (user_id, username, full_name, now))
        await db.commit()


async def set_user_block_status(username_tag: str, is_blocked: int) -> bool:
    """Заблокировать или разблокировать пользователя по его юзернейму (без @)."""
    from config import ADMIN_ID
    async with aiosqlite.connect(DB_PATH) as db:
        # Убираем @ если есть
        tag = username_tag.lstrip('@')
        
        # Если пытаемся заблокировать (is_blocked=1), проверяем не админ ли это
        if is_blocked:
            cursor = await db.execute("SELECT user_id FROM users WHERE username = ?", (tag,))
            row = await cursor.fetchone()
            if row and row[0] == ADMIN_ID:
                return False # Нельзя блокировать админа

        cursor = await db.execute(
            "UPDATE users SET is_blocked = ? WHERE username = ?",
            (is_blocked, tag)
        )
        await db.commit()
        return cursor.rowcount > 0


async def is_user_blocked(user_id: int) -> bool:
    """Проверить, заблокирован ли пользователь."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT is_blocked FROM users WHERE user_id = ?",
            (user_id,)
        )
        row = await cursor.fetchone()
        return bool(row[0]) if row else False
