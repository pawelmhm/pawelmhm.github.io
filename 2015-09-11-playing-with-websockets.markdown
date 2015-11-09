## websocket interface to unix subprocesses

In this post I'm going to add realtime web interface to Linux bash. The idea 
is pretty simple, there's going to be super basic html page with input box and 
some JavaScript. This webpage will be connected to python server with websockets.
Every message sent to server will be evaluated in Linux shell, the output is going
to be communicated back to webpage and shown in html. 

Websockets server it's going to be written with Autobahn - which seems to be
one of coolest websockets implementations for Python. Autobahn websockets
implementation supports both Twisted and Asyncio, which seems really great.
I'm going to use Twisted implementation mainly because I'm just more familiar
with Twisted. 

## Step 1 - preparations

Before we actually start with websockets we'll need to set up something that 
is going to server our index.html file with input box and JavaScript. As you
may know websockets is different protocol from HTTP so you can't have websockets
and HTTP server running as one single web resource. They need to be separated
somehow. Usually you will probably prefer some WSGI app listening on "/" and
websockets server delegated to some specific path. In this setup you could
have flask app running on root domain and handling some specific routes, and 
websockets server on one specific path e.g. "/ws", so that all requests going
to "http://localhost/" will be handled by Flask, and everything going to
"http://localhost/ws" will be handled by your websockets server. 

For this post however I'd like to go with simpler solution, something that will
spare us the details of settinp up WSGI app, so we'll just serve simple static
index.html file with Twisted. 

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

Save this as server.py and create basic index.html file in same directory. Voila
you have basic index.html served by Twisted.

Now let's actually add some websockets to the mix.

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
    root.putChild(u"ws", resource)

    site = Site(root)
    reactor.listenTCP(8080, site)
    reactor.run()


Above code adds simple websockets protocol that is just responding to every
message with pretty stupid message: "message received". It's no big deal, but 
it's pretty nice because at this point you actually have working websockets
server. There is no client side websockets code yet, but you can test your server
with some command line websockets clients or browser extension, e.g. with 
"Simple WebSocket Client" Chrome extension. 

## Step 2 - add client side JavaScript

Now that we have working websockets server we can create our client. We need
two things: first is input box where user can write some strings that are going
to be transmitted to server; second is JavaScript code creating websockets connection
and sending data to our websockets server.

Mozilla Developer Network has some good [docs about this topic](https://developer.mozilla.org/en-US/docs/Web/API/WebSockets_API/Writing_WebSocket_client_applications), I'm going to use
vanilla JS, but you can just as well use jQuery or even some specialized 
library for websockets.

Below is our index html. We put some JavaScript into html html, our JS code
does following things. First it creates websocket instance and defines
some event listener that will tell browser what to do when websocket message
is received. When websocket message is received browser should simply update
"output" node with text content of message. We then fetch input box, add event
listener to "submit" event occuring on input. When "submit" event happens
browser should use our websocket and send message via this socket.

<!DOCTYPE html>
<html>
<head>
<script type="text/javascript">
    // my JavaScript may be bit rusty, sorry
    window.onload = function() {
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
    };
</script>
<style>
    /* just some super ugly css to make things bit more readable*/
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
    </form>
    <div id="output"></div>
</body>
</html>

At this point we have simple websockets server and client that talk to each other. 
Their communication is not very complex, and is actually bit stupid. Server just
echoes back message from client. At this point we can start adding some cool features.

### Launch subprocesses and communicate output

At this point we can add some websockets interface to our operating system. 
We have simple input box, user can enter output there, it will be sent via
websockets to server. Server will execute commands using python subprocess
module and communicate results back to client.

Of course this is just learning exercise and it is certainly NOT a great idea
for real web app. If you ever expose something like this to external world you're 
basically giving away access to your operating system to anyone in the world. 
If you'd like to really put this idea live somewhere you could somehow sandbox
it though, e.g. running it from inside some docker container with very limited
capabilities. That said here goes our websockets server:

import sys
import subprocess

from twisted.web.static import File
from twisted.python import log
from twisted.web.server import Site
from twisted.internet import reactor

from autobahn.twisted.websocket import WebSocketServerFactory, \
    WebSocketServerProtocol

from autobahn.twisted.resource import WebSocketResource


class SomeServerProtocol(WebSocketServerProtocol):
    def onConnect(self, request):
        # print("some request connected {}".format(request))
        pass

    def onMessage(self, payload, isBinary):
        print("payload {}".format(payload))
        arguments = payload.split()
        try:
            output = subprocess.Popen(arguments, stdout=subprocess.PIPE)
            out, err = output.communicate()
        except OSError:
            out, err = "",  "command invalid"

        if err:
            self.sendMessage("error: {}".format(err))
        else:
            self.sendMessage("{}".format(out))


if __name__ == "__main__":
    log.startLogging(sys.stdout)

    # static file server seving index.html as root
    root = File(".")

    factory = WebSocketServerFactory(u"ws://127.0.0.1:8080")
    factory.protocol = SomeServerProtocol
    resource = WebSocketResource(factory)
    # websockets resource on "/ws" path
    root.putChild(u"ws", resource)

    site = Site(root)
    reactor.listenTCP(8080, site)
    reactor.run()

Now you can run your commands from webpage and they will be executed by user running
your websockets application.

### Launch subprocesses and communicate output

Now that we are able to launch subprocesses via websockets we could go one step
farther and actually start python sessions from our webpage. We could launch
python intepreter from our python websockets server. Sounds pretty cool doesn't it.

Unfortunatenly this is not that simple. Let's try to simply run python command in
our webpage. Suprisingly this will open python session within our webserver. This
is not exactly what we would expect. It would be nice to start some new python
process attached to websocket server, execute commands there and keep its state

For simplicity I'll rewrite previous code to only support python. We'll have live
python interpreter in our webpage (so no more system calls).
