# -*- coding: utf-8 -*-

from google.appengine.ext import ndb

import game
import utility


#------------------------
# TMP_VARIABLES NAMES
#------------------------
VAR_PREVIOUS_INPUT = 'previous_input'
VAR_LAST_KEYBOARD = 'last_keyboard'
VAR_LAST_STATE = 'last_state'
VAR_GAME_ROOM = 'game_room'
VAR_CREATE_GAME = 'create_game' # {'stage': int, 'game_name': string, 'number_players': int, ...}
#------------------------
# Person class
#------------------------

class Person(ndb.Model):
    chat_id = ndb.IntegerProperty()
    name = ndb.StringProperty()
    last_name = ndb.StringProperty()
    username = ndb.StringProperty()
    state = ndb.IntegerProperty(default=-1, indexed=True)
    last_mod = ndb.DateTimeProperty(auto_now=True)
    enabled = ndb.BooleanProperty(default=True)
    game_room = ndb.StringProperty()
    tmp_variables = ndb.PickleProperty()
    demo_level = ndb.IntegerProperty(default=1)

    def getId(self):
        return self.key.id()

    def getPropertyUtfMarkdown(self, property, escapeMarkdown=True):
        if property == None:
            return None
        result = property.encode('utf-8')
        if escapeMarkdown:
            result = utility.escapeMarkdown(result)
        return result

    def getFirstName(self, escapeMarkdown=True):
        return self.getPropertyUtfMarkdown(self.name, escapeMarkdown=escapeMarkdown)

    def getLastName(self, escapeMarkdown=True):
        return self.getPropertyUtfMarkdown(self.last_name, escapeMarkdown=escapeMarkdown)

    def getUsername(self, escapeMarkdown=True):
        return self.getPropertyUtfMarkdown(self.username, escapeMarkdown=escapeMarkdown)

    def getFirstNameLastName(self, escapeMarkdown=True):
        if self.last_name == None:
            return self.getFirstName(escapeMarkdown=escapeMarkdown)
        return self.getFirstName(escapeMarkdown=escapeMarkdown) + \
               ' ' + self.getLastName(escapeMarkdown=escapeMarkdown)

    def getFirstNameLastNameUserName(self, escapeMarkdown=True):
        result = self.getFirstName(escapeMarkdown =escapeMarkdown)
        if self.last_name:
            result += ' ' + self.getLastName(escapeMarkdown = escapeMarkdown)
        if self.username:
            result += ' @' + self.getUsername(escapeMarkdown = escapeMarkdown)
        return result

    def setGameRoom(self, name, put=False):
        self.game_room = name
        if put:
            self.put()

    def getGameRoom(self, escapeMarkdown=True):
        return self.getPropertyUtfMarkdown(self.username, escapeMarkdown=escapeMarkdown)

    def getGame(self):
        if self.game_room:
            return game.getGame(self.game_room)

    def setLastKeyboard(self, kb, put=True):
        self.setTmpVariable(VAR_LAST_KEYBOARD, value = kb, put = put)

    def getLastKeyboard(self):
        return self.getTmpVariable(VAR_LAST_KEYBOARD)

    def setName(self, input, put=False):
        self.name = input.decode('utf-8')
        if put:
            self.put()

    def setLastName(self, input, put=False):
        self.last_name = input.decode('utf-8')
        if put:
            self.put()

    def setTmpVariable(self, var_name, value, put=False):
        self.tmp_variables[var_name] = value
        if put:
            self.put()

    def getTmpVariable(self, var_name, initValue=None):
        if var_name in self.tmp_variables:
            return self.tmp_variables[var_name]
        self.tmp_variables[var_name] = initValue
        return initValue

    def updateInfo(self, name, last_name, username, put=True):
        modified = False
        if self.name.encode('utf-8') != name:
            self.name = name
            modified = True
        #if self.last_name.encode('utf-8') != last_name:
        #    self.last_name = last_name
        #    modified = True
        if (self.username!=username):
            self.username = username
            modified = True
        if put and modified:
            self.put()

    def setEnabled(self, enabled, put=False):
        self.enabled = enabled
        if put:
            self.put()

    def setState(self, newstate, put=True):
        #self.last_state = self.state
        self.state = newstate
        if put:
            self.put()

    def getDemoLevel(self):
        return self.demo_level

    def reachedMaxLevel(self):
        import autorule
        return self.getDemoLevel()>autorule.getMaxLevel()

    def increaseDemoLevel(self):
        if not self.reachedMaxLevel():
            self.demo_level += 1

    def removeTmpVariable(self, var_name, put=False):
        self.tmp_variables.pop(var_name, None)
        if put:
            self.put()

    def initTmpVars(self):
        self.tmp_variables = {}


def removeGameFromPeople(playerIdList):
    playerIdListStr = [str(id) for id in playerIdList]
    players = ndb.get_multi([ndb.Key(Person, k) for k in playerIdListStr])
    for p in players:
        p.setGameRoom(None)
    create_futures = ndb.put_multi_async(players)
    ndb.Future.wait_all(create_futures)

def getPersonById(chat_id):
    return Person.get_by_id(str(chat_id))

def addPerson(chat_id, name, last_name, username):
    p = Person(
        id=str(chat_id),
        chat_id=chat_id,
        name=name,
        last_name = last_name,
        username = username
    )
    p.initTmpVars()
    p.put()
    return p


def resetAll():
    all_people = Person.query().fetch()
    for p in all_people:
        p.setGameRoom(None)
        p.demo_level = 1
    create_futures = ndb.put_multi_async(all_people)
    ndb.Future.wait_all(create_futures)