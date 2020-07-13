#!/usr/env/python3

from telegram.ext import Updater, CommandHandler, CallbackContext
from telegram import Update
from os import environ
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

updater = Updater(token=environ['TELEGRAM_BOT_TOKEN'], use_context=True)
dispatcher = updater.dispatcher


class AdminTools:
    # pin
    @staticmethod
    def pin(update: Update, context: CallbackContext):
        """Pins the quoted message in the chat"""
        if update.message.reply_to_message:
            context.bot.pin_chat_message(chat_id=update.message.chat_id,
                                         message_id=update.message.reply_to_message.message_id)
            context.bot.send_message(chat_id=update.message.chat_id, text='Pinned!',
                                     reply_to_message_id=update.message.message_id)
        else:
            context.bot.send_message(chat_id=update.message.chat_id, text='Please quote the message to pin!',
                                     reply_to_message_id=update.message.message_id)

    # ban
    @staticmethod
    def ban(update: Update, context: CallbackContext):
        """Bans the quoted member from the chat"""
        if update.message.reply_to_message:
            context.bot.kick_chat_member(chat_id=update.message.chat_id, user_id=update.message.reply_to_message.from_user.id)
            context.bot.send_message(chat_id=update.message.chat_id, text='Banned!',
                                     reply_to_message_id=update.message.message_id)
        else:
            context.bot.send_message(chat_id=update.message.chat_id, text='Please quote the user to ban!',
                                     reply_to_message_id=update.message.message_id)

    # invite link
    def invitelink(update: Update, context: CallbackContext):
        """Returns an invite link for the chat!"""
        if update.effective_chat.invite_link:
            context.bot.send_message(chat_id=update.message.chat_id,
                                     text=update.effective_chat.invite_link,
                                     reply_to_message_id=update.message.message_id)
        else:
            context.bot.send_message(chat_id=update.message.chat_id, text=context.bot.export_chat_invite_link(chat_id=update.effective_chat.id),
                                     reply_to_message_id=update.message.message_id)

    # delete
    def delete(update: Update, context: CallbackContext):
        """Deletes the quoted message"""
        if update.message.reply_to_message:
            context.bot.delete_message(chat_id=update.message.chat_id,
                                       message_id=update.message.reply_to_message.message_id)
            context.bot.send_message(chat_id=update.message.chat_id, text='Deleted!',
                                     reply_to_message_id=update.message.message_id)
        else:
            context.bot.send_message(chat_id=update.message.chat_id, text='Please quote the message to delete!',
                                     reply_to_message_id=update.message.message_id)


dispatcher.add_handler(CommandHandler('pin', AdminTools.pin))
dispatcher.add_handler(CommandHandler('ban', AdminTools.ban))
dispatcher.add_handler(CommandHandler('invitelink', AdminTools.invitelink))
dispatcher.add_handler(CommandHandler('delete', AdminTools.delete))


if __name__ == '__main__':
    updater.start_polling()
