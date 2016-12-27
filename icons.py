# -*- coding: utf-8 -*-
import card

CANCEL = '❌'
CHECK = '✅'
LEFT_ARROW = '⬅'
RIGHT_ARROW = '➡'
UNDER_CONSTRUCTION = '🚧'
BULLET = '🔹'
TIME_ICON = '⏱'
EXCLAMATION_ICON = '❗'
PLUS = '➕'
TROPHY = '🏆'
EYES = '👀'

YES_BUTTON = CHECK + ' YES'
NO_BUTTON = CANCEL + ' NO'

NO_PLAY_BUTTON = "NO PLAY"
SUBMIT_CARDS_BUTTON = "PROPOSE CARD(S)"
EMPTY_SELECTION_BUTTON = "EMPTY SELECTION"
CONFIRM_NO_PLAY_BUTTON = "CONFIRM NO PLAY"

## CARDS SYMBOLS
CLUBS = '♣'
HEARTS = '♥️' #'♥'
SPADES = '♠'
DIAMONDS = '♦️'

SUITS_ICON = {
    card.CLUBS: CLUBS,
    card.HEARTS: HEARTS,
    card.SPADES: SPADES,
    card.DIAMONDS: DIAMONDS
}

ICON_SUITS = {i:s for s,i in SUITS_ICON.iteritems()}