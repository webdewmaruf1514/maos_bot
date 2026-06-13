import json
import os
import time
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

try:
    import mysql.connector as mysql_connector
except ImportError:  # pragma: no cover - handled at runtime
    mysql_connector = None

load_dotenv()

TOKEN = os.getenv("TG_BOT_TOKEN", "")
API_URL = f"https://api.telegram.org/bot{TOKEN}"
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "2208Mysql!@#Bnpz"),
    "database": os.getenv("DB_NAME", "maosh"),
    "autocommit": True,
}


class BotError(Exception):
    pass


def normalize_phone(phone: str) -> str:
    phone = phone.strip()
    if not phone:
        return phone
    if not phone.startswith("+"):
        phone = f"+{phone}"
    return phone


def build_month_keyboard(months: List[str]) -> List[List[Dict[str, str]]]:
    keyboard: List[List[Dict[str, str]]] = []
    row: List[Dict[str, str]] = []
    for idx, month in enumerate(months, start=1):
        row.append({"text": month})
        if idx % 3 == 0 or idx == len(months):
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([{"text": "/stop"}])
    return keyboard


def decode_salary_message(encoded_message: str, table_number: int) -> str:
    parts = encoded_message.split(":")
    decoded_chars = []
    for part in parts[:-1]:
        decoded_chars.append(chr(int(part) - table_number))
    return "".join(decoded_chars)


def get_db_connection():
    if mysql_connector is None:
        raise RuntimeError("mysql-connector-python is required")
    return mysql_connector.connect(**DB_CONFIG)


