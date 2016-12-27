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

    cards, texts, lines, polygons, width, height = getElements(accepted_cards, rejected_cards)

    img = Image.new("RGBA", (width, height), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)

    for c in cards:
        img.paste(c['img'], box=c['box'], mask=c['img'])
    for t in texts:
        draw.text(t['box'], t['text'], (0, 0, 0), font=FONT)
    for l in lines:
        draw.line(l['box'], fill=(0, 0, 0, 255), width=1)
    for p in polygons:
        draw.polygon(p['box'], fill=(0, 0, 0, 255), outline=(0, 0, 0, 255))

    if show:
        img.show()
    else:
        imgData = StringIO.StringIO()
        img.save(imgData, format="PNG")
        return imgData.getvalue()


'''
card = {'img': card_img, 'box': (x_dst, y_dst)}
text = {'text': text, 'box': (x_dst, y_dst)}
line = {'box': (x1, y1, x2, y2)}
poligon = {'box': (x1, y1, x2, y2, ..., xN, yN)}
'''
def getElements(accepted_cards, rejected_cards):
    cards = []
    texts = []
    lines = []
    polygons = []
    for i, ac in enumerate(accepted_cards):
        c = card.getCardFromRepr(ac)
        card_img = getCardImg(c)
        x_dst = MARGIN + i*(CARD_DIMENSIONS[0] + SPACE_CARDS)
        y_dst = MARGIN
        cards.append({'img': card_img, 'box': (x_dst, y_dst)})
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
                cards.append({'img': card_img, 'box': (x_dst_new, y_dst_row)})
    # render Rejected after
    if firstRejectedColumn:
        x_first_rejected_card = MARGIN + firstRejectedColumn * (CARD_DIMENSIONS[0] + SPACE_CARDS) - SPACE_CARDS
        y_half_first_rejected_card = MARGIN + CARD_DIMENSIONS[1] + 2 * SPACE_CARDS + CARD_DIMENSIONS[1]/2
        x_corner = x_first_rejected_card - CARD_DIMENSIONS[0]/2
        y_arrow = MARGIN + CARD_DIMENSIONS[1] + 2 * SPACE_CARDS
        lines.append({'box':(x_first_rejected_card, y_half_first_rejected_card, x_corner, y_half_first_rejected_card)})
        lines.append({'box':(x_corner, y_half_first_rejected_card, x_corner, y_arrow)})
        polygons.append({'box':(x_corner, y_arrow, x_corner-TRIANGLE_DIMENSION, y_arrow+TRIANGLE_DIMENSION, x_corner+TRIANGLE_DIMENSION, y_arrow+TRIANGLE_DIMENSION)})
        width_rejected = FONT.getsize('Rejected')[0]
        width_after = FONT.getsize('after')[0]
        text_y_base = y_half_first_rejected_card + TRIANGLE_DIMENSION
        texts.append({'text': 'Rejected', 'box':(x_corner-width_rejected/2, text_y_base)})
        texts.append({'text': 'after', 'box': (x_corner-width_after/2, text_y_base + TEXT_HEIGHT)})

    maxCardX = max(c['box'][0] for c in cards) + CARD_DIMENSIONS[0]
    maxCardY = max(c['box'][1] for c in cards) + CARD_DIMENSIONS[1]
    width = maxCardX + MARGIN
    height = maxCardY + MARGIN

    ## draw line under cards
    y_line_separation = MARGIN + CARD_DIMENSIONS[1] + SPACE_CARDS
    lines.append({'box': (MARGIN / 2, y_line_separation, width - MARGIN / 2, y_line_separation)})

    return cards, texts, lines, polygons, width, height

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

