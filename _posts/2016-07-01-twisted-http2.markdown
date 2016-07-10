---
layout: post
title:  "Playing with HTTP 2 on Twisted in Python 3"
date:   2016-07-01 14:34:42
categories: python twisted http2 python3
author: Pawel Miech
keywords: python twisted http2
---

Twisted 16.3.0 will support HTTP 2 server-side. The announcement was made in mailing list
[couple of days ago](http://twistedmatrix.com/pipermail/twisted-python/2016-June/030444.html). Source is available [here](https://twistedmatrix.com/Releases/pre/16.3.0pre1/Twisted-16.3.0rc1.tar.bz2#egg=Twisted[http2,tls]).
Credits for this go to [Cory Benfield](https://github.com/Lukasa), author of other client-side HTTP 2 library [hyper](https://github.com/Lukasa/hyper) and one
of main contributors to python-requests.

This news looks pretty exciting to me so I thought it would be interesting to play around with HTTP 2 server and see how it works. So I'm going to try
and build some simple Twisted website serving content over HTTP 2 and then create bunch of clients (maybe selenium, or maybe just pure Python) connecting to this
sample site. Is there really big difference in performance between HTTP 2 and HTTP 1.1? What are main differences between the two? 

To try out things I'm going to build super simple online book store. My book store will have 3000 science fiction books in store including classics by
Ray Bradbury and Frank Herbert. I gathered by data by simply crawling goodreads.com. My bookstore will have initial page that lists all
stock, each book will have it's own page where you can see some page details. Client will randomly choose 400 books from index list and it will visit
each specific page to see what's there. Will there be any performance difference when page will be loaded over HTTP 2? Or will it be mostly same 
as HTTP 1.1?

## Simple Twisted resource

Twisted web already supports Python 3 so you can easily use Python 3 and 2. For this blog post I'm going to use Python 3.4. 
Version with HTTP2 is still in prerelease (not released officially yet) and HTTP 2 is also optional, so to download it you have to fetch
it from Twisted website (not pip) and tell pip you want optional dependencies.

{%highlight bash %}
> pip install -U https://twistedmatrix.com/Releases/pre/16.3.0pre1/Twisted-16.3.0rc1.tar.bz2#egg=Twisted[http2,tls]
{% endhighlight %}

On Python 2 above command will also download optional dependencies (h2 and tls), but for some reason this doesn't work with Python 3, 
so you need to download h2 manually.

{%highlight bash %}
# download dependency manually when using Python 3
> pip install h2
{% endhighlight %}

For now HTTP 2 support is only available for HTTPS sites. So before to test it we need to create self-signed HTTPS certificate. To generate
certificate you need to run following command:


{%highlight bash %}
> openssl req -x509 -newkey rsa:2048 -keyout key.pem -out cert.pem -days 90 -nodes
{% endhighlight %}
# convert to .crt and install in /usr/shae
> openssl x509 -outform der -in cert.pem -out out.crt
Above generates certificate valid for 90 days without passphrase. After running it you'll need to fill out 
some details about you. You can ignore most of it but keep in mind that some clients will refuse to connect
if common name is not set to host name. So remember to put "localhost" in common name.

So now we have certificate file, with have private key, Twisted with HTTP2 support is installed. We need some data
to play. For this post I'll use data I gathered by crawling goodreads.com website, just bunch of 3000 science fiction books in
json format, you can [download data from here](https://drive.google.com/file/d/0B6myg3n6dqcVcXpPdkJCNUJLOTA/view?pref=2&pli=1).

Let's start with building simple Twisted resource that will serve list of books.

{% highlight python %}
# server.py

import json
import sys

from twisted.internet.ssl import DefaultOpenSSLContextFactory
from twisted.web import server
from twisted.web.resource import Resource
from twisted.internet import reactor
from twisted.python import log

def load_stock():
    with open("books.json") as stock_file:
        return json.load(stock_file)

BOOKS = load_stock()


class Index(Resource):
    def render_GET(self, request):
        return json.dumps(list(BOOKS.keys())).encode("utf8")


class Book(Resource):
    isLeaf = True
    def render_GET(self, request):
        book_id = request.args.get(b"id")
        book = BOOKS.get(book_id[0].decode("utf8"))
        if not book:
            request.setResponseCode(404)
            return b""
        return json.dumps(book).encode("utf8")


if __name__ == "__main__":
    log.startLogging(sys.stdout)

    root = Resource()
    root.putChild(b"", Index())
    root.putChild(b"book", Book())
    site = server.Site(root)
    context_factory = DefaultOpenSSLContextFactory("key.pem", "cert.pem")
    reactor.listenSSL(8080, site, context_factory)
    reactor.run()

{% endhighlight %}

Now that we have our resource, certificate and private keys we can finally launch our Twisted server with HTTP2 support.

{%highlight bash %}
# directory layout looks like this
> tree
.
├── books.json # file with books
├── cert.pem
├── key.pem
└── server.py

0 directories, 4 files
# start Twisted server
> python server.py 
2016-07-03 17:40:22+0200 [-] Log opened.
2016-07-03 17:40:22+0200 [-] Site (TLS) starting on 8080
2016-07-03 17:40:22+0200 [-] Starting factory <twisted.web.server.Site object at 0x7fbc0eeba748>

{% endhighlight %}
So now we have Twisted server that has some alleged HTTP 2 support, but how do we actually test it?
One
To test this out initially let's install curl with http2 support: https://serversforhackers.com/video/curl-with-http2-support.
https://blog.cloudflare.com/tools-for-debugging-testing-and-using-http-2/

doesn't work in chrome? why? Turns out Chrome needs most recent version of OpenSSL. At the moment of writing
this version (1.0.2) is available by default in Ubuntu 16.04. So if you'd like to try out HTTP2 in browser you would
need to either: 1) update your openssl (can be pain and risky as ALL your apps probably use it); 2) 
