import json
import asyncio
import concurrent.futures
import discord
import random
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
        self.games = []
        
    async def on_ready(self):
        print("Logged in as {0}".format(self.user))

    # configures the default channel for messages
    async def config_default_channel(self):
        await self.wait_until_ready()

        # if the channel is not assigned properly,
        if not self.get_channel(commands["default"]["channel"]):
                                                                # attempt to assign it to general
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

    # command for sending a "message" from the commands.json file
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

    async def direct_message(self, channel=None, user=None, data=None, from_file=None):
        if from_file:
            fp = open(from_file, "rb")
            from_file = discord.File(fp)
        if user: # only needed to specify when a DM is needed
            await user.send(content=data, file=from_file)
        else:
            output = await client.get_channel(channel).send(data, file=from_file)
        
    async def start_game(self, message):
        await self.direct_message(message.channel.id, data="New game starting, type `!join` to get in on it")
        self.games.append(OutLaugh(message))
        asyncio.run_coroutine_threadsafe(self.game(self.games[-1]), loop)
        print(repr(self.games))
    
    async def on_message(self, message):  # returns true if command is processed
        for item in self.games:
            await item.on_message(message)
        if message.author != self.user:  # ignore messages from the bot
            if message.content.startswith("default ") or message.content == "default":
                return False
            print(
                "message from {0.author} in {0.channel.id}: {0.content} ".format(message))
            built_in_commands = {
                "!move": self.command_move,
                "!start": self.start_game
                # "!connect": self.connect_to_voice
                # "!test_react": self.test_reaction
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
        await message.add_reaction(get_emoji(emoji))
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

    ##############
    # GAME STUFF #
    ##############
    
# TODO: implement proper reading of DMs and feeding into a main game
class OutLaugh:
    def __init__(self, message):
        self.f = open("questions_all.txt") # replace this with default questions file
        self.questions = self.f.readlines()
        self.max_players = 8
        self.parse_switches(message.content)
        self.players = []        # real players
        self.dummy_players = []  # fake players for testing
        self.pairs = []          # pairs of players
        self.question_queue = {} # questions for each player (by id), selected ahead of time
        self.answers = 0         # total number of answers received

    def parse_switches(switches):
        self.switches = re.split(" ", content)
        self.switches = self.switches[1:]
        self.guild_id = message.guild.id
        for index, item in enumerate(self.switches):
            if item == "--max_players":
                self.max_players = int(self.switches[index + 1])
            if item == "--dummy_players":
                for i in range(int(switches[index + 1])):
                    self.dummy_players.append(GamePlayer(i, i , True))

    async def on_message(self, message):
        if message.guild.id = self.guild_id:
            if message.author != self.user:
                print(message.author.id)
                if message.content == "!join":
                    if self.add_player(message.author):
                        await client.direct_message(message.channel.id, data="{0.name} has joined the game!".format(message.author))
                        print(repr(message.author.dm_channel))
                        await client.direct_message(user=message.author, data="you have joined the game!")
                        print(len(self.players))
                    else:
                        # TODO: make this send a non-generic message
                        await client.direct_message(message.channel.id, data="Either an error occured, you're already in the game, or there are too many players for you to join, {0.name}".format(message.author))
                if message.content == "!begin" and message.author == self.players[0]: # logic check to prevent a random person from starting the game
                    for dummy in self.dummy_players:
                        self.players.append(dummy)
                    if self.players < 4:
                        client.direct_message(message.channel, data="Not enough players")
                    else:
                        self.start_game()

    # returns true if able to add a new player
    def add_player(self, player):
        if len(self.players) < self.max_players:
            if player not in self.players:
                self.players.append(GamePlayer(player.id, player.name))
                return True
        return False
    
    def increment_answered(self):
        self.answers += 1
    
    # Runs the game
    # TODO: implement main game logic to start the game
    async def start_game(self):
        while not self.set_pairs():
            pass
        # Track users that have yet to answer questions.
        has_answered = self.pairs.copy()
        self.set_questions
        
        
    # Gets and removes a question from the list
    def get_question(self):
        question = random.choice(self.questions)
        self.questions.remove(question)
        return question
    
    def set_questions(self):
        for pair in self.pairs:
            question = get_question()
            for player in pair:
                self.question_queue[player.id] = asyncio.run_coroutine_threadsafe(Question(player, question))
    
    # Sets the pairs for the game. This is meant to be called in a while loop, as seen in start_game()
    # Returns True upon a successful configuration
    # Credit to AshEevee_ for coming up with this algorithm
    def set_pairs(self):
        players1 = self.players
        players2 = self.players.copy() # create new arrays for both player sets
        pairs = self.pairs = []
        for p1 in players1:
            p2 = random.choice(players2)
            if p1.id == p2.id:
                return False
            pair = [p1, p2]
            for p in self.pairs:
                if p[0].id == pair[1].id and p[1].id == pair[0].id:
                    return False
                pair = [p1, p2]
            players2.remove(p2)
            self.pairs.append(pair)
        return True

class Question(OutLaugh):
    def __init__(self, player, question):
        self.loop = asyncio.get_running_loop()
        self.ask_question(players, question)
        self.player = player
        self.answer = ""
        self.complete = False

    # TODO: Implement reading message
    async def on_message(self, message):
        if player.id == message.author.id:
            self.recv_answer(message)
    
    # upon receiving a an answer, add it to the answers dict
    def recv_answer(self, message):
        self.answer[self.player] = message.content
        return True

    def ask_question(self, players, question):
        

    def is_question_complete(self):
        if len(self.answers) == 2:
            return True
        return False

class GamePlayer:
    def __init__(self, in_id, name, is_dummy=False):
        self.id = in_id
        self.name = name
        self.is_dummy = is_dummy
        self.points = 0
    
    def add_points(self, num):
        self.points += 500 * num

loop = asyncio.get_event_loop()
client = DiscordBot()
client.run(clientdict["token"])
