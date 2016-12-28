# -*- coding: utf-8 -*-

# import json
import json
import logging
import urllib
import urllib2
import datetime
from datetime import datetime
from time import sleep
import re

# standard app engine imports
from google.appengine.api import urlfetch
from google.appengine.ext import ndb
from google.appengine.ext import deferred
from google.appengine.ext.db import datastore_errors
import requests
import webapp2

import key
import game
from game import Game
import icons
import messages
import person
from person import Person
import utility
import jsonUtil
import utility
import parameters
import render_results

########################
WORK_IN_PROGRESS = False
########################

STATES = {
    1:   'Start State',
    20:  'Game Lobby',
    30:  'Game: God rule',
    31:  'Game: God Chooses Starter',
    32:  'Game: player turn',
    33:  'Game: God or Prophet judges proposed card(s)',
    34:  'Game: God or Prophet judges NO-PLAY',
    35:  'Ask to be a prophet'
}

# ================================
# Telegram Send Request
# ================================
def sendRequest(url, data, recipient_chat_id, debugInfo):
    try:
        resp = requests.post(url, data)
        logging.info('Response: {}'.format(resp.text))
        respJson = json.loads(resp.text)
        success = respJson['ok']
        if success:
            return True
        else:
            status_code = resp.status_code
            error_code = respJson['error_code']
            description = respJson['description']
            p = person.getPersonById(recipient_chat_id)
            if error_code == 403:
                # Disabled user
                logging.info('Disabled user: ' + p.getUserInfoString())
            elif error_code == 400 and description == "INPUT_USER_DEACTIVATED":
                p = person.getPersonById(recipient_chat_id)
                p.setEnabled(False, put=True)
                debugMessage = '❗ Input user disactivated: ' + p.getUserInfoString()
                logging.debug(debugMessage)
                tell(key.FEDE_CHAT_ID, debugMessage, markdown=False)
            else:
                debugMessage = '❗ Raising unknown err ({}).' \
                          '\nStatus code: {}\nerror code: {}\ndescription: {}.'.format(
                    debugInfo, status_code, error_code, description)
                logging.error(debugMessage)
                #logging.debug('recipeint_chat_id: {}'.format(recipient_chat_id))
                logging.debug('Telling to {} who is in state {}'.format(p.chat_id, p.state))
                tell(key.FEDE_CHAT_ID, debugMessage, markdown=False)
    except:
        report_exception()

# ================================
# TELL FUNCTIONS
# ================================

def broadcast(sender, msg, restart_user=False, curs=None, enabledCount = 0):
    #return

    BROADCAST_COUNT_REPORT = utility.unindent(
        """
        Mesage sent to {} people
        Enabled: {}
        Disabled: {}
        """
    )

    users, next_curs, more = Person.query().fetch_page(50, start_cursor=curs)
    try:
        for p in users:
            if p.enabled:
                enabledCount += 1
                if restart_user:
                    restart(p)
                tell(p.chat_id, msg, sleepDelay=True)
    except datastore_errors.Timeout:
        sleep(1)
        deferredSafeHandleException(broadcast, sender, msg, restart_user, curs, enabledCount)
        return
    if more:
        deferredSafeHandleException(broadcast, sender, msg, restart_user, next_curs, enabledCount)
    else:
        total = Person.query().count()
        disabled = total - enabledCount
        msg_debug = BROADCAST_COUNT_REPORT.format(total, enabledCount, disabled)
        tell(sender.chat_id, msg_debug)

def tellMaster(msg, markdown=False, one_time_keyboard=False):
    for id in key.MASTER_CHAT_ID:
        tell(id, msg, markdown=markdown, one_time_keyboard = one_time_keyboard, sleepDelay=True)

def tell(chat_id, msg, kb=None, markdown=True, inline_keyboard=False, one_time_keyboard=False,
         sleepDelay=False, remove_keyboard=False, force_reply=False):

    # reply_markup: InlineKeyboardMarkup or ReplyKeyboardMarkup or ReplyKeyboardHide or ForceReply
    if inline_keyboard:
        replyMarkup = { #InlineKeyboardMarkup
            'inline_keyboard': kb
        }
    elif kb:
        replyMarkup = { #ReplyKeyboardMarkup
            'keyboard': kb,
            'resize_keyboard': True,
            'one_time_keyboard': one_time_keyboard,
        }
    elif remove_keyboard:
        replyMarkup = { #ReplyKeyboardHide
            'remove_keyboard': remove_keyboard
        }
    elif force_reply:
        replyMarkup = { #ForceReply
            'force_reply': force_reply
        }
    else:
        replyMarkup = {}

    data = {
        'chat_id': chat_id,
        'text': msg,
        'disable_web_page_preview': 'true',
        'parse_mode': 'Markdown' if markdown else '',
        'reply_markup': json.dumps(replyMarkup),
    }
    debugInfo = "tell function with msg={} and kb={}".format(msg, kb)
    success = sendRequest(key.BASE_URL + 'sendMessage', data, chat_id, debugInfo)
    if success:
        if sleepDelay:
            sleep(0.1)
        return True

def tell_person(chat_id, msg, markdown=False):
    tell(chat_id, msg, markdown=markdown)
    p = person.getPersonById(chat_id)
    if p and p.enabled:
        return True
    return False

