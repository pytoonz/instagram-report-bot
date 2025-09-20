from flask import Flask, request, jsonify
   import uuid
   import time
   import requests
   import re
   from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
   from telegram.ext import (
       Application,
       CommandHandler,
       MessageHandler,
       CallbackQueryHandler,
       filters,
       ContextTypes,
       ConversationHandler
   )
   from rich.console import Console
   from rich.text import Text
   import logging
   import os

   app = Flask(__name__)
   console = Console()
   logging.basicConfig(level=logging.INFO)
   logger = logging.getLogger(__name__)

   # States for the conversation handler
   BOT_PASSWORD, USERNAME, PASSWORD, TARGET, REPORT_TYPE, CHALLENGE_CODE = range(6)

   # Define ANSI color codes for styling (for console output)
   class TextColor:
       HEADER = '\033[95m'  # Magenta
       OKBLUE = '\033[94m'  # Blue
       OKCYAN = '\033[96m'  # Cyan
       OKGREEN = '\033[92m' # Green
       WARNING = '\033[93m' # Yellow
       FAIL = '\033[91m'    # Red
       ENDC = '\033[0m'     # End of color

   # Bot header display (for console and Telegram)
   def header():
       return """
   > DEV| @SEISMICALLY  • SECURE SYSTEM & REPORTING BOT
   """

   # Predefined bot password
   BOT_ACCESS_PASSWORD = "VERDICT4EVA"

   # Initialize UUID for session
   uid = str(uuid.uuid4())

   async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
       console.print(header(), style='bold red')
       
       await update.message.reply_text(
           f"{header()}\nWelcome to the Report Bot!"
       )
       
       await update.message.reply_text("Please enter the bot access password:")
       return BOT_PASSWORD

   async def check_bot_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
       entered_password = update.message.text.strip()
       if entered_password != BOT_ACCESS_PASSWORD:
           await update.message.reply_text("❌ Incorrect password. Access denied.")
           return ConversationHandler.END
       await update.message.reply_text("✅ Password accepted!\nEnter Your Instagram Username:")
       return USERNAME

   async def get_username(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
       user = update.message.text.strip()
       if not user:
           await update.message.reply_text("❌ You must provide a username. Try again:")
           return USERNAME
       context.user_data['username'] = user
       await update.message.reply_text("Enter Your Instagram Password:")
       return PASSWORD

   async def get_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
       password = update.message.text.strip()
       if not password:
           await update.message.reply_text("❌ You must provide a password. Try again:")
           return PASSWORD
       context.user_data['password'] = password
       await update.message.reply_text("Enter the Target Instagram Username:")
       return TARGET

   async def get_target(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
       target = update.message.text.strip()
       if not target:
           await update.message.reply_text("❌ You must provide a target username. Try again:")
           return TARGET
       context.user_data['target'] = target
       
       keyboard = [
           [InlineKeyboardButton("1 - Spam", callback_data='1'),
            InlineKeyboardButton("2 - Self", callback_data='2')],
           [InlineKeyboardButton("3 - Drugs", callback_data='3'),
            InlineKeyboardButton("4 - Nudity", callback_data='4')],
           [InlineKeyboardButton("5 - Violence", callback_data='5'),
            InlineKeyboardButton("6 - Hate", callback_data='6')],
           [InlineKeyboardButton("7 - Bullying", callback_data='7'),
            InlineKeyboardButton("8 - Impersonation", callback_data='8')]
       ]
       reply_markup = InlineKeyboardMarkup(keyboard)
       await update.message.reply_text("Choose Report Type:", reply_markup=reply_markup)
       return REPORT_TYPE

   async def get_report_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
       query = update.callback_query
       await query.answer()
       try:
           report_type = int(query.data)
           if report_type not in range(1, 9):
               await query.message.reply_text("❌ Invalid selection. Please choose a valid report type:")
               return REPORT_TYPE
           context.user_data['report_type'] = report_type
           await query.message.reply_text(f"You selected report type: {report_type}")
           await perform_login_and_report(query, context)
           return ConversationHandler.END
       except ValueError:
           await query.message.reply_text("❌ Invalid selection. Please choose a valid report type:")
           return REPORT_TYPE

   async def get_challenge_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
       code = update.message.text.strip()
       challenge_url = context.user_data.get('challenge_url')
       if not code or not challenge_url:
           await update.message.reply_text("❌ Invalid or missing code. Try again:")
           return CHALLENGE_CODE
       
       r_challenge = requests.post(
           f"https://i.instagram.com{challenge_url}",
           headers={
               'User-Agent': 'Instagram 114.0.0.38.120 Android (30/3.0; 216dpi; 1080x2340; huawei/google; Nexus 6P; angler; angler; en_US)',
               "Accept": "*/*",
               "Accept-Encoding": "gzip, deflate",
               "Accept-Language": "en-US",
               "X-IG-Capabilities": "3brTvw==",
               "X-IG-Connection-Type": "WIFI",
               "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
               'Host': 'i.instagram.com'
           },
           data={'security_code': code}
       )
       if 'logged_in_user' in r_challenge.text:
           sessionid = r_challenge.cookies.get('sessionid')
           csrftoken = r_challenge.cookies.get('csrftoken')
           context.user_data['sessionid'] = sessionid
           context.user_data['csrftoken'] = csrftoken
           await update.message.reply_text("✅ Challenge passed, proceeding with report...")
           await continue_report(update, context)
           return ConversationHandler.END
       else:
           await update.message.reply_text("❌ Invalid code. Try again:")
           return CHALLENGE_CODE

   async def perform_login_and_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
       user = context.user_data['username']
       password = context.user_data['password']
       target = context.user_data['target']
       report_type = context.user_data['report_type']

       r1 = requests.post(
           'https://i.instagram.com/api/v1/accounts/login/',
           headers={
               'User-Agent': 'Instagram 114.0.0.38.120 Android (30/3.0; 216dpi; 1080x2340; huawei/google; Nexus 6P; angler; angler; en_US)',
               "Accept": "*/*",
               "Accept-Encoding": "gzip, deflate",
               "Accept-Language": "en-US",
               "X-IG-Capabilities": "3brTvw==",
               "X-IG-Connection-Type": "WIFI",
               "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
               'Host': 'i.instagram.com'
           },
           data={
               '_uuid': uid,
               'password': password,
               'username': user,
               'device_id': uid,
               'from_reg': 'false',
               '_csrftoken': 'missing',
               'login_attempt_count': '0'
           },
           allow_redirects=True
       )

       if 'logged_in_user' in r1.text:
           await update.message.reply_text("✅ Logged in successfully!")
           sessionid = r1.cookies['sessionid']
           csrftoken = r1.cookies['csrftoken']
           context.user_data['sessionid'] = sessionid
           context.user_data['csrftoken'] = csrftoken
           await continue_report(update, context)
       elif 'challenge_required' in r1.text:
           try:
               challenge_url = r1.json()['challenge']['api_path']
               context.user_data['challenge_url'] = challenge_url
               await update.message.reply_text("❗ Instagram requires verification. Check your email/SMS for a code and enter it:")
               return CHALLENGE_CODE
           except (KeyError, ValueError):
               await update.message.reply_text("❌ Failed to process challenge. Try again later!")
               return ConversationHandler.END
       else:
           error_messages = {
               'ip_block': "❌ You have been banned from Instagram (IP block)!",
               'The password you entered is incorrect': "❌ Please check your password!",
               'Please check your username and try again': "❌ Username not found!",
               'two_factor_required': "❌ Two-factor authentication required!",
               'inactive user': "❌ This user is banned from Instagram!",
               "We're working on it and we'll get it fixed as soon as we can": "❌ Try again in a minute!",
               'Please wait a few minutes before you try again': "❌ Try again in a minute!",
               'Bad request': "❌ Error in Instagram, try again in 15 minutes!",
               'Invalid Parameters': "❌ Error: Please reinstall the tool from the original source!"
           }
           for error, message in error_messages.items():
               if error in r1.text:
                   await update.message.reply_text(message)
                   return ConversationHandler.END
           await update.message.reply_text(f"❌ General error occurred! Response: {r1.text}")
           return ConversationHandler.END

   async def continue_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
       target = context.user_data['target']
       report_type = context.user_data['report_type']
       sessionid = context.user_data['sessionid']
       csrftoken = context.user_data['csrftoken']

       r2 = requests.post(
           'https://i.instagram.com:443/api/v1/users/lookup/',
           headers={
               "Connection": "close",
               "X-IG-Connection-Type": "WIFI",
               "mid": "XOSINgABAAG1IDmaral3noOozrK0rrNSbPuSbzHq",
               "X-IG-Capabilities": "3R4=",
               "Accept-Language": "ar-sa",
               "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
               "User-Agent": "Instagram 99.4.0 TweakPY_vv1ck (TweakPY_vv1ck)",
               "Accept-Encoding": "gzip, deflate"
           },
           data={"signed_body": f"35a2d547d3b6ff400f713948cdffe0b789a903f86117eb6e2f3e573079b2f038.{{'q':'{target}'}}"}
       )

       if 'No users found' in r2.text:
           adv_search = requests.get(
               f'https://www.instagram.com/{target}',
               headers={
                   'Host': 'www.instagram.com',
                   'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/110.0',
                   'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                   'Accept-Language': 'ar,en-US;q=0.7,en;q=0.3',
                   'Accept-Encoding': 'gzip, deflate, br',
                   'Connection': 'keep-alive',
                   'Cookie': f'csrftoken={csrftoken}',
                   'Upgrade-Insecure-Requests': '1',
                   'Sec-Fetch-Dest': 'document',
                   'Sec-Fetch-Mode': 'navigate',
                   'Sec-Fetch-Site': 'none',
                   'Sec-Fetch-User': '?1',
                   'TE': 'trailers'
               }
           )
           try:
               target_id = re.findall('"profile_id":"(.*?)"', adv_search.text)[0]
           except IndexError:
               try:
                   target_id = re.findall('"page_id":"profilePage_(.*?)"', adv_search.text)[0]
               except IndexError:
                   adv_search2 = requests.get(
                       f'https://www.instagram.com/api/v1/users/web_profile_info/?username={target}',
                       headers={
                           'Host': 'www.instagram.com',
                           'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/110.0',
                           'Accept': '*/*',
                           'Accept-Language': 'ar,en-US;q=0.7,en;q=0.3',
                           'Accept-Encoding': 'gzip, deflate, br',
                           'X-CSRFToken': csrftoken,
                           'X-IG-App-ID': '936619743392459',
                           'X-ASBD-ID': '198387',
                           'X-IG-WWW-Claim': 'hmac.AR3KPEPoXkWYhwtoCUKyUHK80GsE1g2PJI1uPtDlCyo4PHKn',
                           'X-Requested-With': 'XMLHttpRequest',
                           'Alt-Used': 'www.instagram.com',
                           'Connection': 'keep-alive',
                           'Referer': f'https://www.instagram.com/{target}/',
                           'Cookie': f'sessionid={sessionid}',
                           'Sec-Fetch-Dest': 'empty',
                           'Sec-Fetch-Mode': 'cors',
                           'Sec-Fetch-Site': 'same-origin',
                           'TE': 'trailers'
                       }
                   )
                   try:
                       target_id = adv_search2.json()['data']['user']['id']
                   except KeyError:
                       await update.message.reply_text("❌ Failed to get target username. Please enter the Target ID manually:")
                       context.user_data['awaiting_target_id'] = True
                       return TARGET
           await perform_report(update, context, target_id, sessionid, csrftoken, report_type)
       elif '"spam":true' in r2.text:
           await update.message.reply_text("❌ Try again later!")
           return ConversationHandler.END
       else:
           try:
               target_id = str(r2.json()['user_id'])
               await perform_report(update, context, target_id, sessionid, csrftoken, report_type)
           except KeyError:
               await update.message.reply_text("❌ General error occurred!")
               return ConversationHandler.END

   async def perform_report(update: Update, context: ContextTypes.DEFAULT_TYPE, target_id: str, sessionid: str, csrftoken: str, report_type: int) -> None:
       while True:
           try:
               r3 = requests.post(
                   f"https://i.instagram.com/users/{target_id}/flag/",
                   headers={
                       "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/110.0",
                       "Host": "i.instagram.com",
                       'cookie': f"sessionid={sessionid}",
                       "X-CSRFToken": csrftoken,
                       "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
                   },
                   data=f'source_name=&reason_id={report_type}&frx_context=',
                   allow_redirects=False
               )
               if r3.status_code == 429:
                   await update.message.reply_text(f"❌ Account flagged [{r3.status_code}]!")
                   return
               elif r3.status_code == 500:
                   await update.message.reply_text(f"❌ Target not found with status code [{r3.status_code}]!")
                   return
               else:
                   await update.message.reply_text("✅ Report submitted successfully!")
                   time.sleep(10)
           except requests.exceptions.TooManyRedirects:
               await update.message.reply_text("✅ Report submitted successfully!")
               time.sleep(10)
           except Exception as e:
               await update.message.reply_text(f"❌ Report failed with status code [{r3.status_code}]!")
               return

   async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
       await update.message.reply_text("Operation cancelled.")
       return ConversationHandler.END

   # Set up the Telegram bot application
   application = None

   def setup_application():
       global application
       token = os.getenv("TELEGRAM_BOT_TOKEN")
       if not token:
           logger.error("TELEGRAM_BOT_TOKEN environment variable not set")
           raise ValueError("TELEGRAM_BOT_TOKEN not set")
       
       application = Application.builder().token(token).build()
       
       conv_handler = ConversationHandler(
           entry_points=[CommandHandler('start', start)],
           states={
               BOT_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, check_bot_password)],
               USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_username)],
               PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_password)],
               TARGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_target)],
               REPORT_TYPE: [CallbackQueryHandler(get_report_type)],
               CHALLENGE_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_challenge_code)],
           },
           fallbacks=[CommandHandler('cancel', cancel)]
       )

       application.add_handler(conv_handler)

   # Webhook endpoint to receive updates from Telegram
   @app.route('/webhook', methods=['POST'])
   async def webhook():
       global application
       if application is None:
           setup_application()
       
       update = Update.de_json(request.get_json(), application.bot)
       await application.process_update(update)
       return jsonify({"status": "ok"})

   # Route to set the webhook
   @app.route('/set_webhook', methods=['GET'])
   async def set_webhook():
       global application
       if application is None:
           setup_application()
       
       webhook_url = os.getenv("WEBHOOK_URL")
       if not webhook_url:
           logger.error("WEBHOOK_URL environment variable not set")
           return jsonify({"status": "error", "message": "WEBHOOK_URL not set"}), 500
       
       success = await application.bot.set_webhook(url=webhook_url + '/webhook')
       if success:
           logger.info("Webhook set successfully")
           return jsonify({"status": "success", "message": "Webhook set successfully"})
       else:
           logger.error("Failed to set webhook")
           return jsonify({"status": "error", "message": "Failed to set webhook"}), 500

   if __name__ == '__main__':
       setup_application()
       # Remove app.run() as gunicorn will handle this    ENDC = '\033[0m'     # End of color

