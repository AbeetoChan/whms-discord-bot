import discord
from discord.ext import commands
from config import mongo_client, STRIKES_BEFORE_BAN
import asyncio

with open("swear_words.txt") as s:
    SWEAR_WORDS = [sw.lower().replace("\n", "") for sw in s.readlines()]


class Leveling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.users = mongo_client["user_db"]["user_col"]
       
    def handle_member_join(self, user_id):
        x = self.users.insert_one({
            "user_id": user_id,
            "pts": 0, 
            "lvl": 0, 
            "strikes": 0
        })
    
    def remove_member(self, user_id):
        self.users.find_one_and_delete({"user_id": user_id})

    def user_exists(self, user_id):
        return self.users.count_documents({"user_id": user_id}) != 0

    def handle_nonexistent_user_in_db(self, user_id):
        if not self.user_exists(user_id):
            self.handle_member_join(user_id)

    @commands.slash_command(description="See how many swear strikes a user has")
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    @discord.option("user", str, description="The user you want to see the swear strikes of")
    async def see_swear_strikes(self, ctx, user):
        user = ctx.author.guild.get_member_named(user)

        if user is None:
            await ctx.respond("It seems like that person does not exist...")
            return            

        user_id = user.id
        self.handle_nonexistent_user_in_db(user_id)


        strikes = self.users.find_one({"user_id": user_id}, {"strikes": 1})["strikes"]       

        await ctx.respond(f"{user.display_name} has {strikes} strikes", ephemeral=True)

    @commands.slash_command(description="See your level!")
    @commands.guild_only()
    async def level(self, ctx):
        user_id = ctx.author.id
        self.handle_nonexistent_user_in_db(user_id)
        level = self.users.find_one({"user_id": user_id}, {"lvl": 1})["lvl"]

        embed = discord.Embed(
            title="Level",
            description=f"You are level {level}",
            color=discord.Color.gold()
        )

        embed.set_author(name=ctx.author.display_name)

        await ctx.respond(embed=embed)

    @commands.slash_command(description="See this server's level leaderboard!")
    @commands.guild_only()
    async def leaderboard(self, ctx):
        # Computationally expensive
        users = self.users.find({}, {"user_id": 1})
        users = [user["user_id"] for user in users]
        levels = self.users.find({}, {"lvl": 1})
        levels = [level["lvl"] for level in levels]
        values = list(zip(users, levels))

        values.sort(key=lambda k: k[1], reverse=True)

        embed = discord.Embed(
            title="Leaderboard",
            description="The current server leaderboard: \n",
            color=discord.Color.gold()
        )

        for u in values[:5]:
            user = await self.bot.fetch_user(u[0])
            embed.description += f"**{user.display_name}**: level {u[1]}\n"

        if ctx.author.avatar is None:
            embed.set_author(name=ctx.author.display_name)
        else:
            embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar)

        embed.set_footer(text="The rankings are subject to change")
        await ctx.respond(embed=embed)

    @staticmethod
    async def level_up(message, new_level):
        embed = discord.Embed(
            title="Level up!",
            description=f"You have leveled up to level {new_level}!",
            color=discord.Color.gold()
        )

        if message.author.avatar is None:
            embed.set_author(name=message.author.display_name)
        else:
            embed.set_author(name=message.author.display_name, icon_url=message.author.avatar.url)
        await message.reply(embed=embed)

    @staticmethod
    def can_level_up(current_level, pts):
        # This is a reimplementation of mee6's alg
        return (current_level ** 2) / 45 + 3.3 * current_level < pts

    @staticmethod
    def has_profanity_in_it(content: str):
        for sw in SWEAR_WORDS:
            if sw in content:
                return True

        return False

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.id == self.bot.user.id:
            return

        user_id = message.author.id

        self.handle_nonexistent_user_in_db(user_id)

        if self.has_profanity_in_it(message.content):
            self.users.update_one({"user_id": user_id}, {
                "$inc": {"strikes": 1}
            })
            strikes = self.users.find_one({"user_id": user_id}, {"strikes": 1})["strikes"]

            await message.delete()
            dm = await message.author.create_dm()
            await dm.send(f"Please don't send offensive messages like that! Strike #{strikes}")

            if strikes > STRIKES_BEFORE_BAN:
                await asyncio.sleep(2)

                await dm.send("You have been banned for swearing too much!")
                await message.author.ban(reason="Too many swear strikes!")
                
            return

        self.users.update_one({"user_id": user_id}, {
            "$inc": {"pts": 1}
        })

        current_level = self.users.find_one({"user_id": user_id}, {"lvl": 1})["lvl"]
        pts = self.users.find_one({"user_id": user_id}, {"pts": 1})["pts"]

        if self.can_level_up(current_level, pts):
            self.users.update_one({"user_id": user_id}, {
                "$set": {"pts": 0}
            })
            self.users.update_one({"user_id": user_id}, {
                "$inc": {"lvl": 1}
            })
            current_level += 1
            await self.level_up(message, current_level)


    @commands.Cog.listener()
    async def on_member_join(self, member):
        self.handle_member_join(member.id)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        user_id = member.id

        self.remove_member(user_id)

    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError): # noqa
        if isinstance(error, commands.MissingPermissions):
            await ctx.respond("It seems like you do not have the permissions to run this command...")
        else:
            raise error

    
def setup(bot: discord.Bot):
    bot.add_cog(Leveling(bot))
