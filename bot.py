from urllib.request import Request, urlopen, HTTPError
from urllib.parse import quote, urljoin
from bs4 import BeautifulSoup
from pymongo import MongoClient
from time import sleep
from os import environ



class Notifications():
  def __init__(self, nlink, mongo, dbname, colname, token, ids, admin):
    self.NLINK = nlink
    self.MONGO = mongo
    self.DBNAME = dbname
    self.COLNAME = colname
    self.TOKEN = token
    self.IDS = ids.split(',')
    self.ADMIN = admin

    self.client = MongoClient(self.MONGO)
    self.col = self.get_db()

  def get_soup(self):
    with urlopen(Request(self.NLINK, headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64)'})) as response:
        source = response.read()
    return BeautifulSoup(source, 'html.parser')
  
  def get_db(self):
    db = self.client[self.DBNAME]
    col = db[self.COLNAME]
    return col
  
  def get_notifs(self):
    notifications = []
    soup = self.get_soup()
    rows = soup.find('table', {'id': 'customers'}).find_all('tr')[1:]
    rows = filter(lambda x: x.find('a') != None, rows)

    for row in rows:
      date = row.find_all('td')[-1].getText().strip()
      if date == "":
        date = None
      title = row.find_all('td')[0].getText().strip().replace(u'\xa0', ' ')
      links = row.find_all('a')
      links = list(filter(lambda x: x.getText().strip() != "" and len(x.find_all('a')) == 0, links))
      if (title != "" and len(links) != 0):
        link = links[0].get('href').strip()
        link = urljoin(NLINK, link)
        notifications.append((date, title, link))

    return notifications

  def init_db(self, notifs):
    old_notifs = set([(notif['date'], notif['title'], notif['link']) for notif in self.col.find({}, {'_id': 0, 'date': 1, 'title': 1, 'link': 1})])
    for notif in reversed(notifs):
      if notif not in old_notifs:
        self.col.insert_one({'date': notif[0], 'title': notif[1], 'link': notif[2]})
  
  def check_notifs(self, notifs):
    new_notifs = []
    old_notifs = set([(notif['date'], notif['title'], notif['link']) for notif in self.col.find({}, {'_id': 0, 'date': 1, 'title': 1, 'link': 1})])
    for notif in reversed(notifs):
      if notif not in old_notifs:
        new_notifs.append(notif)
        self.col.insert_one({'date': notif[0], 'title': notif[1], 'link': notif[2]})
    return new_notifs
  
  def send_notifs(self, notifs):
    for notif in notifs:
      title = notif[1].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
      caption = "<b>" + title + "</b>"
      caption += "\n\nLink: " + notif[2]
      if notif[0]:
        caption += "\n\nDate: " + notif[0]
      pdf_flag = False
      if self.is_valid(notif[2]) and self.is_pdf(notif[2]):
        pdf_flag = True

      for id in self.IDS:
        if pdf_flag:
          url = f"https://api.telegram.org/bot{self.TOKEN}/sendDocument?chat_id={quote(id)}&document={quote(notif[2])}&caption={quote(caption)}&parse_mode={quote('HTML')}"
        else:
          url = f"https://api.telegram.org/bot{self.TOKEN}/sendMessage?chat_id={quote(id)}&text={quote(caption)}&parse_mode={quote('HTML')}"
        try:
          urlopen(Request(url))
        except Exception as err:
          try:
            text = type(err).__name__ + ":" + str(err)
            text += "\n\nTitle: " + title
            text += "\n\nLink: " + notif[2]
            print(text)
            urlopen(Request(f"https://api.telegram.org/bot{self.TOKEN}/sendMessage?chat_id={quote(self.ADMIN)}&text={quote(text)}"))
          except:
            pass

    print("Notification(s) Sent!")
  
  def is_valid(self, url):
    r = Request(url)
    r.get_method = lambda: 'HEAD'
    try:
        urlopen(r)
        return True
    except HTTPError:
        return False

  def is_pdf(self, url):
    r = urlopen(url)
    return r.getheader('Content-Type') == 'application/pdf'  

  def poll(self, delay=600):
    # notifs = self.get_notifs()
    # self.init_db(notifs)

    while True:
      notifs = self.get_notifs()
      new_notifs = self.check_notifs(notifs)

      if len(new_notifs) > 0:
        print("New Notification(s) Received!")
        self.send_notifs(new_notifs)
      else:
        print("No New Notifications Received!")

      sleep(delay)



NLINK = environ["NLINK"]
MONGO = environ["MONGO"]
DBNAME = environ["DBNAME"]
COLNAME = environ["COLNAME"]
TOKEN = environ["TOKEN"]
IDS = environ["IDS"]
ADMIN = environ["ADMIN"]



notif = Notifications(NLINK, MONGO, DBNAME, COLNAME, TOKEN, IDS, ADMIN)
notif.poll()
