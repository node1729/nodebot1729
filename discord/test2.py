import asyncio
import random
import copy

class OutLaugh():
    def __init__(self, max_players=8):
        self.max_players = max_players
        self.players = []
        self.f = open("questions_all.txt")
        self.questions = self.f.readlines()
        self.pairs = []
    
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
    def add_player(self, player, max_players=8):
        if len(self.players) < max_players:
            if player not in self.players:
                self.players.append(player)
                return True
        return False
    
    # TODO: implement main game logic to start the game
    def start_game(self):
        while not self.set_pairs():
            pass
        pairs_disp = []            
        for item in self.pairs:
            player_out = []
            for player in item:
                player_out.append(player.id)
            pairs_disp.append(player_out)
        print(pairs_disp)
        # for pair in self.pairs:
            # Question.ask_question()

    def get_question(self):
        question = random.choice(self.questions)
        self.questions.remove(question)
        return question
    
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

# while True:
while True:
    test = OutLaugh()
    for i in range(3):
        test.add_player(GamePlayer(i, i))
    test.start_game()