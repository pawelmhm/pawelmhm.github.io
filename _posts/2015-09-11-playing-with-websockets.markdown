---
layout: post
title:  "Creating Websockets Chat with Python"
date:   2016-01-02 14:34:42
categories: python websockets 
author: Pawel Miech
keywords: python websockets twisted autobahn
---

In this post I'm going to write simple chat roulette application using websockets. 
App will consist of very basic user interface with some HTML + JavaScript. When I say "basic"
I really mean it, it's going to be just input box and vanilla JS creating websocket connection.
On the backend side app will have websocket server managing realtime communication between clients.

Websockets are one of the coolest technologies in recent years. They are getting popular mostly because
they allow two-way communication between server and browser. In traditional HTTP application client
sends requests and server issues response after which their exchange is terminated. This model is 
totally okay for most web apps, but it is inefficient for applications that require realtime communication.
[RFC 6455](https://tools.ietf.org/html/rfc6455#section-1.7) is probably most detailed introduction to
websockets specs.

If you'd like to write websocket applications in Python there are couple of choices. If you're 
Django user there [are Channels](http://channels.readthedocs.org/en/latest/), for Flask there is [flask-SocketIO](https://flask-socketio.readthedocs.org/en/latest/).
Both solutions are trying to extend existing web frameworks to allow for usage of websockets. 
[Python Tornado](http://www.tornadoweb.org/en/stable/) on the other hand is a whole web framework built
for realtime asynchronous applications using websockets.

One of the most mature implementations of websockets is [Autobahn-Python](http://autobahn.ws/python/index.html). 
Autobahn websockets implementation supports both Twisted and Asyncio. I'm going to use [Twisted](https://twistedmatrix.com/trac/)
implementation. Why do I think Autobahn + Twisted is worth writing about?

* Twisted is oldest and most stable asynchronous solution for Python, it is still actively developed
(e.g. just recently most components finally gained Python 3 support) and still grows quite quickly (e.g.
there is work on adding [HTTP2 support to Twisted](https://twistedmatrix.com/trac/ticket/7460))
* Twisted is built with asynchronous model at the core, this is absolutely crucial for websocket applications that need
to deal with long-living persistent connection from client


## Hello websocket

Before we actually start with development of server side websockets we'll need to 
set up something that is going to serve index.html file with client side JavaScript + HTML
handling user interaction with your websocket server.

Serving static file with Twisted is trivial and looks like this.

{% highlight python %}

import sys
from twisted.web.static import File
from twisted.python import log
from twisted.web.server import Site
from twisted.internet import reactor

log.startLogging(sys.stdout)
root = File(".")
site = Site(root)
reactor.listenTCP(8080, site)
reactor.run()

{% endhighlight %}

Save this as server.py and create index.html file in same directory. Index.html can be blank for now,
we will write HTML in a moment. 

Now let's actually add some websockets to the mix.

{% highlight python %}

import sys
from twisted.web.static import File
from twisted.python import log
from twisted.web.server import Site
from twisted.internet import reactor

from autobahn.twisted.websocket import WebSocketServerFactory, \
    WebSocketServerProtocol

from autobahn.twisted.resource import WebSocketResource


class SomeServerProtocol(WebSocketServerProtocol):
    def onConnect(self, request):
        print("some request connected {}".format(request))

    def onMessage(self, payload, isBinary):
        self.sendMessage("message received")


if __name__ == "__main__":
    log.startLogging(sys.stdout)

    # static file server seving index.html as root
    root = File(".")

    factory = WebSocketServerFactory(u"ws://127.0.0.1:8080")
    factory.protocol = SomeServerProtocol
    resource = WebSocketResource(factory)
    # websockets resource on "/ws" path
    root.putChild(b"ws", resource)

    site = Site(root)
    reactor.listenTCP(8080, site)
    reactor.run()

{% endhighlight %}

Above code adds simple websockets protocol that is just responding to every
message with pretty stupid message: "message received". It's no big deal, but 
it's pretty nice because at this point you actually have working websockets
server. There is no client side websockets code yet, but you can test your server
with some command line websockets clients or browser extension, e.g. with 
["Simple WebSocket Client" Chrome extension](https://chrome.google.com/webstore/detail/simple-websocket-client/pfdhoblngboilpfeibdedpjgfnlcodoo?hl=en). 
Just run your server.py and ping ws://localhost:8080/ws from Chrome extension.

## Add client side JavaScript

Now that we have working websockets server we can create our client. We need
two things: input box where user can write some strings that are going
to be transmitted to server; and JavaScript code creating websockets connection
and sending data to our websockets server after some UI event occurs.

Mozilla Developer Network has some good [docs about this topic](https://developer.mozilla.org/en-US/docs/Web/API/WebSockets_API/Writing_WebSocket_client_applications), I'm going to use
vanilla JS, but you can just as well use jQuery or even some specialized 
library for websockets (e.g Socket-IO).

Below is our index html. Our JS code
does following things. First it creates websocket instance and defines
some event listener that will tell browser what to do when websocket message
is received. When websocket message is received browser should simply update
"output" node with text content of message. We then fetch input box, add event
listener to "submit" event. When "submit" event happens
browser should use our websocket and send message via this socket.
Sending data is just a matter of making mySocket.send call on WebSocket object.


{% highlight html %}

<!DOCTYPE html>
<html>
<head>
<script type="text/javascript">
    // use vanilla JS because why not
    window.addEventListener("load", function() {
        
        // create websocket instance
        var mySocket = new WebSocket("ws://localhost:8080/ws");
        
        // add event listener reacting when message is received
        mySocket.onmessage = function (event) {
            var output = document.getElementById("output");
            // put text into our output div
            output.textContent = event.data;
        };
        var form = document.getElementsByClassName("foo");
        var input = document.getElementById("input");
        form[0].addEventListener("submit", function (e) {
            // on forms submission send input to our server
            input_text = input.value;
            mySocket.send(input_text);
            e.preventDefault()
        })
    });
</script>
<style>
    /* just some super basic css to make things bit more readable */
    div {
        margin: 10em;
    }
    form {
        margin: 10em;
    }
</style>
</head>
<body>
    <form class="foo">
        <input id="input"></input>
        <input type="submit"></input>
    </form>
    <div id="output"></div>
</body>
</html>

{% endhighlight %}

At this point we have simple websockets server and client that talk to each other. 
Their communication is not very complex. Server just
echoes back message from client. At this point we can start adding some cool features.


## Register and unregister clients

Now that we have basic skeleton of websockets project we can start adding some real functionality.
First thing we need to do is register and unregister clients starting conversations with our server.
To accomplish this we will need to add some factory to our protocol. In Twisted protocols are created
per connection, and they allow you to define event listeners for your application. In case of websockets
this means that your protocol can define event handlers for common scenarios: message being sent, connection being
made, connection lost etc. Factories on the other hand manufacture protocols. They are common to 
multiple protocols, they define how protocols should interact with each other. 

In case of our chat roullette all this means that aside from writing protocol we just need to write 
factory that will define how websocket clients will interact with each other. Of course we also
need to define protocols to specify how are we going to handle typical websockets events.

Let's start with protocol. Our base class will look like this, no real code for now just 
docstring and basic structure of our object.

{% highlight python %}

class SomeServerProtocol(WebSocketServerProtocol):
    def onOpen(self):
        """
        Connection from client is opened. Fires after opening
        websockets handshake has been completed and we can send
        and receive messages.

        Register client in factory, so that it is able to track it.
        Try to find conversation partner for this client.
        """
        pass

    def connectionLost(self, reason):
        """
        Client lost connection, either disconnected or some error.
        Remove client from list of tracked connections.
        """
        pass

    def onMessage(self, payload, isBinary):
        """
        Message sent from client, communicate this message to its conversation partner,
        """
        pass


{% endhighlight %}

Implementation of our protocol would look like this:

{% highlight python %}

class SomeServerProtocol(WebSocketServerProtocol):
    def onOpen(self):
        self.factory.register(self)
        self.factory.findPartner(self)

    def connectionLost(self, reason):
        self.factory.unregister(self)

    def onMessage(self, payload, isBinary):
        self.factory.communicate(self, payload, isBinary)

{% endhighlight %}

Now that we have our protocol we need to define common functionalities per protocol and
add a way to manage interactions between protocols. Our base protocol factory could look like this.


{% highlight python %}

class ChatRouletteFactory(WebSocketServerFactory):
    def register(self, client):
        """
        Add client to list of managed connections.
        """
        pass

    def unregister(self, client):
        """
        Remove client from list of managed connections.
        """
        pass

    def findPartner(self, client):
        """
        Find chat partner for a client. Check if there any of tracked clients
        is idle. If there is no idle client just exit quietly. If there is
        available partner assign him/her to our client.
        """
        pass

    def communicate(self, client, payload, isBinary):
        """
        Broker message from client to its partner.
        """
        pass
        

{% endhighlight %}

and implementation of this could look like this:

{% highlight python %}

class ChatRouletteFactory(WebSocketServerFactory):
    def __init__(self, *args, **kwargs):
        super(ChatRouletteFactory, self).__init__(*args, **kwargs)
        self.clients = {}

    def register(self, client):
        self.clients[client.peer] = {"object": client, "partner": None}

    def unregister(self, client):
        self.clients.pop(client.peer)

    def findPartner(self, client):
        available_partners = [c for c in self.clients if c != client.peer 
                              and not self.clients[c]["partner"]]
        if not available_partners:
            print("no partners for {} check in a moment".format(client.peer))
        else:
            partner_key = random.choice(available_partners)
            self.clients[partner_key]["partner"] = client
            self.clients[client.peer]["partner"] = self.clients[partner_key]["object"]

    def communicate(self, client, payload, isBinary):
        c = self.clients[client.peer]
        if not c["partner"]:
            c["object"].sendMessage("Sorry you dont have partner yet, check back in a minute")
        else:
            c["partner"].sendMessage(payload)

{% endhighlight %}

Now that we have everything defined you only need to tie it together, create instances of objects
and start your program:

{% highlight python %}

if __name__ == "__main__":
    log.startLogging(sys.stdout)

    # static file server seving index.html as root
    root = File(".")

    factory = ChatRouletteFactory(u"ws://127.0.0.1:8080", debug=True)
    factory.protocol = SomeServerProtocol
    resource = WebSocketResource(factory)
    # websockets resource on "/ws" path
    root.putChild(u"ws", resource)

    site = Site(root)
    reactor.listenTCP(8080, site)
    reactor.run()

{% endhighlight %}

You can find full Python source code [here](http://pastebin.com/YJJzreFF), HTML with JS 
is [here](http://pastebin.com/twP1Ksv4). 

With the above code you should be able to talk to yourself via your Chat server. Just open
couple of browser tabs and start writing in each input box. There is probably lots of things
that could be improved, but I just wanted to create very basic demo that could get people started. 
If you do find some bugs or mistakes feel free to ping me.
