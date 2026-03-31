# scheduler.py — Планировщик напоминаний (APScheduler)

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot

from config import TIMEZONE

# Глобальный планировщик
scheduler = AsyncIOScheduler(timezone=TIMEZONE)


async def send_reminder(bot: Bot, user_id: int, time_str: str):
    """Отправить напоминание пользователю."""
    try:
        await bot.send_message(
            user_id,
            f"💅 <b>Напоминание!</b>\n\n"
            f"Напоминаем, что вы записаны на маникюр"
            f"завтра в <b>{time_str}</b>.\n\n"
            f"Ждём вас! ❤️",
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"[Scheduler] Ошибка отправки напоминания пользователю {user_id}: {e}")


async def send_session_start_notification(bot: Bot, user_id: int):
    """Отправить уведомление о начале сеанса."""
    try:
        await bot.send_message(
            user_id,
            "✨ <b>Ваш сеанс начался!</b>\n\n"
            "Мастер уже ждёт вас. Приятного времяпровождения! ❤️",
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"[Scheduler] Ошибка отправки уведомления о начале сеанса пользователю {user_id}: {e}")


def schedule_reminder(bot: Bot, booking_id: int, user_id: int,
                      date_str: str, time_str: str):
    """
    Запланировать напоминание за 24 часа до визита.
    Если до визита менее 24 часов — напоминание НЕ создаётся.
    """
    tz = ZoneInfo(TIMEZONE)
    appointment_dt = datetime.strptime(
        f"{date_str} {time_str}", "%Y-%m-%d %H:%M"
    ).replace(tzinfo=tz)

    reminder_dt = appointment_dt - timedelta(hours=24)
    now = datetime.now(tz)

    if reminder_dt <= now:
        # До визита менее 24 часов.
        # Если до визита больше 2 часов, отправим напоминание через 10 минут после бронирования.
        if appointment_dt > now + timedelta(hours=2):
            reminder_dt = now + timedelta(minutes=10)
        else:
            # Слишком поздно для напоминания
            print(f"[Scheduler] Напоминание для бронирования #{booking_id} не создано "
                  f"(слишком мало времени до визита)")
            return

    job_id = f"reminder_{booking_id}"
    scheduler.add_job(
        send_reminder,
        "date",
        run_date=reminder_dt,
        args=[bot, user_id, time_str],
        id=job_id,
        replace_existing=True
    )
    print(f"[Scheduler] Напоминание #{booking_id} запланировано на {reminder_dt}")


def schedule_session_start_notification(bot: Bot, booking_id: int, user_id: int,
                                        date_str: str, time_str: str):
    """
    Запланировать уведомление о начале сеанса.
    """
    tz = ZoneInfo(TIMEZONE)
    appointment_dt = datetime.strptime(
        f"{date_str} {time_str}", "%Y-%m-%d %H:%M"
    ).replace(tzinfo=tz)

    now = datetime.now(tz)
    if appointment_dt <= now:
        return

    job_id = f"session_start_{booking_id}"
    scheduler.add_job(
        send_session_start_notification,
        "date",
        run_date=appointment_dt,
        args=[bot, user_id],
        id=job_id,
        replace_existing=True
    )
    print(f"[Scheduler] Уведомление о начале #{booking_id} запланировано на {appointment_dt}")


def cancel_booking_notifications(booking_id: int):
    """Отменить все уведомления для бронирования."""
    for prefix in ["reminder_", "review_", "session_start_"]:
        job_id = f"{prefix}{booking_id}"
        try:
            scheduler.remove_job(job_id)
            print(f"[Scheduler] Задача {job_id} отменена")
        except Exception:
            pass


async def restore_reminders(bot: Bot):
    """
    Восстановить все напоминания из базы данных при старте бота.
    Вызывается один раз при запуске.
    """
    from database import get_all_future_bookings

    bookings = await get_all_future_bookings()
    count = 0
    for b in bookings:
        schedule_reminder(bot, b["id"], b["user_id"], b["date"], b["time"])
        schedule_session_start_notification(bot, b["id"], b["user_id"], b["date"], b["time"])
        schedule_review_request(bot, b["id"], b["user_id"], b["date"], b["time"])
        count += 1

    print(f"[Scheduler] Восстановлено {count} наборов уведомлений из базы данных")


async def send_review_request(bot: Bot, booking_id: int, user_id: int):
    """Отправить запрос на оценку маникюра."""
    from keyboards import review_kb
    try:
        await bot.send_message(
            user_id,
            "💅 <b>Как прошёл ваш визит?</b>\n\n"
            "Оцените качество работы мастера по 5-бальной шкале.\n"
            "Ваш отзыв поможет нам стать лучше ❤️",
            parse_mode="HTML",
            reply_markup=review_kb(booking_id)
        )
    except Exception as e:
        print(f"[Scheduler] Ошибка отправки запроса отзыва пользователю {user_id}: {e}")


def schedule_review_request(bot: Bot, booking_id: int, user_id: int,
                             date_str: str, time_str: str):
    """
    Запланировать запрос отзыва через 12 часов после окончания визита.
    """
    tz = ZoneInfo(TIMEZONE)
    appointment_dt = datetime.strptime(
        f"{date_str} {time_str}", "%Y-%m-%d %H:%M"
    ).replace(tzinfo=tz)

    # Запрашиваем отзыв через 12 часов после визита
    review_dt = appointment_dt + timedelta(minutes=1)
    now = datetime.now(tz)

    if review_dt <= now:
        return  # Визит уже прошёл давно

    job_id = f"review_{booking_id}"
    scheduler.add_job(
        send_review_request,
        "date",
        run_date=review_dt,
        args=[bot, booking_id, user_id],
        id=job_id,
        replace_existing=True
    )
    print(f"[Scheduler] Запрос отзыва #{booking_id} запланирован на {review_dt}")

