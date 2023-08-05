#!/usr/bin/env python3

import os
import sys
import signal
import time
import logging
import shelve
import schedule
import configparser
from telegram import Update, ChatMember
from telegram.ext import Updater, CallbackContext, ChatMemberHandler, PollAnswerHandler

logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s', level=logging.DEBUG if os.getenv("DEBUG") is not None else logging.INFO)

updater: Updater = None
state: shelve.Shelf = None

def chat_member_callback(update: Update, context: CallbackContext):
    chats = state["telegram"]["chats"]
    member = update.my_chat_member.new_chat_member
    if member["status"] in (ChatMember.MEMBER, ChatMember.CREATOR, ChatMember.ADMINISTRATOR):
        chats.add(update.effective_chat.id)
    elif update.effective_chat.id in chats:
        chats.remove(update.effective_chat.id)
    state["telegram"]["chats"] = chats

def sighandler(signum, frame):
    state.close()
    if updater:
        updater.stop()
    sys.exit(0)

def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(60)

def start_poll():
    polls = state["telegram"]["polls"]
    logging.info("Notifying")
    if updater:
        for chat in state["telegram"]["chats"]:
            options = ["Ja", "Ja, keine Brötchen", "Nein :("]
            poll = updater.bot.send_poll(chat_id=chat,
                                         question="Bist du morgen beim Frühstück dabei?",
                                         options=options,
                                         is_anonymous=False,
                                         allows_multiple_answers=False)
            polls["telegram"][poll["poll"]["id"]] = [poll["chat"]["id"], poll["message_id"], {}]
    for room in state["matrix"]["rooms"]:
        pass
    state["telegram"]["polls"] = polls

def finish_poll():
    polls = state["telegram"]["polls"]
    if updater:
        for poll in polls.values():
            try:
                updater.bot.stop_poll(chat_id=poll[0], message_id=poll[1])

                # count the number of users who want bread
                participant_count = len([option_ids for option_ids in poll[2].values() if 0 in option_ids])

                bread_count = int(participant_count * 2 - participant_count / 4)
                updater.bot.send_message(chat_id=poll[0], text=f"Brötchen: {bread_count}")
            except:
                pass
    state["telegram"]["polls"] = {}

def poll_answer_callback(update: Update, context: CallbackContext):
    polls = state["telegram"]["polls"]
    answer=update.poll_answer

    # store the last answer for each user_id
    polls[answer["poll_id"]][2].update({answer["user"]["id"]: answer["option_ids"]})
    state["telegram"]["polls"] = polls

def initialize_state():
    if "telegram" not in state:
        state["telegram"] = {}
        if "chats" in state:
            state["telegram"]["chats"] = state["chats"]
        else:
            state["telegram"]["chats"] = set()
        if "polls" in state:
            state["telegram"]["polls"] = state["polls"]
        else:
            state["telegram"]["polls"] = {}
    if "matrix" not in state:
        state["matrix"] = {"rooms": set(), "polls" : {}}

def main(args):
    global state
    global updater
    if len(args) < 2:
        sys.exit(1)
    logging.info("Starting breakfast bot")
    config = configparser.ConfigParser()
    config.read(args[1])
    state = shelve.open("breakfastbot")
    initialize_state()
    signal.signal(signal.SIGINT, sighandler)
    signal.signal(signal.SIGTERM, sighandler)
    schedule.every().thursday.at("10:30").do(start_poll)
    schedule.every().friday.at("07:00").do(finish_poll)
    if 'Telegram' in config:
        updater = Updater(config['Telegram']['api_key'])
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
            sys.exit(0)
        except:
            logging.exception("Something bad happened, recovering in 5 ...")
            time.sleep(5)
            os.execl(sys.argv[0], sys.argv[0], sys.argv[1])
