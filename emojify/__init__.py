from .emojify import Emojify


async def setup(bot):
    await bot.add_cog(Emojify(bot))