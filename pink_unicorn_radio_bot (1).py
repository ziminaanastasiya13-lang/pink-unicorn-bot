"""
🦄 Pink Unicorn Radio Bot для Telegram
=====================================
Аналог @radiohubbot, но для Pink Unicorn Records (Hardstyle / Hardcore / Gabber / Hard Dance)

УСТАНОВКА:
    pip install python-telegram-bot==20.7 requests

ЗАПУСК:
    1. Получи токен у @BotFather в Telegram
    2. Вставь токен в BOT_TOKEN ниже
    3. python pink_unicorn_radio_bot.py

ПРИМЕЧАНИЕ ПО СТРИМУ:
    Бот отправляет прямую ссылку на аудиопоток. Telegram воспроизводит её
    встроенным плеером. Если stream-URL изменится — обнови STREAM_URL.
    Найти актуальный URL можно через Radio Browser API (уже встроено в бота).
"""

import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# ──────────────────────────────────────────────
#  КОНФИГ — вставь свой токен от @BotFather
# ──────────────────────────────────────────────
BOT_TOKEN = "ВСТАВЬ_ТОКЕН_СЮДА"

# URL твоей GitHub Pages страницы с плеером
# После публикации на GitHub Pages вставь сюда свой URL, например:
# WEBAPP_URL = "https://твой-юзернейм.github.io/pink-unicorn-radio/"
WEBAPP_URL = "https://ziminaanastasiya13-lang.github.io/pink-unicorn-radio/"

# Прямая ссылка на поток Pink Unicorn Radio
STREAM_URL = "https://cast2.my-ais.net/8022/stream"   # fallback URL
STATION_NAME = "Pink Unicorn Radio 🦄"
STATION_GENRE = "Hardstyle · Hardcore · Gabber · Hard Dance"
STATION_COUNTRY = "Узбекистан 🇺🇿"
STATION_SITE = "https://pinkunicornrec.wixsite.com/home"
STATION_LOGO = "https://static.wixstatic.com/media/6062a7_fbcc0346d0fe43ac8a6e08d6c6b915aa~mv2_d_1750_1750_s_2.png"

# ──────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def find_stream_url() -> str:
    """Ищет актуальный stream URL через открытый Radio Browser API."""
    global STREAM_URL
    try:
        apis = [
            "https://de1.api.radio-browser.info",
            "https://nl1.api.radio-browser.info",
            "https://at1.api.radio-browser.info",
        ]
        for base in apis:
            resp = requests.get(
                f"{base}/json/stations/byname/Pink%20Unicorn%20Radio",
                headers={"User-Agent": "PinkUnicornRadioBot/1.0"},
                timeout=5,
            )
            if resp.ok:
                stations = resp.json()
                if stations:
                    url = stations[0].get("url_resolved") or stations[0].get("url")
                    if url:
                        STREAM_URL = url
                        logger.info(f"✅ Stream URL найден: {STREAM_URL}")
                        return STREAM_URL
    except Exception as e:
        logger.warning(f"Radio Browser недоступен: {e}")
    logger.info(f"Использую fallback URL: {STREAM_URL}")
    return STREAM_URL


def main_keyboard(webapp_url: str = "") -> InlineKeyboardMarkup:
    """Главная клавиатура бота."""
    from telegram import WebAppInfo
    keyboard = []
    if webapp_url:
        keyboard.append([InlineKeyboardButton("🎧 Слушать в Telegram", web_app=WebAppInfo(url=webapp_url))])
    keyboard += [
        [InlineKeyboardButton("▶️ Открыть в браузере", url=STREAM_URL)],
        [InlineKeyboardButton("ℹ️ О радио", callback_data="info"),
         InlineKeyboardButton("🎵 Жанры", callback_data="genres")],
        [InlineKeyboardButton("🔗 Сайт лейбла", url=STATION_SITE)],
        [InlineKeyboardButton("📡 Прямая ссылка", callback_data="stream_url")],
    ]
    return InlineKeyboardMarkup(keyboard)


def back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="back")]])


# ──────────────────── HANDLERS ────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /start — главное меню."""
    user = update.effective_user
    text = (
        f"🦄 *Привет, {user.first_name}!*\n\n"
        f"Добро пожаловать в *Pink Unicorn Radio Bot* — твой портал в мир Hardstyle, "
        f"Hardcore, Gabber и Hard Dance!\n\n"
        f"Pink Unicorn Records основан в 2017 году. "
        f"Только качественная и оригинальная музыка 24/7.\n\n"
        f"Выбери действие 👇"
    )
    await update.message.reply_photo(
        photo=STATION_LOGO,
        caption=text,
        parse_mode="Markdown",
        reply_markup=main_keyboard(WEBAPP_URL),
    )


