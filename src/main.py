import discord
import config

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = discord.Bot(intents=intents)

bot.load_extension("leveling")

bot.run(config.TOKEN)
