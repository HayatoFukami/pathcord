import sqlite3
import time

import discord
from discord.ext import commands

import settings as settings


class Events(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.start_time = {}  # {member_id: time.time()}

        self.study_room_permissions = discord.PermissionOverwrite(
            stream=True,
            view_channel=True,
            send_messages=True,
            attach_files=True,
            read_message_history=True,
            connect=True,
            speak=True,
            use_voice_activation=True,
            use_application_commands=True
        )

    # 勉強ルームの作成
    # 勉強開始時刻を記録
    @commands.Cog.listener(name='on_voice_state_update')
    async def create_study_room_and_record_start_time(
            self,
            member: discord.Member,
            before: discord.VoiceState,
            after: discord.VoiceState
    ):

        if member.bot:

            return

        # ボイスチャンネルに入った、または、別のボイスチャンネルから移動してきた場合以外だったら return
        if not (after.channel and ((not before.channel) or (before.channel != after.channel))):

            return

        # 参加したボイスチャンネルが勉強ルーム作成ボイスチャンネルの場合
        if after.channel.id in settings.study_room_create_voice_channel_ids:

            overwrites = {}

            # カテゴリーに属している場合
            if after.channel.category:

                if after.channel.category.changed_roles:

                    for role in after.channel.category.changed_roles:

                        overwrites[role] = self.study_room_permissions

                else:

                    overwrites[after.channel.guild.default_role] = self.study_room_permissions

                study_room = await after.channel.category.create_voice_channel(
                    name=f'│{member.display_name}の勉強部屋',
                    overwrites=overwrites,
                    position=len(after.channel.category.channels)
                )

            # カテゴリーに属していない場合
            else:

                if after.channel.changed_roles:

                    for role in after.channel.changed_roles:

                        overwrites[role] = self.study_room_permissions

                else:

                    overwrites[after.channel.guild.default_role] = self.study_room_permissions

                study_room = await after.channel.guild.create_voice_channel(
                    name=f'│{member.display_name}の勉強部屋',
                    overwrites=overwrites
                )

            await member.move_to(study_room)

            con = sqlite3.connect(settings.dbpath)
            cur = con.cursor()

            cur.execute(
                'INSERT INTO study_rooms VALUES (?, ?);',
                (study_room.id, member.id)
            )

            con.commit()
            con.close()

        # メンバーの現在のボイスチャンネルが勉強ルームだった場合
        # 勉強開始時刻を記録
        con = sqlite3.connect(settings.dbpath)
        cur = con.cursor()

        cur.execute(
            'SELECT * FROM study_rooms WHERE channel_id = ?;',
            (after.channel.id,)
        )

        study_room_id = cur.fetchone()

        con.close()

        if study_room_id:

            self.start_time[member.id] = time.time()

        return

    @commands.Cog.listener(name='on_voice_state_update')
    async def delete_study_room_and_record_total_study_time(
            self,
            member: discord.Member,
            before: discord.VoiceState,
            after: discord.VoiceState
    ):

        if member.bot:

            return

        if not (before.channel and ((not after.channel) or (before.channel != after.channel))):

            return

        con = sqlite3.connect(settings.dbpath)
        cur = con.cursor()

        cur.execute(
            'SELECT * FROM study_rooms WHERE channel_id = ?;',
            (before.channel.id,)
        )

        study_room_id = cur.fetchone()

        con.close()

        if not study_room_id:

            return

        if not before.channel.members:

            await before.channel.delete()

            con = sqlite3.connect(settings.dbpath)
            cur = con.cursor()

            cur.execute(
                'DELETE FROM study_rooms WHERE channel_id = ?;',
                (before.channel.id,)
            )

            con.commit()
            con.close()

        if member.id in self.start_time:

            total_study_time = int(time.time() - self.start_time[member.id])

            del self.start_time[member.id]

            con = sqlite3.connect(settings.dbpath)
            cur = con.cursor()

            cur.execute(
                'SELECT * FROM member_study_time WHERE member_id = ?;',
                (member.id,)
            )

            member_study_time = cur.fetchone()

            if member_study_time:

                cur.execute(
                    'UPDATE member_study_time SET seconds = ? WHERE member_id = ?;',
                    (member_study_time[1] + total_study_time, member.id)
                )

            else:

                cur.execute(
                    'INSERT INTO member_study_time VALUES (?, ?);',
                    (member.id, total_study_time)
                )

            con.commit()
            con.close()

        return


async def setup(bot: commands.Bot):
    await bot.add_cog(Events(bot))
