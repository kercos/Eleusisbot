# -*- coding: utf-8 -*-
import StringIO
from PIL import ImageFont
from PIL import Image
from PIL import ImageDraw

FONT_SIZE = 20
FONT = ImageFont.truetype("fonts/Symbola.ttf",FONT_SIZE)

MARGIN = 15
COLUMN_WIDTH = 120
ROW_HEIGHT = 30
TEXT_HEIGHT = FONT.getsize('M')[1]

def getResultImage(result_table, show=False):
    NUMBER_ROWS = len(result_table)
    NUMBER_COLUMNS = len(result_table[0])
    WIDTH = MARGIN * 2 + NUMBER_COLUMNS * COLUMN_WIDTH
    HEIGHT = MARGIN * 2 + TEXT_HEIGHT + NUMBER_ROWS * ROW_HEIGHT
    img = Image.new("RGBA", (WIDTH, HEIGHT), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    for i, row in enumerate(result_table):
        for j, text in enumerate(row):
            text = text.decode('utf-8')
            TEXT_WIDTH = FONT.getsize(text)[0]
            x = MARGIN if j==0 else COLUMN_WIDTH*(j+1) + MARGIN - TEXT_WIDTH
            y = ROW_HEIGHT*(i+1) + MARGIN - TEXT_HEIGHT
            draw.text((x, y), text, (0, 0, 0), font=FONT)
    imgData = StringIO.StringIO()
    img.save(imgData, format="PNG")
    if show:
        img.show()
    return imgData.getvalue()

def test():
    result_table = [
        ['', '👺🃏(x3)', '🕵🔭(x2)', '🕵🃏(x2)', 'TOTAL'],
        ['👺 player1_xx', '4+1', '1', '2', '21'],
        ['🕵 player2_xx', '2', '5+0', '3+1', '24'],
        ['🕵 player3_xx', '1', '4+1', '3+0', '19']
    ]
    getResultImage(result_table, show=True)
