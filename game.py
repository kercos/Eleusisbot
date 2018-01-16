# -*- coding: utf-8 -*-

import logging
from google.appengine.ext import ndb
import parameters
from datetime import datetime
import card

#------------------------
# GAME_VARIABLES KEYS
#------------------------
DEMO_MODE = 'demo_mode' # --> bool
GAME_HAND = 'game_hand' # --> int
GOD_ID = "god_id" # --> int
GOD_RULE = "god_rule" # --> str
STARTING_CARD = "starting_card" # --> str
PLAYERS_ID = 'players_id' # --> [player_id1, player_id2, ...]
PLAYERS_NAME = 'players_name' # --> { player_id1: string, player_id2: string, ... }
PLAYERS_CARDS = 'players_cards' # --> { player_id1: [c1, c2, ...], player_id2: [c1, c2, ...], ... }
PLAYERS_SCORES = 'players_scores' # --> { player_id1: [currentHand, total], player_id2: [currentHand, total], ...}
PLAYERS_HAS_BEEN_PROPHET = 'players_has_been_prophet' # --> [ player_id1, player_id2, ...]
PLAYERS_ELIMINATED = 'players_eliminated' # --> [ player_id1, player_id2, ...]
PLAYERS_ASK_TO_BE_A_PROPHET = 'players_ask_prophet' # --> { player_id1: bool, player_id2: bool, ...}
CURRENT_PROPHET = 'current_prophet' # --> player_id or None
TURN_PLAYER_INDEX = 'turn_player_id' # --> index of the player of current turn
CARDS_DECK = 'cards_deck' # --> [card1_str, card2_str, ...]
YEAR_COUNT = 'year_count' # --> int (incremented every accepted card)
ACCEPTED_CARDS = 'accepted_cards' # --> [card1_str, card2_str, ...]
REJECTED_CARDS = 'rejected_cards' # --> [ [ [c1_str, card2_str, ...], ... ], [...], ... ] # for each year a sequence of sequences
PROPOSED_CARDS = 'proposed_cards' # --> [ c1, c2, ... ] # per each column a sequence of sequences
CARDS_ON_TABLE = 'cards_on_table' # --> int
PROPHET_ACCEPTED_REJECTED_CARDS = 'prophet_accepted_rejected_cards' # --> [int, int]
LAST_PROPHET_DECISION = 'last_prophet_decision' # --> str

#------------------------
# Game class
#------------------------

