import os
import logging
import asyncio
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import aiohttp

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration
BOT_TOKEN = os.environ.get('BOT_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')
API_URL = 'https://fight.cryptofightclub.wtf/api/top-scores'
POST_INTERVAL = 3600  # 1 hour in seconds

# Medal emojis
MEDALS = {
    1: '🥇',
    2: '🥈',
    3: '🥉',
    4: '🏆',
    5: '🎖️'
}

async def fetch_leaderboard():
    """Fetch top scores from the API"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(API_URL) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('success') and data.get('topScores'):
                        return data['topScores']
                else:
                    logger.error(f"API returned status {response.status}")
    except Exception as e:
        logger.error(f"Error fetching leaderboard: {e}")
    return None

def format_leaderboard_message(scores):
    """Format the leaderboard message"""
    message = "🏆 <b>CRYPTO FIGHT CLUB - TOP 5 SCORES</b> 🏆\n\n"
    
    for idx, score in enumerate(scores, 1):
        medal = MEDALS.get(idx, '🎖️')
        game_score = f"{score['gameScore']:,}"
        username = f"@{score['xUsername']}" if score.get('xUsername') else "Anonymous"
        
        message += f"{medal} <b>#{idx}</b> - <code>{game_score}</code>\n"
        message += f"   {username}\n\n"
    
    # Add timestamp
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    message += f"<i>Last updated: {now}</i>"
    
    return message

async def send_leaderboard(context: ContextTypes.DEFAULT_TYPE, chat_id: str = None):
    """Send leaderboard to the chat"""
    target_chat_id = chat_id or CHAT_ID
    
    scores = await fetch_leaderboard()
    
    if scores:
        message = format_leaderboard_message(scores)
        try:
            await context.bot.send_message(
                chat_id=target_chat_id,
                text=message,
                parse_mode='HTML'
            )
            logger.info(f"Leaderboard sent to chat {target_chat_id}")
        except Exception as e:
            logger.error(f"Error sending message: {e}")
    else:
        error_message = "❌ Could not fetch leaderboard data. Please try again later."
        try:
            await context.bot.send_message(
                chat_id=target_chat_id,
                text=error_message
            )
        except Exception as e:
            logger.error(f"Error sending error message: {e}")

async def leaderboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /leaderboard command"""
    chat_id = update.effective_chat.id
    logger.info(f"Leaderboard command received from chat {chat_id}")
    await send_leaderboard(context, str(chat_id))

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    message = (
        "👋 <b>Welcome to Crypto Fight Club Leaderboard Bot!</b>\n\n"
        "Commands:\n"
        "/leaderboard - Show current top 5 scores\n"
        "/start - Show this message\n\n"
        "🤖 I automatically post the leaderboard every hour!"
    )
    await update.message.reply_text(message, parse_mode='HTML')

async def post_leaderboard_job(context: ContextTypes.DEFAULT_TYPE):
    """Job that runs every hour to post leaderboard"""
    logger.info("Running scheduled leaderboard post")
    await send_leaderboard(context)

def main():
    """Start the bot"""
    # Validate configuration
    if not BOT_TOKEN:
        logger.error("Please set BOT_TOKEN environment variable!")
        return
    
    if not CHAT_ID:
        logger.error("Please set CHAT_ID environment variable!")
        return
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("leaderboard", leaderboard_command))
    
    # Schedule hourly leaderboard posts
    job_queue = application.job_queue
    job_queue.run_repeating(
        post_leaderboard_job,
        interval=POST_INTERVAL,
        first=10  # First post after 10 seconds
    )
    
    logger.info("Bot started! Leaderboard will be posted every hour.")
    logger.info(f"Posting to chat ID: {CHAT_ID}")
    
    # Start the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()