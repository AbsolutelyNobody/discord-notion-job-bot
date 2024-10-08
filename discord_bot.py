import os
import asyncio
from datetime import datetime, timezone
import logging
from typing import List

from discord import Intents
from discord.ext import commands
from notion_client import Client
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Retrieve values from environment variables
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
DATABASE_ID = os.getenv("DATABASE_ID")
DISCORD_CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID"))
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", 120))
LOGLEVEL = os.environ.get("LOGLEVEL", "INFO").upper()

# Configure logging
console_handler = logging.StreamHandler()
console_handler.setFormatter(
    logging.Formatter("%(asctime)s %(levelname)s %(message)s", "%Y-%m-%d %H:%M:%S")
)
logger = logging.getLogger(__name__) #name of the logger instance (i think)
logger.setLevel(LOGLEVEL)
logger.addHandler(console_handler)

# Create default intents and disable members intent
intents = Intents.default()

# Initialize the Discord bot with the specified intents
bot = commands.Bot(command_prefix="!", intents=intents)

# Initialize the Notion client
notion = Client(auth=NOTION_API_KEY)

# Store the last checked timestamp
last_checked = datetime.now(timezone.utc).replace(microsecond=0).isoformat()


async def get_notion_pages() -> List[dict]:
    """
    Fetch pages from the Notion database since the last checked timestamp.

    :return: A list of pages.
    """
    global last_checked
    try:
        pages = notion.databases.query(
            **{
                "database_id": DATABASE_ID,
                "filter": {
                    "and": [
                        {
                            
                            #Original timestamp check, but timestamp isn't listed as a property in notion docs
                            "timestamp": "last_edited_time",
                            "last_edited_time": {"after": last_checked},
                            
                        }
                    ]
                },
            }
        ).get("results")
        last_checked = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        logger.info(f"Last checked at: {last_checked}")
        logger.info(f"Database ID: {DATABASE_ID}") #still more testing, but this could stay
        logger.debug(pages)
        print(len(pages)) #why have i started my comments at the bottom? no idea, also testing
        return pages
    except Exception as e:
        logger.error(f"Error fetching pages from Notion: {e}")
        print(f"Error fetching pages from Notion: {e}")
        return []


def format_page_message(page: dict) -> str:
    """
    Format the page title to be sent as a Discord message.

    :param page: The Notion page.
    :return: The formatted message.
    """
    title = page["properties"]["Company"]["title"][0]["text"]["content"]
    status = page["properties"]["Status"]["status"]["name"]
    try:
        location = page["properties"]["Location"]["rich_text"][0]["text"]["content"]
        message = f"Update: {title}\n Status: {status}\n Location: {location}"
    except:
        message = f"Update: {title}\n Status: {status}\n"
    return message


async def poll_notion_database() -> None:
    """
    Poll the Notion database and send updates to a Discord channel.
    """
    while True:
        pages = await get_notion_pages()
        print("Got notion pages") #also testing
        channel = bot.get_channel(DISCORD_CHANNEL_ID)
        print(f"Discord ID: {DISCORD_CHANNEL_ID}") #just for testing
        for page in pages:
            print(f"Page: {page}") #debug stuff, make SURE to remove this it is a illegible nightmare
            message = format_page_message(page)
            try:
                await channel.send(message)
            except Exception as e:
                logger.error(f"Error sending message to Discord: {e}")
        await asyncio.sleep(POLL_INTERVAL)  # Poll every N seconds


@bot.event
async def on_ready() -> None:
    """
    Event that occurs when the bot is ready.
    """
    logger.info(f"{bot.user} is now online!")
    try:
        await poll_notion_database()
    except Exception as e:
        logger.error(f"Error polling Notion database: {e}")


if __name__ == "__main__":
    bot.run(DISCORD_BOT_TOKEN)
