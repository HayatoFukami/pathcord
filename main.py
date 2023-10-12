import os

import discord
from discord.ext import commands

import debug_settings as settings


class Bot(commands.Bot):

    def __init__(self):

        super().__init__(command_prefix='!', intents=discord.Intents.all())

        self.load_extension_directories = ['cogs']

    async def setup_hook(self) -> None:

        for load_extension_directory in self.load_extension_directories:

            for root, dirs, files in os.walk(load_extension_directory):

                for file in files:

                    if file.endswith('.py'):

                        load_file = os.path.join(root, file).replace('/', '.').replace('\\', '.')[:-3]

                        await self.load_extension(load_file)

                        print(load_file)

        await self.tree.sync()

    async def on_ready(self):

        print(f'login: {self.user.name} [{self.user.id}]')


bot = Bot()

bot.run(settings.token)
