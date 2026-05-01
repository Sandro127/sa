import logging
import sqlite3
import json
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)

# Configurazione Log e ID Canale
LOG_CHANNEL_ID = -1003578874292
logging.basicConfig(level=logging.INFO)

# Configurazione Dungeon
TARGETS = {
    "hammer": {"cost": 46000, "name": "Hammer Thief"},
    "ghost": {"cost": 88600, "name": "Ghost Town"},
    "invasion": {"cost": 48600, "name": "Invasion"},
    "zombie": {"cost": 30000, "name": "Zombie Rush"}
}

UPD_WINS = 1

# --- GESTIONE DATABASE SQLITE ---
def init_db():
    conn = sqlite3.connect('forge_master.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (user_id INTEGER PRIMARY KEY, username TEXT, force INTEGER, 
                  asc_pet REAL, asc_mount REAL, asc_skill REAL, dungeon_data TEXT)''')
    conn.commit()
    conn.close()

def get_user(user_id, username="Guerriero"):
    conn = sqlite3.connect('forge_master.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    
    if not row:
        default_d = {k: {"st": 1.0, "rew": 0} for k in TARGETS.keys()}
        c.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?)", 
                  (user_id, username, 0, 0, 0, 0, json.dumps(default_d)))
        conn.commit()
        row = (user_id, username, 0, 0, 0, 0, json.dumps(default_d))
    
    conn.close()
    return {
        "id": row[0], "name": row[1], "force": row[2],
        "asc": {"pet": row[3], "mount": row[4], "skill": row[5]},
        "d": json.loads(row[6])
    }

def save_user(p):
    conn = sqlite3.connect('forge_master.db')
    c = conn.cursor()
    c.execute('''UPDATE users SET force=?, asc_pet=?, asc_mount=?, asc_skill=?, dungeon_data=? 
                 WHERE user_id=?''', 
              (p["force"], p["asc"]["pet"], p["asc"]["mount"], p["asc"]["skill"], 
               json.dumps(p["d"]), p["id"]))
    conn.commit()
    conn.close()

# --- LOGICA CALCOLO ---
def calc_remaining(p, dkey):
    t = TARGETS[dkey]
    d = p["d"][dkey]
    current_total = round(d["st"] * d["rew"])
    gap = t["cost"] - current_total
    if gap <= 0: return "RAGGIUNTO ✅"
    
    # Applicazione Bonus Ascensione
    if dkey == "ghost": gap *= (1 - (p["asc"]["skill"] / 100))
    elif dkey == "invasion": gap /= (1 + (p["asc"]["pet"] / 100))
    elif dkey == "hammer": gap /= (1 + (p["asc"]["mount"] / 100))
    
    return int(gap)

# --- HANDLERS ---
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    p = get_user(uid, update.effective_user.first_name)
    
    msg = f"📊 **STATISTICHE {p['name'].upper()}**\n"
    msg += f"💪 Forza: `{p['force']}`\n\n"
    
    for k, v in TARGETS.items():
        mancanti = calc_remaining(p, k)
        msg += f"🏰 *{v['name']}*\n  └ Avanzamento: `{mancanti}`\n"
    
    await update.message.reply_text(msg, parse_mode="Markdown")

async def start_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["u_list"] = list(TARGETS.keys())
    dk = context.user_data["u_list"][0]
    await update.message.reply_text(f"Aggiornamento: Quante vittorie in **{TARGETS[dk]['name']}**?")
    return UPD_WINS

async def process_u(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        wins = int(update.message.text)
        uid = update.effective_user.id
        u_list = context.user_data.get("u_list")
        
        if not u_list: return ConversationHandler.END
        
        dk = u_list.pop(0)
        p = get_user(uid)
        
        # Aggiornamento logico
        p["d"][dk]["rew"] += (wins * 5)
        p["d"][dk]["st"] += (wins * 0.01)
        save_user(p)
        
        if not u_list:
            await update.message.reply_text("✅ Aggiornamento completato!")
            return ConversationHandler.END
        
        prossimo = u_list[0]
        await update.message.reply_text(f"Ok. Vittorie in **{TARGETS[prossimo]['name']}**?")
        return UPD_WINS
    except ValueError:
        await update.message.reply_text("Inserisci un numero valido.")
        return UPD_WINS

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Operazione annullata.")
    return ConversationHandler.END

# --- MAIN ---
def main():
    init_db()
    app = Application.builder().token("8719290481:AAEVRqfRK-vC7jXsJumH6jmWiIbfmZj_mmg").build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("update", start_update)],
        states={
            UPD_WINS: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_u)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(conv_handler)

    print("Bot pronto e ottimizzato con SQLite.")
    app.run_polling()

if __name__ == "__main__":
    main()
    
