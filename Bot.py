import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
    PicklePersistence,
)

# ID del Canale per i Log
LOG_CHANNEL_ID = -1003578874292

TARGETS = {
    "hammer": {"lvl": 47, "cost": 46000, "name": "Hammer Thief"},
    "ghost": {"lvl": 30, "cost": 88600, "name": "Ghost Town"},
    "invasion": {"lvl": 37, "cost": 48600, "name": "Invasion"},
    "zombie": {"lvl": 30, "cost": 30000, "name": "Zombie Rush"}
}

SETUP_CHOICE, SETUP_VALUE, UPD_WINS, ASC_INPUT, STRENGTH_INPUT = range(5)

# --- FUNZIONI CORE ---

def get_p(context_data, user_id, username="Guerriero"):
    if "players" not in context_data: context_data["players"] = {}
    if user_id not in context_data["players"]:
        context_data["players"][user_id] = {
            "name": username,
            "force": 0,
            "asc": {"pet": 0, "mount": 0, "skill": 0},
            "d": {k: {"st": 1.0, "rew": 0} for k in TARGETS.keys()}
        }
    return context_data["players"][user_id]

def calc_remaining(p, dkey):
    t = TARGETS[dkey]
    d = p["d"][dkey]
    current_total = round(d["st"] * d["rew"])
    gap = t["cost"] - current_total
    
    if gap <= 0: return "RAGGIUNTO ✅"
    
    # Calcolo costo effettivo basato su Ascension
    if dkey == "ghost":
        # Skill riduce il costo totale necessario
        eff_gap = gap * (1 - (p["asc"]["skill"] / 100))
    elif dkey == "invasion":
        # Pet aumenta il guadagno (quindi riduce il gap relativo)
        eff_gap = gap / (1 + (p["asc"]["pet"] / 100))
    elif dkey == "hammer":
        # Mount aumenta il guadagno
        eff_gap = gap / (1 + (p["asc"]["mount"] / 100))
    else:
        eff_gap = gap
        
    return int(eff_gap)

async def send_log(context, message):
    """Invia un log al canale specificato"""
    try:
        await context.bot.send_message(chat_id=LOG_CHANNEL_ID, text=message, parse_mode="Markdown")
    except Exception as e:
        print(f"Errore invio log: {e}")

# --- HANDLERS COMANDI ---

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    p = get_p(context.bot_data, uid, update.effective_user.first_name)
    
    msg = f"📊 **PROGRESSI DI {p['name'].upper()}** (ID: `{uid}`)\n"
    msg += f"💪 Forza attuale: `{p['force']}`\n\n"
    
    for k in TARGETS.keys():
        v = p["d"][k]
        mancanti = calc_remaining(p, k)
        msg += (f"🏰 *{TARGETS[k]['name']}*\n"
                f"  └ Stage: `{v['st']:.2f}` | Risorse: `{round(v['st']*v['rew'])}`/{TARGETS[k]['cost']}\n"
                f"  └ **Mancante (Bonus Incl.): {mancanti}**\n\n")
    
    await update.message.reply_text(msg, parse_mode="Markdown")

async def process_u(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        wins = int(update.message.text)
        uid = update.effective_user.id
        dk = context.user_data["u_list"].pop(0)
        p_full = get_p(context.bot_data, uid)
        p = p_full["d"][dk]
        
        # Logica incremento
        old_st = p["st"]
        if wins > 0:
            p["rew"] += (wins * 5)
            p["st"] += (wins * 0.01)
        
        # Log al canale
        log_msg = (f"📈 **Update Giocatore:** {p_full['name']} (`{uid}`)\n"
                   f"Dungeon: {dk.upper()}\n"
                   f"Vittorie: {wins} | Nuovo Stage: {p['st']:.2f}")
        await send_log(context, log_msg)

        if not context.user_data["u_list"]:
            await update.message.reply_text("✅ Tutti i dungeon aggiornati e loggati!")
            return ConversationHandler.END
        
        return await ask_u(update, context)
    except:
        await update.message.reply_text("Inserisci un numero valido.")
        return UPD_WINS

# --- MAIN ---

def main():
    # Persistenza dati su file
    pers = PicklePersistence(filepath="warriors_database.pickle")
    
    app = Application.builder().token("TUO_TOKEN_QUI").persistence(pers).build()

    # ConversationHandlers (Setup, Strength, Update, Ascension)
    # [Qui vanno aggiunti i ConversationHandler come nel codice precedente]
    
    # Esempio per Update
    update_conv = ConversationHandler(
        entry_points=[CommandHandler("update", start_update)],
        states={UPD_WINS: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_u)]},
        fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)]
    )

    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(update_conv)
    # ... aggiungi gli altri handler ...

    print("Gilda Manager Online...")
    app.run_polling()

if __name__ == "__main__":
    main()
    