def sendText(p, text, markdown=False, restartUser=False):
    split = text.split()
    if len(split) < 3:
        tell(p.chat_id, 'Commands should have at least 2 spaces')
        return
    if not split[1].isdigit():
        tell(p.chat_id, 'Second argumnet should be a valid chat_id')
        return
    id = int(split[1])
    text = ' '.join(split[2:])
    if tell_person(id, text, markdown=markdown):
        user = person.getPersonById(id)
        if restartUser:
            restart(user)
        tell(p.chat_id, 'Successfully sent text to ' + user.getFirstName())
    else:
        tell(p.chat_id, 'Problems in sending text')


# ================================
# SEND LOCATION
# ================================

def sendLocation(chat_id, latitude, longitude, kb=None):
    try:
        resp = urllib2.urlopen(key.BASE_URL + 'sendLocation', urllib.urlencode({
            'chat_id': chat_id,
            'latitude': latitude,
            'longitude': longitude,
        })).read()
        logging.info('send location: {}'.format(resp))
    except urllib2.HTTPError, err:
        if err.code == 403:
            p = Person.query(Person.chat_id == chat_id).get()
            p.enabled = False
            p.put()
            logging.info('Disabled user: ' + p.getUserInfoString())
        else:
            logging.info('Unknown exception: ' + str(err))

# ================================
# SEND VOICE
# ================================

def sendVoice(chat_id, file_id):
    try:
        data = {
            'chat_id': chat_id,
            'voice': file_id,
        }
        resp = requests.post(key.BASE_URL + 'sendVoice', data)
        logging.info('Response: {}'.format(resp.text))
    except urllib2.HTTPError, err:
        report_exception()

# ================================
# SEND PHOTO
# ================================

def sendPhoto(chat_id, file_id_or_url):
    try:
        data = {
            'chat_id': chat_id,
            'photo': file_id_or_url,
        }
        resp = requests.post(key.BASE_URL + 'sendPhoto', data)
        logging.info('Response: {}'.format(resp.text))
    except urllib2.HTTPError, err:
        report_exception()

def sendPhotoData(chat_id, file_data, filename):
    try:
        files = [('photo', (filename, file_data, 'image/png'))]
        data = {
            'chat_id': chat_id,
        }
        resp = requests.post(key.BASE_URL + 'sendPhoto', data=data, files=files)
        logging.info('Response: {}'.format(resp.text))
    except urllib2.HTTPError, err:
        report_exception()


def sendScoreTest(chat_id):
    result_table = [
        ['', '👺🃏(x3)', '🕵🔭(x2)', '🕵🃏(x2)', 'TOTAL'],
        ['👺 player1_xx', '4+1', '1', '2', '21'],
        ['🕵 player2_xx', '2', '5+0', '3+1', '24'],
        ['🕵 player3_xx', '1', '4+1', '3+0', '19']
    ]
    imgData = render_results.getResultImage(result_table)
    sendPhotoData(chat_id, imgData, 'results.png')


def sendTextImage(chat_id, text):
    text = text.replace('+', '%2b')
    text = text.replace(' ', '+')
    text = text.replace('\n','%0B')
    # see http://img4me.com/
    # see https://developers.google.com/chart/image/docs/gallery/dynamic_icons
    # see https://dummyimage.com/
    # see https://placehold.it/
    #img_url = "http://chart.apis.google.com/chart?chst=d_text_outline&chld=000000|20|l|FFFFFF|_|" + text
    img_url = "https://placeholdit.imgix.net/~text?bg=ffffff&txtcolor=000000&txtsize=15&txt={}&w=400&h=200".format(text)
    logging.debug("img_url: {}".format(img_url))
    #img_url = "http://chart.apis.google.com/chart?chst=d_fnote&chld=sticky_y|2|0088FF|h|" + text
    sendPhoto(chat_id, img_url)

# ================================
# SEND DOCUMENT
# ================================

def sendDocument(chat_id, file_id):
    try:
        data = {
            'chat_id': chat_id,
            'document': file_id,
        }
        resp = requests.post(key.BASE_URL + 'sendDocument', data)
        logging.info('Response: {}'.format(resp.text))
    except urllib2.HTTPError, err:
        report_exception()

def sendExcelDocument(chat_id, sheet_tables, filename='file'):
    try:
        xlsData = utility.convert_data_to_spreadsheet(sheet_tables)
        files = [('document', ('{}.xls'.format(filename), xlsData, 'application/vnd.ms-excel'))]
        data = {
            'chat_id': chat_id,
        }
        resp = requests.post(key.BASE_URL + 'sendDocument', data=data, files=files)
        logging.info('Response: {}'.format(resp.text))
    except urllib2.HTTPError, err:
        report_exception()


# ================================
# SEND WAITING ACTION
# ================================

def sendWaitingAction(chat_id, action_type='typing', sleep_time=None):
    try:
        resp = urllib2.urlopen(key.BASE_URL + 'sendChatAction', urllib.urlencode({
            'chat_id': chat_id,
            'action': action_type,
        })).read()
        logging.info('send waiting action: {}'.format(resp))
        if sleep_time:
            sleep(sleep_time)
    except urllib2.HTTPError, err:
        if err.code == 403:
            p = Person.query(Person.chat_id == chat_id).get()
            p.enabled = False
            p.put()
            logging.info('Disabled user: ' + p.getUserInfoString())
        else:
            logging.info('Unknown exception: ' + str(err))

