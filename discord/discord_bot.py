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
    async def direct_message(self, channel=None, user=None, data=None, from_file=None, is_player=False):
        if from_file:
            fp = open(from_file, "rb")
            from_file = discord.File(fp)
        if user: # only needed to specify when a DM is needed
            if is_player:
                user = user.player
                # if not user.is_dummy:
            await user.send(content=data, file=from_file)
        else:
            output = await client.get_channel(channel).send(data, file=from_file)

    # spawns a game
    async def start_game(self, message):
        for item in self.games:
            if item.channel == message.channel.id:
                return False
        await self.direct_message(message.channel.id, data="New game starting, type `!join` to get in on it you lazy fucker")
        self.games.append(OutLaugh(message))
        asyncio.run_coroutine_threadsafe(self.game(self.games[-1]), loop)
        print(repr(self.games))
        return True    
    # async def on_reaction_add(self, reaction, user):
    #     for item in self.games:
    #         await item.on_reaction_add(reaction, user)

    async def on_message(self, message):  # returns true if command is processed
        for item in self.games:
            await item.on_message(message)
        if message.author != self.user:  # ignore messages from the bot
            if message.content.startswith("default ") or message.content == "default":
                return False
            print("message from {0.author} in {0.channel.id}: {0.content} ".format(message))
            built_in_commands = {
                "!move": self.command_move,
                "!start": self.start_game
                # "!connect": self.connect_to_voice
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
    
    async def game(self, GAME):
        return await GAME
    

# TODO: Implement voting properly
# TODO: see if __init__() can be condensed at all
class OutLaugh:
    def __init__(self, message):
        self.f = open("questions_all.txt") # replace this with default questions file
        self.questions = self.f.readlines()
        self.max_players = 8
        self.channel = message.channel.id
        self.players = []        # real players (list of GamePlayer)
        self.dummy_players = []  # fake players for testing (list of GamePlayer)
        self.pairs = []          # pairs of players (list of lists of GamePlayer)
        self.question_queue = [] # questions for each player (by id), selected ahead of time (list of lists of GamePlayer)
        self.answered = []       # answered questions
        self.reacted = []        # people who have reacted
        self.exclude = []        # people who cannot react
        self.broadcast = False   # if true, send messages to main channel where game is running
        self.started = False     # if true, the game is active
        self.waiting_for_votes = False
        self.voted = []          # voted responses, includes player and vote decision
        self.parse_switches(message)

    # extra settings
    def parse_switches(self, switches):
        self.switches = re.split(" ", switches.content)
        self.switches = self.switches[1:]
        self.guild_id = switches.guild.id
        for index, item in enumerate(self.switches):
            if item == "--max_players":
                self.max_players = int(self.switches[index + 1])
            if item == "--dummy_players":
                for i in range(int(self.switches[index + 1])):
                    self.dummy_players.append(GamePlayer(i, i, None, is_dummy=True))
            if item == "--broadcast":
                self.broadcast = True

    # gets the next question if the user has not answered two questions
    async def check_question(self, message=None, from_dummy=False):
        ask_next_question = False
        for questions in self.question_queue:
            for question in questions:
                if from_dummy:
                    if from_dummy[0] == question.player.id and question.answer:
                        print("dummy answer")
                        self.answered[question.id].append(question) # add question to the array in which it belongs
                        self.question_queue[question.id].remove(question) # question no longer belongs here
                        ask_next_question = True
                elif question.player.id == message.author.id and question.answer:
                    print("player answer")
                    self.answered[question.id].append(question) # add question to the array in which it belongs
                    self.question_queue[question.id].remove(question) # question no longer belongs here
                    ask_next_question = True
        if ask_next_question: 
            question_asked = False
            for questions in self.question_queue:
                for question in questions:
                    if not question_asked:
                        if from_dummy:
                            if from_dummy[0] == question.player.id:
                                print("dummy ask")
                                await question.ask_question()
                                question_asked = True
                        elif question.player.id == message.author.id:
                            print("player ask")
                            await question.ask_question()
                            question_asked = True

    # handles adding players and beginning the game
    async def on_message(self, message):
        if message.author != client.user:
            players_asked = [] # players to not ask again
            for questions in self.question_queue:
                for question in questions:
                    if question.player.id not in players_asked:
                        await question.on_message(message)
                    players_asked.append(question.player.id)
            
            # pass received message to Vote array 
            for vote in self.voted:
                await vote.on_message(message)
            
            if message.content == "!join":
                if self.add_player(message):
                    await client.direct_message(message.channel.id, data="{0.name} has joined the game!".format(message.author))
                    await client.direct_message(user=message.author, data="you have joined the game!")
                else:
                    # TODO: make this send a non-generic message
                    await client.direct_message(message.channel.id, data="Either an error occured, you're already in the game, or there are too many players for you to join, {0.name}".format(message.author))
            
            if message.content == "!begin" and message.author.id == self.players[0].id: # logic check to prevent a random person from starting the game
                print("attempting to begin game")
                for dummy in self.dummy_players: # dump dummy players into main players count
                    self.players.append(dummy)
                if len(self.players) < 4:
                    await client.direct_message(message.channel, data="Not enough players")
                else:
                    await self.start_game()
            if self.started and not self.waiting_for_votes:
                await self.check_question(message)

    # returns true if able to add a new player
    def add_player(self, message):
        if len(self.players) < self.max_players:
            if message.author not in self.players:
                self.players.append(GamePlayer(message.author.id, message.author.name, message))
                return True
        return False

    def is_complete(self):
        print(self.answered)
        for item in self.answered:
            if len(item) != 2:
                print(item)
                return False
        return True
    
    def voting_complete(self):
        if len(self.voted) == len(self.players) - 2:
            return True
        return False

    # clean up after each round
    def clean_up(self):
        print("clean up called")
        self.answers = 0
        self.answered = []
        self.pairs = []

    # combines two questions into a readable response
    def construct_message(self, questions):
        message = questions[0].question + "\r\n"
        index = 1
        for item in questions:
            message += str(index) + ": " + item.answer + "\r\n"
            index += 1
        return message
    
    # def construct_result(self, questions):
        

    # Runs the game
    # TODO: implement main game logic to start the game
    async def start_game(self):
        for player in self.players:
            self.answered.append([]) # create an array for each answer pair
        self.started = True
        can_advance = True
        curr_round = 1
        while curr_round < 4:
        # for i in range(1,4):
            if can_advance:
                can_advance = False
                while not self.set_pairs():
                    pass
                self.set_questions()

                # display player ids
                disp_players = []
                for pair in self.pairs:
                    disp_players.append([])
                    for player in pair:
                        disp_players[-1].append(player.id)
                print(repr(disp_players))

                for questions in self.question_queue:
                    question_asked = False
                    for question in questions:
                        if not question_asked:
                            await question.ask_question()
                            print("asking question in main question loop")
                            question_asked = True
                        if question.player.is_dummy:
                            await self.check_question(message=None, from_dummy=[question.player.id])
                            await self.check_question(message=None, from_dummy=[question.player.id])
            else:
                await asyncio.sleep(1)
                if self.is_complete():
                    random.shuffle(self.answered) # randomize list of answers
                    # start receiving messages
                    for pair in self.answered:
                        self.exclude = [] # exclude these players from voting
                        for answer in pair: # players to exclude from reacting, by id
                            self.exclude.append(answer.player.id) 
                        for player in self.players:
                            if player.id in self.exclude:
                                await client.direct_message(user=player.player, data="You answered in this question, just hang tight, a vote here doesn't count")
                            if not player.is_dummy:
                                await client.direct_message(user=player.player, data=self.construct_message(pair)) # send to all players
                            if self.broadcast: # send to main channel, useful for spectators
                                await client.direct_message(channel=self.channel, data=self.construct_message(pair))
                            if player.id not in self.exclude: # send to players that can vote
                                await client.direct_message(user=player.player, data="Vote with either `1` or `2`")                        

                    can_advance = True                
                    # clean up after each round
                    self.clean_up()
        # stop the game
        self.started = False

    # Gets and removes a question from the list
    def get_question(self):
        question = random.choice(self.questions)
        self.questions.remove(question)
        return question
    
    # Sets all the questions and creates a queue of questions to ask each player.
    # No two players see the same first question
    # No two players see the same second question
    def set_questions(self):
        for index, pair in enumerate(self.pairs):
            print(index)
            print(pair)
            question = self.get_question()
            self.question_queue.append([])
            print(question)
            for player in pair:
                self.question_queue[-1].append(Question(player, question, index))
                # print(index)
        # print(len(self.question_queue))

    # Sets the pairs for the game. This is meant to be called in a while loop, as seen in start_game()
    # Returns True upon a successful configuration
    # Credit to AshEevee_ for coming up with this algorithm
    def set_pairs(self):
        players1 = self.players
        players2 = self.players.copy() # create new arrays for both player sets
        pairs = self.pairs = []
        for p1 in players1:
            p2 = random.choice(players2)
            if p1.id == p2.id: # player cannot be itself
                return False
            pair = [p1, p2]
            for p in self.pairs:
                if p[0].id == pair[1].id and p[1].id == pair[0].id: # prevents two identical pairs from existing
                    return False
                pair = [p1, p2]
            players2.remove(p2)
            self.pairs.append(pair)
        return True

    async def create_question(self, QUESTION):
        return await QUESTION

    async def create_timer(self, TIMER):
        return await TIMER

class Vote(OutLaugh):
    def __init__(self, player):
        self.player = player
        self.vote = None
        self.loop = asyncio.get_running_loop()
        if player.is_dummy:
            self.vote = 0

    async def on_message(self, message):
        if message.author.id == self.player.id and super().started and player.id not in super().exclude:
            try:
                self.vote = int(message.content) - 1
                if self.vote not in range(2):
                    raise ValueError()
            except ValueError:
                await client.direct_message(user=player, data="Invalid Response")

class Question(OutLaugh):
    def __init__(self, player, question, question_id):
        self.id = question_id
        self.question = question
        self.loop = asyncio.get_running_loop()
        self.player = player
        self.answer = ""
    
    # TODO: Implement reading message
    async def on_message(self, message):
        if self.player.id == message.author.id:
            print("Attempting to receive answer from {}".format(message.author.name))
            await self.recv_answer(message)

    # upon receiving a an answer, add it to the answers dict
    async def recv_answer(self, message=None):
        if self.player.is_dummy:
            self.answer = str(self.player.id)
        else:
            self.answer = message.content
        print(repr(self.answer))
        print("Player " + str(self.player.id) + " Finished with question " + str(self.id))
        return True

    async def ask_question(self):
        if not self.player.is_dummy:
            await client.direct_message(user=self.player, data=self.question, is_player=True)
        else:
            await self.recv_answer()
        return True

class GamePlayer:
    def __init__(self, in_id, name, message, is_dummy=False):
        self.id = in_id
        self.name = name
        self.player = None
        self.is_dummy = is_dummy
        if not self.is_dummy:
            self.player = message.author
        self.points = 0

    def add_points(self, num, total):
        self.points += round(1000 * (num / total))
        

loop = asyncio.get_event_loop()
client = DiscordBot()
client.run(clientdict["token"])
