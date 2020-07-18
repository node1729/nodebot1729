import importlib
import json
import asyncio
import concurrent.futures
import discord
import random
import time
import os
import re
import youtube_dl
from MusicPlayer import MusicPlayer
# start out by grabbing client info
clientinfo = open("clientinfo.json")
clientdict = json.load(clientinfo)



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

gpt2 = open("gpt2.txt")
gpt2 = gpt2.readlines()


def get_emoji(name):
    return emojis_dict[name]

def get_int(test):
    try:
        int(test)
    except ValueError:
        return False
    return int(test)

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

    # IGNORE THIS
    async def gpt2(self, message):
        if message.guild.id == 107624859353243648:
            i = random.randint(0, len(gpt2))
            outstr = str(i) + ": " + gpt2[i]
            if message.content != "!gpt2":
                if message.content[len("!gpt2 "):] == "{quote}":
                    while "!quote" not in gpt2[i]:
                        i = random.randint(0, len(gpt2))
                    outstr = str(i) + ": " + gpt2[i] + gpt2[i + 1]
                elif get_int(message.content[len("!gpt2 "):]):
                    outstr = message.content[len("!gpt2 "):] + ": " + gpt2[int(message.content[len("!gpt2 "):])]
                else:
                    found = False
                    for j in range(65536):
                        if message.content[len("!gpt2 "):].upper() not in gpt2[i].upper() and not found:
                            i = random.randint(0, len(gpt2))
                        else:
                            found = True
                            
                    if found:
                        outstr = str(i) + ": " + gpt2[i]
                    else:
                        outstr = "Could not find search of `" + message.content[len("!gpt2 "):] + "`"
            await self.direct_message(message.channel.id, data=outstr)
        
    
    # Send a message to either a user or a channel
    async def direct_message(self, channel=None, user=None, data=None, from_file=None, embed=None):
        if from_file:
            fp = open(from_file, "rb")
            from_file = discord.File(fp)
        if user: # only needed to specify when a DM is needed
            await user.send(content=data, file=from_file, embed=embed)
        else:
            output = await client.get_channel(channel).send(data, file=from_file)

    async def on_message(self, message):  # returns true if command is processed
        if message.author != self.user:  # ignore messages from the bot
            for item in self.vcs: # pass down to classes
                await item.on_message(message)
            if message.content.startswith("default ") or message.content == "default":
                return False
            print("message from {0.author} in {0.channel.id} ({0.guild.id}): {0.content} ".format(message))
            built_in_commands = {
                "!move": self.command_move,
                "!connect": self.connect_to_voice,
                "!gpt2": self.gpt2
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
        self.vcs.append(MusicPlayer(message.guild, self, message))
        await self.vcs[-1].connect_to_voice(message)

    # creates a reaction on a message
    async def make_react(self, message, emoji):
        await message.add_reaction(get_emoji(emoji))
        return True

    #########
    # MUSIC #
    #########



loop = asyncio.get_event_loop()
client = DiscordBot()
client.run(clientdict["token"])
