import json
import logging
import os
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

import pandas as pd

from tarama import BIST_HISSELER, INTERVAL, PERIOD_1D, USE_HTF, htf_ok, sinyal_hesapla, veri_cek

NETWORK_RETRY_COUNT = 3
NETWORK_RETRY_DELAY_SECONDS = 10
LOG_PATH = Path("daily_scan_telegram.log")

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


def get_runtime_config() -> tuple[str, str, list[str], bool]:
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    symbols_raw = os.getenv("SYMBOLS", "").strip()
    send_empty_raw = os.getenv("SEND_EMPTY_SCAN_MESSAGE", "true").strip().lower()

    if not bot_token or not chat_id:
        raise RuntimeError("TELEGRAM_BOT_TOKEN ve TELEGRAM_CHAT_ID Railway Variables icinde tanimli olmali.")

    if symbols_raw:
        symbols = [part.strip().upper() for part in symbols_raw.split(",") if part.strip()]
    else:
        symbols = BIST_HISSELER

    send_empty_message = send_empty_raw not in {"0", "false", "hayir", "no"}
    return bot_token, chat_id, symbols, send_empty_message


def run_daily_scan(symbols: list[str]) -> tuple[list[dict], list[str]]:
    al_listesi: list[dict] = []
    hata_listesi: list[str] = []

    for symbol in symbols:
        ticker = f"{symbol}.IS"
        try:
            if USE_HTF and not htf_ok(ticker):
                log_info(f"{symbol}: HTF engelledi")
                continue

            df = veri_cek(ticker, PERIOD_1D, INTERVAL)
            if df is None or len(df) < 30:
                log_info(f"{symbol}: veri yok")
                hata_listesi.append(symbol)
                continue

            al, close = sinyal_hesapla(df)
            if len(al) < 3:
                log_info(f"{symbol}: yetersiz veri")
                continue

            son_al = bool(al.iloc[-1])
            if son_al:
                sinyal_tarihi = df.index[-1].strftime("%d.%m.%Y")
                sinyal_fiyat = round(float(close.iloc[-1]), 2)
                al_listesi.append(
                    {
                        "Hisse": symbol,
                        "Kapanis": sinyal_fiyat,
                        "Sinyal Tarihi": sinyal_tarihi,
                    }
                )
                log_info(f"{symbol}: AL sinyali bulundu @ {sinyal_fiyat}")
            else:
                log_info(f"{symbol}: sinyal yok")
        except Exception as exc:
            log_error(f"{symbol}: hata - {exc}")
            hata_listesi.append(symbol)

    return al_listesi, hata_listesi


def build_message(al_listesi: list[dict], hata_listesi: list[str], total_symbols: int) -> str:
    now_text = datetime.now().strftime("%d.%m.%Y %H:%M")
    lines = [
        f"Gunluk tarama tamamlandi: {now_text}",
        f"Taranan hisse: {total_symbols}",
    ]

    if al_listesi:
        lines.append(f"AL sinyali verenler: {len(al_listesi)}")
        for item in al_listesi:
            lines.append(f"{item['Hisse']}: AL | {item['Kapanis']:.2f} | {item['Sinyal Tarihi']}")
    else:
        lines.append("AL sinyali veren hisse yok")

    if hata_listesi:
        lines.append(f"Hata/veri sorunu: {', '.join(hata_listesi[:15])}")

    return "\n".join(lines)


def main() -> None:
    bot_token, chat_id, symbols, send_empty_message = get_runtime_config()
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
