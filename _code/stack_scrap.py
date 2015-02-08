import re
import requests
from lxml import etree

from celery import Celery

app = Celery("hello" )
app.config_from_object("celeryconfig")
# app.start()
#  celery -A stack_scrap worker -B --loglevel=INFO

@app.task
def questions():
    feed_url = "http://stackoverflow.com/feeds"
    res = requests.get(feed_url)
    # remove namespace because they are incovenient
    xmlstring = re.sub('xmlns="[^"]+"', u'', res.text)
    xmlstring = xmlstring.encode('utf8')
    root = etree.fromstring(xmlstring)

    questions_data = []
    for entry in root.xpath(".//entry"):
        author = "".join(entry.xpath(".//author/name/text()"))
        link = "".join(entry.xpath("././/link/@href"))
        title = "".join(entry.xpath("./title/text()"))
        questions_data.append({"author": author, "link": link, "title": title})

    print questions

    return questions_data
