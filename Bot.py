from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler
from telegram import ReplyKeyboardMarkup
import datetime

# -----------------------------
# CONSTANTS
# -----------------------------
DUNGEONS = ["hammer", "ghost", "invasion", "zombie"]

UPD_HAMMER, UPD_GHOST, UPD_INV, UPD_ZOMBIE = range(4)
ASC_PET, ASC_MOUNT, ASC_SKILL = range(3)


# -----------------------------
# INIT USER DATA
# -----------------------------
def init_user(user_data):
    for d in DUNGEONS:
        user_data.setdefault(f"{d}_stage", 1)
        user_data.setdefault(f"{d}_battles", 0)
        user_data.setdefault(f"{d}_resources", 0)
        user_data.setdefault(f"{d}_wins_today", 0)

    user_data.setdefault("war_mode", "win")
    user_data.setdefault("pet_drop", 0)
    user_data.setdefault("mount_drop", 0)
    user_data.setdefault("skill_reduction", 0)


# -----------------------------
# /start
# -----------------------------
def start(update, context):
    user_data = context.user_data
    init_user(user_data)
    user_data["chat_id"] = update.message.chat_id

    text = (
        "👋 Welcome!\n\n"
        "Available commands:\n\n"
        "/start – Show all commands\n"
        "/stats – Show all your saved data\n"
        "/setwin – Set war rewards for WIN\n"
        "/setlose – Set war rewards for LOSE\n"
        "/ascension – Interactive ascension calculator\n"
        "/update – Update dungeon wins, stages and resources\n"
        "/graph – Show resources graph\n"
    )

    update.message.reply_text(text)


# -----------------------------
# /setwin /setlose
# -----------------------------
def setwin(update, context):
    context.user_data["war_mode"] = "win"
    update.message.reply_text("War mode set to WIN.")

def setlose(update, context):
    context.user_data["war_mode"] = "lose"
    update.message.reply_text("War mode set to LOSE.")


# -----------------------------
# /stats
# -----------------------------
def stats(update, context):
    user_data = context.user_data
    init_user(user_data)

    msg = "📊 YOUR STATS\n\n"

    for d in DUNGEONS:
        msg += (
            f"🏰 {d.capitalize()}\n"
            f"Stage: {user_data[f'{d}_stage']}\n"
            f"Battles: {user_data[f'{d}_battles']}/15\n"
            f"Resources: {user_data[f'{d}_resources']}\n\n"
        )

    msg += f"War mode: {user_data['war_mode']}\n"
    msg += f"Pet drop: {user_data['pet_drop']}%\n"
    msg += f"Mount drop: {user_data['mount_drop']}%\n"
    msg += f"Skill reduction: {user_data['skill_reduction']}%\n"

    update.message.reply_text(msg)


# -----------------------------
# ASCENSION (INTERACTIVE)
# -----------------------------
def ascension(update, context):
    update.message.reply_text("Enter your Pet Double Drop Chance (max 50%):")
    return ASC_PET

def asc_pet(update, context):
    v = int(update.message.text)
    if v > 50:
        update.message.reply_text("Max allowed is 50%. Try again.")
        return ASC_PET
    context.user_data["pet_drop"] = v
    update.message.reply_text("Enter your Mount Double Drop Chance (max 50%):")
    return ASC_MOUNT

def asc_mount(update, context):
    v = int(update.message.text)
    if v > 50:
        update.message.reply_text("Max allowed is 50%. Try again.")
        return ASC_MOUNT
    context.user_data["mount_drop"] = v
    update.message.reply_text("Enter your Skill Cost Reduction (max 25%):")
    return ASC_SKILL

def asc_skill(update, context):
    v = int(update.message.text)
    if v > 25:
        update.message.reply_text("Max allowed is 25%. Try again.")
        return ASC_SKILL

    context.user_data["skill_reduction"] = v
    update.message.reply_text("Ascension data saved.")
    return ConversationHandler.END


# -----------------------------
# /update (INTERACTIVE)
# -----------------------------
def update_cmd(update, context):
    init_user(context.user_data)
    update.message.reply_text("How many wins today in Hammer Thief? (0–2)")
    return UPD_HAMMER

