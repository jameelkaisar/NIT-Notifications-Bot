from urllib.request import Request, urlopen
from urllib.parse import quote
from bs4 import BeautifulSoup
from pymongo import MongoClient
from time import sleep

from os import environ



def get_source(url):
  try:
    with urlopen(Request(url, headers = { 'User-Agent' : 'Mozilla/5.0 (Windows NT 6.1; Win64; x64)' })) as response:
        source = response.read()
    return source
  except:
    return None


def get_file(url, path):
  try:
    urlretrieve(url, path)
    return True
  except:
    return False


def get_db(client):
  db = client['NIT_Notifications']
  col = db['Notifications']
  return col


def init_db(col, notifications):
  col.insert_one({'_id': 0, 'total': 0})
  total = col.find_one({'_id': 0}, {'_id': 0, 'total': 1})['total']
  for title, date, link in reversed(notifications):
    total = col.find_one({'_id': 0}, {'_id': 0, 'total': 1})['total']
    col.insert_one({'_id': total+1, 'title': title, 'date': date, 'link': link})
    col.update_one({'_id': 0}, {'$set': {'total':  total+1}})


def check_db(col, notifications):
  new_notif = []
  old_notif = [notif['link'] for notif in col.find({}, {'_id': 0, 'link': 1}).sort('_id')[1:]]
  for title, date, link in reversed(notifications):
    if link in old_notif:
      continue
    else:
      new_notif.append((title, date, link, ))
      total = col.find_one({'_id': 0}, {'_id': 0, 'total': 1})['total']
      col.insert_one({'_id': total+1, 'title': title, 'date': date, 'link': link})
      col.update_one({'_id': 0}, {'$set': {'total':  total+1}})
  return new_notif


def send_notif(new_notif):
  for title, date, link in new_notif:
    title = title.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    caption = "<b>" + title + "</b>\nDate: " + date
    for id in IDS:
      url = f"https://api.telegram.org/bot{TOKEN}/sendDocument?chat_id={quote(id)}&document={quote(link)}&caption={quote(caption)}&parse_mode={quote('HTML')}"
      try:
        urlopen(Request(url))
      except Exception as err:
        try:
          text = type(err).__name__ + ":" + err + "\nURL: " + url
          print(text)
          urlopen(Request(f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={quote(ADMIN)}&text={quote(text)}"))
        except:
          pass
  print("Notification(s) Sent!")



NLINK = environ["NLINK"]
MONGO = environ["MONGO"]
TOKEN = environ["TOKEN"]
IDS = environ["IDS"].split(',')
ADMIN = environ["ADMIN"]

source = get_source(NLINK)
soup = BeautifulSoup(source, 'html.parser')
notifications = [(notification.find('a').getText().strip(), notification.find_all('td')[-1].getText().strip(), ("https://nitsri.ac.in/Pages/" if notification.find('a').get('href')[-4:].lower() == ".pdf" else "") + notification.find('a').get('href')) for notification in soup.find('table', {'id': 'customers'}).find_all('tr')[1:] if notification.find('a') is not None]

client = MongoClient(MONGO)
col = get_db(client)

# init_db(col, notifications)

while True:
  source = get_source(NLINK)
  soup = BeautifulSoup(source, 'html.parser')
  notifications = [(notification.find('a').getText().strip(), notification.find_all('td')[-1].getText().strip(), ("https://nitsri.ac.in/Pages/" if notification.find('a').get('href')[-4:].lower() == ".pdf" else "") + notification.find('a').get('href')) for notification in soup.find('table', {'id': 'customers'}).find_all('tr')[1:] if notification.find('a') is not None]
  new_notif = check_db(col, notifications)
  if new_notif != []:
    print("New Notification(s) Received!")
    send_notif(new_notif)
  else:
    print("No New Notifications!")
  sleep(15 * 60)

