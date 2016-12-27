# -*- coding: utf-8 -*-

import logging
from google.appengine.ext import ndb
from google.appengine.api import urlfetch
import parameters
import requests
import headlines
import rss_parser
import utility
from datetime import datetime
from random import randint
from random import shuffle
import webapp2
import json
import card
import random

#------------------------
# GAME_VARIABLES KEYS
#------------------------
GOD_ID = "god_id" # --> int
GOD_RULE = "god_rule" # --> str
STARTING_CARD = "starting_card" # --> str
PLAYERS_ID = 'players_id' # --> [player_id1, player_id2, ...]
PLAYERS_NAME = 'players_name' # --> { player_id1: string, player_id2: string, ... }
PLAYERS_CARDS = 'players_cards' # --> { player_id1: string, player_id2: string, ... }
PLAYERS_SCORES = 'players_scores' # --> { player_id1: int, player_id2: int, ...}
PLAYERS_HAS_BEEN_PROPHET = 'players_has_been_prophet' # --> { player_id1: bool, player_id2: bool, ...}
TURN_COUNT = 'turn_count' # --> int (incremented every player's tourn)
TURN_PLAYER_INDEX = 'turn_player_id' # --> id of the player of current turn
CARDS_DECK = 'cards_deck' # --> [card1_str, card2_str, ...]
YEAR_COUNT = 'year_count' # --> int (incremented every accepted card)
ACCEPTED_CARDS = 'accepted_cards' # --> [card1_str, card2_str, ...]
REJECTED_CARDS = 'rejected_cards' # --> [ [ [c1_str, card2_str, ...], ... ], [...], ... ] # per each year a sequence of sequences
PROPOSED_CARDS = 'proposed_cards' # --> [ c1, c2, ... ] # per each year a sequence of sequences

#------------------------
# Game class
#------------------------

