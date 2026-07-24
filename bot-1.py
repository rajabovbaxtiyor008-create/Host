# ============================================================
#  MineStore Bot — продажа сборок серверов Minecraft в Telegram
#  Стек: Python + aiogram 3
#  Деплой: Railway
# ============================================================

import asyncio
import logging
import os
import time

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    CallbackQuery,
    LabeledPrice,
    Message,
    PreCheckoutQuery,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
PROVIDER_TOKEN = os.getenv("PROVIDER_TOKEN")  # токен платёжного провайдера Telegram
ADMIN_ID = os.getenv("ADMIN_ID")  # ваш telegram user id для уведомлений
CURRENCY = os.getenv("CURRENCY", "RUB")

if not BOT_TOKEN:
    raise RuntimeError("Не задан BOT_TOKEN в переменных окружения.")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)

# ============================================================
#  Каталог сборок (легко редактировать / расширять)
#  price указывается в РУБЛЯХ (конвертация в копейки — автоматом)
# ============================================================
PRODUCTS = [
    {
        "id": "funtime",
        "name": "FunTime-style Сборка",
        "price": 2500,
        "desc": (
            "Развлекательный сервер с мини-играми, экономикой и системой кланов.\n"
            "• 10+ мини-игр\n• Кастомная экономика\n• Античит настроен\n"
            "• Готовая панель донат-магазина"
        ),
        "file_link": "https://example.com/downloads/funtime.zip",
    },
    {
        "id": "reallyworld",
        "name": "ReallyWorld-style Сборка",
        "price": 2900,
        "desc": (
            "RPG-сервер с прокачкой, кастомными предметами и квестами.\n"
            "• Система прокачки\n• Кастомные ресурспаки\n• Квесты и сюжет\n"
            "• Кланы и территории"
        ),
        "file_link": "https://example.com/downloads/reallyworld.zip",
    },
    {
        "id": "skyblock",
        "name": "SkyBlock Сборка",
        "price": 1800,
        "desc": (
            "Классический SkyBlock с островами, апгрейдами и рейтингом игроков.\n"
            "• Генератор островов\n• Система рейтинга\n• Магазин ресурсов\n• Ивенты"
        ),
        "file_link": "https://example.com/downloads/skyblock.zip",
    },
    {
        "id": "pvpfaction",
        "name": "PvP Faction Сборка",
        "price": 2200,
        "desc": (
            "Жёсткий PvP-сервер с фракциями, войнами за территорию и рейдами баз.\n"
            "• Система фракций\n• Рейды и захват баз\n• Кастомный крафт\n"
            "• Баланс PvP"
        ),
        "file_link": "https://example.com/downloads/pvpfaction.zip",
    },
    {
        "id": "vanillaplus",
        "name": "Ванильная+ Сборка",
        "price": 1200,
        "desc": (
            "Мягкая модерация, лёгкие улучшения ванильного геймплея.\n"
            "• Кастомная генерация мира\n• Защита территории\n"
            "• Телепорты и тимчаты\n• Лёгкий античит"
        ),
        "file_link": "https://example.com/downloads/vanillaplus.zip",
    },
    {
        "id": "techserver",
        "name": "Технический сервер (Tech)",
        "price": 2600,
        "desc": (
            "Сборка с модами на автоматизацию и технику.\n"
            "• Моды автоматизации\n• Оптимизация TPS\n• Защита машин\n"
            "• Гайд по установке"
        ),
        "file_link": "https://example.com/downloads/techserver.zip",
    },
]


def find_product(product_id: str):
    return next((p for p in PRODUCTS if p["id"] == product_id), None)


# ============================================================
#  /start — приветствие + главное меню
# ============================================================
@router.message(CommandStart())
async def cmd_start(message: Message):
    kb = InlineKeyboardBuilder()
    kb.button(text="🛒 Каталог", callback_data="catalog")
    await message.answer(
        "👋 Добро пожаловать в MineStore!\n\n"
        "Здесь можно купить готовые сборки серверов Minecraft под ключ: "
        "плагины, конфиги, экономика — всё уже настроено.\n\n"
        "Нажмите «Каталог», чтобы посмотреть доступные сборки.",
        reply_markup=kb.as_markup(),
    )


@router.message(Command("catalog"))
async def cmd_catalog(message: Message):
    await send_catalog(message)


async def send_catalog(target):
    kb = InlineKeyboardBuilder()
    for p in PRODUCTS:
        kb.button(text=f"{p['name']} — {p['price']} ₽", callback_data=f"view_{p['id']}")
    kb.adjust(1)
    text = "📦 Доступные сборки серверов:"
    if isinstance(target, Message):
        await target.answer(text, reply_markup=kb.as_markup())
    else:
        await target.message.answer(text, reply_markup=kb.as_markup())


