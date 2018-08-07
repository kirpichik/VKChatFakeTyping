#encoding: utf-8

import threading
import sys

from json.decoder import JSONDecodeError
from requests import get as request
from time import sleep
from inspect import currentframe

# === Константы ===
api = "https://api.vk.com/method/"
tokenPrefix = "?v=5.67&access_token=%s"

setActivity = api + "messages.setActivity" + tokenPrefix + "&type=typing&peer_id=%d"
getChatUsers = api + "messages.getChatUsers" + tokenPrefix + "&chat_id=%d"
addChatUser = api + "messages.addChatUser" + tokenPrefix + "&chat_id=%d&user_id=%d"
getUser = api + "users.get" + tokenPrefix

tokenAddress = "https://oauth.vk.com/token?grant_type=password&client_id=2274003&client_secret=hHbZxrka2uZ6jB1inYsH&username=%s&password=%s"


allies = None
typers = None
needTyping = None
delay = None

# Поток набирающего сообщения аккаунта
class TyperThread(threading.Thread):

   def __init__(self, userId, token, chatId):
      super(TyperThread, self).__init__()
      self.isRunning = True
      self.userId = userId
      self.token = token
      self.chatId = chatId
      self.allies = set()
      self.locker = threading.Lock()

   # Проверяет наличие союзников в чате и возвращает их, в случае необходимости
   def checkAllies(self):
      resp = None
      try:
         resp = request(getChatUsers % (self.token, self.chatId)).json()
      except JSONDecodeError:
         log("JSONDecodeError at line: %d(getting chat users). UserID: %d" % (getLineNumber(), self.userId))
         return
      if "response" not in resp:
         log(self.userId, "can't check chat allies!")
         return
      resp = resp["response"]

      # Проверяем отсутствующих
      self.locker.acquire(blocking=True)
      toAdd = []
      for ally in self.allies:
         if (ally not in resp) and (ally != self.userId):
            toAdd += [ally]
      self.locker.release()

      # Добавляем отсутствующих
      for add in toAdd:
         resp = None
         try:
            resp = request(addChatUser % (self.token, self.chatId, add)).json()
         except JSONDecodeError:
            log("JSONDecodeError at line: %d(readding ally). UserID: %d" % (getLineNumber(), self.userId))
            return

         # Неудалось добавить от имени этого пользователя
         if not (("response" in resp) and (resp["response"] == 1)):
            log(self.userId, "can't add chat allies!")
            return

         log(add, "readded!")


   # Если режим набора активирован, устанавливает статус "набирает сообщение"
   def typing(self):
      if needTyping:
         resp = None
         try:
            resp = request(setActivity % (self.token, self.chatId + 2000000000)).json()
         except JSONDecodeError:
            log("JSONDecodeError at line: %d(start typing). UserID: %d" % (getLineNumber(), self.userId))
            return
         if ("response" in resp) and (resp["response"] == 1):
            log(self.userId, "is typing...")
         else:
            log(self.userId, "isn't typing!")

   def run(self):
      while self.isRunning:
         self.typing()
         sleep(delay)
         self.checkAllies()
         sleep(delay)


   # Обновляет список союзников для данного набирающего
   def updateAllies(self, allies):
      allies = allies.copy()
      self.locker.acquire(blocking=True)
      self.allies = allies
      self.locker.release()

   # Завершает поток
   def finish(self):
      self.isRunning = False
      self.join()


# Уведомляет потоки набирающих о том, что набор союзников изменен
def notifyUpdateAllies():
   for id, data in typers.items():
      data["thread"].updateAllies(allies)


# Справка по командам
def commandHelp(args):
   log('''Commands help:
   help                                           - Show this help
   start                                          - Start typing
   stop                                           - Stop typing
   addallies <id1, id2, ...>                      - Add new allies
   remallies <id1, id2, ...>                      - Remove allies by ID
   addtyper <chat ID> <token or login> [password] - Add new typer
   remtypers <id>                                 - Remove typers by ID
   exit                                           - Exit
   lstypers                                       - List of typers
   lsallies                                       - List of allies
   delay <requests delay>                         - Set requests delay''')


# Устанавливает задержку между запросами
def commandDelay(args):
   global delay

   if len(args) == 0:
      log("Need arguments: <requests delay>")
      return

   try:
      delay = int(args[0])
   except ValueError:
      log("Argument must be a number!")
      return

   log("Delay now:", delay)


# Завершить работу программы
def commandExit(args):
   exit()


# Остановить набор сообщений
def commandStop(args):
   global needTyping

   needTyping = False
   log("Typing stopped.")


# Начать набор сообщений
def commandStart(args):
   global needTyping

   needTyping = True
   log("Typing started.")


# Список аккаунтов, набирающих сообщения
def commandListTypers(args):
   for typer, value in typers.items():
      print(typer)
   log()


