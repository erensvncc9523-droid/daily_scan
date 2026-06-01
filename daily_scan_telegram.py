import json
import logging
import os
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from tarama import (
    ALLOW_DATA_FALLBACK,
    BIST_HISSELER,
    DATA_SOURCE,
    SCRIPT_VERSION as TARAMA_VERSION,
    gunluk_al_tara,
)

NETWORK_RETRY_COUNT = 3
NETWORK_RETRY_DELAY_SECONDS = 10
TIMEZONE = "Europe/Istanbul"


def get_data_dir() -> Path:
    data_dir = Path(os.getenv("BOT_DATA_DIR", "."))
    try:
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir
    except OSError:
        fallback = Path(".")
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


DATA_DIR = get_data_dir()
CONFIG_PATH = Path("telegram_bot_config.json")
LOG_PATH = DATA_DIR / "daily_scan_telegram.log"
SCRIPT_VERSION = "daily_scan_telegram.py 2026-05-10 railway"

logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    encoding="utf-8",
)


def log_info(message: str) -> None:
    print(message)
    logging.info(message)


def log_error(message: str) -> None:
    print(message)
    logging.error(message)


def send_telegram_message(bot_token: str, chat_id: str, text: str) -> None:
    payload = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode("utf-8")
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    last_error = None

    for attempt in range(1, NETWORK_RETRY_COUNT + 1):
        try:
            request = urllib.request.Request(url, data=payload, method="POST")
            with urllib.request.urlopen(request, timeout=20) as response:
                raw = response.read().decode("utf-8", errors="replace")
            parsed = json.loads(raw)
            if not parsed.get("ok", False):
                raise RuntimeError(f"Telegram API error: {parsed}")
            return
        except Exception as exc:
            last_error = exc
            if attempt < NETWORK_RETRY_COUNT:
                time.sleep(NETWORK_RETRY_DELAY_SECONDS)

    raise last_error


def parse_bool(value: object, default: bool) -> bool:
    if value is None:
        return default
    text = str(value).strip().lower()
    if text == "":
        return default
    return text not in {"0", "false", "hayir", "no", "off"}


def load_local_config() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{CONFIG_PATH} okunamadi: {exc}") from exc


def get_runtime_config() -> tuple[str, str, list[str], bool]:
    local_config = load_local_config()
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    symbols_raw = os.getenv("SYMBOLS", "").strip()
    send_empty_raw = os.getenv("SEND_EMPTY_SCAN_MESSAGE")

    if not bot_token:
        bot_token = str(local_config.get("telegram_bot_token", "")).strip()
    if not chat_id:
        chat_id = str(local_config.get("telegram_chat_id", "")).strip()

    if (
        not bot_token
        or bot_token == "BURAYA_BOT_TOKEN"
        or not chat_id
        or chat_id == "BURAYA_CHAT_ID"
    ):
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID Railway Variables icinde veya "
            "telegram_bot_config.json dosyasinda tanimli olmali."
        )

    if symbols_raw:
        symbols = [part.strip().upper() for part in symbols_raw.split(",") if part.strip()]
    else:
        symbols = BIST_HISSELER

    send_empty_message = parse_bool(send_empty_raw, True)
    return bot_token, chat_id, symbols, send_empty_message


def run_daily_scan(symbols: list[str]) -> tuple[list[dict], list[str]]:
    return gunluk_al_tara(symbols, log_info)


def build_message(al_listesi: list[dict], hata_listesi: list[str], total_symbols: int) -> str:
    now_text = datetime.now(ZoneInfo(TIMEZONE)).strftime("%d.%m.%Y %H:%M")
    lines = [
        "📊 Günlük AL Taraması",
        "━━━━━━━━━━━━━━",
        "",
        f"🕒 Tarama zamanı: {now_text}",
        f"🔎 Taranan hisse: {total_symbols}",
        f"📡 Veri ayarı: {DATA_SOURCE}",
        f"🛟 Fallback: {'açık' if ALLOW_DATA_FALLBACK else 'kapalı'}",
        "",
    ]

    if al_listesi:
        lines.append(f"🟢 AL sinyali verenler: {len(al_listesi)}")
        lines.append("")
        for item in al_listesi:
            lines.extend(
                [
                    "━━━━━━━━━━━━━━",
                    f"📌 Hisse: {item['Hisse']}",
                    f"🚦 AL Gücü: {item['AL Gücü']}",
                    f"💰 Kapanış: {item['Kapanış Fiyatı']:.2f}",
                    f"🛑 Stop: {item['Stop Fiyatı']:.2f}",
                    f"📅 Sinyal tarihi: {item['Sinyal Tarihi']}",
                    f"📡 Veri: {item.get('Veri Kaynagi', 'yok')}",
                    "",
                ]
            )
    else:
        lines.append("⚪ AL sinyali veren hisse yok")

    if hata_listesi:
        lines.append("")
        lines.append(f"⚠️ Hata/veri sorunu: {', '.join(hata_listesi[:15])}")

    return "\n".join(lines).strip()


def main() -> None:
    bot_token, chat_id, symbols, send_empty_message = get_runtime_config()
    log_info(f"Script version: {SCRIPT_VERSION}")
    log_info(f"Imported tarama version: {TARAMA_VERSION}")
    log_info(f"Data source: {DATA_SOURCE} | fallback: {'on' if ALLOW_DATA_FALLBACK else 'off'}")
    log_info(f"Gunluk Railway taramasi basladi. Hisse sayisi: {len(symbols)}")

    al_listesi, hata_listesi = run_daily_scan(symbols)
    message = build_message(al_listesi, hata_listesi, len(symbols))

    if al_listesi or send_empty_message:
        send_telegram_message(bot_token, chat_id, message)
        log_info("Gunluk tarama Telegram mesaji gonderildi.")
    else:
        log_info("AL sinyali yok; bos tarama mesaji kapali oldugu icin Telegram gonderilmedi.")


if __name__ == "__main__":
    main()
