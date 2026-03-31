# handlers/start.py — Обработчик команды /start и проверка подписки

from aiogram import Router, Bot, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.enums import ChatMemberStatus

from config import CHANNEL_ID, ADMIN_ID
from keyboards import main_menu_kb, subscription_kb

router = Router()

# Статусы, при которых считаем пользователя подписанным
SUBSCRIBED_STATUSES = {
    ChatMemberStatus.MEMBER,
    ChatMemberStatus.ADMINISTRATOR,
    ChatMemberStatus.CREATOR,
}


async def check_subscription(bot: Bot, user_id: int) -> bool:
    """Проверить подписку пользователя на канал."""
    try:
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in SUBSCRIBED_STATUSES
    except Exception:
        # Если бот не является админом канала или канал не найден
        return True  # Не блокируем пользователей при ошибке


@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot):
    """Обработка команды /start."""

    # Проверяем подписку
    is_subscribed = await check_subscription(bot, message.from_user.id)

    if not is_subscribed:
        await message.answer(
            "👋 <b>Добро пожаловать!</b>\n\n"
            "Для записи необходимо подписаться на наш канал 📢",
            parse_mode="HTML",
            reply_markup=subscription_kb()
        )
        return

    # Показываем главное меню
    await message.answer(
        "👋 <b>Добро пожаловать в салон маникюра!</b>\n\n"
        "💅 Я помогу вам записаться на процедуру.\n"
        "Выберите нужный пункт меню:",
        parse_mode="HTML",
        reply_markup=main_menu_kb(user_id=message.from_user.id)
    )


@router.callback_query(F.data == "check_subscription")
async def check_subscription_callback(callback: CallbackQuery, bot: Bot):
    """Повторная проверка подписки по нажатию кнопки."""
    is_subscribed = await check_subscription(bot, callback.from_user.id)

    if is_subscribed:
        await callback.message.edit_text(
            "✅ <b>Подписка подтверждена!</b>\n\n"
            "💅 Добро пожаловать в салон маникюра!\n"
            "Выберите нужный пункт меню:",
            parse_mode="HTML",
            reply_markup=main_menu_kb(user_id=callback.from_user.id)
        )
    else:
        await callback.answer(
            "❌ Вы ещё не подписались на канал!",
            show_alert=True
        )


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    """Отмена любого активного действия (состояния FSM)."""
    await state.clear()
    await message.answer(
        "❌ Действие отменено.\n\n"
        "💅 <b>Главное меню</b>\n\n"
        "Выберите нужный пункт:",
        parse_mode="HTML",
        reply_markup=main_menu_kb(user_id=message.from_user.id)
    )



@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery, bot: Bot, state: FSMContext):
    """Возврат в главное меню."""
    data = await state.get_data()
    loc_msg_id = data.get("location_msg_id")
    if loc_msg_id:
        try:
            await bot.delete_message(chat_id=callback.from_user.id, message_id=loc_msg_id)
            await state.update_data(location_msg_id=None)
        except Exception:
            pass

    is_subscribed = await check_subscription(bot, callback.from_user.id)

    if not is_subscribed:
        text_not_sub = "📢 Для записи необходимо подписаться на наш канал"
        try:
            await callback.message.edit_text(
                text_not_sub,
                parse_mode="HTML",
                reply_markup=subscription_kb()
            )
        except Exception:
            try:
                await callback.message.delete()
            except Exception:
                pass
            await bot.send_message(
                chat_id=callback.from_user.id,
                text=text_not_sub,
                parse_mode="HTML",
                reply_markup=subscription_kb()
            )
        return

    text_menu = "💅 <b>Главное меню</b>\n\nВыберите нужный пункт:"
    try:
        await callback.message.edit_text(
            text_menu,
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
            text=text_menu,
            parse_mode="HTML",
            reply_markup=main_menu_kb(user_id=callback.from_user.id)
        )


@router.callback_query(F.data == "ignore")
async def ignore_callback(callback: CallbackQuery):
    """Игнорируем нажатия на пустые кнопки (заголовки, дни недели)."""
    await callback.answer()
