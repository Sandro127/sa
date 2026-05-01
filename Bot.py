from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler
import datetime

# -----------------------------
# CONSTANTS
# -----------------------------
DUNGEONS = ["hammer", "ghost", "invasion", "zombie"]

UPD_HAMMER, UPD_GHOST, UPD_INV, UPD_ZOMBIE = range(4)
SET_HAMMER, SET_GHOST, SET_INV, SET_ZOMBIE = range(4)
ASC_PET, ASC_MOUNT, ASC_SKILL = range(3)


# -----------------------------
# INIT PLAYER
# -----------------------------
def init_player(bot_data, user_id, name):
    if "players" not in bot_data:
        bot_data["players"] = {}

    if user_id not in bot_data["players"]:
        bot_data["players"][user_id] = {
            "name": name,
            "pet_drop": 0,
            "mount_drop": 0,
            "skill_reduction": 0,
            "war_mode": "win",
        }

        for d in DUNGEONS:
            bot_data["players"][user_id][f"{d}_stage"] = 1
            bot_data["players"][user_id][f"{d}_battles"] = 0
            bot_data["players"][user_id][f"{d}_resources"] = 0
            bot_data["players"][user_id][f"{d}_wins_today"] = 0


# -----------------------------
# /start
# -----------------------------
def start(update, context):
    user_id = update.message.from_user.id
    name = update.message.from_user.first_name

    init_player(context.bot_data, user_id, name)

    update.message.reply_text(
        "👋 Welcome!\n\n"
        "Available commands:\n\n"
        "/stats – Show your stats\n"
        "/update – Update dungeon wins\n"
        "/setresources – Set your resources manually\n"
        "/setwin – Set war mode to WIN\n"
        "/setlose – Set war mode to LOSE\n"
        "/ascension – Configure ascension bonuses\n"
        "/leaderboard – Show global ranking\n"
    )


# -----------------------------
# /stats
# -----------------------------
def stats(update, context):
    user_id = update.message.from_user.id
    p = context.bot_data["players"][user_id]

    msg = f"📊 STATS FOR {p['name']}\n\n"

    for d in DUNGEONS:
        msg += (
            f"🏰 {d.capitalize()}\n"
            f"Stage: {p[f'{d}_stage']}\n"
            f"Battles: {p[f'{d}_battles']}/15\n"
            f"Resources: {p[f'{d}_resources']}\n\n"
        )

    msg += f"War mode: {p['war_mode']}\n"
    msg += f"Pet drop: {p['pet_drop']}%\n"
    msg += f"Mount drop: {p['mount_drop']}%\n"
    msg += f"Skill reduction: {p['skill_reduction']}%\n"

    update.message.reply_text(msg)


# -----------------------------
# /setwin /setlose
# -----------------------------
def setwin(update, context):
    user_id = update.message.from_user.id
    context.bot_data["players"][user_id]["war_mode"] = "win"
    update.message.reply_text("War mode set to WIN.")

def setlose(update, context):
    user_id = update.message.from_user.id
    context.bot_data["players"][user_id]["war_mode"] = "lose"
    update.message.reply_text("War mode set to LOSE.")


# -----------------------------
# ASCENSION (INTERACTIVE)
# -----------------------------
def ascension(update, context):
    update.message.reply_text("Enter Pet Double Drop Chance (max 50%):")
    return ASC_PET

def asc_pet(update, context):
    user_id = update.message.from_user.id
    v = int(update.message.text)
    if v > 50:
        update.message.reply_text("Max 50%. Try again.")
        return ASC_PET
    context.bot_data["players"][user_id]["pet_drop"] = v
    update.message.reply_text("Enter Mount Double Drop Chance (max 50%):")
    return ASC_MOUNT

def asc_mount(update, context):
    user_id = update.message.from_user.id
    v = int(update.message.text)
    if v > 50:
        update.message.reply_text("Max 50%. Try again.")
        return ASC_MOUNT
    context.bot_data["players"][user_id]["mount_drop"] = v
    update.message.reply_text("Enter Skill Cost Reduction (max 25%):")
    return ASC_SKILL

