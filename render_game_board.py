# -*- coding: utf-8 -*-
import StringIO
from PIL import ImageFont
from PIL import Image
from PIL import ImageDraw
import random
import card
from card import Card

# sprite sheet proprerties
DECK_SPRITE_SHEET_IMAGE = Image.open("img/deck_small.png")
CARD_DIMENSIONS = (36, 50)
INITIAL_PIXELS = (0,0)
IN_BETWEEN_PIXELS = (0,2)
# end of sprite sheet proprerties

#CLUBS, HEARTS, SPADES, DIAMONDS = 'CLUBS', 'HEARTS', 'SPADES', 'DIAMONDS'
SUITS = [card.SPADES, card.CLUBS, card.HEARTS, card.DIAMONDS]
NUMBERS = ['2','3','4','5','6','7','8','9','10','J','Q','K','1']

FONT_SIZE = 12
FONT = ImageFont.truetype("fonts/Roboto-Regular.ttf",FONT_SIZE)

MARGIN = 30
SPACE_CARDS = 10
TRIANGLE_DIMENSION = 5
OVERLAPPING_REJECTED_CARDS = 5

TEXT_HEIGHT = FONT.getsize('M')[1]



def getCardPosition(number, suit):
    #print "number={}, suit={}".format(number, suit)
    assert number in NUMBERS and suit in SUITS
    suit_index = SUITS.index(suit)
    number_index = NUMBERS.index(number)
    x = INITIAL_PIXELS[0] + number_index * (CARD_DIMENSIONS[0] + IN_BETWEEN_PIXELS[0])
    y = INITIAL_PIXELS[1] + suit_index * (CARD_DIMENSIONS[1] + IN_BETWEEN_PIXELS[1])
    return x, y

def getCardImg(card):
    number, suit = card.number, card.suit
    x, y = getCardPosition(number, suit)
    return DECK_SPRITE_SHEET_IMAGE.crop(box = (x, y, x + CARD_DIMENSIONS[0], y + CARD_DIMENSIONS[1]))

def render(g, show=False):
    accepted_cards = g.getAcceptedCards()
    rejected_cards = g.getRejectedCards()

    accepted_columns = len(g.getAcceptedCards())
    max_y_cards = max([len(x) for x in rejected_cards])
    max_x_accepted_cards = MARGIN * 2 + CARD_DIMENSIONS[0] * accepted_columns + SPACE_CARDS * (accepted_columns - 1)

    rejected_columns = len(rejected_cards) if rejected_cards[-1] else len(rejected_cards) - 1
    last_rejected_column = rejected_cards[rejected_columns-1]
    max_x_cards_rejected=0
    if last_rejected_column:
        max_row_last_rejected_column = max([len(x) for x in last_rejected_column])
        max_x_cards_rejected = 2*MARGIN + CARD_DIMENSIONS[0] * rejected_columns + max_row_last_rejected_column * (CARD_DIMENSIONS[0] - OVERLAPPING_REJECTED_CARDS)

    width = max(max_x_cards_rejected, max_x_accepted_cards)
    height = 2*MARGIN + (CARD_DIMENSIONS[1] + SPACE_CARDS) * (1 + max_y_cards)

    img = Image.new("RGBA", (width, height), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    for i, ac in enumerate(accepted_cards):
        c = card.getCardFromRepr(ac)
        card_img = getCardImg(c)
        x_dst = MARGIN + i*(CARD_DIMENSIONS[0] + SPACE_CARDS)
        y_dst = MARGIN
        img.paste(card_img, box=(x_dst, y_dst), mask=card_img)
    firstRejectedColumn = None
    for i, rc_colum in enumerate(rejected_cards):
        x_dst = MARGIN + i * (CARD_DIMENSIONS[0] + SPACE_CARDS)
        for j, rej_row in enumerate(rc_colum):
            y_dst_row = MARGIN + SPACE_CARDS + (CARD_DIMENSIONS[1] + SPACE_CARDS) * (1 + j)
            for k, rc in enumerate(rej_row):
                if firstRejectedColumn==None:
                    firstRejectedColumn = i
                c = card.getCardFromRepr(rc)
                card_img = getCardImg(c)
                x_dst_new = x_dst + k * (CARD_DIMENSIONS[0] - OVERLAPPING_REJECTED_CARDS)
                img.paste(card_img, box=(x_dst_new, y_dst_row), mask=card_img)
    ## draw line under cards
    y_line_separation = MARGIN + CARD_DIMENSIONS[1] + SPACE_CARDS
    draw.line( (MARGIN/2, y_line_separation, width-MARGIN/2, y_line_separation), fill=(0,0,0,255), width=1)
    if firstRejectedColumn:
        x_first_rejected_card = MARGIN + firstRejectedColumn * (CARD_DIMENSIONS[0] + SPACE_CARDS) - SPACE_CARDS
        y_half_first_rejected_card = MARGIN + CARD_DIMENSIONS[1] + 2 * SPACE_CARDS + CARD_DIMENSIONS[1]/2
        x_corner = x_first_rejected_card - CARD_DIMENSIONS[0]/2
        y_arrow = MARGIN + CARD_DIMENSIONS[1] + 2 * SPACE_CARDS
        draw.line((x_first_rejected_card, y_half_first_rejected_card, x_corner, y_half_first_rejected_card), fill=(0,0,0,255), width=1)
        draw.line((x_corner, y_half_first_rejected_card, x_corner, y_arrow), fill=(0, 0, 0, 255), width=1)
        draw.polygon((x_corner, y_arrow, x_corner-TRIANGLE_DIMENSION, y_arrow+TRIANGLE_DIMENSION, x_corner+TRIANGLE_DIMENSION, y_arrow+TRIANGLE_DIMENSION), fill=(0, 0, 0, 255), outline=(0, 0, 0, 255))
        width_rejected = FONT.getsize('Rejected')[0]
        width_after = FONT.getsize('after')[0]
        text_y_base = y_half_first_rejected_card + TRIANGLE_DIMENSION
        draw.text((x_corner-width_rejected/2, text_y_base), "Rejected", (0, 0, 0), font=FONT)
        draw.text((x_corner-width_after/2, text_y_base + TEXT_HEIGHT), "after", (0, 0, 0), font=FONT)
    if show:
        img.show()
    else:
        imgData = StringIO.StringIO()
        img.save(imgData, format="PNG")
        return imgData.getvalue()





def getTestImage(width, height, show=False):
    img = Image.new("RGBA", (width, height), (255, 255, 255, 0))
    for i in range(200):
        #s = random.choice(SUITS)
        #n = random.choice(NUMBERS)
        n = '1'
        s = SUITS[0]
        card = Card(n, s)
        card_img = getCardImg(card)
        #card_img = getCardImg(s, n).resize(NEW_CARD_DIMENSIONS, Image.BICUBIC) #Image.BILINEAR #Image.BILINEAR
        x_dst = random.randint(0, width - card_img.size[0])
        y_dst = random.randint(0, height - card_img.size[1])
        img.paste(card_img, box = (x_dst, y_dst), mask=card_img)
    if show:
        img.show()
    else:
        imgData = StringIO.StringIO()
        img.save(imgData, format="PNG")
        return imgData.getvalue()

