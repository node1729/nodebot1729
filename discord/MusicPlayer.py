import asyncio
import discord
import youtube_dl
import json
import time

from YTDLSource import YTDLSource

class MusicPlayer:
    def __init__(self, guild, bot, message):
        self.guild = guild
        self.message = message
        self.index = 0
        self.queue = []
        self.vc = None
        self.time = None
        self.repeat = 0 # 1 if on
        self.loop = asyncio.get_running_loop()
        self.info = None
        self.bot = bot
        print(self)
    
    # convert from seconds into a more human readable format
    def convert_time(self, seconds):
        s = seconds % 60
        m = seconds // 60 % 60
        h = seconds // 3600 # youtube videos cannot be longer than 12 hours, so there is no issue here
        if h:
            m = ":" + str(m).zfill(2)
        else:
            h = ""
        return str(h) + str(m) + ":" + str(s).zfill(2)
    
    # interface with messages
    async def on_message(self, message):
        if message.author != self.bot.user and message.guild.id == self.guild.id:
                
            commands = {"!play": self.create_queue,
                        "!p": self.create_queue,
                        "!skip": self.skip,
                        "!s": self.skip,
                        "!queue": self.display_queue,
                        "!disconnect": self.disconnect_from_voice,
                        "!repeat": self.toggle_repeat,
                        "!help": self.help,
                        "!np": self.now_playing,
                        "!seek": self.skip_to
            }
            for key in commands:
                if message.content[:len(key) + 1] == key + " " or message.content == key:
                    await commands[key](message)
    
    # display help message
    async def help(self, message):
        fp = open("help.txt")
        outstr = ""
        for item in fp.readlines():
            outstr += item
        await self.direct_message(message.channel.id, data=outstr)
    
    #connect to voice and add to self.vcs
    async def connect_to_voice(self, message):
        voice_channel = discord.utils.get(message.guild.voice_channels)
        self.vc = await voice_channel.connect()

    # turn on or off repeat of the same song, non-destructive to the queue
    async def toggle_repeat(self, message):
        self.repeat += 1
        self.repeat %= 2
        await self.direct_message(channel=message.channel.id, data="Repeat turned {}".format("on" if self.repeat else "off"))

    # displays active queue from current index forward up to 20 items
    async def display_queue(self, message):
        outstr = "```"
        for i in range(self.index, self.index + min(20, len(self.queue[self.index:]))):
            item = self.queue[i]
            part1 = ""
            if len(item["title"]) >= 64:
                part1 = item["title"][:61] + "..."
            else:
                part1 = item["title"]
            if "duration" in item:
                part3 = self.convert_time(item["duration"])
            else:
                part3 = "[n/a]"
            part2 = ""
            for j in range(67 - len(part1) - len(part3)):
                part2 += " "
            outstr += str(i).zfill(3) + ": " + part1 + part2 + part3 + "\n"
        outstr += "```"
        await self.direct_message(message.channel.id, data=outstr)

    # displays current active song
    async def now_playing(self, message):
        if self.time is None:
            await self.direct_message(message.channel.id, data="```Nothing currently playing```")
        else:
            current_time = int(time.time())
            playtime = int(current_time - self.time)
            outstr = "```" + self.queue[self.index]["title"] + "\n"
            if "duration" in self.queue[self.index]:
                percent = int(playtime / int(self.queue[self.index]["duration"]) * 100)
                outstr += str(int(percent)) + "% " + self.convert_time(playtime) + "/" + self.convert_time(self.queue[self.index]["duration"]) + "```\nhttps://youtu.be/" + self.queue[self.index]["id"]
            else: # if we haven't grabbed the current metadata for song
                outstr += self.convert_time(playtime) + "/[n/a]```\nhttps://youtu.be/" + self.queue[self.index]["id"]
            await self.direct_message(message.channel.id, data=outstr)
    
    # seek to an item in queue
    async def skip_to(self, message):
        content = message.content[len("!seek "):]
        if get_int(content):
            self.index = get_int(content) - 1
            self.vc.stop()
    
    #remove voice connection, does not terminate class
    async def disconnect_from_voice(self, message):
        self.time = None
        self.queue = []
        await self.vc.disconnect()
        self.index = 0 # placed after disconnection because on_video_end is called and increments the index, causing an error upon reconnecting
    
    # convert a large dict to a smaller one
    def shrink_dict(self, in_dict):
        out_dict = {"id": in_dict["id"],
                    "title": in_dict["title"],
                    "duration": in_dict["duration"],
                    "upload_date": in_dict["upload_date"]}
        return out_dict
    
    # enqueues items
    async def create_queue(self, message):
        if message.content[:len("!play")] == "!play":
            content = message.content[len("!play "):]
        else:
            content = message.content[len("!p "):]
        search = await YTDLSource.check_search(content, stream=False)
        playlist = await YTDLSource.check_playlist(content, stream=False)
        if search:
            data = await YTDLSource.grab_metadata(content, stream=False)
            self.queue.append(self.shrink_dict(data["entries"][0]))
        elif playlist:
            for item in playlist["entries"]:
                self.queue.append({"title": item["title"], "id": item["id"]})
        else:
            info = await YTDLSource.from_url(content, stream=False)
            self.queue.append(self.shrink_dict(info.data))
        if not self.vc.is_playing() and not self.vc.is_paused(): # check if no music is currently active
            await self.play_video(message)
        for idx, item in enumerate(self.queue):
            try:
                if "duration" not in item:
                    self.queue[idx] = self.shrink_dict(await YTDLSource.grab_metadata("youtu.be/" + item["id"], stream=False))
            except IndexError:
                pass

    # send messages to the channel the bot was called from
    async def direct_message(self, channel, data=None, embed=None):
        await self.bot.direct_message(channel=channel, data=data, embed=embed)
    
    # skip current song
    async def skip(self, message):
        await self.direct_message(message.channel.id, data="Skipping track!")
        self.vc.stop()
    
    # play next song or stop playing altogether. This automatically calls on skip() and disconnect_from_voice()
    def on_video_end(self, e):
        self.time = None
        if not e: # no errors occurred
            self.vc.stop()
            if not self.repeat: # repeating won't increment the index, turning off repeat will continue the queue
                self.index += 1
                if self.index >= len(self.queue):
                    self.loop.create_task(self.direct_message(channel=self.message.channel.id, data="Reached end of queue"))
                    # loop.create_task(self.disconnect_from_voice(self.message))
                else:
                    self.loop.create_task(self.play_video(self.message))

    # download and play the video
    async def play_video(self, message):
        player = await YTDLSource.from_url(self.queue[self.index]["id"])
        await self.direct_message(channel=message.channel.id, data="Playing video {0.title}".format(player))
        try:
            self.time = time.time() // 1
            self.vc.play(player, after=self.on_video_end)
        except (discord.ClientException, TypeError, discord.opus.OpusNotLoaded) as e:
            print(e)