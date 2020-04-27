import asyncio
import sys
import random
import copy

class OutLaugh():
    def __init__(self):
        # self.loop = asyncio.get_running_loop()
        self.players = []
        # self.f = open("questions.txt")
        # self.questions = self.f.readlines()
        # self.f.close()
        # self.user = user
        self.pairs = []
        self.deny_players = []
        # print(repr(self.loop))
    
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
                self.players.append(player)
                return True
        return False
    
    # TODO: implement main game logic to start the game
    # TODO: implement swap_player() to ensure that no player is left without a pair
    def start_game(self):
        print(random.choice(self.players))
        for i in range(len(self.players)):
            pair = self.get_pair(self.players)
            self.pairs.append(pair)
        # while len(self.deny_players) == len(self.players) - 1:
        #     players = []
        #     for player in self.players:
        #         players.append(player)
        #     for player in self.deny_players:
        #         players.remove(player)
        #     player = players[0]
        for item in self.deny_players:
            print(item.id)
        pairs_disp = []
        for item in self.pairs:
            player_out = []
            for player in item:
                player_out.append(player.id)
            pairs_disp.append(player_out)
        print(pairs_disp)

    def ensure_distribution(self, pair):
        player1_count = 0
        player2_count = 0
        for item in self.pairs:
            for index, player in enumerate(pair):
                if player in item and index == 0:
                    player1_count += 1
                if player in item and index == 1:
                    player2_count += 1
        if player1_count == 2 and player2_count < 2:
            if pair[0] not in self.deny_players:
                self.deny_players.append(pair[0])
            return [pair[0]]
        if player1_count < 2 and player2_count == 2:
            if pair[1] not in self.deny_players:
                self.deny_players.append(pair[1])
            return [pair[1]]
        if player1_count == 2 and player2_count == 2:
            if pair[0] not in self.deny_players:
                self.deny_players.append(pair[0])
            if pair[1] not in self.deny_players:
                self.deny_players.append(pair[1])
            return pair
        else:
            return False

    def get_question(self):
        question = random.choice(self.questions)
        self.questions.remove(question)
        return question
    
    # return a list of players that need to be swapped, or False if none need to be swapped
    def get_pair(self, players, player1=None, player2=None):
        if not player1 and not player2:
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
            while player1 == player2:
                player2 = random.choice(players)
            distrib = self.ensure_distribution([player1, player2])
            print(len(self.deny_players))
            print(len(self.players))
            if len(self.deny_players) == len(self.players) - 1:
                players = copy.deepcopy(self.players)
                for player in self.deny_players:
                    if player in players:
                        players.remove(player)
                player_deny = random.choice(self.deny_players)
                self.deny_players.remove(player_deny)
                self.swap_player(player1=player_deny, player2=players[0])
        print([player1.id, player2.id])
        return [player1, player2]

    def swap_player(self, player1, player2):
        for p1, p2 in self.pairs:
            if p1 == player1:
                p1 = player2
                # if player1 in self.deny_players:
                pair_to_remove = [p1, p2]
                for item in self.deny_players:
                    print(item.id)
                print(player1.id)
                print("denied player removed {}".format(player1.id))
        self.pairs.remove(pair_to_remove)
        self.pairs.append([p1, player1])

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

class GamePlayer:
    def __init__(self, in_id, name):
        self.id = in_id
        self.name = name
        self.points = 0
    
    def add_points(self, num):
        self.points += 500 * num

while True:
    test = OutLaugh()
    for i in range(int(4)):
        test.add_player(GamePlayer(i, i))
    
    
    test.start_game()