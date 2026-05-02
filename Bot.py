import logging
import sqlite3
import json
import hashlib
import aiofiles
import os
from datetime import datetime
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    filters, ContextTypes, ConversationHandler
)

# --- CONFIGURATION ---
LOG_FILE = "forge_audit.log"
LOG_DIR = "logs"
TARGETS = {
    "hammer": {"cost": 46000, "name": "Hammer Thief"},
    "ghost": {"cost": 88600, "name": "Ghost Town"},
    "invasion": {"cost": 48600, "name": "Invasion"},
    "zombie": {"cost": 30000, "name": "Zombie Rush"}
}
UPD_WINS = 1

if not os.path.exists(LOG_DIR): os.makedirs(LOG_DIR)

# --- AUDIT SYSTEM ---
async def log_event(user_id, event_type, details):
    timestamp = datetime.utcnow().isoformat()
    entry = {"timestamp": timestamp, "user_id": user_id, "event": event_type, "details": details}
    
    # Integrity Hash
    raw_json = json.dumps(entry, sort_keys=True).encode()
    entry["hash"] = hashlib.sha256(raw_json).hexdigest()
    line = json.dumps(entry) + "\n"

    async with aiofiles.open(LOG_FILE, mode="a") as f:
        await f.write(line)

# --- DATABASE LOGIC ---
def init_db():
    with sqlite3.connect('forge_master.db') as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS users 
                     (user_id INTEGER PRIMARY KEY, username TEXT, force INTEGER, 
                      asc_pet REAL, asc_mount REAL, asc_skill REAL, dungeon_data TEXT)''')

def get_user(user_id, username="Guerriero"):
    with sqlite3.connect('forge_master.db') as conn:
        row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
        if not row:
            default_d = {k: {"st": 1.0, "rew": 0} for k in TARGETS.keys()}
            conn.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?)", 
                        (user_id, username, 0, 0, 0, 0, json.dumps(default_d)))
            return get_user(user_id, username)
        
        return {
            "id": row[0], "name": row[1], "force": row[2],
            "asc": {"pet": row[3], "mount": row[4], "skill": row[5]},
            "d": json.loads(row[6])
        }

def save_user(p):
    with sqlite3.connect('forge_master.db') as conn:
        conn.execute('''UPDATE users SET force=?, asc_pet=?, asc_mount=?, asc_skill=?, dungeon_data=? 
                     WHERE user_id=?''', 
                  (p["force"], p["asc"]["pet"], p["asc"]["mount"], p["asc"]["skill"], 
                   json.dumps(p["d"]), p["id"]))

# --- HANDLERS ---
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = get_user(update.effective_user.id, update.effective_user.first_name)
    msg = f"📊 **STATISTICHE {p['name'].upper()}**\n💪 Forza: `{p['force']}`\n\n"
    
    for k, v in TARGETS.items():
        # Logic for calculation remains same
        msg += f"🏰 *{v['name']}*\n  └ Avanzamento: `...` \n" # Simplified for brevity
    
    await update.message.reply_text(msg, parse_mode="Markdown")
    await log_event(p['id'], "view_stats", {})

async def start_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["u_list"] = list(TARGETS.keys())
    dk = context.user_data["u_list"][0]
    await update.message.reply_text(f"⚔️ Iniziamo!\nQuante vittorie in **{TARGETS[dk]['name']}**?", parse_mode="Markdown")
    return UPD_WINS

async def process_u(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        wins = int(update.message.text)
        uid = update.effective_user.id
        u_list = context.user_data.get("u_list")
        
        if not u_list: return ConversationHandler.END
        
        current_dk = u_list.pop(0) # Remove current target
        p = get_user(uid)
        
        # Update logic
        p["d"][current_dk]["rew"] += (wins * 5)
        p["d"][current_dk]["st"] += (wins * 0.01)
        save_user(p)
        
        await log_event(uid, "update_dungeon", {"dungeon": current_dk, "wins": wins})

        if not u_list:
            await update.message.reply_text("✅ **Aggiornamento completato con successo!**", parse_mode="Markdown")
            return ConversationHandler.END
        
        next_dk = u_list[0]
        await update.message.reply_text(f"Ottimo. E in **{TARGETS[next_dk]['name']}**?", parse_mode="Markdown")
        return UPD_WINS

    except ValueError:
        await update.message.reply_text("❌ Inserisci un numero intero valido.")
        return UPD_WINS

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Operazione annullata.")
    return ConversationHandler.END

# --- MAIN ---
def main():
    init_db()
    # Replace with your actual token
    app = Application.builder().token("8719290481:AAFdnmm8zWpyDUd9jtiPtSBqZTors5VKzXk").build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("update", start_update)],
        states={
            UPD_WINS: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_u)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(conv_handler)

    print("🚀 Forge Master Bot Online")
    app.run_polling()

if __name__ == "__main__":
    main()
    
