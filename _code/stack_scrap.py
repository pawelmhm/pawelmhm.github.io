import re
from time import time
from hashlib import sha224

from celery import Celery
import requests
from lxml import etree
from pymongo import  MongoClient
from pymongo.errors import DuplicateKeyError

app = Celery("hello" )
app.config_from_object("celeryconfig")
# celery -A stack_scrap worker -B --loglevel=INFO

@app.task
def questions():
    feed_url = "http://stackoverflow.com/feeds"
    res = requests.get(feed_url)
    # remove namespace because they are incovenient
    xmlstring = re.sub('xmlns="[^"]+"', u'', res.text)
    xmlstring = xmlstring.encode('utf8')
    root = etree.fromstring(xmlstring)

    questions_data = []
    client = MongoClient("localhost", 27017)
    db = client["stack_questions"]
    coll = db["questions_test"]

    for entry in root.xpath(".//entry"):
        author = "".join(entry.xpath(".//author/name/text()"))
        link = "".join(entry.xpath("././/link/@href"))
        title = "".join(entry.xpath("./title/text()"))
        entry = {
            # links should be unique
            # using them as _id will ensure we will
            # not insert duplicate entries
            "_id": sha224(link).hexdigest(),
            "author": author,
            "link": link,
            "title": title,
            "fetched": int(time())
        }
        try:
            coll.insert(entry)
        except DuplicateKeyError:
            # we alredy have this entry in db
            # so stop, no need to parse rest of xml doc
            break

    return questions_data
