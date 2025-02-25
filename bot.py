import sys
import glob
import importlib
from pathlib import Path
from pyrogram import idle
import logging
import logging.config
import time
import asyncio
import pytz
from aiohttp import web
from pyrogram import Client, __version__
from pyrogram.raw.all import layer
from database.ia_filterdb import Media, Media2, tempDict, choose_mediaDB, db as clientDB
from database.users_chats_db import db
from info import *
from utils import temp
from typing import Union, Optional, AsyncGenerator
from pyrogram import types
from Script import script 
from datetime import date, datetime
from plugins import web_server, check_expired_premium
from Deendayal_botz import DeendayalBot
from util.keepalive import ping_server
from Deendayal_botz.clients import initialize_clients

# Logging Configuration
logging.config.fileConfig('logging.conf')
logging.getLogger().setLevel(logging.INFO)
logging.getLogger("pyrogram").setLevel(logging.ERROR)
logging.getLogger("imdbpy").setLevel(logging.ERROR)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logging.getLogger("aiohttp").setLevel(logging.ERROR)
logging.getLogger("aiohttp.web").setLevel(logging.ERROR)

botStartTime = time.time()
ppath = "plugins/*.py"
files = glob.glob(ppath)

async def Deendayal_start():
    print('\nInitializing Deendayal Dhakad Bot')
    
    # Start bot
    await DeendayalBot.start()
    
    # Fetch bot info
    bot_info = await DeendayalBot.get_me()
    DeendayalBot.username = bot_info.username
    
    await initialize_clients()

    # Load plugins
    for name in files:
        with open(name) as a:
            patt = Path(a.name)
            plugin_name = patt.stem.replace(".py", "")
            plugins_dir = Path(f"plugins/{plugin_name}.py")
            import_path = "plugins.{}".format(plugin_name)
            spec = importlib.util.spec_from_file_location(import_path, plugins_dir)
            load = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(load)
            sys.modules["plugins." + plugin_name] = load
            print("Deendayal Dhakad Imported => " + plugin_name)

    if ON_HEROKU:
        asyncio.create_task(ping_server())

    # Load banned users and chats
    b_users, b_chats = await db.get_banned()
    temp.BANNED_USERS = b_users
    temp.BANNED_CHATS = b_chats

    # Ensure database indexes exist
    await Media.ensure_indexes()
    await Media2.ensure_indexes()
    
    # Check database size
    stats = await clientDB.command('dbStats')
    free_dbSize = round(512 - ((stats['dataSize'] / (1024 * 1024)) + (stats['indexSize'] / (1024 * 1024))), 2)
    
    if DATABASE_URI2 and free_dbSize < 62:
        tempDict["indexDB"] = DATABASE_URI2
        logging.info(f"Since Primary DB has only {free_dbSize} MB left, Secondary DB will be used.")
    elif DATABASE_URI2 is None:
        logging.error("Missing second DB URI! Add SECONDDB_URI now! Exiting...")
        exit()
    else:
        logging.info(f"Primary DB has enough space ({free_dbSize}MB). It will be used for storing data.")

    await choose_mediaDB()

    me = await DeendayalBot.get_me()
    temp.ME = me.id
    temp.U_NAME = me.username
    temp.B_NAME = me.first_name
    temp.B_LINK = me.mention
    DeendayalBot.username = '@' + me.username
    DeendayalBot.loop.create_task(check_expired_premium(DeendayalBot))

    logging.info(f"{me.first_name} running Pyrogram v{__version__} (Layer {layer}) on {me.username}.")
    logging.info(LOG_STR)
    logging.info(script.LOGO)

    # Send a restart message
    tz = pytz.timezone('Asia/Kolkata')
    today = date.today()
    now = datetime.now(tz)
    time_now = now.strftime("%H:%M:%S %p")
    await DeendayalBot.send_message(chat_id=LOG_CHANNEL, text=script.RESTART_TXT.format(temp.B_LINK, today, time_now))

    # Start Web Server
    app = web.AppRunner(await web_server())
    await app.setup()
    bind_address = "0.0.0.0"
    await web.TCPSite(app, bind_address, PORT).start()

    # Keep the bot running
    await idle()

if __name__ == '__main__':
    try:
        asyncio.run(Deendayal_start())
    except KeyboardInterrupt:
        logging.info('Service Stopped. Bye 👋')
