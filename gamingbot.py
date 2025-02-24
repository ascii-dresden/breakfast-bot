#!/usr/bin/env python3

import os
import sys
import signal
import time
import logging
import shelve
import datetime
from telegram import Update, ChatMember
from telegram.ext import Application, ContextTypes, ChatMemberHandler, PollAnswerHandler

logging.basicConfig(
    format="%(asctime)s %(levelname)s:%(message)s",
    level=logging.DEBUG if os.getenv("DEBUG") is not None else logging.INFO,
)

updater: Application = None
state: shelve.Shelf = None


async def chat_member_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chats = state["chats"]
    member = update.my_chat_member.new_chat_member
    if member["status"] in (
        ChatMember.MEMBER,
        ChatMember.OWNER,
        ChatMember.ADMINISTRATOR,
    ):
        chats.add(update.effective_chat.id)
    elif update.effective_chat.id in chats:
        chats.remove(update.effective_chat.id)
    state["chats"] = chats


def sighandler(signum, frame):
    state.close()
    if updater:
        updater.stop()
    sys.exit(0)


async def start_poll(context: ContextTypes.DEFAULT_TYPE):
    polls = state["polls"]
    logging.info("Notifying")
    for chat in state["chats"]:
        options = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Kommende Woche leider nicht"]
        poll = await updater.bot.send_poll(
            chat_id=chat,
            question="Wann magst du kommende Woche bei einem Spieleabend dabei sein? (Beginn 17:30)",
            options=options,
            is_anonymous=False,
            allows_multiple_answers=True,
            message_thread_id = 56,
        )
        polls[poll["poll"]["id"]] = [poll["chat"]["id"], poll["message_id"], {}]
    state["polls"] = polls
    # Stop the poll after 36 hours
    updater.job_queue.run_once(finish_poll, when=129600)


async def finish_poll(context: ContextTypes.DEFAULT_TYPE):
    polls = state["polls"]
    for poll in polls.values():
        try:
            await updater.bot.stop_poll(chat_id=poll[0], message_id=poll[1])

            # count the number of users voting for each option
            vote_count = [0]*6

            for option_ids in poll[2].values():
                for option_id in option_ids:
                    vote_count[option_id] += 1

            # drop the last answer option
            vote_count = vote_count[:5]

            # less than 3 participants does not really make sense
            # otherwise choose (some) day with the most votes
            if max(vote_count) < 3:
                message = f"Diese Woche gibt es leider nicht genug Interesse an einem Spieleabend. Nächste Woche vielleicht wieder :)"
            else:
                options = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag"]
                day = options[vote_count.index(max(vote_count))]
                message = f"Kommende Woche {day} 17:30Uhr findet ein Spieleabend statt! Bitte reagiert mit Daumen hoch oder runter falls ihr (kurzfristig) kommen oder nicht kommen wollt."


            await updater.bot.send_message(
                chat_id=poll[0],
                text=message,
                message_thread_id=56,
            )
        except:
            pass
    state["polls"] = {}


async def poll_answer_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    polls = state["polls"]
    answer = update.poll_answer

    # store the last answer for each user_id
    polls[answer["poll_id"]][2].update({answer["user"]["id"]: answer["option_ids"]})
    state["polls"] = polls


def initialize_state():
    if "chats" not in state:
        state["chats"] = set()
    if "polls" not in state:
        state["polls"] = {}


def main(args):
    global state
    global updater
    if len(args) < 2:
        sys.exit(1)
    logging.info("Starting gaming bot")
    shelve_db = "gamingbot"
    shelve_db_dir = os.getenv("GAMINGBOT_DATA_DIR")
    if shelve_db_dir is not None:
        shelve_db = os.path.join(shelve_db_dir, shelve_db)
    state = shelve.open(shelve_db)
    initialize_state()
    signal.signal(signal.SIGINT, sighandler)
    signal.signal(signal.SIGTERM, sighandler)
    updater = Application.builder().token(args[1]).build()
    updater.add_handler(
        ChatMemberHandler(chat_member_callback, ChatMemberHandler.MY_CHAT_MEMBER)
    )
    updater.add_handler(PollAnswerHandler(poll_answer_callback))
    # Run on Saturday at 8:30 UTC
    # note writing (6,6) to make this a tuple seems stupid
    updater.job_queue.run_daily(start_poll, datetime.time(hour=8, minute=30), days=(6,6))
    logging.info("Bot started...")
    updater.run_polling()


if __name__ == "__main__":
    while True:
        try:
            main(sys.argv)
        except SystemExit:
            logging.info("Caught exit, exiting...")
            state.close()
            sys.exit(0)
        except:
            logging.exception("Something bad happened, recovering in 5 ...")
            time.sleep(5)
            os.execl(sys.argv[0], sys.argv[0], sys.argv[1])