def tg_request(method: str, params: Optional[Dict[str, Any]] = None, use_post: bool = True) -> Dict[str, Any]:
    if params is None:
        params = {}
    if use_post:
        data = urllib.parse.urlencode(params).encode("utf-8")
        req = urllib.request.Request(f"{API_URL}/{method}", data=data, method="POST")
    else:
        query = urllib.parse.urlencode(params)
        req = urllib.request.Request(f"{API_URL}/{method}?{query}", method="GET")
    with urllib.request.urlopen(req, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def send_message(chat_id: int, text: str) -> None:
    tg_request("sendMessage", {"chat_id": chat_id, "text": text, "parse_mode": "HTML"})


def send_keyboard(chat_id: int, text: str, keyboard: List[List[Dict[str, str]]]) -> None:
    tg_request("sendMessage", {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "reply_markup": json.dumps({"keyboard": keyboard, "resize_keyboard": True, "one_time_keyboard": True})
    })


def answer_callback_query(callback_query_id: str, text: Optional[str] = None, show_alert: bool = False) -> None:
    tg_request("answerCallbackQuery", {
        "callback_query_id": callback_query_id,
        "text": text or "",
        "show_alert": int(show_alert),
    })


def handle_update(update: Dict[str, Any]) -> None:
    message = update.get("message", {})
    callback_query = update.get("callback_query", {})
    chat_id = (message.get("chat", {}) or {}).get("id")
    username = (message.get("from", {}) or {}).get("username", "")
    text = message.get("text", "")
    contact = message.get("contact", {})

    if callback_query:
        callback_data = callback_query.get("data")
        callback_query_id = callback_query.get("id")
        chat_id = (callback_query.get("message", {}) or {}).get("chat", {}).get("id")
        if chat_id is None:
            return
        try:
            conn = get_db_connection()
        except RuntimeError:
            return
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM telegram WHERE user_id=%s", (chat_id,))
            user_row = cursor.fetchone()
            if not user_row:
                cursor.execute("INSERT INTO telegram (username, user_id) VALUES (%s, %s)", (username, chat_id))
                conn.commit()
                user_row = {"lang": 1, "agree": 0}
            if callback_data == "/uz":
                answer_callback_query(callback_query_id)
                cursor.execute("UPDATE telegram SET lang=1 WHERE user_id=%s", (chat_id,))
                conn.commit()
                send_message(chat_id, "Botga xush kelibsiz. Telefon raqamingizni yuboring.")
            elif callback_data == "/ru":
                answer_callback_query(callback_query_id)
                cursor.execute("UPDATE telegram SET lang=2 WHERE user_id=%s", (chat_id,))
                conn.commit()
                send_message(chat_id, "Добро пожаловать. Пожалуйста, отправьте ваш номер телефона.")
            elif callback_data == "/1":
                answer_callback_query(callback_query_id)
                cursor.execute("UPDATE telegram SET agree=1 WHERE user_id=%s", (chat_id,))
                conn.commit()
                send_keyboard(chat_id, "Telefon raqamingizni yuboring.", [[{"text": "☎️ Telefon raqami", "request_contact": True}]])
            elif callback_data == "/0":
                answer_callback_query(callback_query_id)
                cursor.execute("UPDATE telegram SET agree=0 WHERE user_id=%s", (chat_id,))
                conn.commit()
        finally:
            conn.close()
        return

    if not chat_id:
        return

    try:
        conn = get_db_connection()
    except RuntimeError:
        return
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM telegram WHERE user_id=%s", (chat_id,))
        user_row = cursor.fetchone()
        if not user_row:
            cursor.execute(
                "INSERT INTO telegram (username, user_id) VALUES (%s, %s)",
                (username, chat_id),
            )
            conn.commit()
            user_row = {"lang": 1, "agree": 0, "auth": 0, "tel_number": None, "tabel_number": None, "update_time": None, "views": 0}

        lang = user_row.get("lang") or 1
        agree = user_row.get("agree") or 0
        auth = user_row.get("auth") or 0
        data_tel = user_row.get("tel_number")
        data_tabel = user_row.get("tabel_number")
        data_update_time = user_row.get("update_time")
        views = user_row.get("views") or 0

        if text == "/start":
            if agree == 1:
                send_keyboard(chat_id, "Tizimga xush kelibsiz! Telefon raqamingizni pastdagi tugma orqali yuboring.", [[{"text": "☎️ Telefon raqami", "request_contact": True}]])
            else:
                send_message(chat_id, "Tilni tanlang / Выберите язык")
            return

        if contact:
            phone = normalize_phone(contact.get("phone_number", ""))
            cursor.execute("SELECT * FROM salary_tg WHERE tel_number=%s", (phone,))
            if cursor.fetchone():
                cursor.execute("UPDATE telegram SET tel_number=%s WHERE user_id=%s", (phone, chat_id))
                conn.commit()
                send_message(chat_id, "Iltimos, tabel raqamingizni kiriting")
            else:
                send_message(chat_id, "Telefon raqamingiz ma'lumotlar bazasida topilmadi")
            return

        if text and text.startswith("/"):
            if text == "/stop":
                send_keyboard(chat_id, "Sessiyani tugatish uchun telefon raqamingizni qayta yuboring.", [[{"text": "☎️ Telefon raqami", "request_contact": True}]])
            return

        if text and data_tel and data_tabel:
            cursor.execute(
                "SELECT * FROM salary_tg WHERE tel_number=%s AND tabel_number=%s AND month_year=%s LIMIT 1",
                (data_tel, data_tabel, text),
            )
            salary_row = cursor.fetchone()
            if salary_row:
                decoded = decode_salary_message(salary_row["info_ru"], int(data_tabel))
                cursor.execute("UPDATE telegram SET views=%s WHERE user_id=%s", (views + 1, chat_id))
                conn.commit()
                send_message(chat_id, decoded)
            else:
                send_message(chat_id, "Bunday oy ma'lumotlari topilmadi")
            return

        if text and data_tel and not data_tabel:
            cursor.execute("SELECT * FROM salary_tg WHERE tabel_number=%s LIMIT 1", (text,))
            if cursor.fetchone():
                cursor.execute("UPDATE telegram SET tabel_number=%s, auth=1, update_time=%s WHERE user_id=%s", (text, int(time.time()), chat_id))
                conn.commit()
                months = []
                cursor.execute("SELECT month_year FROM salary_tg WHERE tabel_number=%s GROUP BY month_year ORDER BY id DESC LIMIT 12", (text,))
                for row in cursor.fetchall():
                    months.append(row["month_year"])
                send_keyboard(chat_id, "Kerakli oyni tanlang", build_month_keyboard(months))
            else:
                send_message(chat_id, "Bunday tabellar raqam topilmadi")
            return

        send_message(chat_id, "Iltimos, /start ni bosing")
    finally:
        conn.close()


def fetch_updates(offset: int = 0) -> Dict[str, Any]:
    params = {"offset": offset, "timeout": 30}
    return tg_request("getUpdates", params, use_post=False)


def run_polling() -> None:
    offset = 0
    while True:
        result = fetch_updates(offset)
        for update in result.get("result", []):
            offset = update["update_id"] + 1
            handle_update(update)
        time.sleep(1)


def main() -> None:
    print("Python bot is ready. Start polling...")
    run_polling()


if __name__ == "__main__":
    main()
