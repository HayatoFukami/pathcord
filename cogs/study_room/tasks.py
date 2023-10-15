import datetime
import sqlite3

import discord
from discord.ext import commands, tasks

import settings as settings


class Tasks(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.send_study_time_ranking.start()

    # 0時から初めて6時間ごとにランキングを送信する。
    @tasks.loop(time=[
        datetime.time(hour=15, tzinfo=datetime.timezone.utc),
        datetime.time(hour=21, tzinfo=datetime.timezone.utc),
        datetime.time(hour=3, tzinfo=datetime.timezone.utc),
        datetime.time(hour=9, tzinfo=datetime.timezone.utc)
    ])
    async def send_study_time_ranking(self):
        # データベースから勉強時間の上位10人を取得する。
        con = sqlite3.connect(settings.dbpath)
        cur = con.cursor()

        cur.execute(
            'SELECT * FROM member_study_time ORDER BY seconds DESC LIMIT 10;'
        )

        top10 = cur.fetchall()

        con.close()

        # もし勉強時間の上位10人がいた場合
        if not top10:

            return

        embed = discord.Embed(
            title='勉強時間ランキング',
            description='勉強時間の上位10人を表示しています。',
            color=discord.Color.green()
        )

        for i in top10:

            # 秒数を時間、分、秒に変換する。
            hours, remainder = divmod(i[1], 3600)
            minutes, seconds = divmod(remainder, 60)

            guild = self.bot.get_guild(settings.guild_id)

            member = guild.get_member(i[0])

            # メンバーがサーバーにいるか確認
            if member:

                # ランキングの順位付きのメンバー情報を追加
                embed.add_field(
                    name=f'{top10.index(i) + 1}位│{member.display_name}',
                    value=f'{int(hours)}時間 {int(minutes)}分 {int(seconds)}秒',
                )

            # もしメンバーがサーバーにいない場合
            else:

                embed.add_field(
                    name=f'{top10.index(i) + 1}位│{i[0]}',
                    value=f'{int(hours)}時間 {int(minutes)}分 {int(seconds)}秒',
                )

        channel = self.bot.get_channel(settings.send_study_time_ranking_channel_id)

        await channel.send(embed=embed)

        return


async def setup(bot: commands.Bot):
    await bot.add_cog(Tasks(bot))