class Game(ndb.Model):
    number_seats = ndb.IntegerProperty()
    public = ndb.BooleanProperty()
    started = ndb.BooleanProperty()
    game_variables = ndb.PickleProperty()
    last_mod = ndb.DateTimeProperty(auto_now=True)

    def getGameRoomName(self):
        return self.key.id()

    def isPublic(self):
        return self.public

    def getCurrentNumberOfPlayers(self):
        return len(self.game_variables[PLAYERS_ID])

    def isGameExpired(self):
        diff_sec = (datetime.now() - self.last_mod).total_seconds()
        if self.started:
            return diff_sec > parameters.GAME_EXPIRATION_SECONDS_IN_GAME
        if self.getCurrentNumberOfPlayers()>0:
            return diff_sec > parameters.GAME_EXPIRATION_SECONDS_IN_WAITING_FOR_PLAYERS
        return False

    def getNumberOfSeats(self):
        return self.number_seats

    def areMorePlayersAccepted(self):
        return self.getCurrentNumberOfPlayers() < self.number_seats

    def remainingSeats(self):
        return self.number_seats - self.getCurrentNumberOfPlayers()

    def getPlayersId(self, excludingGod = False):
        if excludingGod:
            return [x for x in self.game_variables[PLAYERS_ID] if x!=self.getGodPlayerId()]
        return self.game_variables[PLAYERS_ID]

    def getPlayerName(self, p_id):
        return self.game_variables[PLAYERS_NAME][p_id]

    def setPlayerName(self, p_id, name):
        self.game_variables[PLAYERS_NAME][p_id] = name

    def setGodRule(self, rule):
        self.game_variables[GOD_RULE] = rule

    def getTournCount(self):
        return self.game_variables[TURN_COUNT]

    def getGodPlayerId(self):
        return self.getPlayersId()[0]

    def getGodPlayerIdAndName(self):
        god_id = self.getGodPlayerId()
        return god_id, self.getPlayerName(god_id)

    def getSinglePlayerCards(self, p_id, emoji=False):
        cards = self.game_variables[PLAYERS_CARDS][p_id]
        if emoji:
            return [card.renderCardFromRepr(c) for c in cards]
        return cards

    def emptySinglePlayerCards(self, p_id):
        del self.game_variables[PLAYERS_CARDS][p_id][:]  # emty list

    def getPlayersCards(self):
        return self.game_variables[PLAYERS_CARDS]

    def getPlayerTurnIndex(self):
        return self.game_variables[TURN_PLAYER_INDEX]

    def getPlayerTurnId(self):
        index = self.getPlayerTurnIndex()
        return self.game_variables[PLAYERS_ID][index]

    def getPlayerTurnIdAndName(self):
        playersTurnId = self.getPlayerTurnId()
        return playersTurnId, self.getPlayerName(playersTurnId)

    def getPlayerTurnName(self):
        return self.getPlayerName(self.getPlayerTurnIndex())

    def resetGame(self):
        self.game_variables = {
            GOD_RULE: '',
            STARTING_CARD: '',
            PLAYERS_ID: [],
            PLAYERS_NAME: {},
            PLAYERS_CARDS: {},
            PLAYERS_SCORES: {},
            PLAYERS_HAS_BEEN_PROPHET: {},
            TURN_COUNT: 0,
            TURN_PLAYER_INDEX: 0,
            CARDS_DECK: [],
            YEAR_COUNT: 0,
            ACCEPTED_CARDS: [],
            REJECTED_CARDS: [[]],
            PROPOSED_CARDS: []
        }
        self.started = False
        self.put()

    def initializeCardsDeck(self, put=True):
        self.game_variables[CARDS_DECK] = card.getDeckCardListStr(parameters.INITIAL_DECKS, shuffle=True)
        if put:
            self.put()

    def getNextStartingCard(self):
        starting_card = self.game_variables[STARTING_CARD]
        if starting_card:
            self.game_variables[CARDS_DECK].append(starting_card)
        selected = self.dialCardList(1)[0]
        self.game_variables[STARTING_CARD] = selected
        self.put()
        #logging.debug("Newly selected starting card: {}".format(selected))
        return card.renderCardFromRepr(selected)

    def getStartingCard(self, emoji=False):
        starting_card = self.game_variables[STARTING_CARD]
        if emoji:
            return card.renderCardFromRepr(starting_card)
        return starting_card

    def acceptStartingCard(self):
        starting_card = self.getStartingCard()
        self.getAcceptedCards().append(starting_card)
        self.getRejectedCards().append([])

    def startGame(self):
        self.initializeScores()
        self.dialCardsToPlayers()
        self.started = True
        starting_card = card.getCardFromRepr(self.game_variables[STARTING_CARD])
        number = starting_card.getIntNumber()
        self.setUpNextTurn(iterations=number)

    def initializeScores(self):
        for p_id in self.getPlayersId():
            self.game_variables[PLAYERS_SCORES][p_id] = 0
            if p_id != self.getGodPlayerId():
                self.game_variables[PLAYERS_CARDS][p_id] = self.dialCardList(parameters.CARDS_PER_PLAYER)

    def dialCardsToPlayers(self):
        for p_id in self.getPlayersId():
            if p_id != self.getGodPlayerId():
                self.game_variables[PLAYERS_CARDS][p_id] = self.dialCardList(parameters.CARDS_PER_PLAYER)

    def dialCardList(self, numberOfCards):
        deck = self.game_variables[CARDS_DECK]
        if len(deck)<numberOfCards:
            deck.append(card.getDeckCardListStr(1, shuffle=True))
            random.shuffle(deck)
        result = []
        for i in range(numberOfCards):
            result.append(self.game_variables[CARDS_DECK].pop(0))
        return result


    def setUpNextTurn(self, put=True, iterations=1):
        self.game_variables[TURN_COUNT] += 1
        self.game_variables[TURN_PLAYER_INDEX] = self.nextTurnPlayerIndex(iterations = iterations)
        if put:
            self.put()

    def nextTurnPlayerIndex(self, iterations=1):
        number_of_players = self.getNumberOfSeats()
        index = self.getPlayerTurnIndex()
        for i in range(iterations):
            index = (index + 1) % number_of_players
            if self.getGodPlayerId() == self.getPlayersId()[index]:
                index = (index + 1) % number_of_players
        return index

    def readyToStart(self):
        return len(self.getPlayersId()) == self.number_seats

    @ndb.transactional(retries=100, xg=True)
    def addPlayer(self, player, put=True):
        if self.areMorePlayersAccepted():
            self.getPlayersId().append(player.chat_id)
            self.setPlayerName(player.chat_id, player.getFirstName())
            player.setGameRoom(self.getGameRoomName())
            if put:
                self.put()
            return True
        return False

    def getProposedCards(self, emoji=False):
        proposed_cards = self.game_variables[PROPOSED_CARDS]
        if emoji:
            return [card.renderCardFromRepr(c) for c in proposed_cards]
        return proposed_cards

    def emptyProposedCards(self):
        del self.getProposedCards()[:]  # emty list

    def isValidCard(self, card_emoji):
        p_id = self.getPlayerTurnId()
        c = card.reprCardFromRender(card_emoji)
        return c in self.getSinglePlayerCards(p_id)

    def appendInProposedCardsAndRemoveFromHand(self, card_emoji):
        p_id = self.getPlayerTurnId()
        c = card.reprCardFromRender(card_emoji)
        players_card = self.getSinglePlayerCards(p_id)
        if c not in players_card:
            return False
        players_card.remove(c)
        self.getProposedCards().append(c)
        self.put()
        return True

    def returnProposedCardsToPlayer(self):
        p_id = self.getPlayerTurnId()
        proposed_cards = self.getProposedCards()
        self.getSinglePlayerCards(p_id).extend(proposed_cards)
        self.emptyProposedCards()
        self.put()

    def getAcceptedCards(self):
        return self.game_variables[ACCEPTED_CARDS]

    def getRejectedCards(self):
        return self.game_variables[REJECTED_CARDS]

    def acceptProposedCards(self, put=False):
        proposed_cards = self.getProposedCards()
        self.getAcceptedCards().extend(proposed_cards)
        for i in range(len(proposed_cards)):
            self.getRejectedCards().append([])
        self.emptyProposedCards()
        if put:
            self.put()

    def rejectProposedCardsAndGetPenalityCards(self, put=False):
        proposed_cards = list(self.getProposedCards()) #copy
        #logging.debug("rejecting cards: {}".format(proposed_cards))
        p_id = self.getPlayerTurnId()
        self.getRejectedCards()[-1].append(proposed_cards)
        newCardsNumber = 2 * len(proposed_cards)
        newCards = self.dialCardList(newCardsNumber)
        self.getSinglePlayerCards(p_id).extend(newCards)
        self.emptyProposedCards()
        if put:
            self.put()
        return [card.renderCardFromRepr(c) for c in newCards]

    def confirmNoPlay(self, put=False):
        p_id = self.getPlayerTurnId()
        cards_number = len(self.getSinglePlayerCards(p_id))
        self.emptySinglePlayerCards(p_id)
        newCards_number = cards_number - parameters.CARDS_DISCOUNTED_ON_CORRECT_NO_PLAY
        if newCards_number > 0:
            newCards = self.dialCardList(newCards_number)
            self.getSinglePlayerCards(p_id).extend(newCards)
        if put:
            self.put()

    def rejectNoPlay(self, card_emoji, put=False):
        p_id = self.getPlayerTurnId()
        c = card.reprCardFromRender(card_emoji)
        players_card = self.getSinglePlayerCards(p_id)
        if c not in players_card:
            return None
        players_card.remove(c)
        self.getAcceptedCards().append(c)
        self.getRejectedCards().append([])
        newCards = self.dialCardList(parameters.CARDS_PENALTY_ON_INCORRECT_NO_PLAY)
        self.getSinglePlayerCards(p_id).extend(newCards)
        if put:
            self.put()
        return newCards

    def checkIfCurrentPlayerHasWon(self):
        p_id = self.getPlayerTurnId()
        return len(self.getSinglePlayerCards(p_id))==0


def gameExists(name):
    return Game.get_by_id(name) != None

def createGame(name, number_seats, public=False, put=False):
    g = Game.get_by_id(name)
    if g == None:
        g = Game(id=name)
        g.number_seats = number_seats
        g.public = public
        g.resetGame()
        if put:
            g.put()
        return g
    return None

def getGame(name):
    return Game.get_by_id(name)

def deleteGame(game):
    game.key.delete()

#########

def populatePublicGames():
    for game, info in parameters.PUBLIC_GAME_ROOMS_INFO.iteritems():
        createGame(game, info['PLAYERS'], public=True, put=True)

def deleteAllPrivateGames():
    create_futures = ndb.delete_multi_async(
        Game.query(Game.public==False).fetch(keys_only=True)
    )
    ndb.Future.wait_all(create_futures)

def deleteAllGames():
    create_futures = ndb.delete_multi_async(
        Game.query().fetch(keys_only=True)
    )
    ndb.Future.wait_all(create_futures)

def getGameNames():
    return [x.getGameRoomName() for x in Game.query().fetch()]
