# handlers/portfolio.py — Портфолио мастера с категориями

from aiogram import Router, Bot, F
from aiogram.types import CallbackQuery

from keyboards import portfolio_categories_kb, portfolio_nav_kb, main_menu_kb
from database import get_portfolio_categories, get_portfolio_photos

router = Router()


@router.callback_query(F.data == "portfolio_cats")
async def show_portfolio_categories(callback: CallbackQuery):
    """Показать список категорий портфолио."""
    categories = await get_portfolio_categories()

    if not categories:
        text_empty = "📸 <b>Наши работы</b>\n\nРабот пока нет. Загляните позже!"
        try:
            await callback.message.edit_text(
                text_empty,
                parse_mode="HTML",
                reply_markup=main_menu_kb(user_id=callback.from_user.id)
            )
        except Exception:
            try:
                await callback.message.delete()
            except Exception:
                pass
            await callback.bot.send_message(
                chat_id=callback.from_user.id,
                text=text_empty,
                parse_mode="HTML",
                reply_markup=main_menu_kb(user_id=callback.from_user.id)
            )
        return

    text_cats = "📸 <b>Наши работы</b>\n\nВыберите категорию, чтобы посмотреть фото:"
    try:
        await callback.message.edit_text(
            text_cats,
            parse_mode="HTML",
            reply_markup=portfolio_categories_kb(categories)
        )
    except Exception:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.bot.send_message(
            chat_id=callback.from_user.id,
            text=text_cats,
            parse_mode="HTML",
            reply_markup=portfolio_categories_kb(categories)
        )


@router.callback_query(F.data.startswith("portfolio_view:"))
async def show_portfolio_photo(callback: CallbackQuery, bot: Bot):
    """Показать фото в категории с навигацией."""
    _, cat_id_str, page_str = callback.data.split(":")
    category_id = int(cat_id_str)
    page = int(page_str)

    photos = await get_portfolio_photos(category_id)

    if not photos:
        await callback.answer("В этой категории пока нет фото.", show_alert=True)
        return

    total = len(photos)
    page = max(0, min(page, total - 1))
    photo = photos[page]

    caption = photo.get("caption") or ""
    full_caption = f"{'📸 ' + caption if caption else '📸'} ({page + 1}/{total})"

    nav_kb = portfolio_nav_kb(category_id, page, total)

    # Если это редактирование текстового сообщения — удаляем и отправляем фото новым
    try:
        await callback.message.delete()
    except Exception:
        pass

    await bot.send_photo(
        chat_id=callback.from_user.id,
        photo=photo["file_id"],
        caption=full_caption,
        reply_markup=nav_kb
    )
    await callback.answer()
