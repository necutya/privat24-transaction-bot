import os
from datetime import datetime
from threading import Thread, Lock

import time

import schedule as schedule
import telebot

import privat24

MERCHANT_ID = os.environ.get("MERCHANT_ID")
MERCHANT_PASSWORD = os.environ.get("MERCHANT_PASSWORD")
PRIVAT_CARDS = os.environ.get("PRIVAT_CARDS")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_IDS = []

privar24 = privat24.Privat24(MERCHANT_ID, MERCHANT_PASSWORD)
bot = telebot.TeleBot(BOT_TOKEN, parse_mode=None)
lock = Lock()


def get_report(date):
    msg = f"Transaction report for {date}\n\n"

    for card_num in PRIVAT_CARDS.split(','):
        try:
            msg += privar24.get_transaction_list(card_num, date, date).__str__()
        except Exception as e:
            msg += e.__str__() + "\n"

    return msg


@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "To use this bot type /check or /set. Also bot will send daily transaction every day.")


@bot.message_handler(commands=['check'])
def send_welcome(message):
    msg = get_report(datetime.now().strftime("%d.%m.%Y"))
    bot.reply_to(message, msg)


@bot.message_handler(commands=['set'])
def send_welcome(message):
    global CHAT_IDS

    lock.acquire()
    if message.chat.id not in CHAT_IDS:
        CHAT_IDS.append(message.chat.id)
        print(f"Chats for report: {CHAT_IDS}")
        bot.reply_to(message, "Daily report is set")
    else:
        bot.reply_to(message, "Daily report has been alreay set")

    lock.release()


def daily_report():
    lock.acquire()
    if len(CHAT_IDS) > 0:
        msg = get_report(datetime.now().strftime("%d.%m.%Y"))
        for chat_id in CHAT_IDS:
            bot.send_message(chat_id, msg)
    lock.release()


def do_schedule():
    schedule.every(12).hours.do(daily_report)

    while True:
        schedule.run_pending()
        time.sleep(1)


def main_loop():
    thread = Thread(target=do_schedule)
    thread.start()

    bot.polling(True)


if __name__ == '__main__':
    main_loop()
