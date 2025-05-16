#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
بوت تلجرام للاشتراك الإجباري في القنوات
يتحقق البوت من اشتراك المستخدمين في قناة محددة قبل السماح لهم بالتفاعل في المجموعة
"""

import os
import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatMember
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    Filters,
    CallbackContext,
    ConversationHandler,
)
from telegram.error import TelegramError

# تكوين التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# حالات المحادثة
CHANNEL_ID = range(1)

# ملف الإعدادات
CONFIG_FILE = 'config.json'

# الإعدادات الافتراضية
DEFAULT_CONFIG = {
    'required_channel': '@your_channel',
    'welcome_message': 'مرحباً! يجب عليك الاشتراك في القناة المطلوبة أولاً.',
    'not_subscribed_message': 'عذراً، يجب عليك الاشتراك في القناة المطلوبة أولاً للتفاعل في هذه المجموعة.',
    'subscribed_message': 'شكراً لاشتراكك! يمكنك الآن التفاعل في المجموعة.',
    'target_group': '@workinegypt9'
}

def load_config():
    """تحميل إعدادات البوت من الملف"""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as file:
            return json.load(file)
    else:
        # إنشاء ملف الإعدادات الافتراضي إذا لم يكن موجوداً
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG

def save_config(config):
    """حفظ إعدادات البوت في الملف"""
    with open(CONFIG_FILE, 'w', encoding='utf-8') as file:
        json.dump(config, file, ensure_ascii=False, indent=4)

# تحميل الإعدادات
config = load_config()

async def check_subscription(context, user_id, chat_id):
    """التحقق من اشتراك المستخدم في القناة المطلوبة"""
    try:
        channel = config['required_channel']
        member = await context.bot.get_chat_member(chat_id=channel, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except TelegramError as e:
        logger.error(f"خطأ في التحقق من الاشتراك: {e}")
        return False

def start(update: Update, context: CallbackContext) -> None:
    """التعامل مع أمر /start"""
    user = update.effective_user
    message = config['welcome_message']
    
    # إنشاء زر للاشتراك في القناة
    keyboard = [
        [InlineKeyboardButton("الاشتراك في القناة", url=f"https://t.me/{config['required_channel'][1:]}")],
        [InlineKeyboardButton("تحقق من الاشتراك", callback_data='check_subscription')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.message.reply_text(
        f"مرحباً {user.first_name}! {message}",
        reply_markup=reply_markup
    )

def check_subscription_callback(update: Update, context: CallbackContext) -> None:
    """التعامل مع نقرات زر التحقق من الاشتراك"""
    query = update.callback_query
    query.answer()
    
    user_id = query.from_user.id
    is_subscribed = await check_subscription(context, user_id, config['required_channel'])
    
    if is_subscribed:
        query.edit_message_text(text=config['subscribed_message'])
    else:
        # إعادة إنشاء زر الاشتراك
        keyboard = [
            [InlineKeyboardButton("الاشتراك في القناة", url=f"https://t.me/{config['required_channel'][1:]}")],
            [InlineKeyboardButton("تحقق من الاشتراك", callback_data='check_subscription')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query.edit_message_text(
            text=config['not_subscribed_message'],
            reply_markup=reply_markup
        )

def handle_message(update: Update, context: CallbackContext) -> None:
    """التعامل مع الرسائل الواردة في المجموعة"""
    # تجاهل الرسائل الخاصة
    if update.effective_chat.type == 'private':
        return
    
    # تجاهل رسائل المشرفين
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    try:
        member = context.bot.get_chat_member(chat_id=chat_id, user_id=user_id)
        if member.status in ['administrator', 'creator']:
            return
    except TelegramError:
        pass
    
    # التحقق من اشتراك المستخدم
    is_subscribed = await check_subscription(context, user_id, config['required_channel'])
    
    if not is_subscribed:
        # حذف الرسالة
        try:
            context.bot.delete_message(chat_id=chat_id, message_id=update.message.message_id)
        except TelegramError as e:
            logger.error(f"خطأ في حذف الرسالة: {e}")
        
        # إرسال تنبيه خاص للمستخدم
        keyboard = [
            [InlineKeyboardButton("الاشتراك في القناة", url=f"https://t.me/{config['required_channel'][1:]}")],
            [InlineKeyboardButton("تحقق من الاشتراك", callback_data='check_subscription')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            context.bot.send_message(
                chat_id=user_id,
                text=config['not_subscribed_message'],
                reply_markup=reply_markup
            )
        except TelegramError as e:
            logger.error(f"خطأ في إرسال التنبيه: {e}")

def set_channel_command(update: Update, context: CallbackContext) -> int:
    """بدء عملية تعيين القناة المطلوبة"""
    # التحقق من صلاحيات المستخدم
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    if update.effective_chat.type == 'private':
        update.message.reply_text("هذا الأمر متاح فقط في المجموعات.")
        return ConversationHandler.END
    
    try:
        member = context.bot.get_chat_member(chat_id=chat_id, user_id=user_id)
        if member.status not in ['administrator', 'creator']:
            update.message.reply_text("عذراً، هذا الأمر متاح فقط للمشرفين.")
            return ConversationHandler.END
    except TelegramError:
        update.message.reply_text("حدث خطأ في التحقق من صلاحياتك.")
        return ConversationHandler.END
    
    update.message.reply_text(
        "الرجاء إرسال معرف القناة المطلوبة للاشتراك.\n"
        "يجب أن يبدأ المعرف بـ @ مثل: @channel_name"
    )
    
    return CHANNEL_ID

def set_channel(update: Update, context: CallbackContext) -> int:
    """تعيين القناة المطلوبة"""
    channel_id = update.message.text.strip()
    
    if not channel_id.startswith('@'):
        update.message.reply_text("يجب أن يبدأ معرف القناة بـ @")
        return CHANNEL_ID
    
    # التحقق من وجود القناة
    try:
        chat = context.bot.get_chat(channel_id)
        
        # تحديث الإعدادات
        config['required_channel'] = channel_id
        save_config(config)
        
        update.message.reply_text(f"تم تعيين القناة المطلوبة: {chat.title} ({channel_id})")
    except TelegramError as e:
        update.message.reply_text(f"خطأ: لا يمكن العثور على القناة. تأكد من صحة المعرف وأن البوت عضو في القناة.\n{str(e)}")
        return CHANNEL_ID
    
    return ConversationHandler.END

def cancel(update: Update, context: CallbackContext) -> int:
    """إلغاء العملية الحالية"""
    update.message.reply_text("تم إلغاء العملية.")
    return ConversationHandler.END

def set_message_command(update: Update, context: CallbackContext) -> None:
    """تعيين رسالة التنبيه"""
    # التحقق من صلاحيات المستخدم
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    if update.effective_chat.type == 'private':
        update.message.reply_text("هذا الأمر متاح فقط في المجموعات.")
        return
    
    try:
        member = context.bot.get_chat_member(chat_id=chat_id, user_id=user_id)
        if member.status not in ['administrator', 'creator']:
            update.message.reply_text("عذراً، هذا الأمر متاح فقط للمشرفين.")
            return
    except TelegramError:
        update.message.reply_text("حدث خطأ في التحقق من صلاحياتك.")
        return
    
    # التحقق من وجود نص الرسالة
    if not context.args:
        update.message.reply_text(
            "الرجاء إدخال نص الرسالة بعد الأمر.\n"
            "مثال: /setmessage يجب عليك الاشتراك في القناة أولاً!"
        )
        return
    
    # تحديث الإعدادات
    message = ' '.join(context.args)
    config['not_subscribed_message'] = message
    save_config(config)
    
    update.message.reply_text(f"تم تعيين رسالة التنبيه: {message}")

def status_command(update: Update, context: CallbackContext) -> None:
    """عرض حالة البوت والإعدادات الحالية"""
    # التحقق من صلاحيات المستخدم
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    if update.effective_chat.type == 'private':
        update.message.reply_text("هذا الأمر متاح فقط في المجموعات.")
        return
    
    try:
        member = context.bot.get_chat_member(chat_id=chat_id, user_id=user_id)
        if member.status not in ['administrator', 'creator']:
            update.message.reply_text("عذراً، هذا الأمر متاح فقط للمشرفين.")
            return
    except TelegramError:
        update.message.reply_text("حدث خطأ في التحقق من صلاحياتك.")
        return
    
    # عرض الإعدادات الحالية
    status_text = (
        "📊 حالة البوت والإعدادات الحالية:\n\n"
        f"🔹 القناة المطلوبة: {config['required_channel']}\n"
        f"🔹 رسالة الترحيب: {config['welcome_message']}\n"
        f"🔹 رسالة عدم الاشتراك: {config['not_subscribed_message']}\n"
        f"🔹 رسالة الاشتراك: {config['subscribed_message']}\n"
        f"🔹 المجموعة المستهدفة: {config['target_group']}\n\n"
        "📝 الأوامر المتاحة:\n"
        "/setchannel - تعيين القناة المطلوبة\n"
        "/setmessage - تعيين رسالة التنبيه\n"
        "/status - عرض حالة البوت"
    )
    
    update.message.reply_text(status_text)

def main() -> None:
    """تشغيل البوت"""
    # استخدام التوكن المحدد مباشرة
    token = "7706255544:AAGxtuPVo6tAO1PoTsbcY8SFbZEPTR_KWN8"
    
    updater = Updater(token)
    dispatcher = updater.dispatcher
    
    # إضافة معالجات الأوامر
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("status", status_command))
    dispatcher.add_handler(CommandHandler("setmessage", set_message_command))
    
    # إضافة معالج المحادثة لتعيين القناة
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("setchannel", set_channel_command)],
        states={
            CHANNEL_ID: [MessageHandler(Filters.text & ~Filters.command, set_channel)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    dispatcher.add_handler(conv_handler)
    
    # إضافة معالج نقرات الأزرار
    dispatcher.add_handler(CallbackQueryHandler(check_subscription_callback, pattern='^check_subscription$'))
    
    # إضافة معالج الرسائل
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    
    # بدء البوت
    updater.start_polling()
    logger.info("تم بدء تشغيل البوت!")
    updater.idle()

if __name__ == '__main__':
    main()