# Список союзников
def commandListAllies(args):
   for ally in allies:
      print(ally)
   log()


# Удалить набирающего сообщения
def commandRemoveTypers(args):
   if len(args) < 1:
      log("Need arguments: <id1, id2, ...>")
      return
   for arg in args:
      try:
         id = int(arg)
         typer = typers.pop(id)
         if typer != None:
            typer["thread"].finish()
      except ValueError:
         log("Argument %s must be a number!", arg)
   log("Typers removed.")

# Добавить набирающего сообщения
def commandAddTyper(args):
   if len(args) < 2:
      log("Need arguments: <chat ID> <token or login> [password]")
      return

   token = args[1]
   userId = 0
   chatId = 0
   try:
      chatId = int(args[0])
   except ValueError:
      log("Chat ID must be a number!")
      return

   if len(args) > 2:
      login = args[1]
      passwd = args[2]

      resp = None
      try:
         resp = request(tokenAddress % (login, passwd)).json()
      except JSONDecodeError:
         log("JSONDecodeError at line: %d(getting token from password)." % (getLineNumber()))
         return

      # Проверка капчи
      while ("error" in resp) and (resp["error"] == "need_captcha"):
         print("Go to %s and type captha here." % (resp["captcha_img"]))
         try:
            captcha = str(input("Captcha: "))
         except KeyboardInterrupt:
            log("Login cancelled.")
         try:
            resp = request((tokenAddress % (login, passwd)) + ("&captcha_sid=%s&captcha_key=%s" % (resp["captcha_sid"], captcha))).json()
         except JSONDecodeError:
            log("JSONDecodeError at line: %d(getting captcha)." % (getLineNumber()))
            return
      if ("error" in resp) and (resp["error"] == "invalid_client"):
         log("Login or password incorrect.")
         return
      log("Token:", resp["access_token"])
      token = resp["access_token"]
      userId = resp["user_id"]
   else:
      resp = None
      try:
         resp = request(getUser % (token)).json()
      except JSONDecodeError:
         log("JSONDecodeError at line: %d(getting userID from token)." % (getLineNumber()))
         return
      if "error" in resp:
         log("Wrong token.")
         return
      userId = resp["response"][0]["id"]

   thread = TyperThread(userId, token, chatId)
   thread.daemon = True
   typers[userId] = {"token": token, "chat_id": chatId, "thread": thread}

   allies.update([userId])

   notifyUpdateAllies()
   thread.start()

   log("Typer added.")


# Удалить союзника, которого нужно было возвращать
def commandRemoveAllies(args):
   if len(args) < 1:
      log("Need arguments: <id1, id2, ...>")
      return
   ids = set()
   for arg in args:
      try:
         ids.update([int(arg)])
      except ValueError:
         log("Arguments must be a number!")
         return

   for id in ids:
      if typers.get(id) != None:
         log("Can't remove %d, because it's typer.")
         continue
      allies.discard(id)

   notifyUpdateAllies()
   log("Allies removed.")


# Добавить союзника, которого нужно возвращать
def commandAddAllies(args):
   if len(args) < 1:
      log("Need arguments: <id1, id2, ...>")
      return

   ids = set()
   for arg in args:
      try:
         ids.update([int(arg)])
      except ValueError:
         log("Arguments must be a number!")
         return

   allies.update(ids)
   notifyUpdateAllies()

   log("Allies added.")


# Записывает список команд
def setupCommands():
   return {
      "stop":       commandStop,
      "start":      commandStart,
      "remallies":  commandRemoveAllies,
      "addtyper":   commandAddTyper,
      "remtypers":  commandRemoveTypers,
      "addallies":  commandAddAllies,
      "exit":       commandExit,
      "help":       commandHelp,
      "lsallies":   commandListAllies,
      "lstypers":   commandListTypers,
      "delay":      commandDelay
   }


# Обрабатывает команды
def commandsAccepter(commands):
   while True:
      command = None
      try:
         command = str(input())
      except KeyboardInterrupt:
         exit()
      split = command.split()
      command = split[0]
      if len(command) == 0:
         sys.stdout.write("> ")
         continue
      args = []
      if len(split) > 1:
         args = split[1:]
      executor = commands.get(command.lower())
      if executor == None:
         log("Unknown command. Try type 'help'.")
      else:
         executor(args)


def log(*args):
   sys.stdout.write("\r")
   for arg in args:
      sys.stdout.write(str(arg) + " ")
   sys.stdout.write("\n> ")

def getLineNumber():
   return currentframe().f_back.f_lineno

if __name__ == "__main__":
   allies = set()
   typers = {}
   needTyping = False
   delay = 1

   sys.stdout.write("> ")

   commandsAccepter(setupCommands())

