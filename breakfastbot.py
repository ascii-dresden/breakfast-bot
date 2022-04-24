#!/usr/bin/env python3

import os
import sys
import signal
import time
import logging
import schedule
import shelve
from telegram import Bot, Update, Chat, ChatMember
from telegram.ext import Updater, CallbackContext, ChatMemberHandler, PollAnswerHandler

logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s', level=logging.DEBUG if os.getenv("DEBUG") is not None else logging.INFO)

updater: Updater = None
state: shelve.Shelf = None

def chat_member_callback(update: Update, context: CallbackContext):
    global state
    chats = state["chats"]
    member = update.my_chat_member.new_chat_member
    if member["status"] in (ChatMember.MEMBER, ChatMember.CREATOR, ChatMember.ADMINISTRATOR):
        chats.add(update.effective_chat.id)
    elif update.effective_chat.id in chats:
        chats.remove(update.effective_chat.id)
    state["chats"] = chats

def sighandler(signum, frame):
    state.close()
    if updater:
        updater.stop()
    exit(0)

def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(60)

def start_poll():
    global updater
    global state
    polls = state["polls"]
    logging.info("Notifying")
    for chat in state["chats"]:
        options = ["Ja", "Ja, keine Brötchen", "Nein :("]
        poll = updater.bot.send_poll(chat_id=chat,
                                     question="Bist du morgen beim Frühstück dabei?",
                                     options=options,
                                     is_anonymous=False,
                                     allows_multiple_answers=False)
        polls[poll["poll"]["id"]] = [poll["chat"]["id"], poll["message_id"], 0]
    state["polls"] = polls

def finish_poll():
    global updater
    global state
    polls = state["polls"]
    for poll_id, poll in polls.items():
        try:
            updater.bot.stop_poll(chat_id=poll[0], message_id=poll[1])
            bread_count = int(poll[2] * 2 - poll[2] / 4)
            updater.bot.send_message(chat_id=poll[0], text=f"Brötchen: {bread_count}")
        except:
            pass
    state["polls"] = {}

def poll_answer_callback(update: Update, context: CallbackContext):
    global state
    polls = state["polls"]
    answer=update.poll_answer
    if answer["option_ids"][0] == 0:
        polls[answer["poll_id"]][2] += 1
    state["polls"] = polls

def initialize_state():
    global state
    if "chats" not in state:
        state["chats"] = set()
    if "polls" not in state:
        state["polls"] = {}

def main(args):
    global state
    global updater
    if len(args) < 2:
        exit(1)
    logging.info("Starting breakfast bot")
    state = shelve.open("breakfastbot")
    initialize_state()
    signal.signal(signal.SIGINT, sighandler)
    signal.signal(signal.SIGTERM, sighandler)
    schedule.every().thursday.at("10:30").do(start_poll)
    schedule.every().friday.at("07:00").do(finish_poll)
    updater = Updater(args[1])
    updater.dispatcher.add_handler(ChatMemberHandler(chat_member_callback, ChatMemberHandler.MY_CHAT_MEMBER))
    updater.dispatcher.add_handler(PollAnswerHandler(poll_answer_callback))
    updater.start_polling()
    logging.info("Bot started...")
    run_scheduler()


if __name__ == "__main__":
    while True:
        try:
            main(sys.argv)
        except SystemExit:
            logging.info("Catched exit, exiting...")
            state.close()
            exit(0)
        except:
            logging.exception("Something bad happened, recovering in 5 ...")
            time.sleep(5)
            os.execl(sys.argv[0], sys.argv[0], sys.argv[1])