# ================================
# SEND GAME
# ================================
# telegram.me/EleusisBot?game=EleusisGame

def sendGame(chat_id):
    data = {
        'chat_id': chat_id,
        'game_short_name': 'EleusisGame',
    }
    try:
        resp = requests.post(key.BASE_URL + 'sendGame', data)
        logging.info('Response: {}'.format(resp.text))
    except:
        report_exception()

# ================================
# ANSWER ONLINE QUERY
# ================================

def answerCallbackQueryGame(callback_query_id):
    data = {
        'callback_query_id': callback_query_id,
        'url': 'http://dialectbot.appspot.com/audiomap/mappa.html'
    }
    try:
        resp = requests.post(key.BASE_URL + 'answerCallbackQuery', data)
        logging.info('Response: {}'.format(resp.text))
    except:
        report_exception()


# ================================
# RESTART
# ================================
def restart(p, msg=None):
    if msg:
        tell(p.chat_id, msg)
    redirectToState(p, 1)


# ================================
# SWITCH TO STATE
# ================================
def redirectToState(p, new_state, **kwargs):
    if p.state != new_state:
        logging.debug("In redirectToState. current_state:{0}, new_state: {1}".format(str(p.state),str(new_state)))
        p.setState(new_state)
    repeatState(p, **kwargs)

# ================================
# REPEAT STATE
# ================================
def repeatState(p, put=False, **kwargs):
    methodName = "goToState" + str(p.state)
    method = possibles.get(methodName)
    if not method:
        tell(p.chat_id, "A problem has been detected (" + methodName +
              "). Write to @kercos." + '\n' +
              "You will be now redirected to the initial screen.")
        restart(p)
    else:
        if put:
            p.put()
        method(p, **kwargs)

# ================================
# GAME FUNCTIONS
# ================================

def terminateGame(g, msg=''):
    broadcastGameBoardPlayers(g)
    person.setGameRoomMulti(g.getPlayersId(), None)
    if msg:
        broadcastMsgToPlayers(g, msg)
    redirectPlayersToState(g, 1)
    if g.isPublic():
        g.resetGame()
    else:
        game.deleteGame(g)

def broadcastMsgToPlayers(g, msg, kb=None, exclude = None):
    for id in g.getPlayersId():
        if id != exclude:
            tell(id, msg, kb, sleepDelay=True)

def broadcastCardsToPlayers(g, exclusion_player_id):
    for p_id in g.getPlayersId(excludingGod=True):
        if p_id ==  exclusion_player_id:
            continue
        msg = "Here are your cards."
        cards = g.getSinglePlayerCards(p_id, emoji=True)
        kb = utility.distributeElementMaxSize(cards, maxSize = parameters.CARDS_PER_ROW)
        tell(p_id, msg, kb)

def broadcastGameBoardPlayers(g):
    import render_game_board
    file_data = render_game_board.render(g)
    for id in g.getPlayersId():
        sendPhotoData(id, file_data, 'results.png')
        sleep(0.1)

def redirectPlayersToState(g, new_state, **kwargs):
    for id in g.getPlayersId():
        p = person.getPersonById(id)
        redirectToState(p, new_state, **kwargs)

#def sendPlayersWaitingAction(g, sleep_time=None):
#    for chat_id in g.getPlayersId():
#        sendWaitingAction(chat_id, sleep_time = sleep_time)

# ================================
# GO TO STATE 1: Initial Screen
# ================================
def goToState1(p, **kwargs):
    input = kwargs['input'] if 'input' in kwargs.keys() else None
    giveInstruction = input is None
    kb = [[icons.SINGLE_PLAYER_GAME], [icons.MULTI_PLAYER_GAME],[icons.INFO]]
    if giveInstruction:
        msg = 'Press {} if you want to play against the computer or ' \
              '{} if you want to enter a multi-player game'.format(
            icons.SINGLE_PLAYER_GAME, icons.MULTI_PLAYER_GAME)
        tell(p.chat_id, msg, kb)
    else:
        if input in [icons.INFO]:
            tell(p.chat_id, messages.INSTRUCTIONS)
        elif input == icons.SINGLE_PLAYER_GAME:
            tell(p.chat_id, "{} Not yer implemented".format(icons.UNDER_CONSTRUCTION))
        elif input == icons.MULTI_PLAYER_GAME:
            redirectToState(p, 20)
        elif p.chat_id in key.MASTER_CHAT_ID:
            if input.startswith('/sendText'):
                sendText(p, input, markdown=True)
            elif input == '/testScore':
                sendScoreTest(p.chat_id)
            elif input == '/testImg':
                import pil_test
                imgData = pil_test.getTestImage(300, 200)
                sendPhotoData(p.chat_id, imgData, 'cards.png')
            elif input == '/testHtml':
                sendGame(p.chat_id)
            else:
                tell(p.chat_id, messages.NOT_VALID_INPUT, kb=kb)
        else: # including input == ''
            tell(p.chat_id, messages.NOT_VALID_INPUT, kb=kb)

