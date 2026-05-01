import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# Stati per il Setup Iniziale e l'Update
(SET_STAGE, SET_TOTAL_RES, SET_REWARD, 
 ASC_PET, ASC_MOUNT, ASC_SKILL,
 UPD_WINS) = range(7)

# --- LOGICA CORE ---

def init_player(context_data, user_id, name):
    if "players" not in context_data: context_data["players"] = {}
    if user_id not in context_data["players"]:
        context_data["players"][user_id] = {
            "name": name,
            "ascension": {"pet": 0, "mount": 0, "skill": 0},
            "dungeons": {
                "hammer": {"stage": 1, "battles": 0, "total": 0, "reward": 0, "wins_today": None},
                "ghost": {"stage": 1, "battles": 0, "total": 0, "reward": 0, "wins_today": None},
                "invasion": {"stage": 1, "battles": 0, "total": 0, "reward": 0, "wins_today": None},
                "zombie": {"stage": 1, "battles": 0, "total": 0, "reward": 0, "wins_today": None}
            }
        }
    return context_data["players"][user_id]

# --- COMANDO /UPDATE (Giornaliero) ---

async def start_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in context.bot_data.get("players", {}):
        await update.message.reply_text("Usa prima /setup per configurare il tuo profilo!")
        return ConversationHandler.END
    
    # Chiediamo i risultati per tutti i dungeon in una volta o uno alla volta
    context.user_data["temp_upd"] = list(init_player(context.bot_data, user_id, "").get("dungeons").keys())
    return await next_dungeon_step(update, context)

async def next_dungeon_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data["temp_upd"]:
        await update.message.reply_text("✅ Tutti i dungeon sono stati aggiornati!")
        return ConversationHandler.END
    
    current = context.user_data["temp_upd"][0]
    await update.message.reply_text(f"Quante vittorie in **{current.upper()}** oggi? (0, 1, 2)", parse_mode="Markdown")
    return UPD_WINS

async def process_wins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    wins = int(update.message.text)
    d_key = context.user_data["temp_upd"].pop(0)
    p = context.bot_data["players"][user_id]["dungeons"][d_key]

    # LOGICA RICHIESTA:
    # 1. Risorse base (anche se perdi) = Reward * 2
    # 2. Bonus vittoria = +5 per ogni vittoria
    guadagno_base = p["reward"] * 2
    bonus_vittoria = wins * 5
    p["total"] += (guadagno_base + bonus_vittoria)

    # 3. Avanzamento stage (solo se vince)
    p["battles"] += wins
    if p["battles"] >= 15:
        p["stage"] += 1
        p["battles"] -= 15 # Torna a 0 (o mantiene l'eccesso se vinceva 2 volte al 14/15)
        await update.message.reply_text(f"🌟 LIVELLO COMPLETATO! {d_key} sale allo stage {p['stage']}!")

    p["wins_today"] = wins
    return await next_dungeon_step(update, context)

# --- COMANDO /STATS ---

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in context.bot_data.get("players", {}):
        await update.message.reply_text("Nessun dato trovato. Usa /setup.")
        return

    p = context.bot_data["players"][user_id]
    msg = f"📊 **PROFILO DI {p['name'].upper()}**\n\n"
    for dk, dv in p["dungeons"].items():
        msg += (f"🏰 **{dk.capitalize()}**\n"
                f"Stage: `{dv['stage']}-{dv['battles']}/15`\n"
                f"Risorse Totali: `{dv['total']}`\n"
                f"Reward Base: `{dv['reward']}`\n\n")
    
    msg += f"✨ **ASCENSIONE**: Pet {p['ascension']['pet']}% | Skill -{p['ascension']['skill']}%"
    await update.message.reply_text(msg, parse_mode="Markdown")

# --- GESTIONE ERRORI E CHIUSURA ---
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Azione annullata.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# --- MAIN ---
def main():
    # Sostituisci col tuo Token
    app = Application.builder().token("IL_TUO_TOKEN").build()

    # Conversation per l'Update giornaliero
    update_conv = ConversationHandler(
        entry_points=[CommandHandler("update", start_update)],
        states={
            UPD_WINS: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_wins)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    app.add_handler(CommandHandler("start", stats)) # O un benvenuto
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(update_conv)
    # Aggiungi qui gli altri handler per /setup e /ascension seguendo lo stesso schema

    print("Bot avviato...")
    app.run_polling()

if __name__ == "__main__":
    main()
    