def upd_hammer(update, context):
    context.user_data["hammer_wins_today"] = int(update.message.text)
    update.message.reply_text("How many wins today in Ghost Town? (0–2)")
    return UPD_GHOST

def upd_ghost(update, context):
    context.user_data["ghost_wins_today"] = int(update.message.text)
    update.message.reply_text("How many wins today in Invasion? (0–2)")
    return UPD_INV

def upd_inv(update, context):
    context.user_data["invasion_wins_today"] = int(update.message.text)
    update.message.reply_text("How many wins today in Zombie Rush? (0–2)")
    return UPD_ZOMBIE

def upd_zombie(update, context):
    msg = "🏰 DUNGEON UPDATE\n\n"

    for d in DUNGEONS:
        wins_today = context.user_data[f"{d}_wins_today"]
        old_stage = context.user_data[f"{d}_stage"]
        old_battles = context.user_data[f"{d}_battles"]
        old_resources = context.user_data[f"{d}_resources"]

        # Update battles
        new_battles = old_battles + wins_today
        stage_up = False

        if new_battles >= 15:
            new_battles -= 15
            new_stage = old_stage + 1
            stage_up = True
        else:
            new_stage = old_stage

        # Resources
        resources_today = wins_today * 5
        new_resources = old_resources + resources_today

        # Save
        context.user_data[f"{d}_stage"] = new_stage
        context.user_data[f"{d}_battles"] = new_battles
        context.user_data[f"{d}_resources"] = new_resources

        # Report
        msg += f"🏰 {d.capitalize()}\n"
        msg += f"Wins today: {wins_today}\n"
        msg += f"Resources gained: {' + '.join(['5']*wins_today) if wins_today>0 else '0'} = {resources_today}\n"
        msg += f"Total resources: {old_resources} + {resources_today} = {new_resources}\n"
        msg += f"Stage: {old_stage} → {new_stage}\n"
        msg += f"Battles: {old_battles} + {wins_today} = {old_battles + wins_today}"
        if stage_up:
            msg += f" → {new_battles} (stage up)"
        msg += "\n\n"

    update.message.reply_text(msg)
    return ConversationHandler.END


# -----------------------------
# DAILY RESET (00:00)
# -----------------------------
def daily_reset(context):
    user_data = context.job.context
    for d in DUNGEONS:
        user_data[f"{d}_wins_today"] = 0

    context.bot.send_message(
        chat_id=user_data["chat_id"],
        text="🔄 Daily reset completed. Wins today set to 0."
    )


# -----------------------------
# REMINDER AT 20:00
# -----------------------------
def reminder(context):
    user_data = context.job.context
    for d in DUNGEONS:
        if user_data.get(f"{d}_wins_today", 0) < 2:
            context.bot.send_message(
                chat_id=user_data["chat_id"],
                text="⚠️ You still have dungeon attacks available today!"
            )
            break


# -----------------------------
# MAIN
# -----------------------------
def main():
    updater = Updater("YOUR_TOKEN", use_context=True)
    dp = updater.dispatcher

    # ASCENSION HANDLER
    asc_handler = ConversationHandler(
        entry_points=[CommandHandler("ascension", ascension)],
        states={
            ASC_PET: [MessageHandler(Filters.text, asc_pet)],
            ASC_MOUNT: [MessageHandler(Filters.text, asc_mount)],
            ASC_SKILL: [MessageHandler(Filters.text, asc_skill)],
        },
        fallbacks=[]
    )

    # UPDATE HANDLER
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

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("stats", stats))
    dp.add_handler(CommandHandler("setwin", setwin))
    dp.add_handler(CommandHandler("setlose", setlose))
    dp.add_handler(asc_handler)
    dp.add_handler(upd_handler)

    # DAILY RESET AT 00:00
    updater.job_queue.run_daily(
        daily_reset,
        time=datetime.time(hour=0, minute=0, second=0),
        context=dp.user_data
    )

    # REMINDER AT 20:00
    updater.job_queue.run_daily(
        reminder,
        time=datetime.time(hour=20, minute=0, second=0),
        context=dp.user_data
    )

    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