# ================================
# GO TO STATE 20: Game Lobby
# ================================
def goToState20(p, **kwargs):
    input = kwargs['input'] if 'input' in kwargs.keys() else None
    giveInstruction = input is None
    public_games = [game.getGame(x) for x in parameters.PUBLIC_GAME_ROOM_NAMES]
    public_game_room_names = [x.getGameRoomName() for x in public_games if x.areMorePlayersAccepted()] #else icons.REFRESH
    public_game_room_names_str = ', '.join(public_game_room_names)
    kb = [public_game_room_names,[icons.NEW_GAME_ROOM],[icons.BACK]]
    if giveInstruction:
        msg = "YOU ARE IN THE *LOBBY*\n" \
              "Please press on one of the *public rooms* below ({}), " \
              "enter the name of an existing *private room*, " \
              "or *create a new one*.".format(public_game_room_names_str)
        tell(p.chat_id, msg, kb)
    else:
        if input == icons.REFRESH:
            repeatState(p)
        elif input == icons.BACK:
            restart(p)
        elif input == icons.NEW_GAME_ROOM:
            p.setTmpVariable(person.VAR_CREATE_GAME, {'stage': 0})
            redirectToState(p, 21)
        elif input != '':
            public = input in parameters.PUBLIC_GAME_ROOM_NAMES
            if not public:
                input = input.upper()
            g = game.getGame(input)
            if g:
                if g.addPlayer(p):
                    redirectToState(p, 22)
                else:
                    msg = "Sorry, there are no more places available in this Game, choose another room or try later."
                    tell(p.chat_id, msg)
                    sendWaitingAction(p.chat_id, sleep_time=1)
                    repeatState(p)
            else:
                msg = "{} You didn't enter a valid Game name, " \
                      "if you want to create a new one press {}.".format(icons.EXCLAMATION_ICON, icons.NEW_GAME_ROOM)
                tell(p.chat_id, msg)
        else:  # input == ''
            tell(p.chat_id, messages.NOT_VALID_INPUT, kb=p.getLastKeyboard())

# ================================
# GO TO STATE 21: Create new game
# ================================
def goToState21(p, **kwargs):
    input = kwargs['input'] if 'input' in kwargs.keys() else None
    if input == '':
        tell(p.chat_id, messages.NOT_VALID_INPUT, kb=p.getLastKeyboard())
        return
    if input == icons.BACK:
        redirectToState(p, 20)  # lobby
        return
    giveInstructions = input is None
    game_parameters = p.getTmpVariable(person.VAR_CREATE_GAME)
    stage = game_parameters['stage']
    if stage == 0: # game name
        if giveInstructions:
            kb = [[icons.BACK]]
            p.setLastKeyboard(kb)
            msg = "Please enter the name of a new game."
            tell(p.chat_id, msg, kb)
        else:
            input = input.upper()
            if game.gameExists(input):
                msg = "{} A game with this name already exists. Please try again.".format(icons.EXCLAMATION_ICON)
                tell(p.chat_id, msg)
            else:
                game_parameters['stage'] = 1
                game_parameters['game_name'] = input
                repeatState(p, put=True)
    elif stage == 1: # number of players
        if giveInstructions:
            kb = [['3','4','5','6'],[icons.BACK]]
            p.setLastKeyboard(kb)
            msg = "Please enter the number of people."
            tell(p.chat_id, msg, kb)
        else:
            if utility.representsIntBetween(input, 2, 30):
                sendWaitingAction(p.chat_id)
                number_players = int(input)
                game_name = game_parameters['game_name']
                g = game.createGame(game_name, number_players)
                g.addPlayer(p)
                redirectToState(p, 22)
            else:
                msg = "{} Please enter a number between 3 and 30.".format(icons.EXCLAMATION_ICON)
                tell(p.chat_id, msg)

# ================================
# GO TO STATE 22: Game: Waiting for start
# ================================
def goToState22(p, **kwargs):
    input = kwargs['input'] if 'input' in kwargs.keys() else None
    giveInstruction = input is None
    g = p.getGame()
    if giveInstruction:
        msg = "Entering the game *{}*".format(g.getGameRoomName())
        tell(p.chat_id, msg, remove_keyboard=True)
        broadcastMsgToPlayers(g, "Player {} joined the game!".format(p.getFirstName()))
        if g.readyToStart():
            msg = "All seats have been occupied! Setting up the game..."
            broadcastMsgToPlayers(g, msg)
            g.initializeCardsDeck()
            redirectPlayersToState(g, 30)
        else:
            msg = "Waiting for {} other players...".format(g.remainingSeats())
            broadcastMsgToPlayers(g, msg)
    else:
        msg = "{} Please wait for the other players to join the game.".format(icons.EXCLAMATION_ICON)
        tell(p.chat_id, msg)


