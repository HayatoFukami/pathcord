import asyncio
import sqlite3

import discord
from discord import app_commands
from discord.ext import commands

import settings as settings


# noinspection PyUnresolvedReferences
@app_commands.guild_only
class Study(app_commands.Group):
    def __init__(self):
        super().__init__(name='study')
        self.pomodoro_channels = []  # channel_idを格納するリスト

    @app_commands.command(
        name='status',
        description='勉強時間のステータスを表示します。'
    )
    async def status(
            self,
            interaction: discord.Interaction
    ):

        await interaction.response.defer(ephemeral=True)

        # メンバーがデータベースに登録されているか確認する。
        con = sqlite3.connect(settings.dbpath)
        cur = con.cursor()

        cur.execute(
            'SELECT * FROM member_study_time WHERE member_id = ?;',
            (interaction.user.id,)
        )

        member_study_time = cur.fetchone()

        con.close()

        # もしメンバーがデータベースに登録されていなかった場合
        if not member_study_time:
            await interaction.followup.send(
                '勉強時間が記録されていません。'
            )
            return

        # もしメンバーがデータベースに灯篭されていた場合
        # メンバーが全員の中で何番目に勉強時間が多いか特定する

        con = sqlite3.connect(settings.dbpath)
        cur = con.cursor()

        cur.execute(
            'SELECT * FROM member_study_time ORDER BY seconds DESC;'
        )

        member_study_times = cur.fetchall()

        con.close()

        rank = 0

        for i in member_study_times:
            rank += 1
            if i[0] == interaction.user.id:
                break

        # 秒数を時間、分、秒に変換する。
        hours, remainder = divmod(member_study_time[1], 3600)
        minutes, seconds = divmod(remainder, 60)

        embed = discord.Embed(
            title='勉強時間ステータス',
            description='勉強時間のステータスを表示しています。',
            color=discord.Color.green()
        )

        embed.set_author(
            name=f'{interaction.user.display_name}',
            icon_url=interaction.user.display_avatar.url
        )

        embed.add_field(
            name='勉強時間',
            value=f'{int(hours)}時間{int(minutes)}分{int(seconds)}秒',
            inline=True
        )

        embed.add_field(
            name='ランク',
            value=f'{rank}位',
            inline=True
        )

        await interaction.followup.send(embed=embed)

    @app_commands.command(
        name='ranking',
        description='勉強時間のランキングを表示します。'
    )
    async def ranking(
            self,
            interaction: discord.Interaction
    ):

        await interaction.response.defer(ephemeral=True)

        # データベースから勉強時間の上位10人を取得する。
        con = sqlite3.connect(settings.dbpath)
        cur = con.cursor()

        cur.execute(
            'SELECT * FROM member_study_time ORDER BY seconds DESC LIMIT 10;'
        )

        top10 = cur.fetchall()

        con.close()

        # もし勉強時間の上位10人がいた場合
        if top10:

            embed = discord.Embed(
                title='勉強時間ランキング',
                description='勉強時間の上位10人を表示しています。',
                color=discord.Color.green()
            )

            for i in top10:

                # 秒数を時間、分、秒に変換する。
                hours, remainder = divmod(i[1], 3600)
                minutes, seconds = divmod(remainder, 60)

                member = interaction.guild.get_member(i[0])

                # メンバーがサーバーにいるか確認
                if member:

                    # ランキングの順位付きのメンバー情報を追加
                    embed.add_field(
                        name=f'{top10.index(i) + 1}位│{member.display_name}',
                        value=f'{int(hours)}時間 {int(minutes)}分 {int(seconds)}秒',
                        inline=False
                    )

                # もしメンバーがサーバーにいない場合
                else:

                    embed.add_field(
                        name=f'{top10.index(i) + 1}位│{i[0]}',
                        value=f'{int(hours)}時間 {int(minutes)}分 {int(seconds)}秒',
                        inline=False
                    )

            await interaction.followup.send(embed=embed)

        # もし勉強時間の上位10人がいなかった場合
        else:

            await interaction.followup.send('勉強時間が記録されているメンバーがいません。')

    @app_commands.command(
        name='pomodoro',
        description='ポモドーロタイマーを起動します。'
    )
    @app_commands.rename(
        work_time='勉強時間',
        break_time='休憩時間',
        cycles='サイクル数'
    )
    @app_commands.describe(
        work_time='勉強時間を設定します。デフォルトでは25(分)です。',
        break_time='休憩時間を設定します。デフォルトでは5(分)です。',
        cycles='サイクル数を設定します。デフォルトでは4(回)です。'
    )
    async def pomodoro_timer(
            self,
            interaction: discord.Interaction,
            work_time: int = 25,
            break_time: int = 5,
            cycles: int = 4
    ):

        await interaction.response.defer(ephemeral=True)

        # ボイスチャンネルに接続しているか確認する。
        if not interaction.user.voice:
            await interaction.followup.send('ボイスチャンネルに接続してからコマンドを実行してください。')

            return

        # 現在のボイスチャンネルでポモドーロタイマーが起動しているか確認する。
        if interaction.user.voice.channel.id in self.pomodoro_channels:
            await interaction.followup.send('既にポモドーロタイマーが起動しています。')

            return

        # 現在のボイスチャンネルが勉強ルームか確認する。
        con = sqlite3.connect(settings.dbpath)
        cur = con.cursor()

        cur.execute(
            'SELECT * FROM study_rooms WHERE channel_id = ?;',
            (interaction.user.voice.channel.id,)
        )

        study_room_id = cur.fetchone()

        con.close()

        if not study_room_id:
            await interaction.followup.send('勉強ルームでコマンドを実行してください。')

            return

        # ポモドーロタイマーを起動する。
        self.pomodoro_channels.append(interaction.user.voice.channel.id)

        await interaction.followup.send('ポモドーロタイマーを起動しました。')

        default_channel_id = interaction.user.voice.channel.id

        # ポモドーロタイマーのループ
        for cycle in range(cycles):

            study_room = interaction.guild.get_channel(default_channel_id)

            if not study_room:
                self.pomodoro_channels.remove(default_channel_id)

                return

            embed = discord.Embed(
                title='作業開始',
                description=f'時間は{work_time}分です。',
                color=discord.Color.teal()
            )

            for member in study_room.members:
                await member.send(embed=embed)

            await study_room.send(embed=embed)

            await asyncio.sleep(work_time * 60)

            study_room = interaction.guild.get_channel(default_channel_id)

            if not study_room:
                self.pomodoro_channels.remove(default_channel_id)

                return

            if (cycle + 1) == cycles:

                self.pomodoro_channels.remove(default_channel_id)

                embed = discord.Embed(
                    title='ポモドーロタイマーが終了しました。',
                    description='お疲れ様でした。',
                    color=discord.Color.yellow()
                )

                for member in study_room.members:
                    await member.send(embed=embed)

                await study_room.send(embed=embed)

                return

            embed = discord.Embed(
                title='休憩開始',
                description=f'時間は{break_time}分です。',
                color=discord.Color.blue()
            )

            for member in study_room.members:
                await member.send(embed=embed)

            await study_room.send(embed=embed)

            await asyncio.sleep(break_time * 60)

        await interaction.followup.send('Error. Please contact the developer.')