def asc_skill(update, context):
    user_id = update.message.from_user.id
    v = int(update.message.text)
    if v > 25:
        update.message.reply_text("Max 25%. Try again.")
        return ASC_SKILL
    context.bot_data["players"][user_id]["skill_reduction"] = v
    update.message.reply_text("Ascension bonuses saved.")
    return ConversationHandler.END


# -----------------------------
# /update (INTERACTIVE)
# -----------------------------
def update_cmd(update, context):
    update.message.reply_text("Wins today in Hammer Thief? (0–2)")
    return UPD_HAMMER

def upd_hammer(update, context):
    context.user_data["hammer_wins"] = int(update.message.text)
    update.message.reply_text("Wins today in Ghost Town? (0–2)")
    return UPD_GHOST

def upd_ghost(update, context):
    context.user_data["ghost_wins"] = int(update.message.text)
    update.message.reply_text("Wins today in Invasion? (0–2)")
    return UPD_INV

def upd_inv(update, context):
    context.user_data["invasion_wins"] = int(update.message.text)
    update.message.reply_text("Wins today in Zombie Rush? (0–2)")
    return UPD_ZOMBIE

def upd_zombie(update, context):
    user_id = update.message.from_user.id
    p = context.bot_data["players"][user_id]

    wins = {
        "hammer": context.user_data["hammer_wins"],
        "ghost": context.user_data["ghost_wins"],
        "invasion": context.user_data["invasion_wins"],
        "zombie": context.user_data["zombie_wins"],
    }

    msg = "🏰 DUNGEON UPDATE\n\n"

    for d in DUNGEONS:
        w = wins[d]
        old_stage = p[f"{d}_stage"]
        old_battles = p[f"{d}_battles"]
        old_res = p[f"{d}_resources"]

        new_battles = old_battles + w
        stage_up = False

        if new_battles >= 15:
            new_battles -= 15
            new_stage = old_stage + 1
            stage_up = True
        else:
            new_stage = old_stage

        gained = w * 5
        new_res = old_res + gained

        p[f"{d}_stage"] = new_stage
        p[f"{d}_battles"] = new_battles
        p[f"{d}_resources"] = new_res

        msg += (
            f"🏰 {d.capitalize()}\n"
            f"Wins: {w}\n"
            f"Resources: {' + '.join(['5']*w) if w>0 else '0'} = {gained}\n"
            f"Total: {old_res} + {gained} = {new_res}\n"
            f"Stage: {old_stage} → {new_stage}\n"
            f"Battles: {old_battles} + {w} = {old_battles+w}"
        )
        if stage_up:
            msg += f" → {new_battles} (stage up)"
        msg += "\n\n"

    update.message.reply_text(msg)
    return ConversationHandler.END


# -----------------------------
# /setresources (INTERACTIVE)
# -----------------------------
def setresources(update, context):
    update.message.reply_text("Resources for Hammer Thief:")
    return SET_HAMMER

def set_hammer(update, context):
    context.user_data["hammer_res"] = int(update.message.text)
    update.message.reply_text("Resources for Ghost Town:")
    return SET_GHOST

def set_ghost(update, context):
    context.user_data["ghost_res"] = int(update.message.text)
    update.message.reply_text("Resources for Invasion:")
    return SET_INV

def set_inv(update, context):
    context.user_data["invasion_res"] = int(update.message.text)
    update.message.reply_text("Resources for Zombie Rush:")
    return SET_ZOMBIE