# ================================
# GO TO STATE 30: Game: God Rule
# ================================
def goToState30(p, **kwargs):
    input = kwargs['input'] if 'input' in kwargs.keys() else None
    g = p.getGame()
    giveInstruction = input is None
    god_id, god_name = g.getGodPlayerIdAndName()
    isGod = p.chat_id == god_id
    if giveInstruction:
        if isGod:
            msg = "*You are God!*\n" \
                  "{} Please write down the secret rule of the game as clearly as possible.".format(icons.EYES)
        else:
            msg = "The God of this game is {}. S/he is writing down the secret rule of the game...".format(god_name)
        tell(p.chat_id, msg)
    else:
        if isGod:
            if input == '':
                tell(p.chat_id, messages.NOT_VALID_INPUT)
            else:
                g.setGodRule(input)
                msg = "👍 Great, God has chosen the rule!"
                broadcastMsgToPlayers(g, msg)
                #sendPlayersWaitingAction(g, sleep_time=1)
                redirectPlayersToState(g, 31)
        else:
            msg = "{} Please wait for {} to choose the secret rule.".format(icons.EXCLAMATION_ICON, god_name)
            tell(p.chat_id, msg)

# ================================
# GO TO STATE 31: Game: God Chooses Starter
# ================================
def goToState31(p, **kwargs):
    input = kwargs['input'] if 'input' in kwargs.keys() else None
    g = p.getGame()
    giveInstruction = input is None
    god_id, god_name = g.getGodPlayerIdAndName()
    isGod = p.chat_id == god_id
    god_kb = [[icons.YES_BUTTON, icons.NO_BUTTON]]
    if giveInstruction:
        if isGod:
            nextDeckCard = g.getNextStartingCard()
            msg = "You need to select the starting card.\n" \
                  "{} Is {} a good starting card?".format(icons.EYES, nextDeckCard)
            tell(p.chat_id, msg, kb=god_kb)
        else:
            msg = "The God is choosing the starting card...".format(god_name)
            tell(p.chat_id, msg)
    else:
        if isGod:
            if input == icons.NO_BUTTON:
                nextDeckCard = g.getNextStartingCard()
                msg = "Ok, let's try with next one.\nIs {} a good starting card?".format(nextDeckCard)
                tell(p.chat_id, msg, kb=god_kb)
            elif input == icons.YES_BUTTON:
                g.acceptStartingCard()
                broadcastGameBoardPlayers(g)
                msg = "👍 Great, God has chosen the starting card {}!\nThe game can now start!".format(g.getStartingCard(emoji=True))
                broadcastMsgToPlayers(g, msg)
                #sendPlayersWaitingAction(g)
                g.startGame()
                broadcastCardsToPlayers(g, exclusion_player_id = g.getCurrentPlayerId())
                redirectPlayersToState(g, 32)
            else:
                tell(p.chat_id, messages.NOT_VALID_INPUT)
        else:
            msg = "{} Please wait for {} to choose the starting card.".format(icons.EXCLAMATION_ICON, god_name)
            tell(p.chat_id, msg)


# ================================
# GO TO STATE 32: Game: Player Next Turn
# ================================
def goToState32(p, **kwargs):
    input = kwargs['input'] if 'input' in kwargs.keys() else None
    continuation = kwargs['continuation'] if 'continuation' in kwargs.keys() else False
    g = p.getGame()
    giveInstruction = input is None
    god_id, god_name = g.getGodPlayerIdAndName()
    isGod = p.chat_id == god_id
    currentPlayerId, currentPlayerName = g.getCurrentPlayerIdAndName()
    isPlayerTurn = p.chat_id == currentPlayerId
    selected_cards = g.getProposedCards(emoji=True)
    players_command_buttons = [icons.SUBMIT_CARDS_BUTTON, icons.EMPTY_SELECTION_BUTTON] if selected_cards else [icons.NO_PLAY_BUTTON]
    players_enabled_prophet = None
    if g.checkIfCurrentPlayerCanBeProphet(checkIfAskedEnable=False, put=False):
        players_enabled_prophet = [icons.ASK_ME_TO_BE_A_PROPHET_ENABLED] if g.getPlayerAskToBeAProphet(currentPlayerId) else [icons.ASK_ME_TO_BE_A_PROPHET_DISABLED]
    if giveInstruction:
        if isPlayerTurn:
            players_cards = g.getSinglePlayerCards(p.chat_id, emoji=True)
            player_kb = []
            if players_cards:
                player_kb = utility.distributeElementMaxSize(players_cards, maxSize=parameters.CARDS_PER_ROW)
            player_kb.insert(0, players_command_buttons)
            if players_enabled_prophet:
                player_kb.insert(1, players_enabled_prophet)
            if not continuation:
                msg = "{} You are next, please select a card " \
                      "or press {} if you think you have no cards to play.".format(icons.EYES, icons.NO_PLAY_BUTTON)
            elif selected_cards:
                selected_cards_str = ', '.join(selected_cards)
                msg = "You have selected the following card(s):\n\n{}\n\n" \
                      "{} Please, select more cards or submit.".format(selected_cards_str, icons.EYES)
            else:
                msg = "{} Please, select a card " \
                      "or press {} if you think you have no card to play.".format(icons.EYES, icons.NO_PLAY_BUTTON)
            tell(p.chat_id, msg, player_kb)
        else:
            msg = "It's {}'s turn. Let's wait for him/her to choose a card...".format(currentPlayerName)
            tell(p.chat_id, msg, remove_keyboard=isGod)
    else:
        if isPlayerTurn:
            if input in players_enabled_prophet:
                enabled = g.flipPlayerAskToBeAProphet(currentPlayerId)
                if enabled:
                    msg = "{} After you play, you will be asked if you want to be a Prophet.".format(icons.CHECK)
                else:
                    msg = "{} After you play, you won't be asked if you want to be a Prophet.".format(icons.CANCEL)
                tell(p.chat_id, msg)
                repeatState(p)
            elif input in players_command_buttons:
                if input == icons.SUBMIT_CARDS_BUTTON:
                    redirectPlayersToState(g, 33)
                elif input == icons.EMPTY_SELECTION_BUTTON:
                    g.returnProposedCardsToPlayer()
                    repeatState(p)
                elif input == icons.NO_PLAY_BUTTON:
                    redirectPlayersToState(g, 34)
            elif g.isValidCard(input):
                g.appendInProposedCardsAndRemoveFromHand(input)
                repeatState(p, continuation=True)
            else:
                tell(p.chat_id, messages.NOT_VALID_INPUT)
        else:
            msg = "{} Please wait for {} to propose a card.".format(icons.EXCLAMATION_ICON, currentPlayerName)
            tell(p.chat_id, msg)

