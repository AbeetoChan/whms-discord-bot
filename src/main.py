import json
import discord
import config

#######################
####################### 

intents: discord.Intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = discord.Bot(intents=intents)

bot.load_extension("leveling")
#bot.load_extension("teacher_review")

bot.run(config.TOKEN)