class Game(ndb.Model):
    number_seats = ndb.IntegerProperty()
    public = ndb.BooleanProperty()
    game_variables = ndb.PickleProperty()
    last_mod = ndb.DateTimeProperty(auto_now=True)

    def resetOrDeleteGame(self):
        import person
        person.removeGameFromPeople(self.getPlayersId())
        if self.isPublic():
            self.resetGame()
        else:
            deleteGame(self)

    def resetGame(self):
        self.game_variables = {
            DEMO_MODE: False,
            GAME_HAND: 0,
            GOD_ID: None,
            GOD_RULE: '',
            STARTING_CARD: '',
            PLAYERS_ID: [],
            PLAYERS_NAME: {},
            PLAYERS_CARDS: {},
            PLAYERS_SCORES: {},
            PLAYERS_HAS_BEEN_PROPHET: [],
            PLAYERS_ELIMINATED: [],
            PLAYERS_ASK_TO_BE_A_PROPHET: {},
            CURRENT_PROPHET: None,
            TURN_PLAYER_INDEX: 0,
            CARDS_DECK: [],
            YEAR_COUNT: 0,
            ACCEPTED_CARDS: [],
            REJECTED_CARDS: [[]],
            PROPOSED_CARDS: [],
            CARDS_ON_TABLE: 0,
            PROPHET_ACCEPTED_REJECTED_CARDS: [0,0],
            LAST_PROPHET_DECISION: ''
        }
        self.put()

    def initGame(self, demoMode=False, put=True):
        for p_id in self.getPlayersId():
            self.game_variables[PLAYERS_SCORES][p_id] = [0,0]
        if demoMode:
            self.game_variables[DEMO_MODE] = True
        self.initNextHand(put=put)

    def restartCurrentHand(self, put=True):
        self.game_variables[GAME_HAND] -= 1
        self.initNextHand()

    def initNextHand(self, put=True):
        currentHand = self.game_variables[GAME_HAND]
        if not self.isDemoMode():
            self.game_variables[GOD_ID] = self.getPlayersId()[currentHand]
        self.game_variables[GAME_HAND] += 1
        self.game_variables[CARDS_DECK] = card.getDeckCardListStr(parameters.INITIAL_DECKS, shuffle=True)
        self.game_variables[PLAYERS_HAS_BEEN_PROPHET] = []
        self.game_variables[PLAYERS_ELIMINATED] = []
        self.game_variables[CURRENT_PROPHET] = None
        self.game_variables[TURN_PLAYER_INDEX] = currentHand
        self.game_variables[YEAR_COUNT] = 0
        self.game_variables[ACCEPTED_CARDS] = []
        self.game_variables[REJECTED_CARDS] = [[]]
        self.game_variables[PROPOSED_CARDS] = []
        self.game_variables[CARDS_ON_TABLE] = 0
        self.game_variables[PROPHET_ACCEPTED_REJECTED_CARDS] = [0, 0]
        for p_id in self.getPlayersId(excludingGod=True):
            self.game_variables[PLAYERS_ASK_TO_BE_A_PROPHET][p_id] = False
            if p_id == self.getGodPlayerId():
                self.game_variables[PLAYERS_CARDS][p_id] = []
            else:
                self.game_variables[PLAYERS_CARDS][p_id] = self.dialCardList(parameters.CARDS_PER_PLAYER)
        for score in self.game_variables[PLAYERS_SCORES].values():
            score[0] = 0 # set current hand scores to zero
        if put:
            self.put()

    def getHandNumber(self):
        return self.game_variables[GAME_HAND]

    def startGame(self):
        self.dialCardsToPlayers()
        starting_card = card.getCardFromRepr(self.game_variables[STARTING_CARD])
        number = starting_card.getIntNumber()
        self.setUpNextTurn(iterations=number)

    def allHandsHaveBeenPlayed(self):
        return self.number_seats == self.game_variables[GAME_HAND]

    def getFinalWinnerName(self):
        scoresDict = self.game_variables[PLAYERS_SCORES]
        p_id_winner = max(scoresDict.iterkeys(), key=lambda key: scoresDict[key][1])
        return self.getPlayerName(p_id_winner)

    def getGameRoomName(self):
        return self.key.id()

    def isPublic(self):
        return self.public

    def getCurrentNumberOfPlayers(self):
        return len(self.game_variables[PLAYERS_ID])

    def isGameExpired(self):
        diff_sec = (datetime.now() - self.last_mod).total_seconds()
        if self.getCurrentNumberOfPlayers()>0:
            return diff_sec > parameters.GAME_EXPIRATION_SECONDS
        return False

    def isDemoMode(self):
        return self.game_variables[DEMO_MODE]

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

    def getPlayersNames(self):
        return self.game_variables[PLAYERS_NAME]

    def setPlayerName(self, p_id, name):
        self.game_variables[PLAYERS_NAME][p_id] = name

    def setGodRule(self, rule):
        self.game_variables[GOD_RULE] = rule

    def getGodRule(self):
        return self.game_variables[GOD_RULE]

    def getGodPlayerId(self):
        return self.game_variables[GOD_ID]

    def getGodIdAndName(self):
        if self.isDemoMode():
            return None, "God"
        god_id = self.getGodPlayerId()
        return god_id, self.getPlayerName(god_id)

    def getSinglePlayerCards(self, p_id, emoji=False):
        cards = self.game_variables[PLAYERS_CARDS][p_id]
        if emoji:
            return [card.renderCardFromRepr(c) for c in cards]
        return cards

    def getCurrentPlayerCards(self, emoji=False):
        p_id = self.getCurrentPlayerId()
        return self.getSinglePlayerCards(p_id, emoji)

    def emptySinglePlayerCards(self, p_id):
        del self.game_variables[PLAYERS_CARDS][p_id][:]  # emty list

    def getPlayersCards(self):
        return self.game_variables[PLAYERS_CARDS]

    def getPlayerTurnIndex(self):
        return self.game_variables[TURN_PLAYER_INDEX]

    def getCurrentPlayerId(self):
        index = self.getPlayerTurnIndex()
        return self.game_variables[PLAYERS_ID][index]

    def getCurrentPlayerName(self):
        p_id = self.getCurrentPlayerId()
        return self.getPlayerName(p_id)

    def getCurrentPlayerIdAndName(self):
        p_id = self.getCurrentPlayerId()
        return p_id, self.getPlayerName(p_id)

    def getPlayerTurnName(self):
        return self.getPlayerName(self.getPlayerTurnIndex())

    def getPlayersEliminated(self):
        return self.game_variables[PLAYERS_ELIMINATED]

    def setCurrentPlayerEliminated(self):
        p_id = self.getCurrentPlayerId()
        return self.game_variables[PLAYERS_ELIMINATED].append(p_id)

    def areAllPlayersEliminated(self):
        remaining = self.number_seats - len(self.getPlayersEliminated()) -1 # god
        if self.getCurrentProphetId():
            remaining -= 1
        return remaining <= 0

    def getPlayerAskToBeAProphet(self, p_id):
        return self.game_variables[PLAYERS_ASK_TO_BE_A_PROPHET][p_id]

    def flipPlayerAskToBeAProphet(self, p_id):
        self.game_variables[PLAYERS_ASK_TO_BE_A_PROPHET][p_id] = not self.game_variables[PLAYERS_ASK_TO_BE_A_PROPHET][p_id]
        self.put()
        return self.game_variables[PLAYERS_ASK_TO_BE_A_PROPHET][p_id]

    def getCardsOnTableCount(self):
        return self.game_variables[CARDS_ON_TABLE]

    def increaseCardsOnTableCount(self, newCardsCount):
        self.game_variables[CARDS_ON_TABLE] += newCardsCount

    def getNumberOfPlayersStillInGame(self):
        return self.number_seats - len(self.getPlayersEliminated())

    def getPlayesWhoHaveBeenProphet(self):
        return self.game_variables[PLAYERS_HAS_BEEN_PROPHET]

    def setCurrentProphetId(self, p_id):
        self.game_variables[CURRENT_PROPHET] = p_id
        if p_id is not None:
            self.game_variables[PROPHET_ACCEPTED_REJECTED_CARDS] = [0,0]
            self.getPlayesWhoHaveBeenProphet().append(p_id)

    def getCurrentProphetId(self):
        return self.game_variables[CURRENT_PROPHET]

    def getCurrentProphetName(self):
        p_id = self.game_variables[CURRENT_PROPHET]
        return self.getPlayerName(p_id)

    def getCurrentProphetIdAndName(self):
        p_id = self.game_variables[CURRENT_PROPHET]
        p_name = self.getPlayerName(p_id)
        return p_id, p_name

    def getCurrentJudgeIdNameIsProphet(self):
        prophet_id = self.getCurrentProphetId()
        if prophet_id is not None:
            result = list(self.getCurrentProphetIdAndName())
            result.append(True)
            return result
        elif self.isDemoMode():
            return None, None, prophet_id
        result = list(self.getGodIdAndName())
        result.append(False)
        return result

    def getLastProphetDecision(self):
        return self.game_variables[LAST_PROPHET_DECISION]

    def setLastProphetDecision(self, input, put=True):
        self.game_variables[LAST_PROPHET_DECISION] = input
        if put:
            self.put()

    def cardsToSuddenDeath(self):
        if self.getCurrentProphetId():
            cardsSinceLastProphetStarted = sum(self.game_variables[PROPHET_ACCEPTED_REJECTED_CARDS])
            return parameters.CARDS_TO_SUDDEN_DEATH_PROPHET - cardsSinceLastProphetStarted
        return parameters.CARDS_TO_SUDDEN_DEATH_STANDARD - self.getCardsOnTableCount()

    def isSuddenDeath(self):
        return self.cardsToSuddenDeath()<=0

    def getNextStartingCard(self, put=True):
        starting_card = self.game_variables[STARTING_CARD]
        if starting_card:
            self.game_variables[CARDS_DECK].append(starting_card)
        selected = self.dialCardList(1)[0]
        self.game_variables[STARTING_CARD] = selected
        if put:
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
        self.acceptSingleCard(starting_card)

    def dialCardsToPlayers(self):
        for p_id in self.getPlayersId():
            if p_id != self.getGodPlayerId():
                self.game_variables[PLAYERS_CARDS][p_id] = self.dialCardList(parameters.CARDS_PER_PLAYER)

    def dialCardList(self, numberOfCards):
        deck = self.game_variables[CARDS_DECK]
        if len(deck)<numberOfCards:
            deck.extend(card.getDeckCardListStr(1, shuffle=True))
            #random.shuffle(deck)
        result = []
        for i in range(numberOfCards):
            result.append(deck.pop(0))
        return result

    def setUpNextTurn(self, iterations=1):
        exclude_ids = [self.getGodPlayerId(), self.getCurrentProphetId()]
        exclude_ids.extend(self.getPlayersEliminated())
        logging.debug("Setting up next turn. Exluding ids: {}".format(exclude_ids))
        number_of_players = self.getNumberOfSeats()
        index = self.getPlayerTurnIndex()
        for i in range(iterations):
            while True:
                index = (index + 1) % number_of_players
                p_id = self.getPlayersId()[index]
                if p_id not in exclude_ids:
                    logging.debug("Turn Player index={} id={}".format(index, p_id))
                    break
        self.game_variables[TURN_PLAYER_INDEX] = index
        self.put()

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
        p_id = self.getCurrentPlayerId()
        c = card.reprCardFromRender(card_emoji)
        return c in self.getSinglePlayerCards(p_id)

    def appendInProposedCardsAndRemoveFromHand(self, card_emoji, put=True):
        p_id = self.getCurrentPlayerId()
        c = card.reprCardFromRender(card_emoji)
        players_card = self.getSinglePlayerCards(p_id)
        if c not in players_card:
            return False
        players_card.remove(c)
        self.getProposedCards().append(c)
        if put:
            self.put()
        return True

    def returnProposedCardsToPlayer(self):
        p_id = self.getCurrentPlayerId()
        proposed_cards = self.getProposedCards()
        self.getSinglePlayerCards(p_id).extend(proposed_cards)
        self.emptyProposedCards()
        self.put()

    def returnLastProposedCardToPlayer(self):
        p_id = self.getCurrentPlayerId()
        proposed_cards = self.getProposedCards()
        lastProposed = proposed_cards.pop()
        self.getSinglePlayerCards(p_id).append(lastProposed)
        self.put()

    def getAcceptedCards(self):
        return self.game_variables[ACCEPTED_CARDS]

    def getRejectedCards(self):
        return self.game_variables[REJECTED_CARDS]

    def acceptProposedCards(self, prophetDecision=False, put=False):
        for c in self.getProposedCards():
            self.acceptSingleCard(c, prophetDecision)
        self.emptyProposedCards()
        if put:
            self.put()

    def acceptSingleCard(self, card, prophetDecision=False):
        self.getAcceptedCards().append(card)
        self.getRejectedCards().append([])
        self.increaseCardsOnTableCount(1)
        if prophetDecision:
            self.game_variables[PROPHET_ACCEPTED_REJECTED_CARDS][0] += 1

    def giveCardsToPlayerId(self, p_id, newCardsNumber):
        newCards = self.dialCardList(newCardsNumber)
        self.getSinglePlayerCards(p_id).extend(newCards)
        return newCards

    def rejectProposedCards(self, prophetDecision=False, getPenaltyCards = True, doubleCardsInPenalty = True):
        proposed_cards = list(self.getProposedCards()) #copy
        number_proposed_cards = len(proposed_cards)
        self.increaseCardsOnTableCount(len(proposed_cards))
        p_id = self.getCurrentPlayerId()
        self.getRejectedCards()[-1].append(proposed_cards)
        self.emptyProposedCards()
        if prophetDecision:
            self.game_variables[PROPHET_ACCEPTED_REJECTED_CARDS][1] += number_proposed_cards
        if getPenaltyCards:
            if doubleCardsInPenalty:
                newCardsNumber = 2 * number_proposed_cards
            else:
                newCardsNumber = number_proposed_cards
            newCards = self.giveCardsToPlayerId(p_id, newCardsNumber)
            return [card.renderCardFromRepr(c) for c in newCards]

    def overthrownProphetAndGivePenaltyCards(self):
        p_id = self.getCurrentProphetId()
        newCardsNumber = parameters.CARDS_PENALTY_PROPHET
        newCards = self.giveCardsToPlayerId(p_id, newCardsNumber)
        self.setCurrentProphetId(None)
        return [card.renderCardFromRepr(c) for c in newCards]

    def confirmNoPlay(self, put=False):
        p_id = self.getCurrentPlayerId()
        cards_number = len(self.getSinglePlayerCards(p_id))
        self.emptySinglePlayerCards(p_id)
        newCards_number = cards_number - parameters.CARDS_DISCOUNTED_ON_CORRECT_NO_PLAY
        if newCards_number > 0:
            self.giveCardsToPlayerId(p_id, newCards_number)
        if put:
            self.put()

    def rejectNoPlay(self, card_emoji, prophetDecision=False, put=False):
        p_id = self.getCurrentPlayerId()
        c = card.reprCardFromRender(card_emoji)
        players_card = self.getSinglePlayerCards(p_id)
        if c not in players_card:
            return None
        players_card.remove(c)
        self.acceptSingleCard(c, prophetDecision)
        newCards = self.giveCardsToPlayerId(p_id, parameters.CARDS_PENALTY_ON_INCORRECT_NO_PLAY)
        if put:
            self.put()
        return [card.renderCardFromRepr(c) for c in newCards]

    def checkIfCurrentPlayerCanBeProphet(self, checkIfAskedEnable, put):
        if self.getCurrentProphetId(): # there is still a prophet active
            return False
        p_id = self.getCurrentPlayerId()
        if p_id in self.getPlayersEliminated():
            return False
        if checkIfAskedEnable and not self.getPlayerAskToBeAProphet(p_id):
            return False
        if p_id in self.getPlayesWhoHaveBeenProphet():
            return False
        if self.getNumberOfPlayersStillInGame() < parameters.MIN_ALIVE_PLAYERS_FOR_PROPHET:
            return False
        if put:
            self.put()
        return True

    def checkIfCurrentPlayerHasNoCardsLeft(self):
        p_id = self.getCurrentPlayerId()
        return len(self.getSinglePlayerCards(p_id))==0

    def computeScores(self):
        logging.debug("Computing scores")
        SCORES_DICT = self.game_variables[PLAYERS_SCORES]
        for score in SCORES_DICT.values():
            # set current hand scores to zero
            score[0] = 0
        number_cards_players = [len(x) for x in self.getPlayersCards().values()]
        logging.debug("Players Cards: {}".format(number_cards_players))
        maxCardsHand = max(number_cards_players)
        logging.debug("maxCardsHand={}".format(maxCardsHand))
        for p_id in self.getPlayersId(excludingGod=True):
            cardsPlayer = len(self.getSinglePlayerCards(p_id))
            basePoints = maxCardsHand - cardsPlayer
            if cardsPlayer==0:
                basePoints += 4 # bonus for player who finished the cards
            SCORES_DICT[p_id][0] = basePoints
            logging.debug("Player id={} cardsPlayer={} basePoints={}".format(p_id, cardsPlayer, basePoints))
        prophet_id = self.getCurrentProphetId()
        if prophet_id:
            prophet_accepted, prophet_rejected = self.game_variables[PROPHET_ACCEPTED_REJECTED_CARDS]
            prophet_extra_points = prophet_accepted + 2 * prophet_rejected
            SCORES_DICT[prophet_id][0] += prophet_extra_points
        max_points = max([x[0] for x in SCORES_DICT.values()])
        if prophet_id:
            # check for exception in rule3 of point to God
            rec_sum = lambda x: sum(map(rec_sum, x)) if isinstance(x, list) else x
            total_cards = sum(ACCEPTED_CARDS) + rec_sum(self.game_variables[ACCEPTED_CARDS])
            cards_with_prophet = sum(self.game_variables[PROPHET_ACCEPTED_REJECTED_CARDS])
            cards_before_prophet = total_cards - cards_with_prophet
            logging.debug("total_cards={} cards_before_prophet={} cards_with_prophet={}".format(total_cards, cards_before_prophet, cards_with_prophet))
            double_cards_before_prophet = cards_before_prophet*2
            if double_cards_before_prophet < max_points:
                SCORES_DICT[self.getGodPlayerId()][0] = double_cards_before_prophet
                logging.debug("Exception of rule in assigning points to god: number of cards preceding the prophet less than highest score.")
            else:
                SCORES_DICT[self.getGodPlayerId()][0] = max_points
        else:
            SCORES_DICT[self.getGodPlayerId()][0] = max_points
        result_table = [['NAME', 'HAND', 'TOTAL']]
        for p_id in self.getPlayersId():
            player_scores = SCORES_DICT[p_id]
            player_scores[1] += player_scores[0]
            result_table.append([self.getPlayerName(p_id), str(player_scores[0]), str(player_scores[1])])
        return result_table


def gameExists(name):
    return Game.get_by_id(name) != None

def createGame(name, number_seats, demoMode=False, public=False, put=False):
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


def resetPublicGames():
    publicGames = Game.query(Game.public == True).fetch()
    for g in publicGames:
        g.resetGame()

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