# ================================
# GO TO STATE 33: Game: God or Prophet judges proposed card(s)
# ================================
def goToState33(p, **kwargs):
    input = kwargs['input'] if 'input' in kwargs.keys() else None
    g = p.getGame()
    giveInstruction = input is None
    currentPlayerId, currentPlayerName = g.getCurrentPlayerIdAndName()
    god_id, god_name = g.getGodPlayerIdAndName()
    proposed_cards = g.getProposedCards(emoji=True)
    proposed_cards_str = ', '.join(proposed_cards)
    isGod = p.chat_id == god_id
    isPlayerTurn = p.chat_id == currentPlayerId
    god_kb = [[icons.YES_BUTTON, icons.NO_BUTTON]]
    if giveInstruction:
        if isGod:
            msg = "{} has choosen the following card(s):\n\n{}\n\n" \
                  "Do you accept it/them?".format(currentPlayerName, proposed_cards_str)
            tell(god_id, msg, god_kb, one_time_keyboard=True)
        elif isPlayerTurn:
            cards = g.getSinglePlayerCards(currentPlayerId, emoji=True)
            player_kb = None
            if cards:
                player_kb = utility.distributeElementMaxSize(cards, maxSize=parameters.CARDS_PER_ROW)
            msg = "You have choosen the following card(s):\n\n{}\n\n" \
                  "Let's see if God accepts it.".format(proposed_cards_str)
            tell(currentPlayerId, msg, player_kb)
        else:
            msg = "{} has choosen the following card(s):\n\n{}\n\n" \
                  "Let's see if God accepts it.".format(currentPlayerName, proposed_cards_str)
            tell(p.chat_id, msg)
    else:
        if isGod:
            if input in god_kb[0]:
                if input == icons.YES_BUTTON:
                    g.acceptProposedCards()
                    msg = "{} God has accepted the following card(s)\n\n{}\n\nproposed by {}".format(icons.CHECK, proposed_cards_str, currentPlayerName)
                    broadcastMsgToPlayers(g, msg)
                    if checkIfCurrentPlayerHasWon(g):
                        return
                elif input == icons.NO_BUTTON:
                    newCards = g.rejectProposedCardsAndGetPenalityCards()
                    newCards_str = ', '.join(newCards)
                    msg = "{} God has rejected the following card(s)\n\n{}\n\n" \
                          "proposed by {} who gets {} extra cards.".format(
                        icons.CANCEL, proposed_cards_str, currentPlayerName, len(newCards))
                    broadcastMsgToPlayers(g, msg)
                    msg = "Your new cards: {}".format(newCards_str)
                    player_kb = None
                    cards = g.getSinglePlayerCards(currentPlayerId, emoji=True)
                    if cards:
                        player_kb = utility.distributeElementMaxSize(cards, maxSize=parameters.CARDS_PER_ROW)
                    tell(currentPlayerId, msg, kb = player_kb)
                    if checkIfPlayerIsEliminatedAndTerminateGame(g):
                        return
                else:
                    tell(p.chat_id, messages.NOT_VALID_INPUT)
                    return
                broadcastGameBoardPlayers(g)
                prophetCheckProcedure(g)
            else:
                tell(p.chat_id, messages.NOT_VALID_INPUT, kb=god_kb)
        else:
            msg = "{} Please wait for God to judge {}'s card.".format(icons.EXCLAMATION_ICON, currentPlayerName)
            tell(p.chat_id, msg)

