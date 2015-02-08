import json

from pymongo import  MongoClient

import cherrypy

class StackMirror(object):
    @cherrypy.expose
    def index(self):
        return file("index.html")

    @cherrypy.expose
    def update(self, timestamp=None):
        client = MongoClient("localhost", 27017)
        db = client["stack_questions"]
        coll = db["questions_test"]
        results = [e for e in coll.find()]
        return json.dumps(results)

cherrypy.quickstart(StackMirror())
