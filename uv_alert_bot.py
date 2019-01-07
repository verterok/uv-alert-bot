import asyncio
import base64
import time
import logging
import shelve
import tempfile

from io import BytesIO

import yaml # fades.pypi pyyaml == 3.12
import telepot # fades.pypi == 12.1
import telepot.aio
from telepot.aio.loop import MessageLoop

from aiosmtpd.controller import Controller # fades.pypi == 1.1
from aiosmtpd.handlers import Message

import ftp


class UnifiAlertMessage(Message):

    def __init__(self, bot):
        super(UnifiAlertMessage, self).__init__()
        self.bot = bot

    def handle_message(self, message):
        logging.info("Received email, bot state: %s - subject: %s",
                     self.bot.active, message.get('subject', 'no-subject'))
        if self.bot.active:
            parts = [part for part in message.walk()
                     if part.get_content_type() == 'image/jpeg']
            if not parts:
                self.bot.sendMessage(message['subject'])
            for part in parts:
                image = BytesIO(base64.decodebytes(
                    part.get_payload().encode('utf-8')))
                self.bot.sendPhoto(image, topic="email")
        else:
            logging.info("Bot is not active, ignoring email")

    async def smtpd_main(self, hostname, port):
        cont = Controller(self, hostname=hostname, port=port)
        cont.start()


class AlertBot:

    message_limit = 5
    no_call = 0

    def __init__(self, bot, loop, valid_users, state):
        super(AlertBot, self).__init__()
        self.valid_users = valid_users
        self.state = state
        self.loop = loop
        self.bot = bot
        self.active = self.state.get('active')
        self.topics = {"ftp": {}, "email": {}}

    def sendMessage(self, message):
        if self.state.get('group') and self.active:
            self.loop.create_task(self.bot.sendMessage(
                self.state.get('group')['id'], message))

    def sendPhoto(self, image, topic):
        if topic == 'ftp':
            now = time.time()
            last_call =  self.topics[topic].get('last_call', self.no_call)
            call_delta = now - last_call
            logging.info("Got image from: %s - last_call: %s - delta: %s",
                         topic, last_call, call_delta)
            if self.state.get('group') and self.active:
                if last_call == self.no_call or \
                        call_delta > self.message_limit:
                    self.topics[topic]['last_call'] = now
                else:
                    logging.info("Throttling message from topic: %s - "
                                 "delta: %s", topic, call_delta)
                    return
        self.loop.create_task(self.bot.sendPhoto(
            self.state.get('group')['id'], image))

    async def handle(self, msg):
        content_type, chat_type, chat_id = telepot.glance(msg)
        logging.info("Message received: content: %s, type: %s, chat_id: %s, "
                     "msg: %s", content_type, chat_type, chat_id, msg)
        user = msg['from']['username']
        if user not in self.valid_users:
            logging.warning("Message from UNKNOWN user: %s, content: %s, type:"
                            " %s, chat_id: %s, msg: %s", user, content_type,
                            chat_type, chat_id, msg)
            await self.bot.sendMessage(chat_id, "Sorry, I can't do that. "
                                       "Please contact the bot admin")
            return
        if 'text' not in msg:
            # ignore it
            logging.debug("Ignoring message: %s", msg)
            return
        if chat_type == 'group' and msg['text'] == '/start':
            group = self.state.get('group')
            if group:
                logging.warning("Already bound to a group: %s", group['title'])
                if group['id'] == chat_id:

                    await self.bot.sendMessage(chat_id,
                                               "Already using this group")
                else:
                    await self.bot.sendMessage(
                        chat_id, "Already using group: {}".format(group))
            else:
                self.state['group'] = msg['chat']
                return
        if msg['text'] in ['/ac', '/activate']:
            self.active = True
            self.state['active'] = self.active
        elif msg['text'] in ['/de', '/deactivate']:
            self.active = False
            self.state['active'] = self.active
        elif msg['text'] in ['/st', '/status']:
            status = "Desactivada"
            if self.active:
                status = "Activada"
            await self.bot.sendMessage(chat_id, status)

    def ftp_event(self, topic, filepath):
        if topic == 'ftpd_file_received' and self.active:
            with open(filepath, 'rb') as fd:
                self.sendPhoto(fd.read(), topic="ftp")


def main(config, state):
    logging.basicConfig(level=logging.INFO)
    loop = asyncio.get_event_loop()
    bot = telepot.aio.Bot(config['token'])
    alert_bot = AlertBot(bot, loop, config['valid_users'], state)
    email_handler = UnifiAlertMessage(alert_bot)
    smtp_listen = config.get('smtp_listen', '0.0.0.0')
    smtp_port = config.get('smtp_port', 8025)
    # create smtpd task
    loop.create_task(email_handler.smtpd_main(smtp_listen, smtp_port))
    # create the ftpd task
    ftp_user = config['ftp']['user']
    ftp_password = config['ftp']['password']
    ftp_port = config['ftp']['port']
    ftp_dir = tempfile.mkdtemp()
    loop.run_in_executor(None, ftp.run_ftpd, '0.0.0.0', ftp_port, alert_bot,
                         ftp_user, ftp_password, ftp_dir)
    # create bot task
    loop.create_task(MessageLoop(bot, alert_bot.handle).run_forever())
    logging.info("Starting Bot and smtpd")
    loop.run_forever()


if __name__ == '__main__':
    # load config
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('config')
    options = parser.parse_args()
    with open(options.config, 'r') as fd:
        config = yaml.safe_load(fd)
    state = shelve.open(config['state_file'])
    main(config, state)