# ================================
# GO TO STATE 34: Game: God or Prophet judges NO-PLAY
# ================================
def goToState34(p, **kwargs):
    input = kwargs['input'] if 'input' in kwargs.keys() else None
    g = p.getGame()
    giveInstruction = input is None
    god_id, god_name = g.getGodPlayerIdAndName()
    currentPlayerId, currentPlayerName = g.getCurrentPlayerIdAndName()
    isGod = p.chat_id == god_id
    if giveInstruction:
        if isGod:
            cards = g.getSinglePlayerCards(currentPlayerId, emoji=True)
            god_kb = utility.distributeElementMaxSize(cards, maxSize=parameters.CARDS_PER_ROW)
            god_kb.insert(0, [icons.CONFIRM_NO_PLAY_BUTTON])
            msg = "{} claims s/he has no card to play. " \
                  "{} Please confirm the NO PLAY or select a card which can be played.".format(currentPlayerName, icons.EYES)
            tell(p.chat_id, msg, kb=god_kb)
        else:
            msg = "{} claims s/he has no card to play. Let's see what God thinks.".format(currentPlayerName)
            tell(p.chat_id, msg)
    else:
        if isGod:
            if input == icons.CONFIRM_NO_PLAY_BUTTON:
                g.confirmNoPlay()
                msg = "God has confirmed {} has no cards to play, " \
                      "so {} of his/her cards are discarded and all the rest are refreshed!".format(
                    currentPlayerName, parameters.CARDS_DISCOUNTED_ON_CORRECT_NO_PLAY)
                broadcastMsgToPlayers(g, msg)
                if checkIfCurrentPlayerHasWon(g):
                    return
            elif g.isValidCard(input):
                penaltyCards = g.rejectNoPlay(input)
                msg = "God has rejected {0}'s claim and declares that {1} is a perfectly valid card. " \
                      "{0} will get {2} additional penality cards.".format(
                    currentPlayerName, input, len(penaltyCards))
                broadcastMsgToPlayers(g, msg)
            else:
                tell(p.chat_id, messages.NOT_VALID_INPUT)
                return
            broadcastGameBoardPlayers(g)
            prophetCheckProcedure(g)
        else:
            msg = "{} Please wait for {} to judge the NO PLAY claim.".format(icons.EXCLAMATION_ICON, god_name)
            tell(p.chat_id, msg)

def checkIfCurrentPlayerHasWon(g):
    if g.checkIfCurrentPlayerHasWon():
        msg = "Player {} has won the game!!".format(g.getCurrentPlayerName())
        terminateGame(g, msg)
        return True
    return False

def prophetCheckProcedure(g):
    if g.checkIfCurrentPlayerCanBeProphet(checkIfAskedEnable=True, put=True):
        redirectPlayersToState(g, 35)
    else:
        g.setUpNextTurn()
        redirectPlayersToState(g, 32)

def checkIfPlayerIsEliminatedAndTerminateGame(g):
    if g.isSuddenDeath():
        g.setCurrentPlayerEliminated()
        msg = "{} has been eliminated!".format(g.getCurrentPlayerName())
        broadcastMsgToPlayers(g, msg)
        if g.areAllPlayersEliminated():
            msg = "Game has terminated since all players have been eliminated!"
            terminateGame(g, msg)
            return True
    return False

# ================================
# GO TO STATE 35: Game: Ask to be a prophet
# ================================
def goToState35(p, **kwargs):
    input = kwargs['input'] if 'input' in kwargs.keys() else None
    g = p.getGame()
    giveInstruction = input is None
    god_id, god_name = g.getGodPlayerIdAndName()
    currentPlayerId, currentPlayerName = g.getCurrentPlayerIdAndName()
    isGod = p.chat_id == god_id
    isPlayerTurn = p.chat_id == currentPlayerId
    if giveInstruction:
        if isPlayerTurn:
            msg = "{} Do you want to be a Prophet?".format(icons.EYES)
            player_kb = [[icons.YES_BUTTON, icons.NO_BUTTON]]
            tell(p.chat_id, msg, player_kb)
        else:
            msg = "Let's see if {} wants to be a Prophet...".format(currentPlayerName)
            tell(p.chat_id, msg, remove_keyboard=isGod)
    else:
        if isPlayerTurn:
            if input in [icons.YES_BUTTON, icons.NO_BUTTON]:
                if input == icons.YES_BUTTON:
                    msg = "Great news: {} is the new Prophet!".format(currentPlayerName)
                    broadcastMsgToPlayers(g, msg)
                    g.setUpProphet()
                else:
                    msg = "{} has decided not to be a prophet!".format(currentPlayerName)
                    broadcastMsgToPlayers(g, msg)
                g.setUpNextTurn()
                redirectPlayersToState(g, 32)
            else:
                tell(p.chat_id, messages.NOT_VALID_INPUT)
        else:
            msg = "{} Please wait for {} to decide whether s/he wants to be a Prophet.".format(icons.EXCLAMATION_ICON, currentPlayerName)
            tell(p.chat_id, msg)

# ================================
# HANDLERS
# ================================

class SafeRequestHandler(webapp2.RequestHandler):
    def handle_exception(self, exception, debug_mode):
        report_exception()

class MeHandler(webapp2.RequestHandler):
    def get(self):
        urlfetch.set_default_fetch_deadline(60)
        self.response.write(json.dumps(json.load(urllib2.urlopen(key.BASE_URL + 'getMe'))))

class SetWebhookHandler(webapp2.RequestHandler):
    def get(self):
        urlfetch.set_default_fetch_deadline(60)
        allowed_updates = ["message", "inline_query", "chosen_inline_result", "callback_query"]
        data = {
            'url': key.WEBHOOK_URL,
            'allowed_updates': json.dumps(allowed_updates),
        }
        resp = requests.post(key.BASE_URL + 'setWebhook', data)
        logging.info('SetWebhook Response: {}'.format(resp.text))
        self.response.write(resp.text)

class GetWebhookInfo(webapp2.RequestHandler):
    def get(self):
        urlfetch.set_default_fetch_deadline(60)
        resp = requests.post(key.BASE_URL + 'getWebhookInfo')
        logging.info('GetWebhookInfo Response: {}'.format(resp.text))
        self.response.write(resp.text)

