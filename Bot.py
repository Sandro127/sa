import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)

# --- CONFIGURAZIONI TARGET (Dall'Excel) ---
TARGETS = {
    "hammer": {"lvl": 47, "cost": 46000, "name": "Hammer Thief"},
    "ghost": {"lvl": 30, "cost": 88600, "name": "Ghost Town"},
    "invasion": {"lvl": 37, "cost": 48600, "name": "Invasion"},
    "zombie": {"lvl": 30, "cost": 30000, "name": "Zombie Rush"} # Valore stimato
}

# Stati Conversazione
SETUP_CHOICE, SETUP_VALUE, UPD_WINS, ASC_INPUT = range(4)

# --- LOGICA DI SUPPORTO ---
def get_p(context_data, user_id, name="Guerriero"):
    if "players" not in context_data: context_data["players"] = {}
    if user_id not in context_data["players"]:
        context_data["players"][user_id] = {
            "name": name,
            "asc": {"pet": 0, "mount": 0, "skill": 0},
            "d": {k: {"st": 1, "ba": 0, "tot": 0, "rew": 0} for k in TARGETS.keys()}
        }
    return context_data["players"][user_id]

def calc_remaining(p, dkey):
    if dkey not in TARGETS: return 0
    t = TARGETS[dkey]
    d = p["d"][dkey]
    gap = t["cost"] - d["tot"]
    if gap <= 0: return "TARGET RAGGIUNTO! ✅"
    
    # Applica Bonus Ascension
    if dkey == "ghost": # Skill cost reduction
        gap *= (1 - (p["asc"]["skill"] / 100))
    elif dkey == "invasion": # Pet double drop
        gap /= (1 + (p["asc"]["pet"] / 100))
    elif dkey == "hammer": # Mount double drop (ipotizzato sui martelli)
        gap /= (1 + (p["asc"]["mount"] / 100))
        
    return int(gap)

# --- HANDLERS COMANDI ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚔️ **We Are Warriors - Gilda Manager**\n\n"
        "1. Usa /setup per impostare i tuoi dati iniziali.\n"
        "2. Usa /ascension per i tuoi bonus percentuale.\n"
        "3. Ogni giorno usa /update per le vittorie.\n"
        "4. Vedi i progressi con /stats.",
        parse_mode="Markdown"
    )

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if "players" not in context.bot_data or uid not in context.bot_data["players"]:
        await update.message.reply_text("Profilo non trovato. Usa /setup.")
        return
    
    p = context.bot_data["players"][uid]
    msg = f"📊 **STATISTICHE DI {p['name'].upper()}**\n\n"
    
    for k, v in p["d"].items():
        mancano = calc_remaining(p, k)
        msg += (f"🏰 **{TARGETS[k]['name']}**\n"
                f"  └ Stage: `{v['st']}.{v['ba']:02d}/15` | Tot: `{v['tot']}`\n"
                f"  └ Mancanti al Target: `{mancano}`\n\n")
    
    msg += (f"✨ **ASCENSION**\n"
            f"  └ Pet: `{p['asc']['pet']}%` | Mount: `{p['asc']['mount']}%` | Skill: `-{p['asc']['skill']}%`")
    await update.message.reply_text(msg, parse_mode="Markdown")

# --- CONVERSATION: SETUP ---
async def start_setup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [["Hammer", "Ghost"], ["Invasion", "Zombie"], ["FINE"]]
    await update.message.reply_text("Seleziona il dungeon da configurare:", 
        reply_markup=ReplyKeyboardMarkup(kb, one_time_keyboard=True))
    return SETUP_CHOICE

async def setup_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text.lower()
    if txt == "fine":
        await update.message.reply_text("Setup completato!", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    context.user_data["curr_s"] = txt
    await update.message.reply_text(f"Inserisci: `STAGE` `TOT_RISORSE` `REWARD_BASE` (es: 18 45000 596)")
    return SETUP_VALUE

async def save_setup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        st, tot, rew = map(int, update.message.text.split())
        p = get_p(context.bot_data, update.effective_user.id)
        p["d"][context.user_data["curr_s"]].update({"st": st, "tot": tot, "rew": rew, "ba": 0})
        await update.message.reply_text("✅ Salvato.")
        return await start_setup(update, context)
    except:
        await update.message.reply_text("Formato errato. Riprova.")
        return SETUP_VALUE

# --- CONVERSATION: UPDATE ---
async def start_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["u_list"] = list(TARGETS.keys())
    return await ask_u(update, context)

async def ask_u(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data["u_list"]:
        await update.message.reply_text("Aggiornamento completato!")
        return ConversationHandler.END
    cur = context.user_data["u_list"][0]
    await update.message.reply_text(f"Vittorie in **{cur.upper()}** (0-2)?")
    return UPD_WINS

async def process_u(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        wins = int(update.message.text)
        dk = context.user_data["u_list"].pop(0)
        p = context.bot_data["players"][update.effective_user.id]["d"][dk]
        
        # Logica: Risorse = (Rew * 2) + (Wins * 5)
        p["tot"] += (p["rew"] * 2) + (wins * 5)
        
        # Logica: Stage up solo con vittorie
        p["ba"] += wins
        if p["ba"] >= 15:
            p["st"] += 1
            p["ba"] -= 15
            await update.message.reply_text(f"🚀 STAGE UP! {dk} ora livello {p['st']}")
            
        return await ask_u(update, context)
    except:
        await update.message.reply_text("Metti un numero (0, 1, 2).")
        return UPD_WINS

# --- CONVERSATION: ASCENSION ---
async def start_asc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Inserisci bonus: `PET%` `MOUNT%` `SKILL_RED%` (es: 10 5 15)")
    return ASC_INPUT

async def save_asc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        pe, mo, sk = map(int, update.message.text.split())
        p = get_p(context.bot_data, update.effective_user.id)
        p["asc"] = {"pet": pe, "mount": mo, "skill": sk}
        await update.message.reply_text("✨ Bonus aggiornati!")
        return ConversationHandler.END
    except:
        return ASC_INPUT

# --- MAIN ---
def main():
    # RIGENERA IL TOKEN SU BOTFATHER SE LO HAI PERSO/PUBBLICATO!
    app = Application.builder().token("8719290481:AAHME7D5aEvXL9-tIuuGYRlDzXgBPFh0_Ck").build()

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("setup", start_setup)],
        states={SETUP_CHOICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, setup_choice)],
                SETUP_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_setup)]},
        fallbacks=[]))

    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("update", start_update)],
        states={UPD_WINS: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_u)]},
        fallbacks=[]))
    
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("ascension", start_asc)],
        states={ASC_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_asc)]},
        fallbacks=[]))

    print("Bot online...")
    app.run_polling()

if __name__ == "__main__":
    main()
     
