# -*- coding: utf-8 -*-

from PIL import Image
import random
import StringIO


'''
deck.png 13 cards x 4 suits
order: clubs, hearts, spades, diamonds
dimensions 951x394
each card: 72x97
1px at the beginning and in between cards both vertically and horizontally
2px at the end both vertically and horizontally
951 = 72x13 + 13 + 2
394 = 97x4 + 4 + 2
'''

'''
deck_small.png 13 cards x 4 suits
order: spades, clubs, hearts, diamonds
dimensions 468x206
each card: 36x50
0px at the beginning both vertically and horizontally
0px in between cards horizontally
2px in between cards vertically
468 = 36x13
206 = 50x4 + 2*3
'''

DECK_SPRITE_SHEET_IMAGE = Image.open("img/deck_small.png")

ORIGINAL_CARD_DIMENSIONS = (36, 50)
INITIAL_PIXELS = (0,0)
IN_BETWEEN_PIXELS = (0,2)

CLUBS, HEARTS, SPADES, DIAMONDS = 'CLUBS', 'HEARTS', 'SPADES', 'DIAMONDS'
SUITS = [SPADES, CLUBS, HEARTS, DIAMONDS]
NUMBERS = ['1','2','3','4','5','6','7','8','9','10','J','Q','K']

def getCardPosition(suit, number):
    assert suit in SUITS and number in NUMBERS
    suit_index = SUITS.index(suit)
    number_index = NUMBERS.index(number)
    x = INITIAL_PIXELS[0] + number_index * (ORIGINAL_CARD_DIMENSIONS[0] + IN_BETWEEN_PIXELS[0])
    y = INITIAL_PIXELS[1] + suit_index * (ORIGINAL_CARD_DIMENSIONS[1] + IN_BETWEEN_PIXELS[1])
    return x, y

def getCardImg(suit, number):
    x, y = getCardPosition(suit, number)
    return DECK_SPRITE_SHEET_IMAGE.crop(box = (x, y, x + ORIGINAL_CARD_DIMENSIONS[0], y + ORIGINAL_CARD_DIMENSIONS[1]))

NEW_CARD_DIMENSIONS = (18, 25)

def getTestImage(width, height, show=False):
    img = Image.new("RGBA", (width, height), (255, 255, 255, 0))
    for i in range(200):
        s = random.choice(SUITS)
        n = random.choice(NUMBERS)
        card_img = getCardImg(s,n)
        #card_img = getCardImg(s, n).resize(NEW_CARD_DIMENSIONS, Image.BICUBIC) #Image.BILINEAR #Image.BILINEAR
        x_dst = random.randint(0, width - card_img.size[0])
        y_dst = random.randint(0, height - card_img.size[1])
        img.paste(card_img, box = (x_dst, y_dst), mask=card_img)
    imgData = StringIO.StringIO()
    img.save(imgData, format="PNG")
    if show:
        img.show()
    else:
        return imgData.getvalue()
