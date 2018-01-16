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
import autorule
import date_time_util

from google.appengine.api import urlfetch
urlfetch.set_default_fetch_deadline(45)

########################
WORK_IN_PROGRESS = False
########################

STATES = {
    1:   'Start State',
    10:  'Demo Mode',
    20:  'Game Lobby',
    30:  'Game: God rule',
    31:  'Game: God Chooses Starter',
    32:  'Game: player turn',
    33:  'Game: God or Prophet judges proposed card(s)',
    331:  'Game: God judges Prophet on proposed card(s)',
    34:  'Game: God or Prophet judges NO-PLAY',
    341:  'Game: God judges Prophet on NO-PLAY',
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
                logging.info('Disabled user: ' + p.getFirstNameLastNameUserName())
            elif error_code == 400 and description == "INPUT_USER_DEACTIVATED":
                p = person.getPersonById(recipient_chat_id)
                p.setEnabled(False, put=True)
                debugMessage = '❗ Input user disactivated: ' + p.getFirstNameLastNameUserName()
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
    import render_results
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

def terminateHand(g, expired=False, forcedExitName=None, personWon=True):
    if expired or forcedExitName:
        if expired:
            msg = "{} The game has terminated because it has been idle for too long".format(icons.TIME_ICON)
        else: #forcedExitName
            msg = "The game has terminated because {} exited.".format(forcedExitName)
        broadcastMsgToPlayers(g, msg)
        redirectPlayersToState(g, 1)
        g.resetOrDeleteGame()
        return
    msg = ''
    if g.isDemoMode():
        p_id = g.getCurrentPlayerId()
        p = person.getPersonById(p_id)
        if personWon:
            ruleDescription = autorule.getRuleDescription(g.getGodRule())
            levelStr = "the random lavel" if p.reachedMaxLevel() else "level {}".format(p.getDemoLevel())
            demoMsg = "{0} You won {1}!! {0}\n\n" \
                      "{2} The *secret rule* of the game was:\n{3}".format(
                icons.TROPHY, levelStr, icons.KEY, utility.escapeMarkdown(ruleDescription))
            p.increaseDemoLevel()
        else:
            demoMsg = "😩 You have lost... but you can try again 🤗"
        tell(p_id, demoMsg)
        redirectToState(p, 10)
        g.resetOrDeleteGame()
    else:
        if personWon is False:
            msg += "Game has terminated since all players have been eliminated!\n\n"
        elif g.checkIfCurrentPlayerHasNoCardsLeft():
            handWinnerMsg = "{0} {1} has finished all his/her cards!! {0}".format(icons.TROPHY, g.getCurrentPlayerName())
            broadcastMsgToPlayers(g, handWinnerMsg)
        msg = "{} The *secret rule* of the game was:\n{}".format(icons.KEY, utility.escapeMarkdown(g.getGodRule()))
        broadcastMsgToPlayers(g, msg)
        broadcastGameBoardPlayers(g)
        broadcastGameResultTableToPlayers(g)
        if g.allHandsHaveBeenPlayed():
            finalWinnerMsg = "{} The winner of the game is {}! {}".format(
                icons.TROPHY*3, g.getFinalWinnerName(), icons.TROPHY*3)
            broadcastMsgToPlayers(g, finalWinnerMsg)
            redirectPlayersToState(g, 1)
            g.resetOrDeleteGame()
        else:
            g.initNextHand()
            redirectPlayersToState(g, 30)

def broadcastMsgToPlayers(g, msg, kb=None, exclude = ()):
    for id in g.getPlayersId():
        if id not in exclude:
            tell(id, msg, kb, sleepDelay=True)

def broadcastCardsToPlayers(g, exclude = ()):
    for p_id in g.getPlayersId(excludingGod=True):
        if p_id not in exclude:
            msg = "Here are your cards."
            cards = g.getSinglePlayerCards(p_id, emoji=True)
            kb = utility.distributeElementMaxSize(cards, maxSize = parameters.CARDS_PER_ROW)
            tell(p_id, msg, kb)

def broadcastGameBoardPlayers(g):
    import render_game_board
    file_data = render_game_board.render(g)
    for id in g.getPlayersId():
        sendPhotoData(id, file_data, 'board.png')
        sleep(0.1)

def broadcastWaitingActionToPlayers(g, exclude = (), sleep_time=None):
    for chat_id in g.getPlayersId():
        if chat_id not in exclude:
            sendWaitingAction(chat_id, sleep_time = sleep_time)

def broadcastGameResultTableToPlayers(g):
    broadcastNumberOfCardsOfPlayers(g)
    import render_results
    result_table = g.computeScores()
    file_data = render_results.getResultImage(result_table)
    for id in g.getPlayersId():
        sendPhotoData(id, file_data, 'results.png')
        sleep(0.1)

def redirectPlayersToState(g, new_state, **kwargs):
    for id in g.getPlayersId():
        p = person.getPersonById(id)
        redirectToState(p, new_state, **kwargs)

# ================================
# GO TO STATE 1: Initial Screen
# ================================
def goToState1(p, **kwargs):
    input = kwargs['input'] if 'input' in kwargs.keys() else None
    giveInstruction = input is None
    kb = [[icons.DEMO_MODE], [icons.MULTI_PLAYER_GAME], [icons.INFO]]
    if giveInstruction:
        msg = 'Press {} if you want to play against the computer or ' \
              '{} if you want to enter a multi-player game'.format(
            icons.DEMO_MODE, icons.MULTI_PLAYER_GAME)
        tell(p.chat_id, msg, kb)
    else:
        if input in [icons.INFO]:
            tell(p.chat_id, messages.INSTRUCTIONS)
        elif input == icons.DEMO_MODE:
            redirectToState(p, 10)
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
# GO TO STATE 10: Demo Mode
# ================================
def goToState10(p, **kwargs):
    input = kwargs['input'] if 'input' in kwargs.keys() else None
    giveInstruction = input is None
    level = p.getDemoLevel()
    reachedMaxLevel = p.reachedMaxLevel()
    RANDOM_PLAY_BUTTON = "🎯 RANDOM LEVEL"
    LEVEL_PLAY_BUTTON = "🎯 PLAY LEVEL {}".format(level)
    FIRST_BUTTON = RANDOM_PLAY_BUTTON if reachedMaxLevel else LEVEL_PLAY_BUTTON
    if giveInstruction:
        kb = [[FIRST_BUTTON], [icons.BACK]]
        if reachedMaxLevel:
            msg = '👏 You reached the last level of the game!\n\n' \
                  'Stay tuned for new levels. In the meantime you can play in *random mode*.'
        elif level==1:
            msg = "You can use this mode to practise with several Eleusis rules " \
                  "with increasing levels of complexity.\n\n" \
                  "You can now start with *level 1*."
        else:
            msg = 'You reached *level {}*!'.format(p.getDemoLevel())
        tell(p.chat_id, msg, kb)
    else:
        if input == FIRST_BUTTON:
            if reachedMaxLevel:
                msg = 'Initializing random level'
            else:
                msg = 'Initializing level {}'.format(level)
            tell(p.chat_id, msg)
            sendWaitingAction(p.chat_id)
            while True:
                gameRoomName = 'Demo Mode - {} - {} - {}'.format(
                    level, p.getFirstName(), date_time_util.datetimeStringCET(seconds=True))
                g = game.createGame(gameRoomName, 1)
                if g == None:  # already present
                    sleep(1)
                else:
                    break
            g.addPlayer(p, put=False)
            autorule.initializeDemoGame(g, level)
            broadcastGameBoardPlayers(g)
            logging.debug("Redirecting to 32")
            redirectToState(p, 32)
        elif input == icons.BACK:
            redirectToState(p, 1)
        else: # including input == ''
            tell(p.chat_id, messages.NOT_VALID_INPUT)

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
        msgPlayerJoined = "Player {} joined the game!".format(p.getFirstName())
        broadcastMsgToPlayers(g, msgPlayerJoined)
        if g.readyToStart():
            msgSeatsOccupied = "All seats have been occupied! Setting up the game..."
            broadcastMsgToPlayers(g, msgSeatsOccupied)
            g.initGame()
            redirectPlayersToState(g, 30)
        else:
            msgWaitingForPlayers = "Waiting for {} other players...".format(g.remainingSeats())
            broadcastMsgToPlayers(g, msgWaitingForPlayers)
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
    god_id, god_name = g.getGodIdAndName()
    isGod = p.chat_id == god_id
    if giveInstruction:
        msg = "{} *HAND {}*\n\n".format(icons.HAND, g.getHandNumber())
        if isGod:
            msg += "*You are God!*\n" \
                  "{} Please write down the secret rule of the game as clearly as possible.".format(icons.EYES)
        else:
            msg += "The God of this hand is {}.\n" \
                  "{} S/he is writing down the secret rule of the game...".format(god_name, icons.KEY)
        tell(p.chat_id, msg)
        #broadcastWaitingActionToPlayers(g, exclude=[god_id])
    else:
        if isGod:
            if input == '':
                tell(p.chat_id, messages.NOT_VALID_INPUT)
            else:
                g.setGodRule(input)
                msgChosenRule = "👍 Great, God has chosen the rule!"
                broadcastMsgToPlayers(g, msgChosenRule)
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
    god_id, god_name = g.getGodIdAndName()
    isGod = p.chat_id == god_id
    god_kb = [[icons.YES_BUTTON, icons.NO_BUTTON]]
    if giveInstruction:
        if isGod:
            nextDeckCard = g.getNextStartingCard()
            msg = "You need to select the starting card.\n\n" \
                  "{} Is {} a good starting card?".format(icons.EYES, nextDeckCard)
            tell(p.chat_id, msg, kb=god_kb)
            #broadcastWaitingActionToPlayers(g, exclude=[god_id])
        else:
            msg = "The God is choosing the starting card...".format(god_name)
            tell(p.chat_id, msg)
    else:
        if isGod:
            if input == icons.NO_BUTTON:
                nextDeckCard = g.getNextStartingCard()
                msg = "Ok, let's try with next one.\n{} Is {} a good starting card?".format(icons.EYES, nextDeckCard)
                tell(p.chat_id, msg, kb=god_kb)
            elif input == icons.YES_BUTTON:
                g.acceptStartingCard()
                broadcastGameBoardPlayers(g)
                msgChosenStartingCard = "👍 Great, God has chosen the starting card: {}\n\n" \
                                        "The game hand can now start!".format(g.getStartingCard(emoji=True))
                broadcastMsgToPlayers(g, msgChosenStartingCard)
                g.startGame()
                broadcastCardsToPlayers(g, exclude = [g.getCurrentPlayerId()])
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
    god_id, god_name = g.getGodIdAndName()
    isGod = p.chat_id == god_id
    currentPlayerId, currentPlayerName = g.getCurrentPlayerIdAndName()
    isPlayerTurn = p.chat_id == currentPlayerId
    selected_cards = g.getProposedCards(emoji=True)
    players_command_buttons = [icons.SUBMIT_CARDS_BUTTON, icons.EMPTY_SELECTION_BUTTON, icons.REMOVE_LAST_CARD] if selected_cards else [icons.NO_PLAY_BUTTON]
    players_enabled_prophet = []
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
                if len(selected_cards) == parameters.MAX_NUMBER_OF_PROPOSED_CARDS:
                    msg = "You have selected the following card(s):\n\n{}\n\n" \
                          "{} Please, modify the selected cards or submit " \
                          "(you reached the maximum number of cards you can select).".format(selected_cards_str, icons.EYES)
                else:
                    msg = "You have selected the following card(s):\n\n{}\n\n" \
                          "{} Please, select more cards or submit.".format(selected_cards_str, icons.EYES)
            else:
                msg = "{} Please, select a card " \
                      "or press {} if you think you have no card to play.".format(icons.EYES, icons.NO_PLAY_BUTTON)
            tell(p.chat_id, msg, player_kb)
        else:
            msg = "It's {}'s turn. Let's wait for him/her to propose some card(s)...".format(currentPlayerName)
            tell(p.chat_id, msg, remove_keyboard=isGod)
    else:
        if input in players_enabled_prophet:
            enabled = g.flipPlayerAskToBeAProphet(currentPlayerId)
            if enabled:
                clause = " (if the current Prophet is overthrown)" if g.getCurrentProphetId() else ""
                msg = "{} After you play, you will be asked if you want to be a Prophet{}.".format(icons.CHECK, clause)
            else:
                msg = "{} After you play, you won't be asked if you want to be a Prophet.".format(icons.CANCEL)
            tell(p.chat_id, msg)
            repeatState(p, continuation=True)
        elif isPlayerTurn:
            if input in players_command_buttons:
                if input == icons.SUBMIT_CARDS_BUTTON:
                    redirectPlayersToState(g, 33)
                elif input == icons.EMPTY_SELECTION_BUTTON:
                    g.returnProposedCardsToPlayer()
                    repeatState(p)
                elif input == icons.REMOVE_LAST_CARD:
                    g.returnLastProposedCardToPlayer()
                    repeatState(p)
                elif input == icons.NO_PLAY_BUTTON:
                    redirectPlayersToState(g, 34)
            elif g.isValidCard(input):
                if len(g.getProposedCards())== parameters.MAX_NUMBER_OF_PROPOSED_CARDS:
                    msg = "❗ You have reached the  maximum number of cards you can select. " \
                          "Please, modify the selected cards or submit"
                    tell(p.chat_id, msg)
                else:
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
    judge_id, judge_name, judge_isProphet = g.getCurrentJudgeIdNameIsProphet()
    computer_god_no_prophet = judge_id is None
    god_judge_str = "the Prophet" if judge_isProphet else "God"
    proposed_cards = g.getProposedCards(emoji=True)
    proposed_cards_str = ', '.join(proposed_cards)
    isHumanJudge = p.chat_id == judge_id
    isPlayerTurn = p.chat_id == currentPlayerId
    judge_kb = [[icons.YES_BUTTON, icons.NO_BUTTON]]
    if giveInstruction:
        if isHumanJudge:
            msg = "{} has choosen the following card(s):\n\n{}\n\n" \
                  "{} Do you accept it/them?".format(currentPlayerName, proposed_cards_str, icons.EYES)
            tell(judge_id, msg, judge_kb, one_time_keyboard=True)
        elif isPlayerTurn:
            cards = g.getSinglePlayerCards(currentPlayerId, emoji=True)
            player_kb = None
            if cards:
                player_kb = utility.distributeElementMaxSize(cards, maxSize=parameters.CARDS_PER_ROW)
            msg = "You have choosen the following card(s):\n\n{}\n\n" \
                  "Let's see if {} accepts it/them.".format(proposed_cards_str, god_judge_str)
            tell(currentPlayerId, msg, player_kb, remove_keyboard = player_kb == None)
            if computer_god_no_prophet:
                accepted = autorule.areProposedCardsAccepted(g)
                godAcceptanceCards(g, accepted, currentPlayerName, currentPlayerId)
        else:
            msg = "{} has choosen the following card(s):\n\n{}\n\n" \
                  "Let's see what {} thinks...".format(currentPlayerName, proposed_cards_str, god_judge_str)
            tell(p.chat_id, msg)
    else:
        if isHumanJudge:
            if input in judge_kb[0]:
                if judge_isProphet:
                    g.setLastProphetDecision(input)
                    accepted_3rd_str = "has accepted" if input == icons.YES_BUTTON else "has rejected"
                    accepted_2nd_str = "have accepted" if input == icons.YES_BUTTON else "have rejected"
                    icon = icons.CHECK if input == icons.YES_BUTTON else icons.CANCEL
                    msgGodJudgeProphetOnCards = "{} The prophet {} the cards proposed by {}. " \
                                                "Let's see what God thinks...".format(
                        icon, accepted_3rd_str, currentPlayerName)
                    broadcastMsgToPlayers(g, msgGodJudgeProphetOnCards, exclude=[judge_id])
                    msgProphet = "{} You {} the cards proposed by {}. " \
                                 "Let's see what God thinks...".format(
                        icon, accepted_2nd_str, currentPlayerName)
                    tell(judge_id, msgProphet)
                    redirectPlayersToState(g, 331)
                else: # GOD
                    accepted = input==icons.YES_BUTTON
                    godAcceptanceCards(g, accepted, currentPlayerName, currentPlayerId)
            else:
                tell(p.chat_id, messages.NOT_VALID_INPUT, kb=judge_kb)
        else:
            msg = "{} Please wait for {} to judge {}'s card.".format(icons.EXCLAMATION_ICON, god_judge_str, currentPlayerName)
            tell(p.chat_id, msg)


def godAcceptanceCards(g, accepted, currentPlayerName, currentPlayerId):
    if accepted:
        g.acceptProposedCards()
        msg = "{} God has accepted the card(s) proposed by {}".format(icons.CHECK, currentPlayerName)
        broadcastMsgToPlayers(g, msg, exclude=[currentPlayerId])
        msgPlayer = "{} God has accepted the card(s) you proposed!".format(icons.CHECK)
        tell(currentPlayerId, msgPlayer)
        if checkIfCurrentPlayerHasWonAndTerminateHand(g):
            return
    else:
        newCards = g.rejectProposedCards()
        newCards_str = ', '.join(newCards)
        msg = "{} God has rejected the card(s) proposed by {} who gets {} new penalty cards.".format(
            icons.CANCEL, currentPlayerName, len(newCards))
        broadcastMsgToPlayers(g, msg, exclude=[currentPlayerId])
        msgPlayer = "{} God has rejected the card(s) you proposed. You will get {} new penalty cards: {}".format(
            icons.CANCEL, len(newCards), newCards_str)
        updateCurrentPlayerCards(g, msgPlayer)
        if checkIfPlayerIsEliminatedAndTerminateHand(g):
            return
    broadcastGameBoardPlayers(g)
    askToBeAProphetOrGoToNextTurn(g)

# ================================
# GO TO STATE 331: Game: God judges Prophet on card acceptence/rejection
# ================================
def goToState331(p, **kwargs):
    input = kwargs['input'] if 'input' in kwargs.keys() else None
    g = p.getGame()
    giveInstruction = input is None
    god_id, god_name = g.getGodIdAndName()
    currentPlayerId, currentPlayerName = g.getCurrentPlayerIdAndName()
    isGod = p.chat_id == god_id
    prophetId = g.getCurrentProphetId()
    prophetDecision = g.getLastProphetDecision()
    accepted_rejected_str = "accepted" if prophetDecision == icons.YES_BUTTON else "rejected"
    accepted_rejected_inv_str = "rejected" if prophetDecision==icons.YES_BUTTON else "accepted"
    CONFIRM_EXPLANATION_BUTTON = icons.YES_BUTTON + ": card(s) were correctly {}".format(accepted_rejected_str)
    NO_EXPLANATION_BUTTON = icons.NO_BUTTON + ": card(s) should have been {}".format(accepted_rejected_inv_str)
    god_kb = [[CONFIRM_EXPLANATION_BUTTON], [NO_EXPLANATION_BUTTON]]
    if giveInstruction:
        if isGod:
            msg = "{} Do you agree with the Prophet?".format(icons.EYES)
            tell(p.chat_id, msg, kb=god_kb, one_time_keyboard=True)
    else:
        logging.debug("Input: {}\nAccepted input: {}".format(input, CONFIRM_EXPLANATION_BUTTON))
        if isGod:
            if input == CONFIRM_EXPLANATION_BUTTON:
                if prophetDecision == icons.YES_BUTTON:
                    g.acceptProposedCards(prophetDecision=True)
                    msg = "{} God agrees with the Prophet's decision " \
                          "of accepting the cards proposed by {}.".format(icons.CHECK, currentPlayerName)
                    broadcastMsgToPlayers(g, msg, exclude=[prophetId, currentPlayerId])
                    msgProphet = "{} God agrees with your decision " \
                          "of accepting the cards proposed by {}.".format(icons.CHECK, currentPlayerName)
                    tell(prophetId, msgProphet)
                    msgPlayer = "{} God agrees with the Prophet's decision " \
                          "of accepting your cards.".format(icons.CHECK)
                    tell(currentPlayerId, msgPlayer)
                    if checkIfCurrentPlayerHasWonAndTerminateHand(g):
                        return
                else: # prophetDecision == icons.NO_BUTTON:
                    penaltyCards = g.rejectProposedCards(prophetDecision=True)
                    penaltyCards_str = ', '.join(penaltyCards)
                    msg = "{} God agress with the Prophet's decision " \
                          "of rejecting the cards proposed by {} " \
                          "who gets {} new penalty cards.".format(icons.CHECK, currentPlayerName, len(penaltyCards))
                    broadcastMsgToPlayers(g, msg, exclude=[currentPlayerId])
                    msgPlayer = "{} God agress with the Prophet's decision " \
                          "of rejecting the cards you proposed. " \
                          "You will get {} new penalty cards: {}".format(icons.CHECK, len(penaltyCards), penaltyCards_str)
                    updateCurrentPlayerCards(g, msgPlayer)
                    if checkIfPlayerIsEliminatedAndTerminateHand(g):
                        return
            elif input == NO_EXPLANATION_BUTTON:
                if prophetDecision == icons.YES_BUTTON:
                    #g.rejectProposedCards(prophetDecision=True, getPenaltyCards=True, doubleCardsInPenalty=False)
                    g.rejectProposedCards(prophetDecision=True, getPenaltyCards=False)
                    msg = "{0} God disagrees with the Prophet's decision " \
                          "of accepting the cards proposed by {1}." \
                          "{1} doesn't get any penalty card.".format(icons.CANCEL, currentPlayerName)
                     #     "{1} Will get back the same number of cards proposed."
                    overthrowProphet(g, msg, playerWasWrong=True)
                    if checkIfCurrentPlayerHasWonAndTerminateHand(g):
                        return
                    #if checkIfPlayerIsEliminatedAndTerminateHand(g):
                    #    return
                else:
                    g.acceptProposedCards()
                    msg = "{} God disagrees with the Prophet's decision " \
                          "of rejecting the cards proposed by {}, " \
                          "which was/were in facat correct!".format(icons.CANCEL, currentPlayerName)
                    overthrowProphet(g, msg, playerWasWrong=False)
                    if checkIfCurrentPlayerHasWonAndTerminateHand(g):
                        return
            else:
                tell(p.chat_id, messages.NOT_VALID_INPUT, kb=god_kb)
                return
            broadcastGameBoardPlayers(g)
            askToBeAProphetOrGoToNextTurn(g)
        else:
            msg = "{} Please wait for {} to judge the Prophet's decision.".format(icons.EXCLAMATION_ICON, god_name)
            tell(p.chat_id, msg)

# ================================
# GO TO STATE 34: Game: God or Prophet judges NO-PLAY
# ================================
def goToState34(p, **kwargs):
    input = kwargs['input'] if 'input' in kwargs.keys() else None
    g = p.getGame()
    giveInstruction = input is None
    currentPlayerId, currentPlayerName = g.getCurrentPlayerIdAndName()
    judge_id, judge_name, judge_isProphet = g.getCurrentJudgeIdNameIsProphet()
    god_judge_str = "the Prophet" if judge_isProphet else "God"
    isHumanJudge = p.chat_id == judge_id
    isPlayerTurn = p.chat_id == currentPlayerId
    computer_god_no_prophet = judge_id is None
    if giveInstruction:
        if isHumanJudge:
            cards = g.getSinglePlayerCards(currentPlayerId, emoji=True)
            judge_kb = utility.distributeElementMaxSize(cards, maxSize=parameters.CARDS_PER_ROW)
            judge_kb.insert(0, [icons.CONFIRM_NO_PLAY_BUTTON])
            p.setLastKeyboard(judge_kb)
            msg = "{} claims s/he has no card to play.\n\n" \
                  "{} Please confirm the NO PLAY or select a card which can be played.".format(currentPlayerName, icons.EYES)
            tell(p.chat_id, msg, kb=judge_kb, one_time_keyboard=True)
        elif isPlayerTurn:
            cards = g.getSinglePlayerCards(currentPlayerId, emoji=True)
            player_kb = None
            if cards:
                player_kb = utility.distributeElementMaxSize(cards, maxSize=parameters.CARDS_PER_ROW)
            msg = "You claim you have no card to play.\n\n" \
                  "Let's see what {} thinks...".format(god_judge_str)
            tell(currentPlayerId, msg, player_kb)
            if computer_god_no_prophet:
                alternative_card = autorule.selectOneAcceptedCard(g)
                godAcceptanceNoPlay(g, alternative_card, currentPlayerName, currentPlayerId)
        else:
            msg = "{} claims s/he has no card to play.\n\n" \
                  "Let's see what {} thinks...".format(currentPlayerName, god_judge_str)
            tell(p.chat_id, msg)
    else:
        if isHumanJudge:
            if judge_isProphet:
                g.setLastProphetDecision(input)
                if input == icons.CONFIRM_NO_PLAY_BUTTON:
                    msg = "{} The Prophet agrees that {} has no cards to play.\n\n" \
                          "Let's see what God thinks...".format(icons.CHECK, currentPlayerName)
                    msgPlayer = "{} The Prophet agrees that you have no cards to play.\n\n" \
                          "Let's see what God thinks...".format(icons.CHECK)
                elif g.isValidCard(input):
                    msg = "{} The Prophet does NOT think that {} has no cards to play, " \
                          "and claims that {} is a perfectly valid card.\n\n" \
                          "Let's see what God thinks...".format(
                        icons.CANCEL, currentPlayerName, input)
                    msgPlayer = "{} The Prophet does NOT think that you have no cards to play, " \
                          "and claims that {} is a perfectly valid card.\n\n" \
                          "Let's see what God thinks...".format(
                        icons.CANCEL, currentPlayerName, input)
                else:
                    tell(p.chat_id, messages.NOT_VALID_INPUT, kb=p.getLastKeyboard())
                    return
                broadcastMsgToPlayers(g, msg, exclude=[currentPlayerId])
                tell(currentPlayerId, msgPlayer)
                redirectPlayersToState(g, 341)
            else:
                if input == icons.CONFIRM_NO_PLAY_BUTTON or g.isValidCard(input):
                    alternative_card = None if input == icons.CONFIRM_NO_PLAY_BUTTON else input
                    godAcceptanceNoPlay(g, alternative_card, currentPlayerName, currentPlayerId)
                else:
                    tell(p.chat_id, messages.NOT_VALID_INPUT, kb=p.getLastKeyboard())
        else:
            msg = "{} Please wait for {} to judge the NO PLAY claim.".format(icons.EXCLAMATION_ICON, judge_name)
            tell(p.chat_id, msg)

def godAcceptanceNoPlay(g, alternative_card, currentPlayerName, currentPlayerId):
    if alternative_card==None:
        g.confirmNoPlay()
        msg = "{} God agrees that {} has no card to play, " \
              "so {} of his/her cards are discarded and all the rest are refreshed!".format(
            icons.CHECK, currentPlayerName, parameters.CARDS_DISCOUNTED_ON_CORRECT_NO_PLAY)
        broadcastMsgToPlayers(g, msg, exclude=[currentPlayerId])
        msgPlayer = "{} God agrees that you have no card to play, " \
              "so {} of your cards are discarded and all the rest are refreshed!".format(
            icons.CHECK, parameters.CARDS_DISCOUNTED_ON_CORRECT_NO_PLAY)
        updateCurrentPlayerCards(g, msgPlayer)
        if checkIfCurrentPlayerHasWonAndTerminateHand(g):
            return
    else:
        penaltyCards = g.rejectNoPlay(alternative_card)
        penaltyCards_str = ', '.join(penaltyCards)
        msg = "{0} God has rejected {1}'s claim that no card could be played, " \
              "and declares that {2} is a perfectly valid card. " \
              "{1} will get {3} additional penality cards.".format(
            icons.CANCEL, currentPlayerName, alternative_card, len(penaltyCards))
        broadcastMsgToPlayers(g, msg, exclude=[currentPlayerId])
        msgPlayer = "{0} God has rejected your claim that no card could be played, " \
              "and declares that {1} is a perfectly valid card. " \
              "You will get {2} additional penality cards: {3}".format(
            icons.CANCEL, alternative_card, len(penaltyCards), penaltyCards_str)
        updateCurrentPlayerCards(g, msgPlayer)
        if checkIfPlayerIsEliminatedAndTerminateHand(g):
            return
    broadcastGameBoardPlayers(g)
    askToBeAProphetOrGoToNextTurn(g)


# ================================
# GO TO STATE 341: Game: God judges Prophet on no-play
# ================================
def goToState341(p, **kwargs):
    input = kwargs['input'] if 'input' in kwargs.keys() else None
    g = p.getGame()
    giveInstruction = input is None
    god_id, god_name = g.getGodIdAndName()
    currentPlayerId, currentPlayerName = g.getCurrentPlayerIdAndName()
    isGod = p.chat_id == god_id
    lastProphetResponse = g.getLastProphetDecision()
    no_play_confirmed_by_prophet = lastProphetResponse == icons.CONFIRM_NO_PLAY_BUTTON
    if no_play_confirmed_by_prophet:
        YES_EXPLANATION_BUTTON = icons.YES_BUTTON + ": no card could be played"
        god_commands = [YES_EXPLANATION_BUTTON]
    else:
        YES_EXPLANATION_BUTTON = icons.YES_BUTTON + ": {} is a correct card".format(lastProphetResponse)
        NO_EXPLANATION_BUTTON = icons.NO_BUTTON + ": {} had no valid cards".format(currentPlayerName)
        god_commands = [NO_EXPLANATION_BUTTON, YES_EXPLANATION_BUTTON] #will be added in reverse
    if giveInstruction:
        if isGod:
            cards = g.getSinglePlayerCards(currentPlayerId, emoji=True)
            if not no_play_confirmed_by_prophet:
                cards.remove(lastProphetResponse)
            god_kb = utility.distributeElementMaxSize(cards, maxSize=parameters.CARDS_PER_ROW)
            for c in god_commands:
                god_kb.insert(0, [c])
            p.setLastKeyboard(god_kb)
            msg = "{} Do you agree with the Prophet?\n\n".format(icons.EYES)
            if no_play_confirmed_by_prophet:
                msg += "If you don't agree with the Prophet, " \
                       "please select a valid card that could have been played below."
            else:
                msg += "If you don't agree with the Prophet because the chosen card is incorrect, " \
                       "but there was another one that could have been played, please select it below."
            tell(p.chat_id, msg, kb=god_kb, one_time_keyboard=True)
    else:
        if isGod:
            if input in god_commands:
                if input == YES_EXPLANATION_BUTTON:
                    if no_play_confirmed_by_prophet:
                        g.confirmNoPlay()
                        msg = "{} God agrees with the Prophet that {} has no card to play, " \
                              "so {} of his/her cards are discarded and all the rest are refreshed!".format(
                            icons.CHECK, currentPlayerName, parameters.CARDS_DISCOUNTED_ON_CORRECT_NO_PLAY)
                        broadcastMsgToPlayers(g, msg, exclude=[currentPlayerId])
                        msgPlayer = "{} God agrees with the Prophet that you has no card to play, " \
                              "so {} of your cards are discarded and all the rest are refreshed!".format(
                            icons.CHECK, parameters.CARDS_DISCOUNTED_ON_CORRECT_NO_PLAY)
                        updateCurrentPlayerCards(g, msgPlayer)
                        if checkIfCurrentPlayerHasWonAndTerminateHand(g):
                            return
                    else: #prophet picked a card
                        penaltyCards = g.rejectNoPlay(lastProphetResponse, prophetDecision=True)
                        penaltyCards_str = ', '.join(penaltyCards)
                        msg = "{0} God agrees with the Prophet that {1} had some cards to play," \
                              "and that {2} is a perfectly valid card. " \
                              "{1} will get {3} additional penality cards.".format(
                            icons.CHECK, currentPlayerName, lastProphetResponse, len(penaltyCards))
                        broadcastMsgToPlayers(g, msg, exclude=[currentPlayerId])
                        msgPlayer = "{0} God agrees with the Prophet that you had cards to play," \
                              "and that {1} is a perfectly valid card. " \
                              "You will get {2} additional penality cards: {}".format(
                            icons.CHECK, lastProphetResponse, len(penaltyCards), penaltyCards_str)
                        updateCurrentPlayerCards(g, msgPlayer)
                        if checkIfPlayerIsEliminatedAndTerminateHand(g):
                            return
                else: # NO_EXPLANATION_BUTTON
                    assert no_play_confirmed_by_prophet
                    msg = "{} God disagrees with the Prophet, " \
                          "and agrees with {} that no card could be played. ".format(icons.CANCEL, currentPlayerName)
                    overthrowProphet(g, msg, playerWasWrong=False)
                    if checkIfPlayerIsEliminatedAndTerminateHand(g):
                        return
            elif g.isValidCard(input) and input!=lastProphetResponse:
                if no_play_confirmed_by_prophet:
                    msg = "{} God disagrees with the Prophet that {} had no card to play," \
                          "and declares that {} is a valid card.".format(
                        icons.CANCEL, currentPlayerName, input)
                else: #prophet picked a card
                    msg = "{} God agrees with the Prophet that {} had at least a card to play, " \
                          "but disagrees that {} is a valid card, and claims instead that {} is a valid card.".format(
                        icons.CANCEL, currentPlayerName, lastProphetResponse, input)
                g.appendInProposedCardsAndRemoveFromHand(input, put=False)
                g.acceptProposedCards()
                overthrowProphet(g, msg, playerWasWrong=True)
                if checkIfPlayerIsEliminatedAndTerminateHand(g):
                    return
            else:
                tell(p.chat_id, messages.NOT_VALID_INPUT, kb=p.getLastKeyboard())
                return
            broadcastGameBoardPlayers(g)
            askToBeAProphetOrGoToNextTurn(g)
        else:
            msg = "{} Please wait for {} to judge the Prophet's decision.".format(icons.EXCLAMATION_ICON, god_name)
            tell(p.chat_id, msg)

def updateCurrentPlayerCards(g, msg):
    currentPlayerId = g.getCurrentPlayerId()
    updatePlayerCards(g, currentPlayerId, msg)

def updatePlayerCards(g, currentPlayerId, msg):
    cards = g.getSinglePlayerCards(currentPlayerId, emoji=True)
    if cards:
        player_kb = utility.distributeElementMaxSize(cards, maxSize=parameters.CARDS_PER_ROW)
        tell(currentPlayerId, msg, kb=player_kb)
    else:
        msg += '\n\nYou have no more cards!'
        tell(currentPlayerId, msg, remove_keyboard=True)

def overthrowProphet(g, msg, playerWasWrong):
    currentProphetId, currentProphetName = g.getCurrentProphetIdAndName()
    penaltyCards = g.overthrownProphetAndGivePenaltyCards()
    penaltyCards_str = ', '.join(penaltyCards)
    no_penalty_clause = "No penalty cards are given to {}.".format(g.getCurrentPlayerName())
    msg += "\n\n{} The Prophet {} has been overthrown, " \
           "and gets {} penalty cards.".format(
        icons.THUMB_DOWN, currentProphetName, parameters.CARDS_PENALTY_PROPHET)
    if playerWasWrong:
        msg += '\n\n' + no_penalty_clause
    broadcastMsgToPlayers(g, msg, exclude=[currentProphetId])
    msgProphet = msg + "\n\nYour new cards: {}".format(penaltyCards_str)
    cards = g.getSinglePlayerCards(currentProphetId, emoji=True)
    prophet_kb = utility.distributeElementMaxSize(cards, maxSize=parameters.CARDS_PER_ROW)
    tell(currentProphetId, msgProphet, kb=prophet_kb)

def checkIfCurrentPlayerHasWonAndTerminateHand(g):
    if g.checkIfCurrentPlayerHasNoCardsLeft():
        # game ends because a player finished the cards
        terminateHand(g)
        return True
    return False

def askToBeAProphetOrGoToNextTurn(g):
    if g.checkIfCurrentPlayerCanBeProphet(checkIfAskedEnable=True, put=True):
        redirectPlayersToState(g, 35)
    else:
        broadcastNumberOfCardsOfPlayers(g)
        g.setUpNextTurn()
        redirectPlayersToState(g, 32)

'''
def broadcastNumberOfCardsOfCurrentPlayer(g):
    p_id, p_name = g.getCurrentPlayerIdAndName()
    cards_number = len(g.getSinglePlayerCards(p_id))
    msg = "🖐 {} is left with {} cards.".format(p_name, cards_number)
    broadcastMsgToPlayers(g, msg, exclude=[p_id])
'''

def broadcastNumberOfCardsOfPlayers(g):
    players_cards = g.getPlayersCards()
    god_id = g.getGodPlayerId()
    players_name = g.getPlayersNames()
    msg = "#⃣ Players Cards:"
    for p_id, name in players_name.items():
        if p_id == god_id:
            continue
        msg += "\n • {}: {}".format(name,len(players_cards[p_id]))
    broadcastMsgToPlayers(g, msg)

def checkIfPlayerIsEliminatedAndTerminateHand(g):
    if g.isSuddenDeath():
        g.setCurrentPlayerEliminated()
        p_id, p_name = g.getCurrentPlayerIdAndName()
        msg = "{} has been eliminated!".format(p_name)
        broadcastMsgToPlayers(g, msg, exclude=[p_id])
        msgPlayer = "You have been eliminated!"
        tell(p_id, msgPlayer, remove_keyboard=True)
        if g.areAllPlayersEliminated():
            # game ends because all players (except prophet if exists) have been eliminated
            terminateHand(g, personWon=False)
            return True
    return False

# ================================
# GO TO STATE 35: Game: Ask to be a prophet
# ================================
def goToState35(p, **kwargs):
    input = kwargs['input'] if 'input' in kwargs.keys() else None
    g = p.getGame()
    giveInstruction = input is None
    god_id, god_name = g.getGodIdAndName()
    currentPlayerId, currentPlayerName = g.getCurrentPlayerIdAndName()
    isGod = p.chat_id == god_id
    isPlayerTurn = p.chat_id == currentPlayerId
    player_kb = [[icons.YES_BUTTON, icons.NO_BUTTON]]
    if giveInstruction:
        if isPlayerTurn:
            msg = "{} Do you want to be a Prophet?".format(icons.EYES)
            tell(p.chat_id, msg, player_kb, one_time_keyboard=True)
        else:
            msg = "Let's see if {} wants to be a Prophet...".format(currentPlayerName)
            tell(p.chat_id, msg, remove_keyboard=isGod)
    else:
        if isPlayerTurn:
            if input in [icons.YES_BUTTON, icons.NO_BUTTON]:
                if input == icons.YES_BUTTON:
                    g.setCurrentProphetId(currentPlayerId)
                    msg = "{} Great news: {} is the new Prophet!".format(icons.PROPHET, currentPlayerName)
                    broadcastMsgToPlayers(g, msg)
                    broadcastGameBoardPlayers(g)
                else:
                    msg = "{} has decided not to be a prophet!".format(currentPlayerName)
                    broadcastMsgToPlayers(g, msg)
                broadcastNumberOfCardsOfPlayers(g)
                g.setUpNextTurn()
                redirectPlayersToState(g, 32)
            else:
                tell(p.chat_id, messages.NOT_VALID_INPUT, kb = player_kb)
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
        self.response.write(json.dumps(json.load(urllib2.urlopen(key.BASE_URL + 'getMe'))))

class SetWebhookHandler(webapp2.RequestHandler):
    def get(self):
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
        resp = requests.post(key.BASE_URL + 'getWebhookInfo')
        logging.info('GetWebhookInfo Response: {}'.format(resp.text))
        self.response.write(resp.text)

class DeleteWebhook(webapp2.RequestHandler):
    def get(self):
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
                # hand terminates becuase game has expired
                terminateHand(g, expired = True)

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
                return
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
                return
            if text == '/info':
                tell(chat_id, messages.INSTRUCTIONS)
                return
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
                    msg = "Hi {}, welcome back to EleusisBot!\n".format(p.getFirstName())
                    tell(p.chat_id, msg)
                    p.setEnabled(True, put=False)
                    restart(p)
            elif text.startswith("/exit"):
                g = p.getGame()
                if g==None:
                    msg = "{} You are not in a game!".format(icons.EXCLAMATION_ICON)
                    tell(p.chat_id, msg)
                else:
                    # hand terminates because a player has exited
                    terminateHand(g, forcedExitName=p.getFirstName(), personWon=False)
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
    import sys, traceback
    from google.appengine.ext.db import InternalError
    exc_type, exc_value, exc_traceback = sys.exc_info()
    if exc_type == InternalError:
        msg = 'Cought GAE db internal error (ignored)'
        tell(key.FEDE_CHAT_ID, msg, markdown=False)
        logging.info(msg)
        return
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