def set_zombie(update, context):
    user_id = update.message.from_user.id
    p = context.bot_data["players"][user_id]

    p["hammer_resources"] = context.user_data["hammer_res"]
    p["ghost_resources"] = context.user_data["ghost_res"]
    p["invasion_resources"] = context.user_data["invasion_res"]
    p["zombie_resources"] = context.user_data["zombie_res"]

    msg = "📦 RESOURCES UPDATED\n\n"
    msg += f"Hammer Thief: {p['hammer_resources']}\n"
    msg += f"Ghost Town: {p['ghost_resources']}\n"
    msg += f"Invasion: {p['invasion_resources']}\n"
    msg += f"Zombie Rush: {p['zombie_resources']}\n"

    update.message.reply_text(msg)
    return ConversationHandler.END


# -----------------------------
# /leaderboard
# -----------------------------
def leaderboard(update, context):
    players = context.bot_data.get("players", {})

    ranking = []
    for uid, p in players.items():
        total = (
            p["hammer_resources"] +
            p["ghost_resources"] +
            p["invasion_resources"] +
            p["zombie_resources"]
        )
        ranking.append((p["name"], total))

    ranking.sort(key=lambda x: x[1], reverse=True)

    msg = "🏆 LEADERBOARD\n\n"
    for i, (name, total) in enumerate(ranking, start=1):
        msg += f"{i}) {name} — {total} resources\n"

    if ranking:
        msg += f"\n🥇 Top player: {ranking[0][0]}"

    update.message.reply_text(msg)


# -----------------------------
# DAILY RESET
# -----------------------------
def daily_reset(context):
    for p in context.bot_data.get("players", {}).values():
        for d in DUNGEONS:
            p[f"{d}_wins_today"] = 0


# -----------------------------
# REMINDER
# -----------------------------
def reminder(context):
    for uid, p in context.bot_data.get("players", {}).items():
        for d in DUNGEONS:
            if p[f"{d}_wins_today"] < 2:
                context.bot.send_message(
                    chat_id=uid,
                    text="⚠️ You still have dungeon attacks available today!"
                )
                break


# -----------------------------
# MAIN
# -----------------------------
def main():
    updater = Updater("8719290481:AAFFYUVZMIpXD9dGbQ4ZUEs3r9xsS2tWGh0", use_context=True)
    dp = updater.dispatcher

    # ASCENSION
    asc_handler = ConversationHandler(
        entry_points=[CommandHandler("ascension", ascension)],
        states={
            ASC_PET: [MessageHandler(Filters.text, asc_pet)],
            ASC_MOUNT: [MessageHandler(Filters.text, asc_mount)],
            ASC_SKILL: [MessageHandler(Filters.text, asc_skill)],
        },
        fallbacks=[]
    )

    # UPDATE
    upd_handler = ConversationHandler(
        entry_points=[CommandHandler("update", update_cmd)],
        states={
            UPD_HAMMER: [MessageHandler(Filters.text, upd_hammer)],
            UPD_GHOST: [MessageHandler(Filters.text, upd_ghost)],
            UPD_INV: [MessageHandler(Filters.text, upd_inv)],
            UPD_ZOMBIE: [MessageHandler(Filters.text, upd_zombie)],
        },
        fallbacks=[]
    )

    # SET RESOURCES
    setres_handler = ConversationHandler(
        entry_points=[CommandHandler("setresources", setresources)],
        states={
            SET_HAMMER: [MessageHandler(Filters.text, set_hammer)],
            SET_GHOST: [MessageHandler(Filters.text, set_ghost)],
            SET_INV: [MessageHandler(Filters.text, set_inv)],
            SET_ZOMBIE: [MessageHandler(Filters.text, set_zombie)],
        },
        fallbacks=[]
    )

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("stats", stats))
    dp.add_handler(CommandHandler("setwin", setwin))
    dp.add_handler(CommandHandler("setlose", setlose))
    dp.add_handler(CommandHandler("leaderboard", leaderboard))
    dp.add_handler(asc_handler)
    dp.add_handler(upd_handler)
    dp.add_handler(setres_handler)

    updater.job_queue.run_daily(daily_reset, time=datetime.time(0, 0))
    updater.job_queue.run_daily(reminder, time=datetime.time(20, 0))

    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