async def room_commands_check(
        interaction: discord.Interaction
):
    if not interaction.user.voice:
        await interaction.followup.send('ボイスチャンネルに接続してからコマンドを実行してください。')

        return False

    con = sqlite3.connect(settings.dbpath)
    cur = con.cursor()

    cur.execute(
        'SELECT * FROM study_rooms WHERE channel_id = ?;',
        (interaction.user.voice.channel.id,)
    )

    study_room = cur.fetchone()

    con.close()

    if not study_room:
        await interaction.followup.send('勉強ルームでコマンドを実行してください。')

        return False

    if not study_room[1] == interaction.user.id:
        await interaction.followup.send('勉強ルームのオーナーでないとコマンドを実行できません。')

        return False

    return True


# noinspection PyUnresolvedReferences
@app_commands.guild_only
class Room(app_commands.Group):
    def __init__(self):
        super().__init__(name='room', parent=Study())

    # noinspection PyUnresolvedReferences
    @app_commands.command(
        name='rename',
        description='勉強ルームの名前を変更します。'
    )
    @app_commands.rename(
        new_name='新しい名前'
    )
    @app_commands.describe(
        new_name='新しい勉強ルームの名前を設定します。'
    )
    async def rename(
            self,
            interaction: discord.Interaction,
            new_name: str
    ):
        await interaction.response.defer(ephemeral=True)

        if await room_commands_check(interaction):
            await interaction.user.voice.channel.edit(name=f'│{new_name}')

            await interaction.followup.send(f'勉強ルームの名前を**{new_name}**に変更しました。')

        return

    @app_commands.command(
        name='limit',
        description='勉強ルームの人数制限を設定します。'
    )
    @app_commands.rename(
        limit='人数制限'
    )
    @app_commands.describe(
        limit='勉強ルームの人数制限を設定します。'
    )
    async def limit(
            self,
            interaction: discord.Interaction,
            limit: int
    ):

        await interaction.response.defer(ephemeral=True)

        if await room_commands_check(interaction):
            await interaction.user.voice.channel.edit(user_limit=limit)

            await interaction.followup.send(f'勉強ルームの人数制限を**{limit}**人に変更しました。')

        return

    @app_commands.command(
        name='lock',
        description='勉強ルームをロックします。'
    )
    async def lock(
            self,
            interaction: discord.Interaction
    ):

        await interaction.response.defer(ephemeral=True)

        if await room_commands_check(interaction):

            overwrites = {}

            if interaction.user.voice.channel.changed_roles:

                for role in interaction.user.voice.channel.changed_roles:
                    overwrites[role] = discord.PermissionOverwrite(connect=False)

            else:

                overwrites[interaction.guild.default_role] = discord.PermissionOverwrite(connect=False)

            await interaction.user.voice.channel.edit(overwrites=overwrites)

            await interaction.followup.send('勉強ルームをロックしました。')

        return

    @app_commands.command(
        name='unlock',
        description='勉強ルームのロックを解除します。'
    )
    async def unlock(
            self,
            interaction: discord.Interaction
    ):

        await interaction.response.defer(ephemeral=True)

        if await room_commands_check(interaction):

            overwrites = {}

            if interaction.user.voice.channel.changed_roles:

                for role in interaction.user.voice.channel.changed_roles:
                    overwrites[role] = discord.PermissionOverwrite(connect=True)

            else:

                overwrites[interaction.guild.default_role] = discord.PermissionOverwrite(connect=True)

            await interaction.user.voice.channel.edit(overwrites=overwrites)

            await interaction.followup.send('勉強ルームのロックを解除しました。')

        return

    @app_commands.command(
        name='kick',
        description='勉強ルームから指定したメンバーをキックします。'
    )
    @app_commands.rename(
        member='メンバー'
    )
    @app_commands.describe(
        member='勉強ルームからキックするメンバーを設定します。'
    )
    async def kick(
            self,
            interaction: discord.Interaction,
            member: discord.Member
    ):

        await interaction.response.defer(ephemeral=True)

        if await room_commands_check(interaction):
            await member.move_to(None)

            await interaction.followup.send(f'**{member.display_name}**を勉強ルームからキックしました。')

        return

    @app_commands.command(
        name='ban',
        description='勉強ルームから指定したメンバーをBANします。'
    )
    @app_commands.rename(
        member='メンバー'
    )
    @app_commands.describe(
        member='勉強ルームからBANするメンバーを設定します。'
    )
    async def ban(
            self,
            interaction: discord.Interaction,
            member: discord.Member
    ):

        await interaction.response.defer(ephemeral=True)

        if await room_commands_check(interaction):
            await interaction.user.voice.channel.edit(overwrites={member: discord.PermissionOverwrite(connect=False)})

            await interaction.followup.send(f'**{member.display_name}**を勉強ルームからBANしました。')

        return

    @app_commands.command(
        name='unban',
        description='勉強ルームから指定したメンバーのBANを解除します。'
    )
    @app_commands.rename(
        member='メンバー'
    )
    @app_commands.describe(
        member='勉強ルームからBANを解除するメンバーを設定します。'
    )
    async def unban(
            self,
            interaction: discord.Interaction,
            member: discord.Member
    ):

        await interaction.response.defer(ephemeral=True)

        if await room_commands_check(interaction):
            await interaction.user.voice.channel.edit(overwrites={member: discord.PermissionOverwrite(connect=True)})

            await interaction.followup.send(f'**{member.display_name}**の勉強ルームからのBANを解除しました。')

        return

    @app_commands.command(
        name='owner',
        description='勉強ルームのオーナーを変更します。'
    )
    @app_commands.rename(
        member='新しいオーナー'
    )
    @app_commands.describe(
        member='勉強ルームのオーナーにするメンバーを設定します。'
    )
    async def owner(
            self,
            interaction: discord.Interaction,
            member: discord.Member
    ):

        await interaction.response.defer(ephemeral=True)

        if await room_commands_check(interaction):

            if (not member.voice) or (member.voice.channel != interaction.user.voice.channel):
                await interaction.followup.send('オーナーにするメンバーがボイスチャンネルに接続していません。')

                return

            if member.bot:

                await interaction.followup.send('ボットをオーナーにすることはできません。')

                return

            con = sqlite3.connect(settings.dbpath)
            cur = con.cursor()

            cur.execute(
                'UPDATE study_rooms SET owner_id = ? WHERE channel_id = ?;',
                (member.id, interaction.user.voice.channel.id)
            )

            con.commit()

            con.close()

            await interaction.followup.send(f'勉強ルームのオーナーを**{member.display_name}**に変更しました。')

        return


async def setup(bot: commands.Bot):
    bot.tree.add_command(Room())
