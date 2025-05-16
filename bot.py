from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)
from groq import Groq
import os
from config import BOT_TOKEN, GROQ_API_KEY
from database import init_db, add_task, get_tasks, delete_task

# Initialize Groq client
client = Groq(api_key=GROQ_API_KEY)

# User states
user_states = {}

# Command: /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hello! I am your NIS Assistant Bot.\n"
        "You can manage tasks or ask questions.\n"
        "Commands:\n"
        "/add - Add a new task\n"
        "/tasks - Show all your tasks\n"
        "/delete <task_id> - Delete a task\n"
        "Or just send me any question!"
    )

# Command: /add
async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_states[user_id] = "awaiting_task"
    await update.message.reply_text("Please send me the task you want to add.")

# Command: /tasks
async def show_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    tasks = get_tasks(user_id)
    if not tasks:
        await update.message.reply_text("You don't have any tasks.")
    else:
        reply = "\n".join([f"{task[0]}. {task[1]}" for task in tasks])
        await update.message.reply_text(f"Your tasks:\n{reply}")

# Command: /delete
async def remove_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        task_id = int(context.args[0])
        delete_task(task_id)
        await update.message.reply_text(f"Task {task_id} deleted.")
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /delete <task_id>")

# Function to send prompt to Groq
async def ask_groq(prompt: str) -> str:
    try:
        response = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error from Groq: {str(e)}"

# Text message handler
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text

    if user_states.get(user_id) == "awaiting_task":
        add_task(user_id, text)
        user_states[user_id] = None
        await update.message.reply_text("Task added!")
        return

    await update.message.reply_text("Thinking... 🤔")
    response = await ask_groq(text)
    await update.message.reply_text(response)

# Main function
def main():
    init_db()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add))
    app.add_handler(CommandHandler("tasks", show_tasks))
    app.add_handler(CommandHandler("delete", remove_task))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("✅ Bot is running with Groq + LLaMA 3")
    app.run_polling()

if __name__ == "__main__":
    main()