@router.callback_query(F.data == "catalog")
async def cb_catalog(call: CallbackQuery):
    await call.answer()
    await send_catalog(call)


# ============================================================
#  Карточка товара
# ============================================================
@router.callback_query(F.data.startswith("view_"))
async def cb_view_product(call: CallbackQuery):
    await call.answer()
    product_id = call.data.split("_", 1)[1]
    product = find_product(product_id)
    if not product:
        await call.message.answer("Товар не найден.")
        return

    kb = InlineKeyboardBuilder()
    kb.button(text="💳 Купить", callback_data=f"buy_{product['id']}")
    kb.button(text="⬅️ Назад к каталогу", callback_data="catalog")
    kb.adjust(1)

    await call.message.answer(
        f"🎮 <b>{product['name']}</b>\n\n{product['desc']}\n\n💰 Цена: <b>{product['price']} ₽</b>",
        parse_mode="HTML",
        reply_markup=kb.as_markup(),
    )


# ============================================================
#  Оплата через Telegram Payments
#  Требует PROVIDER_TOKEN от платёжного провайдера,
#  подключённого через @BotFather -> Payments.
# ============================================================
@router.callback_query(F.data.startswith("buy_"))
async def cb_buy(call: CallbackQuery):
    await call.answer()
    product_id = call.data.split("_", 1)[1]
    product = find_product(product_id)
    if not product:
        await call.message.answer("Товар не найден.")
        return

    if not PROVIDER_TOKEN:
        # Резервный сценарий: без подключённого провайдера —
        # оформляем заявку вручную (админ подтверждает оплату сам).
        await call.message.answer(
            f"Вы выбрали: <b>{product['name']}</b> ({product['price']} ₽)\n\n"
            "Онлайн-оплата пока не подключена. Для покупки свяжитесь с "
            "администратором — он вышлет реквизиты и после оплаты пришлёт "
            "архив сборки.",
            parse_mode="HTML",
        )
        if ADMIN_ID:
            username = call.from_user.username or call.from_user.id
            await bot.send_message(
                ADMIN_ID,
                f"🔔 Новый запрос на покупку!\n"
                f"Товар: {product['name']}\nЦена: {product['price']} ₽\n"
                f"Покупатель: @{username}",
            )
        return

    payload = f"order_{product['id']}_{call.from_user.id}_{int(time.time())}"
    prices = [LabeledPrice(label=product["name"], amount=product["price"] * 100)]

    try:
        await bot.send_invoice(
            chat_id=call.from_user.id,
            title=product["name"],
            description=product["desc"],
            payload=payload,
            provider_token=PROVIDER_TOKEN,
            currency=CURRENCY,
            prices=prices,
            start_parameter=f"buy_{product['id']}",
        )
    except Exception as e:
        logging.error(f"Ошибка при создании счёта: {e}")
        await call.message.answer(
            "Не удалось создать счёт на оплату. Попробуйте позже или "
            "напишите администратору."
        )


# Подтверждение перед оплатой (обязательный шаг Telegram Payments)
@router.pre_checkout_query()
async def process_pre_checkout(pre_checkout_q: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_q.id, ok=True)


# Успешная оплата — выдаём товар
@router.message(F.successful_payment)
async def process_successful_payment(message: Message):
    payload = message.successful_payment.invoice_payload or ""
    parts = payload.split("_")
    product_id = parts[1] if len(parts) > 1 else None
    product = find_product(product_id)

    if product:
        text = (
            f"✅ Оплата прошла успешно!\n\n"
            f"Ваша сборка: <b>{product['name']}</b>\n"
            f"📥 Скачать: {product['file_link']}\n\n"
            "Инструкция по установке будет отправлена отдельным сообщением. "
            "Если возникнут вопросы — пишите в поддержку."
        )
    else:
        text = "✅ Оплата прошла успешно! Мы свяжемся с вами для передачи файлов."

    await message.answer(text, parse_mode="HTML")

    if ADMIN_ID:
        username = message.from_user.username or message.from_user.id
        await bot.send_message(
            ADMIN_ID,
            f"💰 Оплачен заказ!\n"
            f"Товар: {product['name'] if product else product_id}\n"
            f"Покупатель: @{username}",
        )


# ============================================================
#  Поддержка
# ============================================================
@router.message(Command("support"))
async def cmd_support(message: Message):
    await message.answer("По всем вопросам пишите: @your_support_username")


# ============================================================
#  Запуск
# ============================================================
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
