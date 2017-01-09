# -*- coding: utf-8 -*-

import card
import logging
import random

def all(startCardRepr):
    return True

def modulo13(number):
    number = number % 13
    while number<=0:
        number += 13
    return number

def plusMinusOne(sequenceRepr, newCardRepr):
    lastInSequence = card.getCardFromRepr(sequenceRepr[-1])
    newCard = card.getCardFromRepr(newCardRepr)
    newCardIntNumbet = newCard.getIntNumber()
    lastInSequenceIntNumber = lastInSequence.getIntNumber()
    lastInSequenceIntNumberPlusOne = modulo13(lastInSequenceIntNumber+1)
    lastInSequenceIntNumberMinusOne = modulo13(lastInSequenceIntNumber-1)
    return newCardIntNumbet in [lastInSequenceIntNumberPlusOne, lastInSequenceIntNumberMinusOne]

def alternationOfColors(sequenceRepr, newCardRepr):
    lastInSequence = card.getCardFromRepr(sequenceRepr[-1])
    newCard = card.getCardFromRepr(newCardRepr)
    lastInSequenceColor = lastInSequence.getColor()
    newCardColor = newCard.getColor()
    return newCardColor != lastInSequenceColor

def sameSuitOrSameNumber(sequenceRepr, newCardRepr):
    lastInSequence = card.getCardFromRepr(sequenceRepr[-1])
    newCard = card.getCardFromRepr(newCardRepr)
    return newCard.suit == lastInSequence.suit or newCard.number == lastInSequence.number

def plusOnePlusTwo(sequenceRepr, newCardRepr):
    lastInSequence = card.getCardFromRepr(sequenceRepr[-1])
    newCard = card.getCardFromRepr(newCardRepr)
    lastInSequenceIntNumber = lastInSequence.getIntNumber()
    newCardIntNumbet = newCard.getIntNumber()
    toSum = 1 if len(sequenceRepr)%2==1 else 2
    lastInSequenceIntNumberPlus = modulo13(lastInSequenceIntNumber + toSum)
    return newCardIntNumbet == lastInSequenceIntNumberPlus

def fourSuits(sequenceRepr, newCardRepr):
    newCard = card.getCardFromRepr(newCardRepr)
    first4Cards = card.getCardFromReprList(sequenceRepr[:4])
    #logging.debug("first 4 cards: {}".format(first4Cards))
    if len(first4Cards)<4:
        for c in first4Cards:
            if newCard.suit == c.suit:
                return False
        return True
    pos = len(sequenceRepr) % 4
    return newCard.suit == first4Cards[pos].suit

def blackOnOddRedOnEven(sequenceRepr, newCardRepr):
    lastInSequence = card.getCardFromRepr(sequenceRepr[-1])
    newCard = card.getCardFromRepr(newCardRepr)
    lastWasEven = (lastInSequence.getIntNumber() % 2) == 0
    cardColor = newCard.getColor()
    return lastWasEven and cardColor==card.RED or not lastWasEven and cardColor==card.BLACK

def grEqOnRedLowEqOnBlack(sequenceRepr, newCardRepr):
    lastInSequence = card.getCardFromRepr(sequenceRepr[-1])
    newCard = card.getCardFromRepr(newCardRepr)
    lastWasRed = lastInSequence.getColor() == card.RED
    newCardNumber = newCard.getIntNumber()
    lastCardNumber = lastInSequence.getIntNumber()
    if newCardNumber == lastCardNumber:
        return True
    grPrevious = newCardNumber > lastCardNumber
    return grPrevious and lastWasRed or not grPrevious and not lastWasRed

def absDiffLowEqThree(sequenceRepr, newCardRepr):
    lastInSequence = card.getCardFromRepr(sequenceRepr[-1])
    newCard = card.getCardFromRepr(newCardRepr)
    newCardNumber = newCard.getIntNumber()
    lastCardNumber = lastInSequence.getIntNumber()
    return abs(newCardNumber-lastCardNumber)<=3

def alternationParity(sequenceRepr, newCardRepr):
    lastInSequence = card.getCardFromRepr(sequenceRepr[-1])
    newCard = card.getCardFromRepr(newCardRepr)
    lastWasEven = (lastInSequence.getIntNumber() % 2) == 0
    cardIsEven = (newCard.getIntNumber() % 2) == 0
    return lastWasEven != cardIsEven

def sameSuitOneBeforeLastOrSameNumberLast(sequenceRepr, newCardRepr):
    lastInSequence = card.getCardFromRepr(sequenceRepr[-1])
    newCard = card.getCardFromRepr(newCardRepr)
    if lastInSequence.getIntNumber() == newCard.getIntNumber():
        return True
    if len(sequenceRepr)==1:
        return False
    oneBeforeLastInSequence = card.getCardFromRepr(sequenceRepr[-2])
    return oneBeforeLastInSequence.suit == newCard.suit