# Bot header display (for console and Telegram)
def header():
    return """
> DEV| @SEISMICALLY  • SECURE SYSTEM & REPORTING BOT
"""

# Predefined bot password
BOT_ACCESS_PASSWORD = "VERDICT4EVA"

# Initialize UUID for session
uid = str(uuid.uuid4())

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    console.print(header(), style='bold red')
    
    await update.message.reply_text(
        f"{header()}\nWelcome to the Report Bot!"
    )
    
    await update.message.reply_text("Please enter the bot access password:")
    return BOT_PASSWORD

async def check_bot_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    entered_password = update.message.text.strip()
    if entered_password != BOT_ACCESS_PASSWORD:
        await update.message.reply_text("❌ Incorrect password. Access denied.")
        return ConversationHandler.END
    await update.message.reply_text("✅ Password accepted!\nEnter Your Instagram Username:")
    return USERNAME

async def get_username(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.text.strip()
    if not user:
        await update.message.reply_text("❌ You must provide a username. Try again:")
        return USERNAME
    context.user_data['username'] = user
    await update.message.reply_text("Enter Your Instagram Password:")
    return PASSWORD

async def get_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    password = update.message.text.strip()
    if not password:
        await update.message.reply_text("❌ You must provide a password. Try again:")
        return PASSWORD
    context.user_data['password'] = password
    await update.message.reply_text("Enter the Target Instagram Username:")
    return TARGET

async def get_target(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    target = update.message.text.strip()
    if not target:
        await update.message.reply_text("❌ You must provide a target username. Try again:")
        return TARGET
    context.user_data['target'] = target
    
    keyboard = [
        [InlineKeyboardButton("1 - Spam", callback_data='1'),
         InlineKeyboardButton("2 - Self", callback_data='2')],
        [InlineKeyboardButton("3 - Drugs", callback_data='3'),
         InlineKeyboardButton("4 - Nudity", callback_data='4')],
        [InlineKeyboardButton("5 - Violence", callback_data='5'),
         InlineKeyboardButton("6 - Hate", callback_data='6')],
        [InlineKeyboardButton("7 - Bullying", callback_data='7'),
         InlineKeyboardButton("8 - Impersonation", callback_data='8')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Choose Report Type:", reply_markup=reply_markup)
    return REPORT_TYPE

async def get_report_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    try:
        report_type = int(query.data)
        if report_type not in range(1, 9):
            await query.message.reply_text("❌ Invalid selection. Please choose a valid report type:")
            return REPORT_TYPE
        context.user_data['report_type'] = report_type
        await query.message.reply_text(f"You selected report type: {report_type}")
        await perform_login_and_report(query, context)
        return ConversationHandler.END
    except ValueError:
        await query.message.reply_text("❌ Invalid selection. Please choose a valid report type:")
        return REPORT_TYPE

async def get_challenge_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    code = update.message.text.strip()
    challenge_url = context.user_data.get('challenge_url')
    if not code or not challenge_url:
        await update.message.reply_text("❌ Invalid or missing code. Try again:")
        return CHALLENGE_CODE
    
    r_challenge = requests.post(
        f"https://i.instagram.com{challenge_url}",
        headers={
            'User-Agent': 'Instagram 114.0.0.38.120 Android (30/3.0; 216dpi; 1080x2340; huawei/google; Nexus 6P; angler; angler; en_US)',
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "en-US",
            "X-IG-Capabilities": "3brTvw==",
            "X-IG-Connection-Type": "WIFI",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            'Host': 'i.instagram.com'
        },
        data={'security_code': code}
    )
    if 'logged_in_user' in r_challenge.text:
        sessionid = r_challenge.cookies.get('sessionid')
        csrftoken = r_challenge.cookies.get('csrftoken')
        context.user_data['sessionid'] = sessionid
        context.user_data['csrftoken'] = csrftoken
        await update.message.reply_text("✅ Challenge passed, proceeding with report...")
        await continue_report(update, context)
        return ConversationHandler.END
    else:
        await update.message.reply_text("❌ Invalid code. Try again:")
        return CHALLENGE_CODE

async def perform_login_and_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = context.user_data['username']
    password = context.user_data['password']
    target = context.user_data['target']
    report_type = context.user_data['report_type']

    r1 = requests.post(
        'https://i.instagram.com/api/v1/accounts/login/',
        headers={
            'User-Agent': 'Instagram 114.0.0.38.120 Android (30/3.0; 216dpi; 1080x2340; huawei/google; Nexus 6P; angler; angler; en_US)',
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "en-US",
            "X-IG-Capabilities": "3brTvw==",
            "X-IG-Connection-Type": "WIFI",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            'Host': 'i.instagram.com'
        },
        data={
            '_uuid': uid,
            'password': password,
            'username': user,
            'device_id': uid,
            'from_reg': 'false',
            '_csrftoken': 'missing',
            'login_attempt_count': '0'
        },
        allow_redirects=True
    )

    if 'logged_in_user' in r1.text:
        await update.message.reply_text("✅ Logged in successfully!")
        sessionid = r1.cookies['sessionid']
        csrftoken = r1.cookies['csrftoken']
        context.user_data['sessionid'] = sessionid
        context.user_data['csrftoken'] = csrftoken
        await continue_report(update, context)
    elif 'challenge_required' in r1.text:
        try:
            challenge_url = r1.json()['challenge']['api_path']
            context.user_data['challenge_url'] = challenge_url
            await update.message.reply_text("❗ Instagram requires verification. Check your email/SMS for a code and enter it:")
            return CHALLENGE_CODE
        except (KeyError, ValueError):
            await update.message.reply_text("❌ Failed to process challenge. Try again later!")
            return ConversationHandler.END
    else:
        error_messages = {
            'ip_block': "❌ You have been banned from Instagram (IP block)!",
            'The password you entered is incorrect': "❌ Please check your password!",
            'Please check your username and try again': "❌ Username not found!",
            'two_factor_required': "❌ Two-factor authentication required!",
            'inactive user': "❌ This user is banned from Instagram!",
            "We're working on it and we'll get it fixed as soon as we can": "❌ Try again in a minute!",
            'Please wait a few minutes before you try again': "❌ Try again in a minute!",
            'Bad request': "❌ Error in Instagram, try again in 15 minutes!",
            'Invalid Parameters': "❌ Error: Please reinstall the tool from the original source!"
        }
        for error, message in error_messages.items():
            if error in r1.text:
                await update.message.reply_text(message)
                return ConversationHandler.END
        await update.message.reply_text(f"❌ General error occurred! Response: {r1.text}")
        return ConversationHandler.END

async def continue_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    target = context.user_data['target']
    report_type = context.user_data['report_type']
    sessionid = context.user_data['sessionid']
    csrftoken = context.user_data['csrftoken']

    r2 = requests.post(
        'https://i.instagram.com:443/api/v1/users/lookup/',
        headers={
            "Connection": "close",
            "X-IG-Connection-Type": "WIFI",
            "mid": "XOSINgABAAG1IDmaral3noOozrK0rrNSbPuSbzHq",
            "X-IG-Capabilities": "3R4=",
            "Accept-Language": "ar-sa",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "User-Agent": "Instagram 99.4.0 TweakPY_vv1ck (TweakPY_vv1ck)",
            "Accept-Encoding": "gzip, deflate"
        },
        data={"signed_body": f"35a2d547d3b6ff400f713948cdffe0b789a903f86117eb6e2f3e573079b2f038.{{'q':'{target}'}}"}
    )

    if 'No users found' in r2.text:
        adv_search = requests.get(
            f'https://www.instagram.com/{target}',
            headers={
                'Host': 'www.instagram.com',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/110.0',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Language': 'ar,en-US;q=0.7,en;q=0.3',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Cookie': f'csrftoken={csrftoken}',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'TE': 'trailers'
            }
        )
        try:
            target_id = re.findall('"profile_id":"(.*?)"', adv_search.text)[0]
        except IndexError:
            try:
                target_id = re.findall('"page_id":"profilePage_(.*?)"', adv_search.text)[0]
            except IndexError:
                adv_search2 = requests.get(
                    f'https://www.instagram.com/api/v1/users/web_profile_info/?username={target}',
                    headers={
                        'Host': 'www.instagram.com',
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/110.0',
                        'Accept': '*/*',
                        'Accept-Language': 'ar,en-US;q=0.7,en;q=0.3',
                        'Accept-Encoding': 'gzip, deflate, br',
                        'X-CSRFToken': csrftoken,
                        'X-IG-App-ID': '936619743392459',
                        'X-ASBD-ID': '198387',
                        'X-IG-WWW-Claim': 'hmac.AR3KPEPoXkWYhwtoCUKyUHK80GsE1g2PJI1uPtDlCyo4PHKn',
                        'X-Requested-With': 'XMLHttpRequest',
                        'Alt-Used': 'www.instagram.com',
                        'Connection': 'keep-alive',
                        'Referer': f'https://www.instagram.com/{target}/',
                        'Cookie': f'sessionid={sessionid}',
                        'Sec-Fetch-Dest': 'empty',
                        'Sec-Fetch-Mode': 'cors',
                        'Sec-Fetch-Site': 'same-origin',
                        'TE': 'trailers'
                    }
                )
                try:
                    target_id = adv_search2.json()['data']['user']['id']
                except KeyError:
                    await update.message.reply_text("❌ Failed to get target username. Please enter the Target ID manually:")
                    context.user_data['awaiting_target_id'] = True
                    return TARGET
        await perform_report(update, context, target_id, sessionid, csrftoken, report_type)
    elif '"spam":true' in r2.text:
        await update.message.reply_text("❌ Try again later!")
        return ConversationHandler.END
    else:
        try:
            target_id = str(r2.json()['user_id'])
            await perform_report(update, context, target_id, sessionid, csrftoken, report_type)
        except KeyError:
            await update.message.reply_text("❌ General error occurred!")
            return ConversationHandler.END

async def perform_report(update: Update, context: ContextTypes.DEFAULT_TYPE, target_id: str, sessionid: str, csrftoken: str, report_type: int) -> None:
    while True:
        try:
            r3 = requests.post(
                f"https://i.instagram.com/users/{target_id}/flag/",
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/110.0",
                    "Host": "i.instagram.com",
                    'cookie': f"sessionid={sessionid}",
                    "X-CSRFToken": csrftoken,
                    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
                },
                data=f'source_name=&reason_id={report_type}&frx_context=',
                allow_redirects=False
            )
            if r3.status_code == 429:
                await update.message.reply_text(f"❌ Account flagged [{r3.status_code}]!")
                return
            elif r3.status_code == 500:
                await update.message.reply_text(f"❌ Target not found with status code [{r3.status_code}]!")
                return
            else:
                await update.message.reply_text("✅ Report submitted successfully!")
                time.sleep(10)
        except requests.exceptions.TooManyRedirects:
            await update.message.reply_text("✅ Report submitted successfully!")
            time.sleep(10)
        except Exception as e:
            await update.message.reply_text(f"❌ Report failed with status code [{r3.status_code}]!")
            return

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Operation cancelled.")
    return ConversationHandler.END

# Set up the Telegram bot application
application = None

def setup_application():
    global application
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN environment variable not set")
        raise ValueError("TELEGRAM_BOT_TOKEN not set")
    
    application = Application.builder().token(token).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            BOT_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, check_bot_password)],
            USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_username)],
            PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_password)],
            TARGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_target)],
            REPORT_TYPE: [CallbackQueryHandler(get_report_type)],
            CHALLENGE_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_challenge_code)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    
    application.add_handler(conv_handler)

# Webhook endpoint to receive updates from Telegram
@app.route('/webhook', methods=['POST'])
async def webhook():
    global application
    if application is None:
        setup_application()
    
    update = Update.de_json(request.get_json(), application.bot)
    await application.process_update(update)
    return jsonify({"status": "ok"})

# Route to set the webhook
@app.route('/set_webhook', methods=['GET'])
async def set_webhook():
    global application
    if application is None:
        setup_application()
    
    webhook_url = os.getenv("WEBHOOK_URL")
    if not webhook_url:
        logger.error("WEBHOOK_URL environment variable not set")
        return jsonify({"status": "error", "message": "WEBHOOK_URL not set"}), 500
    
    success = await application.bot.set_webhook(url=webhook_url + '/webhook')
    if success:
        logger.info("Webhook set successfully")
        return jsonify({"status": "success", "message": "Webhook set successfully"})
    else:
        logger.error("Failed to set webhook")
        return jsonify({"status": "error", "message": "Failed to set webhook"}), 500

if __name__ == '__main__':
    setup_application()
    port = int(os.getenv("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
