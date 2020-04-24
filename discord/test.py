import asyncio
import random

class OutLaugh():
    def __init__(self, user):
        self.loop = asyncio.get_running_loop()
        self.players = {}
        self.f = open("questions.txt")
        self.questions = self.f.readlines()
        self.f.close()
        self.user = user
        self.pairs = []
        self.deny_players = []
        print(repr(self.loop))
    
    # async def on_message(self, message):
    #     if message.author != self.user:
    #         print(message.author.id)
    #         if message.content == "!join":
    #             if self.add_player(message.author):
    #                 await client.direct_message(message.channel.id, data="{0.name} has joined the game!".format(message.author))
    #                 print(repr(message.author.dm_channel))
    #                 await client.direct_message(user=message.author, data="you have joined the game!")
    #                 print(len(self.players))
    #             else:
    #                 await client.direct_message(message.channel.id, data="Either an error occured, you're already in the game, or there are too many players for you to join, {0.name}".format(message.author))
    #         if message.content == "!begin" and message.author == self.players[0]:
    #             self.start_game()

    # returns true if able to add a new player
    def add_player(self, player):
        if len(self.players) < 8:
            if player not in self.players:
                self.players[player] = GamePlayer(player)
                return True
        return False
    
    # TODO: implement main game logic to start the game
    # TODO: implement swap_player() to ensure that no player is left without a pair
    def start_game(self):
        for i in range(len(self.players)):
            pair = self.get_pair(self.players)
            self.pairs.append(pair)
        while len(self.deny_players) == len(self.players) - 1:
            players = []
            for player in self.players:
                players.append(player)
            for player in self.deny_players:
                players.remove(player)
            player = players[0]

    def ensure_distribution(self, pair):
        player1_count = 0
        player2_count = 0
        for item in self.pairs:
            for player in pair:
                if player[0] in item:
                    player1_count += 1
                if player[1] in item:
                    player1_count += 1
        if player1_count == 2 and player2_count < 2:
            return [player1]
        if player1_count < 2 and player2_count == 2:
            return [player2]
        if player1_count == 2 and player2_count == 2:
            return [player1, player2]
        else:
            return False

    def get_question(self):
        question = random.choice(self.questions)
        self.questions.remove(question)
        return question
    
    # return a list of players that need to be swapped, or False if none need to be swapped
    def get_pair(self, players, keep_player=None):
        player1 = random.choice(players)
        player2 = random.choice(players)
        while player2 == player1:
            player2 = random.choice(players)
        distrib = self.ensure_distribution([player1, player2])
        while distrib:
            if player1 in distrib:
                player1 = random.choice(players)
            if player2 in distrib:
                player2 = random.choice(players)
            distrib = self.ensure_distribution([player1, player2])
        return [player1, player2]
            

class Question(OutLaugh):
    def __init__(self, question, players):
        for player in players:
            direct_message(player, data=question)
        self.player1, self.player2 = players
        self.answers = {}
    
    def recv_question(self, user, answer):
        self.answers[user] = answer
        return True
    
    def ask_question(self, players, question):
        for user in players:
            client.direct_message(user=user, content=question)
        return True



class Player():
    def __init__(self, in_id, name):
        self.id = in_id
        self.name = name

class GamePlayer:
    def __init__(self, player):
        self.id = player.id
        self.name = player.name
        self.points = 0
    
    def add_points(self, num):
        self.points += 500 * num
        
test = OutLaugh()
for i in range(8):
    test.add_player(Player(i, i))
