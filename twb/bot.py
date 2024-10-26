import os
import shutil
import threading
import time
from pathlib import Path
from subprocess import check_output
from typing import NamedTuple

import asyncio
import uvloop

from hypy_utils.logging_utils import setup_logger
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

from twb.twitter_gql import TwitterGQL

log = setup_logger()
OUT_PATH = Path(r"/d/Backup/Twitter/Automated")


class QueueEntry(NamedTuple):
    username: str
    update: Update
    context: ContextTypes.DEFAULT_TYPE
    progress: int = 0


queue: list[QueueEntry] = []


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("""
Usage:
/twitter <username> - Backup a user's tweets
""".strip())


async def twitter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Do some basic checks
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /twitter <username>")
        return
    username = context.args[0]

    # Check if already archived
    if any(f for f in OUT_PATH.glob("*.tar.zst") if f.stem.split(' ', 1)[-1].rsplit('.', 1)[0].lower() == username.lower()):
        await update.message.reply_text(f"Already archived {username}. Please check https://cdn.hydev.org/backup/Twitter/")
        return

    # Add to queue
    queue.append(QueueEntry(username, update, context))
    await update.message.reply_text(f"Added {username} to the queue (Currently {len(queue)} in queue)")


async def process_thread():
    while True:
        if queue:
            e = queue.pop(0)

            async def on_progress(msg: str):
                # Edit the existing message instead of sending a new one
                try:
                    await e.context.bot.edit_message_text(
                        chat_id=e.update.effective_chat.id,
                        message_id=progress_message.message_id,
                        text=msg
                    )
                except Exception as edit_exc:
                    log.error(f"Failed to edit message: {edit_exc}")

            try:
                # Send the initial message and keep track of the message ID
                progress_message = await e.context.bot.send_message(
                    e.update.effective_chat.id,
                    f"Starting backup for {e.username}..."
                )

                await api.crawl_all(e.username, on_progress)

                await e.context.bot.edit_message_text(
                    chat_id=e.update.effective_chat.id,
                    message_id=progress_message.message_id,
                    text=f"Done crawling {e.username}, packing now..."
                )

                # Pack
                raw = f"backups/{e.username}"
                ouf = OUT_PATH / f"{time.strftime('%Y-%m-%d')} {e.username}.tar.zst"
                log.info(f"Packing {raw} to {ouf}")
                check_output(["tar", "-I", "zstd -T34 -19", "-cf", str(ouf), "-C", 'backups', e.username])

                # Remove the folder
                # shutil.rmtree(raw)

                await e.context.bot.edit_message_text(
                    chat_id=e.update.effective_chat.id,
                    message_id=progress_message.message_id,
                    text=f"Done archiving {e.username}, check https://cdn.hydev.org/backup/Twitter/"
                )
            except Exception as exc:
                await e.context.bot.edit_message_text(
                    chat_id=e.update.effective_chat.id,
                    message_id=progress_message.message_id,
                    text=f"Error: {exc}"
                )
                log.error(exc)
                raise exc

        else:
            await asyncio.sleep(1)



async def post_init(application):
    print("Starting process thread")
    application.create_task(process_thread())


def main():
    app = ApplicationBuilder().token(os.environ['TG_TOKEN']).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("twitter", twitter))
    print("Running...")
    app.run_polling()


if __name__ == '__main__':
    api = TwitterGQL(Path("cookiezi"))
    main()
