# -*- coding: utf-8 -*-

import icons
import utility


INSTRUCTIONS = utility.unindent(
    """
    With this bot you can play the *Eleusis Game* alone or with other people.

    If you are not familiar with this game, please have a look at the \
    [Wikipedia article](https://en.wikipedia.org/wiki/Eleusis_%28card_game%29) \
    and the [Rules](http://www.logicmazes.com/games/eleusis/express.html)

    Please join the [Eleusis Group](https://telegram.me/joinchat/B8zsMQsw-w1rd1UvEZbvjw) \
    to get in touch with other players.

    Have fun!! 😀
    """
)

COMMNADS = utility.unindent(
    """
    🔹 /info get information about EleusisBot
    🔹 /exit exit the game (the game will terminate and all other players will exit as well)
    """
)

NOT_VALID_INPUT = "{} Input not valid, please try again.".format(icons.EXCLAMATION_ICON)