import os
import sqlite3
import logging
import re
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Updater, CommandHandler, MessageHandler,
    Filters, ConversationHandler, CallbackContext
)

# --- CONFIG ---
TOKEN = "8719290481:AAF-BDk9j-idnkbgM0IMIyPbRqLukCNCQMU"
ID_CANALE = "-1003578874292"

# Stati
POTENZA, FORGIA, TEMPO_OFF, D1, D2, D3, D4, RIS_UPDATE, V_H, V_S, V_P, V_O = range(12)

logging.basicConfig(level=logging.ERROR)

DB_PATH = "forge_master.db"


# --- DB ---
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS player_data (
                user_id INTEGER PRIMARY KEY,
                potenza TEXT,
                m_min REAL,
                o_sec REAL,
                h_max REAL,
                d1_s INTEGER, d1_b INTEGER,
                d2_s INTEGER, d2_b INTEGER,
                d3_s INTEGER, d3_b INTEGER,
                d4_s INTEGER, d4_b INTEGER,
                risorse TEXT
            )
        """)


# --- Parsing helpers ---
def estrai_numeri(testo: str):
    return re.findall(r"\d+(?:[.,]\d+)?", testo.replace(',', '.'))

def to_float(s: str):
    return float(s)

def parse_two_ints(text: str):
    t = text.strip()
    t = re.sub(r"\s+", " ", t)

    m = re.match(r"^(\d+)[\s\.\-]+(\d+)$", t)
    if m:
        return int(m.group(1)), int(m.group(2))

    m = re.match(r"^(\d+)$", t)
    if m:
        return int(m.group(1)), 0

    return None, None


def calcola_progressione(stage, battaglie_attuali, nuove_vincite):
    totale = int(battaglie_attuali) + int(nuove_vincite)
    nuovo_stage = int(stage)
    if totale >= 15:
        nuovo_stage += 1
        totale -= 15
    return nuovo_stage, totale


def valid_0_1_2(text: str):
    return text in {"0", "1", "2"}


# --- HANDLERS ---
def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "⚙️ CONFIGURAZIONE\n"
        "Inserisci la **Potenza** (testo o numero):"
    )
    return POTENZA


def get_potenza(update: Update, context: CallbackContext):
    context.user_data["potenza"] = update.message.text.strip()
    update.message.reply_text("⚒ FORGIA: Martelli/min e Oro/sec? (Max 2.0) - es: 1.2 1.5")
    return FORGIA


def get_forgia(update: Update, context: CallbackContext):
    n = estrai_numeri(update.message.text)
    if not n:
        update.message.reply_text("⚠️ Inserisci numeri validi. Reinserisci:")
        return FORGIA

    m = to_float(n[0])
    o = to_float(n[1]) if len(n) > 1 else m

    if m > 2.0 or o > 2.0:
        update.message.reply_text("⚠️ Max 2.0! Reinserisci:")
        return FORGIA

    context.user_data["m_min"] = m
    context.user_data["o_sec"] = o
    update.message.reply_text("⏳ OFFLINE: Ore (0-24)? es: 8")
    return TEMPO_OFF


def get_tempo(update: Update, context: CallbackContext):
    n = estrai_numeri(update.message.text)
    if not n:
        update.message.reply_text("⚠️ Inserisci un numero ore (0-24).")
        return TEMPO_OFF

    ore = to_float(n[0])
    if not (0 <= ore <= 24):
        update.message.reply_text("⚠️ Ore fuori range (0-24). Riprova:")
        return TEMPO_OFF

    context.user_data["h_max"] = ore
    update.message.reply_text("🏰 HAMMER Stage.Battaglia (es: 1-0 oppure 2.3):")
    return D1


def get_d1(update: Update, context: CallbackContext):
    s, b = parse_two_ints(update.message.text)
    if s is None:
        update.message.reply_text("⚠️ Formato non valido per D1. Es: 1-0 o 2.3")
        return D1
    context.user_data["d1"] = [s, b]
    update.message.reply_text("🏰 SKILL Stage.Battaglia:")
    return D2


def get_d2(update: Update, context: CallbackContext):
    s, b = parse_two_ints(update.message.text)
    if s is None:
        update.message.reply_text("⚠️ Formato non valido per D2. Es: 1-0 o 2.3")
        return D2
    context.user_data["d2"] = [s, b]
    update.message.reply_text("🏰 PET Stage.Battaglia:")
    return D3


def get_d3(update: Update, context: CallbackContext):
    s, b = parse_two_ints(update.message.text)
    if s is None:
        update.message.reply_text("⚠️ Formato non valido per D3. Es: 1-0 o 2.3")
        return D3
    context.user_data["d3"] = [s, b]
    update.message.reply_text("🏰 POTION Stage.Battaglia:")
    return D4


def get_d4(update: Update, context: CallbackContext):
    s, b = parse_two_ints(update.message.text)
    if s is None:
        update.message.reply_text("⚠️ Formato non valido per D4. Es: 1-0 o 2.3")
        return D4

    required = ["potenza", "m_min", "o_sec", "h_max", "d1", "d2", "d3"]
    if any(k not in context.user_data for k in required):
        update.message.reply_text("⚠️ Config incompleta. Riprova con /start.")
        return ConversationHandler.END

    uid = update.message.from_user.id
    d1 = context.user_data["d1"]
    d2 = context.user_data["d2"]
    d3 = context.user_data["d3"]

    with sqlite3.connect(DB_PATH) as conn:
       conn.execute(
    "CREATE TABLE IF NOT EXISTS player_data ("
    "user_id INTEGER PRIMARY KEY,"
    "potenza TEXT,"
    "m_min REAL,"
    "o_sec REAL,"
    "h_max REAL,"
    "d1_s INTEGER, d1_b INTEGER,"
    "d2_s INTEGER, d2_b INTEGER,"
    "d3_s INTEGER, d3_b INTEGER,"
    "d4_s INTEGER, d4_b INTEGER,"
    "risorse TEXT)"
)
# Salva D4
    context.user_data["d4"] = [s, b]

    d4 = context.user_data["d4"]

    # Salvataggio nel DB
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            INSERT OR REPLACE INTO player_data (
                user_id, potenza, m_min, o_sec, h_max,
                d1_s, d1_b, d2_s, d2_b, d3_s, d3_b, d4_s, d4_b, risorse
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            uid,
            context.user_data["potenza"],
            context.user_data["m_min"],
            context.user_data["o_sec"],
            context.user_data["h_max"],
            d1[0], d1[1],
            d2[0], d2[1],
            d3[0], d3[1],
            d4[0], d4[1],
            "N/A"
        ))

    update.message.reply_text("✅ Configurazione salvata!")

    # Invia al canale
    testo = (
        f"⚙️ NUOVA CONFIG\n"
        f"👤 Utente: {uid}\n"
        f"💥 Potenza: {context.user_data['potenza']}\n"
        f"⚒ Martelli/min: {context.user_data['m_min']}\n"
        f"💰 Oro/sec: {context.user_data['o_sec']}\n"
        f"⏳ Ore offline: {context.user_data['h_max']}\n"
        f"🏰 D1: {d1[0]}-{d1[1]}\n"
        f"🏰 D2: {d2[0]}-{d2[1]}\n"
        f"🏰 D3: {d3[0]}-{d3[1]}\n"
        f"🏰 D4: {d4[0]}-{d4[1]}"
    )

    context.bot.send_message(chat_id=ID_CANALE, text=testo)

    return ConversationHandler.END


def cancel(update: Update, context: CallbackContext):
    update.message.reply_text("❌ Configurazione annullata.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


def main():
    init_db()

    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            POTENZA: [MessageHandler(Filters.text & ~Filters.command, get_potenza)],
            FORGIA: [MessageHandler(Filters.text & ~Filters.command, get_forgia)],
            TEMPO_OFF: [MessageHandler(Filters.text & ~Filters.command, get_tempo)],
            D1: [MessageHandler(Filters.text & ~Filters.command, get_d1)],
            D2: [MessageHandler(Filters.text & ~Filters.command, get_d2)],
            D3: [MessageHandler(Filters.text & ~Filters.command, get_d3)],
            D4: [MessageHandler(Filters.text & ~Filters.command, get_d4)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    dp.add_handler(conv)

    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
