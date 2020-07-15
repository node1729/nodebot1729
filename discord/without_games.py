import json
import asyncio
import concurrent.futures
import discord
import random
import time
import os
import re
import youtube_dl

# start out by grabbing client info
clientinfo = open("clientinfo.json")
clientdict = json.load(clientinfo)

youtube_dl.utils.bug_reports_message = lambda: ""

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '/tmp/%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0' # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ffmpeg_options = {
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

# commands file
try:
    open("commands.json")
except FileNotFoundError:
    print("building commands.json")
    outfile = open("commands.json", "w")
    json.dump({"!ping": {"channel": -1, "return_type": "message",
                         "data": "pong", "indexed": False, "users": "any"}}, outfile, indent=4)
    outfile.flush()
    outfile.close()
commands_file = open("commands.json")
commands = json.load(commands_file)
commands_file.close()

emoji_file = open("emoji-names.json")
emojis_dict = json.load(emoji_file)


def get_emoji(name):
    return emojis_dict[name]

# TODO: Make everything return something that makes sense with other functions
class DiscordBot(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self.bg_task = self.loop.create_task(self.background_timer())
        self.loop.create_task(self.config_default_channel())
        self.vcs = []
        discord.opus.load_opus("libopus.so.0")

    async def on_ready(self):
        print("Logged in as {0}".format(self.user))

    # configures the default channel for messages
    async def config_default_channel(self):
        await self.wait_until_ready()

        # if the channel is not assigned properly,
        if not self.get_channel(commands["default"]["channel"]): # attempt to assign it to general
            channel = discord.utils.get(
                self.get_all_channels(), name="bot-commands")
            if channel:
                await self.reconfig_channel(channel.id, "default")
            else:
                print("Falling back to first channel in get_all_channels()")
                channel = await self.get_all_channels()
                channel = next(channel)
                await self.reconfig_channel(channel.id, "default")

    # edits what channel a commmand belongs in
    # return True if channel is successfully changed
    async def reconfig_channel(self, channel_id, command):
        if not type(channel_id) == int:
            try:
                int(channel_id[2:-1])
                if channel_id[:2] != "<#" or channel_id[-1:] != ">":
                    raise ValueError
            except ValueError:
                # command_simple_message( Error finding channel")
                return False
            channel_id = int(channel_id[2:-1])

        if self.get_channel(channel_id):
            commands_file = open("commands.json", "w")
            commands[command]["channel"] = channel_id
            json.dump(commands, commands_file, indent=4)
            commands_file.close()
            return True

        else:
            print("Error finding channel")
            return False

    async def command_move(self, message):
        if message.author.guild_permissions.administrator:
            msg = re.split(" ", message.content, 2)
            if len(msg) == 3:  # move a single command to a channel
                channel_id = msg[2]
                command_move = msg[1]
                print(msg)
                await self.reconfig_channel(channel_id, command_move)
                output = await message.channel.send("Successfully moved {} to {}".format(command_move, channel_id))
                return output

    ###################
    # COMMAND HANDLER #
    ###################

    # command for sending a response from the commands.json file
    async def command_simple_message(self, message, key=None, from_file=None, data=None):
        if from_file:
            fp = open(from_file, "rb")
            from_file = discord.File(fp)
        if not message:
            channel = channel_id
        elif not key:
            channel = message.channel.id
        else:
            channel = commands[key]["channel"]
            # overwrites any existing data fed in to command if key exists
            data = commands[key]["data"]
            from_file = commands[key]["file"]
            if ((message.author.guild_permissions.administrator)
                    or (not message.author.guild_permissions.administrator and not commands[key]["admin"])):
                output = await client.get_channel(channel).send(data, file=from_file)
                return output
        return False

    # Send a message to either a user or a channel
    async def direct_message(self, channel=None, user=None, data=None, from_file=None):
        if from_file:
            fp = open(from_file, "rb")
            from_file = discord.File(fp)
        if user: # only needed to specify when a DM is needed
            await user.send(content=data, file=from_file)
        else:
            output = await client.get_channel(channel).send(data, file=from_file)

    async def on_message(self, message):  # returns true if command is processed
        if message.author != self.user:  # ignore messages from the bot
            for item in self.vcs: # pass down to classes
                await item.on_message(message)
            if message.content.startswith("default ") or message.content == "default":
                return False
            print("message from {0.author} in {0.channel.id}: {0.content} ".format(message))
            built_in_commands = {
                "!move": self.command_move,
                "!connect": self.connect_to_voice,
                # "!disconnect": self.disconnect_from_voice,
                # "!play": self.create_queue
            }
            for key in built_in_commands:
                # if message.channel.id == commands["default"]["channel"]:
                if message.content.startswith(key + " ") or message.content == key:
                    output = await built_in_commands[key](message)
                    return output

            for key in commands:
                if message.channel.id == commands[key]["channel"]:
                    if message.content.startswith(key + " ") or message.content == key:
                        if commands[key]["return_type"] == "message":
                            output = await self.command_simple_message(message, key=key)
                            return output
        return False

    async def connect_to_voice(self, message):
        for vc in self.vcs:
            if vc.guild.id == message.guild.id:
                await vc.connect_to_voice(message)
                return True
        self.vcs.append(MusicPlayer(message.guild, message))
        await self.vcs[-1].connect_to_voice(message)

    # creates a reaction on a message
    async def make_react(self, message, emoji):
        await message.add_reaction(get_emoji(emoji))
        return True

    #########
    # MUSIC #
    #########

class MusicPlayer:
    def __init__(self, guild, message):
        self.guild = guild
        self.message = message
        self.index = 0
        self.queue = []
        self.vc = None
        self.loop = asyncio.get_running_loop()
    
    async def on_message(self, message):
        if message.author != client.user and message.guild.id == self.guild.id:
            print(message.content)
            if message.content[:len("!play")] == "!play":
                await self.create_queue(message)
    
    #connect to voice and add to self.vcs
    async def connect_to_voice(self, message):
        voice_channel = discord.utils.get(message.guild.voice_channels, name="General", bitrate=64000)
        self.vc = await voice_channel.connect()
    
    #remove voice connection, does not terminate class
    async def disconnect_from_voice(self, message):
        await self.vc.disconnect()
        
    async def create_queue(self, message):
        content = message.content[len("!play "):]
        self.queue.append(content)
        print(self.queue)
        if not self.vc.is_playing() and not self.vc.is_paused(): # check if no music is currently active
            await self.play_video(message)

    async def direct_message(self, channel, data):
        await client.direct_message(channel=channel, data=data)
    
    def on_video_end(self, e):
        if not e: # no errors occurred
            self.vc.stop()
            self.index += 1
            if self.index >= len(self.queue):
                loop.create_task(self.direct_message(channel=self.message.channel.id, data="Reached end of queue"))
                loop.create_task(self.disconnect_from_voice(self.message))
            else:
                loop.create_task(self.play_video(self.message))
                
                

    # async def on_video_end(self, message):
    #     print(message)
    #     vc.stop() # end audio stream
    #     print(self.music_queues)
    #     if self.music_queues[message.guild.id]["index"] + 1 < len(self.music_queues[message.guild.id]["queue"]):
    #         if self.music_queues[message.guild.id]["index"] > 0:
    #             self.music_queues[message.guild.id]["index"] += 1
    #         await self.play_video(message, vc)
    #     else:
    #         await self.direct_message(channel=message.channel.id, data="Reached end of queue, automatically disconnecting")
    #         await self.disconnect_from_voice(message)
            
    async def play_video(self, message):
        player = await YTDLSource.from_url(self.queue[self.index])
        await client.direct_message(channel=message.channel.id, data="Attempting to play video {0.title}".format(player))
        try:
            self.vc.play(player, after=self.on_video_end)
        except (discord.ClientException, TypeError, discord.opus.OpusNotLoaded) as e:
            print(e)
    

loop = asyncio.get_event_loop()
client = DiscordBot()
client.run(clientdict["token"])
