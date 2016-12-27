# -*- coding: utf-8 -*-

import random
import icons

CLUBS, HEARTS, SPADES, DIAMONDS = 'CLUBS', 'HEARTS', 'SPADES', 'DIAMONDS'
SUITS = [SPADES, CLUBS, HEARTS, DIAMONDS]

NUMBERS = ['1','2','3','4','5','6','7','8','9','10','J','Q','K']

SUIT_CHAR = lambda suit: suit[0]
NUMBER_CHAR = lambda number: 'X' if number=='10' else number
CHAR_NUMBER = lambda char: '10' if char=='X' else char

CHAR_SUIT = {
    'C': 'CLUBS',
    'H': 'HEARTS',
    'S': 'SPADES',
    'D': 'DIAMONDS'
}


class Card():
    number = str
    suit = str

    def getIntNumber(self):
        return NUMBERS.index(self.number)+1

    def __init__(self, number, suit):
        assert number in NUMBERS and suit in SUITS
        self.number = number
        self.suit = suit

    def __repr__(self):
        return '{}{}'.format(NUMBER_CHAR(self.number), SUIT_CHAR(self.suit))

    def render(self):
        return '{}{}'.format(self.number, icons.SUITS_ICON[self.suit])

def getCardFromRepr(repr):
    number_char = repr[0]
    suit_char = repr[1]
    number =  CHAR_NUMBER(number_char)
    suit = CHAR_SUIT[suit_char]
    return Card(number, suit)

def getCardFromRender(s):
    number, suit_icon = (s[0:2], s[2:]) if s.startswith('10') else (s[0], s[1:])
    suit = icons.ICON_SUITS[suit_icon]
    return Card(number, suit)

def renderCardFromRepr(repr):
    c = getCardFromRepr(repr)
    return c.render()

def reprCardFromRender(repr):
    c = getCardFromRender(repr)
    return c.__repr__()


def getDeckCardListStr(num=1, shuffle=True):
    deck = [str(Card(n,s)) for s in SUITS for n in NUMBERS] * num
    if shuffle:
        random.shuffle(deck)
    return deck