class DeleteWebhook(webapp2.RequestHandler):
    def get(self):
        urlfetch.set_default_fetch_deadline(60)
        resp = requests.post(key.BASE_URL + 'deleteWebhook')
        logging.info('DeleteWebhook Response: {}'.format(resp.text))
        self.response.write(resp.text)


# ================================
# ================================
# ================================

class CheckExpiredGames(SafeRequestHandler):
    def get(self):
        for g in Game.query():
            if g.isGameExpired():
                msg = "{} The game has terminated because it has been idle for too long".format(icons.TIME_ICON)
                terminateGame(g, msg)

# ================================
#  CALLBACK QUERY
# ================================

def dealWithCallbackQuery(callback_query):
    logging.debug('dealing with callback query')
    game_short_name = callback_query['game_short_name'] if 'game_short_name' in callback_query else None
    if game_short_name:
        callback_query_id = callback_query['id']
        answerCallbackQueryGame(callback_query_id)
        return
    logging.debug('callback query not recognized')


# ================================
#  WEBHOOK HANDLER
# ================================

class WebhookHandler(SafeRequestHandler):
    def post(self):
        body = jsonUtil.json_loads_byteified(self.request.body)
        logging.info('request body: {}'.format(body))

        callback_query = body["callback_query"] if "callback_query" in body else None
        if callback_query:
            dealWithCallbackQuery(callback_query)
            return

        if 'message' not in body:
            return
        message = body['message']

        if 'chat' not in message:
            return

        chat = message['chat']
        chat_id = chat['id']
        if 'first_name' not in chat:
            return
        text = message.get('text') if 'text' in message else ''
        name = chat['first_name']
        last_name = chat['last_name'] if 'last_name' in chat else None
        username = chat['username'] if 'username' in chat else None
        #location = message['location'] if 'location' in message else None
        contact = message['contact'] if 'contact' in message else None
        photo = message.get('photo') if 'photo' in message else None
        document = message.get('document') if 'document' in message else None
        voice = message.get('voice') if 'voice' in message else None

        p = person.getPersonById(chat_id)

        if p is None:
            # new user
            logging.info("Text: " + text)
            if text == '/help':
                tell(chat_id, messages.INSTRUCTIONS)
            elif text.startswith("/start"):
                p = person.addPerson(chat_id, name, last_name, username)
                msg = "Hi {}, welcome to EleusisBot!\n".format(p.getFirstName()) # + START_MESSAGE
                tell(chat_id, msg)
                restart(p)
                tellMaster("New user: " + p.getFirstNameLastNameUserName())
            else:
                msg = "Press on /start if you want to enter. If you encounter any problem, please contact @kercos"
                tell(chat_id, msg)
        else:
            # known user
            p.updateInfo(name, last_name, username)
            if text == '/help':
                tell(chat_id, messages.COMMNADS)
            if text == '/info':
                tell(chat_id, messages.INSTRUCTIONS)
            elif text == '/state':
                if p.state in STATES:
                    tell(p.chat_id, "You are in state " + str(p.state) + ": " + STATES[p.state])
                else:
                    tell(p.chat_id, "You are in state " + str(p.state))
            elif text.startswith("/start"):
                if p.getGame()!=None:
                    msg = "{} You are still in a game!".format(icons.EXCLAMATION_ICON)
                    tell(p.chat_id, msg)
                else:
                    msg = "Hi {}, welcome back to EleusisBot!\n\n".format(p.getFirstName())
                    tell(p.chat_id, msg)
                    p.setEnabled(True, put=False)
                    restart(p)
            elif text.startswith("/exit"):
                g = p.getGame()
                if g==None:
                    msg = "{} You are not in a game!".format(icons.EXCLAMATION_ICON)
                    tell(p.chat_id, msg)
                else:
                    terminateGame(g, "The game has terminated because {} exited.".format(p.getFirstName()))
            elif WORK_IN_PROGRESS and p.chat_id not in key.TEST_PLAYERS:
                logging.debug('person {} not in {}'.format(p.chat_id, key.TEST_PLAYERS))
                tell(p.chat_id, icons.UNDER_CONSTRUCTION + " System under maintanence, try later.")
            else:
                logging.debug("Sending {} to state {} with input {}".format(p.getFirstName(), p.state, text))
                repeatState(p, input=text, contact=contact, photo=photo, document=document, voice=voice)

def deferredSafeHandleException(obj, *args, **kwargs):
    #return
    try:
        deferred.defer(obj, *args, **kwargs)
    except: # catch *all* exceptions
        report_exception()

def report_exception():
    import traceback
    msg = "❗ Detected Exception: " + traceback.format_exc()
    tell(key.FEDE_CHAT_ID, msg, markdown=False)
    logging.error(msg)

app = webapp2.WSGIApplication([
    ('/me', MeHandler),
    ('/set_webhook', SetWebhookHandler),
    ('/delete_webhook', DeleteWebhook),
    ('/get_webhook_info', GetWebhookInfo),
    (key.WEBHOOK_PATH, WebhookHandler),
    ('/checkExpiredGames', CheckExpiredGames),
], debug=True)

possibles = globals().copy()
possibles.update(locals())