async def play_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /play — отправить аудиопоток."""
    await send_stream(update.message, context)


async def info_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /info."""
    await update.message.reply_text(
        build_info_text(), parse_mode="Markdown", reply_markup=back_keyboard()
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик инлайн-кнопок."""
    query = update.callback_query
    await query.answer()

    if query.data == "play":
        await send_stream(query.message, context, edit=True)

    elif query.data == "info":
        await query.edit_message_caption(
            caption=build_info_text(),
            parse_mode="Markdown",
            reply_markup=back_keyboard(),
        )

    elif query.data == "genres":
        text = (
            "🎶 *Жанры Pink Unicorn Radio:*\n\n"
            "⚡ *Hardstyle* — энергичный бит, пронзительные синты, мощный бас\n"
            "🔥 *Hardcore / Gabber* — экстремально быстро и брутально\n"
            "💜 *Hard Dance* — танцевальная электронная музыка с напором\n\n"
            "_Только оригинальная музыка — никакого мейнстрима!_"
        )
        await query.edit_message_caption(
            caption=text, parse_mode="Markdown", reply_markup=back_keyboard()
        )

    elif query.data == "stream_url":
        url = find_stream_url()
        text = (
            f"📡 *Прямая ссылка на поток:*\n\n"
            f"`{url}`\n\n"
            f"Вставь в VLC, Winamp, foobar2000 или любой медиаплеер с поддержкой потоков."
        )
        await query.edit_message_caption(
            caption=text, parse_mode="Markdown", reply_markup=back_keyboard()
        )

    elif query.data == "back":
        text = (
            f"🦄 *Pink Unicorn Radio*\n\n"
            f"{STATION_GENRE}\n"
            f"{STATION_COUNTRY}\n\n"
            "Выбери действие 👇"
        )
        await query.edit_message_caption(
            caption=text, parse_mode="Markdown", reply_markup=main_keyboard(WEBAPP_URL)
        )


async def send_stream(message, context: ContextTypes.DEFAULT_TYPE, edit=False) -> None:
    """Отправляет аудиопоток пользователю."""
    url = STREAM_URL
    text = (
        f"🎧 *{STATION_NAME}*\n"
        f"_{STATION_GENRE}_\n\n"
        f"▶️ Нажми Play чтобы слушать прямо в Telegram!\n\n"
        f"Или открой ссылку в браузере / медиаплеере:\n`{url}`"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🌐 Открыть в браузере", url=url)],
        [InlineKeyboardButton("⬅️ Главное меню", callback_data="back")],
    ])

    if edit:
        try:
            await message.edit_caption(
                caption=text, parse_mode="Markdown", reply_markup=keyboard
            )
        except Exception:
            pass
    else:
        # Telegram умеет воспроизводить аудиопоток как голосовое сообщение
        try:
            await message.reply_audio(
                audio=url,
                title=STATION_NAME,
                performer="Pink Unicorn Records",
                caption=f"🦄 {STATION_GENRE}",
            )
        except Exception:
            # fallback — просто текст со ссылкой
            await message.reply_text(
                text, parse_mode="Markdown", reply_markup=keyboard
            )


def build_info_text() -> str:
    return (
        f"🦄 *{STATION_NAME}*\n\n"
        f"🎵 Жанры: {STATION_GENRE}\n"
        f"🌍 Страна: {STATION_COUNTRY}\n"
        f"📅 Основан: 2017\n"
        f"👤 Владелец: Александр Плетнёв\n\n"
        f"_Pink Unicorn Records выпускает только качественную и оригинальную музыку. "
        f"Мы всегда в поиске новых талантов!_\n\n"
        f"✉️ [pinkunicornrec@gmail.com](mailto:pinkunicornrec@gmail.com)\n"
        f"🌐 [Сайт]({STATION_SITE})\n"
        f"🎵 [Beatport](https://www.beatport.com/label/pink-unicorn-records/65562)\n"
        f"☁️ [SoundCloud](https://soundcloud.com/pinkunicornrec)\n"
        f"📘 [Facebook](https://www.facebook.com/pinkunicornrec/)\n"
        f"🎬 [YouTube](https://www.youtube.com/channel/UCPIa2dLYzYn0J_7BE-rGXYw)"
    )


async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Неизвестная команда."""
    await update.message.reply_text(
        "Используй /start для главного меню или /play для запуска радио 🎧"
    )


def main() -> None:
    if BOT_TOKEN == "ВСТАВЬ_ТОКЕН_СЮДА":
        print("❌ Вставь токен бота в переменную BOT_TOKEN!")
        print("   Получи токен у @BotFather в Telegram")
        return

    # Ищем актуальный stream URL при старте
    print("🔍 Ищу актуальный stream URL...")
    find_stream_url()
    print(f"📡 Stream URL: {STREAM_URL}")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("play", play_cmd))
    app.add_handler(CommandHandler("info", info_cmd))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.COMMAND, unknown))

    print(f"🦄 Pink Unicorn Radio Bot запущен!")
    print(f"   Поток: {STREAM_URL}")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
