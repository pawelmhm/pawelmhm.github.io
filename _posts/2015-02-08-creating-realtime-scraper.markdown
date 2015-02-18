---
layout: post
title:  "Creating simple realtime app with Celery, CherryPy and MongoDb."
date:   2015-02-15 14:34:42
categories: python
author: Pawel Miech
keywords: celery, cherrypy, mongodb, python, javascript
---

In this post I'd like to create demo realtime Stack Overflow mirror with 
[Celery](http://www.celeryproject.org/), [CherryPy](http://www.cherrypy.org/)
and MongoDB. By realtime I mean that app will fetch results
from remote resource in short intervals, and it will display results 
in simple one page js-html app without user clicking browser refresh button.

Design for the whole project is quite simple. First we'll create 
basic HTTP client that will connect to [Stack Overflow xml feed](http://stackoverflow.com/feeds) and parse results.
The client itself will be synchronous, created with python-requests,
but it will be executed as periodic task running with Celery beat scheduler. 
It will run at regular intervals, check if there are new questions in SO, if there
are, it will insert them into database.

To this I'll add simple REST-ful backend that will return results in JSON.
Endpoint will accept timestamp parameter, API will return all results
fetched from Stack Overflow after time designated by timestamp. I'm going
to use CherryPy because it's simple and easy to get started with. 
CherryPy has really gentle learning curve, if you know some Python you can get
up and running in matter of minutes, design of framework seems intuitive, there
is no overheard of settings, it does not enforce any design paradigm, it
gives you freedom to do what you'd like to do.

Our CherryPy app will simply serve static index.html file on root resource,
it will serve static js script on /static url, and it will have one endpoint 
/update that will return results fetched by SO client after certain timestamp. 

Finally I'll add some frontend to whole mixture - trivial JS script polling our
/update endpoint and appending (or actually prepending) results to DOM. I'm 
going to use poling instead of websockets, because it's a bit easier to start
with polling, you remain on the level of simple HTTP GET without having 
to setup websockets server. It also seems like polling is in wider use, 
while writing this post I checked Twitter implementation of timeline and 
it seems that it uses polling in the background. 
If open dev tools while on Twitter timelien, you'll see plain AJAX requests 
taking place in the background polling with regular intervals. 

## Simple Stack Overflow Scraper

Fist let's write a client that will parse Stack Overflow feed and get all 
new questions for us. Recent questions feed is located at: http://stackoverflow.com/feeds,
it's plain rss xml, that we can easily parse by using xpaths. If you prefer
BeautifulSoup or some other library, nothing should stop you from using it!
I prefer xpaths only because I use them quite often so I'm familiar with them.

{% highlight python %}

# stack_scrap.py

import re
from time import time
from hashlib import sha224

import requests
from lxml import etree
from pymongo import  MongoClient
from pymongo.errors import DuplicateKeyError

def questions():
    feed_url = "http://stackoverflow.com/feeds"
    res = requests.get(feed_url)
    # remove namespace because they are incovenient
    xmlstring = re.sub('xmlns="[^"]+"', u'', res.text)
    xmlstring = xmlstring.encode('utf8')
    root = etree.fromstring(xmlstring)

    client = MongoClient("localhost", 27017)
    db = client["stack_questions"]
    coll = db["questions"]

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

{% endhighlight %}

The script simply visits feed and extracts title, link and author
of the post, it then stores this data into MongoDB. We use hash of
link [as object id](http://docs.mongodb.org/manual/reference/glossary/#term-objectid) to ensure that duplicate records are not inserted
into collection. When you try to insert duplicate id in mongodb
it stops this operation and returns an error. If this happens
we know that we encountered post that we already have in database,
new questions were added to db, and we are starting so see old content
and we can stop.

You can call 'questions' function, run it normally and perhaps
print some results to see if it works ok.

## Making our client execute periodically

Now we would like to be able to run our script
at regular intervals. As usual there are many ways to do this.
You can set it up as cron job or you can even use Python's time.sleep()
if you want to be really pythonic. I'm going to use Celery. Celery is 
an asynchronous task runner, it allows you to turn your function into
a task that will be executed in the background. It will nicely handle all
problems with your script, it can retry task, report problems log what happens
etc. Running your process in the background and having something that
manages is properly is huge benefit, your server app can just forget about
this task, it can do its thing as it normally does without minding task 
running in the background. 

Turning our Stack scraper into Celery task is easy, we just need to create 
Celery app instance and decorate our task with Celery 'task' decorator.

{% highlight python %}

# stack_scrap.py

from celery import Celery
app = Celery("hello world")
app.config_from_object("celeryconfig")

@app.task
def questions():
    feed_url = "http://stackoverflow.com/feeds"
    # rest of our code stays the same

{% endhighlight %}

We'll use following Celery config:


{% highlight python %}

# celeryconfig.py

from datetime import timedelta

CELERYBEAT_SCHEDULE = {
    "poll_SO": {
        "task": "stack_scrap.questions",
        "schedule": timedelta(seconds=30),
        "args": []
    }
}

{% endhighlight %}
You need to call it with

{% highlight bash %}

> celery -A stack_scrap worker -B --loglevel=INFO

{% endhighlight %}

You should in logs that Celery is up and running, scheduling task
at regular invervals:


{% highlight bash %}

[2015-02-15 19:20:37,511: INFO/Beat] Scheduler: Sending due task poll_SO (stack_scrap.questions)
[2015-02-15 19:20:37,528: INFO/MainProcess] Received task: stack_scrap.questions[bba18f4d-ada6-4efa-a490-7fa1e355223d]

{% endhighlight %}
If you open mongo shell and check yout 'questions' collection in 'stack_questions'
database you'll see new posts inserted.

## Create web app 
We now have a script that pings Stack Overflow and checks if there are 
new questions in xml feed. Now time to actually display results
in a browser. 

First we need a server that will server some static assets 
(our index.html and js) and will return posts from database.
This can be written with CherryPy in a matter of minutes,
what is cool about CherryPy is that it looks like plain old
python, it doesn't read like a framework at all. 


{% highlight python %}

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

{% endhighlight %}

You can start our app just like you'd run any other python script, 
this is all you need to start it

{% highlight bash %}

> ~/github_blog/pawelmhm.github.io/_code$ python site.py 
[15/Feb/2015:19:51:31] ENGINE Listening for SIGHUP.
[15/Feb/2015:19:51:31] ENGINE Listening for SIGTERM.
[15/Feb/2015:19:51:31] ENGINE Listening for SIGUSR1.
[15/Feb/2015:19:51:31] ENGINE Bus STARTING
[15/Feb/2015:19:51:31] ENGINE Started monitor thread 'Autoreloader'.
[15/Feb/2015:19:51:31] ENGINE Started monitor thread '_TimeoutMonitor'.
[15/Feb/2015:19:51:31] ENGINE Serving on http://127.0.0.1:8080
[15/Feb/2015:19:51:31] ENGINE Bus STARTED

{% endhighlight %}

## Finally let's add some JavaScript

Now that our server is listening for connections we can add some client
site code. We need a way to update index.html page with results of our crawl.
How a browser is going to get results that are up to date? We don't
want to just click refresh, our app has to be realtime. Users don't like
to click refresh, they can forget about clicking refresh and loose some 
crucial content. One solution would be websockets, other easier solution
would involve using JavaScript setTimeout and just repeatingly calling 
our server /update endpoint. 

Our client-side code will send ajax GET request to /update endpoint with
timestamp as sole parameter. When the page first loads timestamp will be
set to zero and script will fetch all results from database. After
fetching results it will append them to DOM and add 'modified' attribute
to div. In subsequent calls it will take value of 'modified' attribute and use 
it to query server. So our JS should essentialy say something like:
"hey, server, give me all results fetched after I last updated DOM".
If server doesn't have anything it will respond with blank answer and
script will do nothing, if there are some new questions fetched by our
celery stack scraper it will append them to DOM, and refresh 'modified'
atribute.

Polling part will look like this:

{% highlight javascript %}

function doPoll() {
    $.ajax({
        url: "update",
        data: {
            "timestamp": parseInt($('#realtime').attr("modified") / 1000) || 0
        }
    }).done(function (data) {
        append_to_dom(data);
    }).always(function () {
        setTimeout(doPoll, 5000);
    })
}

{% endhighlight %}

We'll use jQuery [always](http://api.jquery.com/deferred.always/) so that the 
code will set timeouts even in case of failures. 

Part appending to DOM is rather typical, you could use some js templates, 
like Mustache to make code cleaner and more readable, generating DOM
from string is probably bad practice but we'll do this here for the
sake of simplicity.

Full JavaScript code:

{% highlight javascript %}
// realtime.js
"use strict";

function append_to_dom(data) {
    var data = JSON.parse(data)
    if (data.length == 0) {
        return
    }
    var blocks = data.map(function (question) {
        var block = "<div class='row'><div><span><a href='" + question.link;
        block += "'>" + question.title + "</span></a></div>";
        block += "<div><small>" + question.author + " "
        block += question.fetched + "</small></div></div>";
        return block;
    });
    $("#realtime").prepend(blocks).hide().fadeIn();
    $("#realtime").attr("modified", Date.now());
}

function doPoll() {
    $.ajax({
        url: "update",
        data: {
            "timestamp": parseInt($('#realtime').attr("modified") / 1000) || 0
        }
    }).done(function (data) {
        append_to_dom(data);
    }).always(function () {
        setTimeout(doPoll, 5000);
    })
}


$(document).ready(function () {
    doPoll();
})

{% endhighlight %}

At this point it's ready, you should start your celery scraper,
launch python site, and you'll see SO questions displayed.

![screenshot]({{site.url}}/_code/out.ogv)