RULE_TABLES = {
    'ALTERNATION_COLORS': {
        'rule_description': 'Alternation of colors ([RED,] BLACK, RED, BLACK, ...).',
        'starter_function': all,
        'acceptance_function': alternationOfColors,
    },
    'PLUS_MINUS_ONE': {
        'rule_description': 'The card played must be one more or less than the number of the last accepted card.',
        'starter_function': all,
        'acceptance_function': plusMinusOne,
    },
    'SAME_SUIT_OR_SAME_NUMBER': {
        'rule_description': 'The card played must be either of the same suit or the same value as the last accepted card.',
        'starter_function': all,
        'acceptance_function': sameSuitOrSameNumber,
    },
    'FOUR_SUITS': {
        'rule_description': 'First 4 cards should be of different suits, and the sequence should repeat thereafter.',
        'starter_function': all,
        'acceptance_function': fourSuits,
    },
    'PLUS_ONE_PLUS_TWO': {
        'rule_description': 'The card played must be one more or two more than the last accepted card in sequence.',
        'starter_function': all,
        'acceptance_function': plusOnePlusTwo,
    },
    'BLACK_ON_ODD_RED_ON_EVEN': {
        'rule_description': 'If the last legally played card was odd, play a black card. Otherwise play a red one.',
        'starter_function': all,
        'acceptance_function': blackOnOddRedOnEven,
    },
    'GREQ_ON_RED_LOWEQ_ON_BLACK': {
        'rule_description': 'If the last legally played card was black, play a card of equal or higher value. If the last card played was red, play a card of equal or lower value.',
        'starter_function': all,
        'acceptance_function': grEqOnRedLowEqOnBlack,
    },
    'ABS_DIFF_LOWEQ_THREE': {
        'rule_description': 'The card played must be at most three number higher or lower than the last legally played card..',
        'starter_function': all,
        'acceptance_function': absDiffLowEqThree,
    },
    'ALTERNATION_PARITY': {
        'rule_description': 'Alternation of parity ([EVEN,] ODD, EVEN, ODD, ... ).',
        'starter_function': all,
        'acceptance_function': alternationParity,
    },
    'SAME_SUIT_ONE_BEFORE_LAST_OR_SAME_NUMBER_LAST': {
        'rule_description': 'The card played must be of the suit of the one before the last legally played card or the same number of the last one.',
        'starter_function': all,
        'acceptance_function': sameSuitOneBeforeLastOrSameNumberLast,
    }
}

LEVELS_RULE_KEY = {
    1: 'ALTERNATION_COLORS',
    2: 'PLUS_MINUS_ONE',
    3: 'SAME_SUIT_OR_SAME_NUMBER',
    4: 'ALTERNATION_PARITY',
    5: 'FOUR_SUITS',
    6: 'PLUS_ONE_PLUS_TWO',
    7: 'BLACK_ON_ODD_RED_ON_EVEN',
    8: 'GREQ_ON_RED_LOWEQ_ON_BLACK',
    9: 'ABS_DIFF_LOWEQ_THREE',
    10: 'SAME_SUIT_ONE_BEFORE_LAST_OR_SAME_NUMBER_LAST'
}

def getRuleDescription(rule_key):
    return RULE_TABLES[rule_key]['rule_description']

def getMaxLevel():
    return len(LEVELS_RULE_KEY)

def initializeDemoGame(g, level):
    if level in LEVELS_RULE_KEY.keys():
        rule_key = LEVELS_RULE_KEY[level]
    else:
        rule_key = random.choice(LEVELS_RULE_KEY.values())
    logging.debug("Demo mode - selecting rule: {}".format(rule_key))
    table = RULE_TABLES[rule_key]
    g.setGodRule(rule_key)
    g.initGame(demoMode=True, put=False)
    starter_function = table['starter_function']
    while True:
        start_card = g.getNextStartingCard(put=False)
        if starter_function(start_card):
            g.acceptStartingCard()
            break
    g.startGame()


def areProposedCardsAccepted(g):
    rule_key = g.getGodRule()
    table = RULE_TABLES[rule_key]
    acceptence_function = table['acceptance_function']
    proposedCards = g.getProposedCards()
    acceptedCardsCopy = list(g.getAcceptedCards())
    for pc in proposedCards:
        if acceptence_function(acceptedCardsCopy, pc):
            acceptedCardsCopy.append(pc)
        else:
            return False
    return True

def selectOneAcceptedCard(g):
    rule_key = g.getGodRule()
    table = RULE_TABLES[rule_key]
    acceptence_function = table['acceptance_function']
    acceptedCards = g.getAcceptedCards()
    player_cards_copy = list(g.getCurrentPlayerCards())
    random.shuffle(player_cards_copy)
    for pc in player_cards_copy:
        if acceptence_function(acceptedCards, pc):
            return card.renderCardFromRepr(pc)
    return None

'''
pokerHandWithPrevious()
sum(PROPOSED,LAST,LLAST)%2==1
(isRed(PROPOSED) && (isFigure(PROPOSED) || getNumber(PROPOSED)==1)) || (isBlack(PROPOSED) && !isFigure(PROPOSED) && getNumber(PROPOSED)!=1)
'''