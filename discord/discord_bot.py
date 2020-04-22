import json
import asyncio
import discord
import time
import re

# start out by grabbing client info
clientinfo = open("clientinfo.json")
clientdict = json.load(clientinfo)

# commands file
try:
    open("commands.json")
except FileNotFoundError:
    print("building commands.json")
    outfile = open("commands.json", "w")
    json.dump({"!ping": {"channel": -1, "return_type": "message", "data": "pong", "indexed": False, "users": "any"}}, outfile, indent=4)
    outfile.flush()
    outfile.close()
commands_file = open("commands.json")
commands = json.load(commands_file)
commands_file.close()


# TODO: Make everything return something that makes sense with other functions
class DiscordBot(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # self.bg_task = self.loop.create_task(self.background_timer())
        self.loop.create_task(self.config_default_channel())
    async def on_ready(self):
        print("Logged in as {0}".format(self.user))

    # configures the default channel for messages
    async def config_default_channel(self):
        await self.wait_until_ready()
        
        if not self.get_channel(commands["default"]["channel"]):# if the channel is not assigned properly,
                                                                # attempt to assign it to general
            channel = discord.utils.get(self.get_all_channels(), name="bot-commands")
            if channel:
                await self.reconfig_channel(channel.id, "default")
            else:
                print("Falling back to first channel in get_all_channels()")
                channel = await self.get_all_channels()
                channel = next(channel)
                await self.reconfig_channel(channel.id, "default")

    #edits what channel a commmand belongs in
    async def reconfig_channel(self, channel_id, command):  # return True if channel is successfully changed
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
            if len(msg) == 3: # move a single command to a channel
                channel_id = msg[2]
                command_move = msg[1]
                print(msg)
                await self.reconfig_channel(channel_id, command_move)
                output = await message.channel.send("Successfully moved {} to {}".format(command_move, channel_id))
                return output
                
    ###################
    # COMMAND HANDLER #
    ###################
    
    async def command_simple_message(self, message, key=None, from_file=None, data=None): # command for sending a "message" from the commands.json file
        if not key:
            channel = message.channel.id
        else:
            channel = commands[key]["channel"]
            data = commands[key]["data"] # overwrites any existing data fed in to command if key exists
            from_file = commands[key]["file"]
        if ((message.author.guild_permissions.administrator)
            or (not message.author.guild_permissions.administrator and not commands[key]["admin"])):
            if from_file:
                fp = open(from_file, "rb")
                from_file = discord.File(fp)
            output = await client.get_channel(channel).send(data, file=from_file)
            return output
        return False
    

    async def on_message(self, message): # returns true if command is processed
        if message.author != self.user: # ignore messages from the bot 
            if message.content.startswith("default ") or message.content == "default":
                return False
            print("message from {0.author} in {0.channel.id}: {0.content} ".format(message))
            built_in_commands = {
                                "!move": self.command_move
                                # "!connect": self.connect_to_voice
                                }
            for key in built_in_commands:
                if message.channel.id == commands["default"]["channel"]:
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

    # creates a reaction on a message
    async def make_react(self, message, emoji):
        await message.add_reaction(emoji)
        return True
    
    ###############
    # OTHER STUFF #
    ###############
    
    # TODO: THIS
    # intended for use with background_timer() TODO: make this code work on new configuration
    # async def on_time(self):
    #     if self.get_channel(settings["message_channel"]["default"]):
    #         channel = self.get_channel(settings["message_channel"]["default"])
    #         await channel.send("sample text")
    #         return True
    #     else:
    #         print("invalid configuration for automatic messages")
    #         return False

    # Runs a timer that automatically triggeres based upon the time TODO: make code work on new configuration
    # async def background_timer(self):
    #     await self.wait_until_ready()
        
    #     channel = self.get_channel(settings["message_channel"]["default"])
    #     while not self.is_closed():
    #         current_time = time.asctime()
    #         day_of_week = current_time[:3] # Sun, Mon, Tue, Wed, Thu, Fri, Sat
    #         month = current_time[4:7]      # Jan, Feb, Mar, Apr, May, Jun, Jul, Aug, Sep, Oct, Nov, Dec
    #         day = current_time[8:10]       # space padded 2 character number
    #         hour = current_time[11:13]     # 0 padded 2 character number
    #         minute = current_time[14:16]   # 0 padded 2 character number
    #         second = current_time[17:19]   # 0 padded 2 character number
    #         year = current_time[20:]       # 4 character number
    #         # example reminder for 09:00 MWF class
    #         #days = ["Mon", "Wed", "Fri"]
    #         #if day_of_week in days and hour == "09" and minute == "00" and second == "00":
    #         #    await channel.send("Reminder")
    #         await asyncio.sleep(1)

    # #########
    # # MUSIC # (THIS HAS HALTED PROGRESS FOR NOW)
    # #########
    # async def connect_to_voice(self, message):
    #     await discord.VoiceChannel.connect()

# TODO: implement proper reading of DMs and feeding into a main game
class TruthAndLiePlayer():
    async def __init__(self, *args, **kwargs):
        self.player = player_id
        # self.loop.create_task(self.)
    
    
client = DiscordBot()
client.run(clientdict["token"])
