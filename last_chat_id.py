#!/usr/bin/env python3
#encoding: utf-8

from json.decoder import JSONDecodeError
from requests import get as request
from time import sleep

api = 'https://api.vk.com/method/'
tokenPrefix = '?v=5.67&access_token=%s'

getChat = api + 'messages.getChat' + tokenPrefix + '&chat_id=%d'

# Проверяет существование чата по его ID
def is_chat_exists(token, chat_id):
   print('Requesting', chat_id)
   if chat_id <= 0:
      return False

   sleep(0.3)
   resp = request(getChat % (token, chat_id)).json()
   if 'error' in resp:
      code = resp['error']['error_code']
      if code == 100:
         return False
      else:
         raise RuntimeError('Received unknown error code: ' + str(code))
   elif 'response' in resp:
      return True
   else:
      raise RuntimeError('Received unknown JSON object: ' + str(resp))


# Выполняет двоичный поиск для нахождения последнего существующего ID чата
def search_for_last_chat_id(token, begin):
   if begin <= 0:
      return 0

   lower_bound = 0
   upper_bound = begin
   while lower_bound != upper_bound:
      compared_value = (lower_bound + upper_bound) // 2
      if is_chat_exists(token, compared_value):
         if not is_chat_exists(token, compared_value + 1):
            return compared_value
         else:
            lower_bound = compared_value + 1
      else:
         if is_chat_exists(token, compared_value - 1):
            return compared_value - 1
         else:
            upper_bound = compared_value


if __name__ == '__main__':
   token = str(input('Token: '))
   begin = int(input('Initial ID: '))
   while is_chat_exists(token, begin):
      begin = int(input('This chat exists, type ID greater than this: '))

   print('Result is:', search_for_last_chat_id(token, begin))

