import json

from pymongo import MongoClient
import cherrypy
from os import path, curdir

class StackMirror(object):
    db = MongoClient("localhost", 27017)["stack_questions"]

    @cherrypy.expose
    def index(self):
        return file("index.html")

    @cherrypy.expose
    def update(self, timestamp=None):
        try:
            timestamp = int(timestamp)
        except TypeError:
            timestamp = 0
        coll = self.db["questions"]
        records = coll.find({"fetched": {"$gt":timestamp}}).sort(
                    "fetched", direction=-1)
        return json.dumps([e for e in records])

cherrypy.quickstart(StackMirror(), "/", { "/static": {
                        "tools.staticfile.on": True,
                        "tools.staticfile.filename" : path.join(path.abspath(curdir), "realtime.js")}})
