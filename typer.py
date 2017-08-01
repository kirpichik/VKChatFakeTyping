#encoding: utf-8

from requests import get as request
from time import sleep

# === Константы ===
api = "https://api.vk.com/method/"
tokenPrefix = "?v=5.67&access_token=%s"

setActivity = api + "messages.setActivity" + tokenPrefix + "&type=typing&peer_id=%d"
getChatUsers = api + "messages.getChatUsers" + tokenPrefix + "&chat_id=%d"
addChatUser = api + "messages.addChatUser" + tokenPrefix + "&chat_id=%d&user_id=&d"
getUser = api + "users.get" + tokenPrefix

tokenAddress = "https://oauth.vk.com/token?grant_type=password&client_id=2274003&client_secret=hHbZxrka2uZ6jB1inYsH&username=%s&password=%s"


'''
Добавление пользователей и прочие настройки
'''
def setup():
   num = int(input("Users count: "))
   users = {}
   while num > 0:
      token = str(input("Access-Token(type 'pass' to login using password): "))
      userId = 0
      if token == "pass": # Вход через логин и пароль
         login = str(input("Login: "))
         passwd = str(input("Password: "))
         resp = request(tokenAddress % (login, passwd)).json()

         # Проверка капчи
         while ("error" in resp) and (resp["error"] == "need_captcha"):
            print("Go to %s and type captha here." % (resp["captcha_img"]))
            captcha = str(input("Captcha: "))
            resp = request((tokenAddress % (login, passwd)) + ("&captcha_sid=%s&captcha_key=%s" % (resp["captcha_sid"], captcha))).json()
         
         print("Token:", resp["access_token"])
         token = resp["access_token"]
         userId = resp["user_id"]
      else:
         resp = request(getUser % (token)).json()
         if "error" in resp:
            print("Wrong token.")
            continue
         userId = resp["response"][0]["id"]

      chatId = int(input("Chat id: "))
      users[userId] = {"token": token, "chat_id": chatId}
      num -= 1
      print("Added user: %d. %d users left." % (userId, num))

   delay = int(input("Delay in sec.: "))
   return (users, delay)


'''
Проверка наличия пользователя в чате
token - Пользователь, от имени которого надо проверить наличие другого пользователя в чате.
chatId - ID чата у пользователя, который проверяет.
userId - ID проверяемого пользователя.
'''
def isInChat(token, chatId, userId):
   resp = request(getChatUsers % (token, chatId)).json()
   return ("response" in resp) and (userId in resp["response"])


'''
Попытка вернуть кикнутых союзников из чата
users - Все союзники.
saver - Пользователь, от имени которого пытаемся вернуть.
'''
def tryToSave(users, saver):
   for userId, data in users.items():
      if data["exists"]:
         continue

      resp = request(addChatUser % (users[saver]["token"], users[saver]["chat_id"], userId)).json()
      
      # Неудалось добавить от имени этого пользователя
      if not (("response" in resp) and (resp["response"] == 1)):
         users[saver]["exists"] = False
         return False
      
      print("%d readded!" % (userId))
      data["exists"] = True
   return True


'''
Проверяет наличие всех союзников в чате и если кого-то нет, пытается его вернуть
users - Все союзники.
'''
def checkAllies(users):
   # Проверка на наличие
   allIn = True
   for userId, data in users.items():
      data["exists"] = isInChat(data["token"], data["chat_id"], userId)
      allIn = allIn and data["exists"]
   
   if allIn:
      return
   
   # Пытаемся вернуть
   for userId, data in users.items():
      if data["exists"] and tryToSave(users, userId):
         return
   
   print("Nobody in chat! Game over!")
   exit()


'''
Выставляет статус написания и проверяет наличие союзников в чате
users - Все союзники.
'''
def doWriting(users, delay):
   # Проверка наличия союзников
   checkAllies(users)
   sleep(delay)
   
   # Выставление статуса набора сообщений
   for userId, data in users.items():
      resp = request(setActivity % (data["token"], data["chat_id"] + 2000000000)).json()
      if ("response" in resp) and (resp["response"] == 1):
         print(userId, "typing...")
      else:
         print(userId, "isn't typing!")
   sleep(delay)
   
   # Еще одна проверка
   checkAllies(users)
   sleep(delay)


if __name__ == "__main__":
   try:
      users, delay = setup()
      while True:
         doWriting(users, delay)
   except KeyboardInterrupt:
      print("\nOkay :(")
      exit()
