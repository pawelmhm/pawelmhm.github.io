---
layout: post
title:  "Making 1 million requests with python-aiohttp"
date:   2016-04-22 6:00
categories: asyncio python aiohttp
author: Paweł Miech
keywords: asyncio, aiohttp, python
edited: 2023-04-13 20:00
---

In this post I'd like to test limits of [python aiohttp](http://aiohttp.readthedocs.org/en/stable/) and check its performance  in 
terms of requests per minute. Everyone knows that asynchronous code performs
better when applied to network operations, but it's still interesting to check this
assumption and understand how exactly it is better and why it's is better. I'm going
to check it by trying to make 1 million requests with aiohttp client. How many requests per minute will aiohttp make?
What kind of exceptions and crashes can you expect when you try to make such volume
of requests with very primitive scripts? What are main gotchas that you need
to think about when trying to make such volume of requests?

## Hello asyncio/aiohttp

Async programming is not easy. It's not easy because using callbacks and thinking in terms of events
and event handlers requires more effort than usual synchronous programming. But
it is also difficult because asyncio is still relatively new and there are few
blog posts, tutorials about it. [Official docs](https://docs.python.org/3/library/asyncio.html)
are very terse and contain only basic examples. There are some Stack Overflow questions 
but not [that many](http://stackoverflow.com/questions/tagged/python-asyncio?sort=votes&pageSize=50)
only 410 as of time of writing (compare with [2 585 questions tagged "twisted"](http://stackoverflow.com/questions/tagged/twisted))
There are couple of nice blog posts and articles about asyncio
over there such as [this](http://aosabook.org/en/500L/a-web-crawler-with-asyncio-coroutines.html),
[that](http://www.snarky.ca/how-the-heck-does-async-await-work-in-python-3-5), [that](http://sahandsaba.com/understanding-asyncio-node-js-python-3-4.html) or perhaps even [this](https://community.nitrous.io/tutorials/asynchronous-programming-with-python-3)
or [this](https://compiletoi.net/fast-scraping-in-python-with-asyncio/). 

To make it easier let's start with the basics - simple HTTP hello world - 
just making GET and fetching one single HTTP response. 

In synchronous world you just do:

{% highlight python %}

import requests

def hello():
    return requests.get("http://httpbin.org/get")

print(hello())


{% endhighlight %}

How does that look in aiohttp?

{% highlight python %}

#!/usr/local/bin/python3.11.2
import asyncio
from aiohttp import ClientSession

async def hello(url: str):
    async with ClientSession() as session:
        async with session.get(url) as response:
            response = await response.read()
            print(response)

asyncio.run(hello("http://httpbin.org/headers"))

{% endhighlight %}

hmm looks like I had to write lots of code for such a basic task...  There is "async def" and "async with" and two "awaits" here. It
seems really confusing at first sight, let's try to explain it then. 

You make your function asynchronous by using [async keyword](https://www.python.org/dev/peps/pep-0492/#await-expression) before function definition and using await
keyword. There are actually two asynchronous operations that our hello() function performs. First
it fetches response asynchronously, then it reads response body in asynchronous manner.

Aiohttp recommends to use ClientSession as primary interface to make requests. ClientSession
allows you to store cookies between requests and keeps objects that are common for
all requests (event loop, connection and other things). Session needs to be closed after using it,
and closing session is another asynchronous operation, this is why you need [`async with`](https://www.python.org/dev/peps/pep-0492/#asynchronous-context-managers-and-async-with)
every time you deal with sessions.

After you open client session you can use it to make requests. This is where another asynchronous
operation starts, downloading request. Just as in case of client sessions responses must be closed
explicitly, and context manager's `with` statement ensures it will be closed properly in all
circumstances.

To start your program you need to make a call to asyncio.run().

It all does sound bit difficult but it's not that complex and looks logical if you spend
some time trying to understand it.

## Fetch multiple urls

Now let's try to do something more interesting, fetching multiple urls one after another.
With synchronous code you would do just:

{% highlight python %}

for url in urls:
    print(requests.get(url).text)

{% endhighlight %}

This is really quick and easy, async will not be that easy, so you should always consider if something more complex
is actually necessary for your needs. If your app works nice with synchronous code maybe there
is no need to bother with async code? If you do need to bother with async code here's how you do
that. Our `hello()` async function stays the same but we need to wrap it in asyncio [`TaskGroup`](https://docs.python.org/3/library/asyncio-task.html) object
and pass whole lists of Future objects as tasks to be executed in the loop.

{% highlight python %}
import asyncio
from aiohttp import ClientSession

async def hello(url: str):
    async with ClientSession() as session:
        async with session.get(url) as response:
            response = await response.text()
            print(response)

async def main():
    tasks = []
    # I'm using test server localhost, but you can use any url
    url = "http://localhost:8000/{}"
    async with asyncio.TaskGroup() as group:
        for i in range(10):
            group.create_task(hello(url.format(i)))

asyncio.run(main()) 

{% endhighlight %}

Now let's say we want to collect all responses in one list and do some 
postprocessing on them. At the moment we're not keeping response body
anywhere, we just print it, let's keep response in the list, and 
print all responses at the end as JSON.

To collect several responses we will use asyncio [`Queue'](https://docs.python.org/3/library/asyncio-queue.html).
Result of each download will be stored inside queue, at the end of processing
results will be printed as JSON.

{% highlight python %}
import asyncio
from aiohttp import ClientSession
import json

async def hello(url: str, queue: asyncio.Queue):
    async with ClientSession() as session:
        async with session.get(url) as response:
            result = {"response": await response.text(), "url": url}
            await queue.put(result)


async def main():
    # I'm using test server localhost, but you can use any url
    url = "http://localhost:8000/{}"
    results = []
    queue = asyncio.Queue()
    async with asyncio.TaskGroup() as group:
        for i in range(10):
            group.create_task(hello(url.format(i), queue))

    while not queue.empty():
        results.append(await queue.get())
    
    print(json.dumps(results))


asyncio.run(main()) 
{% endhighlight %}


### Common gotchas

Now let's simulate real process of learning and let's make mistake in above script and try to debug it,
this should be really helpful for demonstration purposes.

This is how sample broken async function looks like:

{% highlight python %}
# WARNING! BROKEN CODE DO NOT COPY PASTE
async def fetch(url):
    async with ClientSession() as session:
        async with session.get(url) as response:
            return response.read()

{% endhighlight %}

This code is broken, but it's not that easy to figure out why
if you dont know much about asyncio. Even if you know Python well but you dont
know asyncio or aiohttp well you'll be in trouble to figure out what happens.

What is output of above function?

It produces following output:

{% highlight python %}

pawel@pawel-VPCEH390X ~/p/l/benchmarker> ./bench.py 
[<generator object ClientResponse.read at 0x7fa68d465728>, <generator object ClientResponse.read at 0x7fa68cdd9468>, <generator object ClientResponse.read at 0x7fa68d4656d0>, <generator object ClientResponse.read at 0x7fa68cdd9af0>]

{% endhighlight %}

What happens here? You expected to get response objects after all processing is done, but here you actually get
bunch of generators, why is that? 

It happens because as I've mentioned earlier `response.read()` is async
operation, this means that it does not return result immediately, it just returns generator. 
This generator still needs to be called and
executed, and this does not happen by default, `yield from` in Python 3.4 and `await` in Python 3.5 were
added exactly for this purpose: to actually iterate over generator function. Fix to above error
is just adding await before `response.read()`.


{% highlight python %}
    # async operation must be preceded by await 
    return await response.read() # NOT: return response.read()
{% endhighlight %}

Always remember about using "await" if you're actually awaiting something.

## Sync vs Async

Finally time for some fun. Let's check if async is really worth the hassle. What's the
difference in efficiency between asynchronous client and blocking client? How many
requests per minute can I send with my async client? 

With this questions in mind I set up simple (async) aiohttp server. 
My server is going to read full html text of Frankenstein by Marry Shelley. It will
add random delays between responses. Some responses will have zero delay, and some will
have maximum of 3 seconds delay. This should resemble real applications, few
apps respond to all requests with same latency, usually latency differs
from response to response.

Server code looks like this:

{% highlight python %}
#!/usr/local/bin/python3.5
import asyncio
from datetime import datetime
from aiohttp import web
import random

# set seed to ensure async and sync client get same distribution of delay values
# and tests are fair
random.seed(1)

async def hello(request):
    n = datetime.now().isoformat()
    delay = random.randint(0, 3)
    await asyncio.sleep(delay)
    headers = {"content_type": "text/html", "delay": str(delay)}
    # opening file is not async here, so it may block, to improve
    # efficiency of this you can consider using asyncio Executors
    # that will delegate file operation to separate thread or process
    # and improve performance
    # https://docs.python.org/3/library/asyncio-eventloop.html#executor
    # https://pymotw.com/3/asyncio/executors.html
    with open("frank.html", "rb") as html_body:
        print("{}: {} delay: {}".format(n, request.path, delay))
        response = web.Response(body=html_body.read(), headers=headers)
    return response

app = web.Application()
app.add_routes([web.get("/{name}", hello)])
web.run_app(app, port=8000)

{% endhighlight %}

Synchronous client looks like this:

{% highlight python %}

import requests
r = 100

url = "http://localhost:8000/{}"
for i in range(r):
    res = requests.get(url.format(i))
    delay = res.headers.get("DELAY")
    d = res.headers.get("DATE")
    print("{}:{} delay {}".format(d, res.url, delay))

{% endhighlight %}

How long will it take to run this? 

On my machine running above synchronous client took 2:45.54 minutes. 

My async code looks just like above code samples above. How long will async client take? 

On my machine it took 0:03.48 seconds. 

It is interesting that it took exactly as long as longest delay 
from my server. If you look into messages printed by client script you can see how
great async HTTP client is. Some responses had 0 delay but others got 3 seconds delay. In synchronous client
they would be blocking and waiting, your machine would simply stay idle for this time. 
Async client does not waste time, when something is delayed it simply does
something else, issues other requests or processes all other responses. You can see this clearly in logs, first there
are responses with 0 delay, then after they arrrived you can see responses with 1 seconds delay, 
and so on until most delayed responses arrive. 

## Testing the limits

Now that we know our async client is better let's try to test its limits and try to crash our
localhost. I'm going to reset server delays to zero now (so no more random.choice of delays)
and just see how fast we can go.

I'm going to start with sending 1k async requests. I'm curious how many requests
my client can handle.

{% highlight bash %}

> time python3 bench.py

2.68user 0.24system 0:07.14elapsed 40%CPU (0avgtext+0avgdata 53704maxresident)k
0inputs+0outputs (0major+14156minor)pagefaults 0swaps

{% endhighlight %}

So 1k requests take 7 seconds, pretty nice! How about 10k? Trying to make 10k requests 
unfortunately fails...


{% highlight python %}

responses are <_GatheringFuture finished exception=ClientOSError(24, 'Cannot connect to host localhost:8080 ssl:False [Can not connect to localhost:8080 [Too many open files]]')>
Traceback (most recent call last):
  File "/home/pawel/.local/lib/python3.5/site-packages/aiohttp/connector.py", line 581, in _create_connection
  File "/usr/local/lib/python3.5/asyncio/base_events.py", line 651, in create_connection
  File "/usr/local/lib/python3.5/asyncio/base_events.py", line 618, in create_connection
  File "/usr/local/lib/python3.5/socket.py", line 134, in __init__
OSError: [Errno 24] Too many open files

{% endhighlight %}

That's bad, seems like I stumbled across [10k connections problem](http://www.webcitation.org/6ICibHuyd). 

It says "too many open files", and probably refers to number of open sockets.
Why does it call them files? Sockets are just file descriptors, operating systems limit number of open sockets
allowed. How many files are too many? I checked with python resource module and it seems like it's around 1024.
How can we bypass this? Primitive way is just increasing limit of open files. But this
is probably not the good way to go. Much better way is just adding some synchronization
in your client limiting number of concurrent requests it can process. I'm going to do this
by adding [`asyncio.Semaphore()`](https://docs.python.org/3/library/asyncio-sync.html#asyncio.Semaphore) with max tasks of 1000.

Modified client code looks like this now:

{% highlight python %}
# modified fetch function with semaphore
import asyncio
from aiohttp import ClientSession

async def fetch(url, session):
    async with session.get(url) as response:
        delay = response.headers.get("DELAY")
        date = response.headers.get("DATE")
        print("{}:{} with delay {}".format(date, response.url, delay))
        return await response.text()


async def bound_fetch(sem, url, session):
    # Getter function with semaphore.
    async with sem:
        await fetch(url, session)


async def run(r):
    url = "http://localhost:8000/{}"
    tasks = []
    # create instance of Semaphore
    sem = asyncio.Semaphore(1000)

    # Create client session that will ensure we dont open new connection
    # per each request.
    async with ClientSession() as session:
        for i in range(r):
            # pass Semaphore and session to every GET request
            task = asyncio.ensure_future(bound_fetch(sem, url.format(i), session))
            tasks.append(task)

        responses = asyncio.gather(*tasks)
        await responses

number = 10000
asyncio.run(run(number))

{% endhighlight %}

At this point I can process 10k urls. It takes 23 seconds and returns some exceptions but overall
it's pretty nice!

How about 100 000? This really makes my computer work hard but suprisingly 
it works ok. Server turns out to be suprisingly stable although
you can see that ram usage gets pretty high at this point, cpu usage is around 
100% all the time. What I find interesting is that my server takes significantly less cpu than client.
Here's snapshot of linux `ps` output.

{% highlight python %}

pawel@pawel-VPCEH390X ~/p/l/benchmarker> ps ua | grep python

USER       PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND
pawel     2447 56.3  1.0 216124 64976 pts/9    Sl+  21:26   1:27 /usr/local/bin/python3.5 ./test_server.py
pawel     2527  101  3.5 674732 212076 pts/0   Rl+  21:26   2:30 /usr/local/bin/python3.5 ./bench.py

{% endhighlight %}

Overall it took around 53 seconds to process.

{% highlight python %}
53.86user 1.58system 0:55.53elapsed 99%CPU (0avgtext+0avgdata 419216maxresident)k
0inputs+0outputs (0major+110195minor)pagefaults 0swaps

{% endhighlight %}

Pretty powerful if you ask me.

Finally I'm going to try 1 million requests. I really hope my laptop is not going
to explode when testing that. 

1 000 000 requests finished in 9 minutes. 

{% highlight bash %}

530.86user 13.81system 9:05.17elapsed 99%CPU (0avgtext+0avgdata 3811640maxresident)k
0inputs+0outputs (0major+942576minor)pagefaults 0swaps

{% endhighlight %}

It means average request per minute rate of 111 111. Impressive.

## Epilogue

You can see that asynchronous HTTP clients can be pretty powerful. Performing
1 million requests from async client is not difficult, and the client performs really well in comparison
to synchronous code.

I wonder how it compares to other languages and async frameworks? Perhaps in some
future post I could compare [Twisted Treq](https://github.com/twisted/treq) with 
aiohttp. There is also question how many concurrent requests can be issued by 
async libraries in other languages. E.g. what would be results of benchmarks
for some Java async frameworks? Or C++ frameworks? Or some Rust HTTP clients? 

### _EDITS (24/04/2016)_

* improved code sample that uses Semaphore
* added comment about using executor when opening file
* added link to HN comment about EADDRNOTAVAIL exception

### _EDITS (10/09/2016)_

Earlier version of this post contained problematic usage of ClientSession that caused
client to crash. You can find this older version of article
[here](https://github.com/pawelmhm/pawelmhm.github.io/blob/23bd0ee3d53584bfac3fae7a956f8dd20bc7882f/_posts/2016-04-22-asyncio-aiohttp.markdown). 
For more details about this issue see this [GitHub ticket](https://github.com/KeepSafe/aiohttp/issues/1142).

### _EDITS (08/11/2016)_

Fixed minor bugs in code samples: 

* removed useless positional argument 'loop' to run()
* added positional argument url to hello() async def
* added missing colon in requests sync code sample

### _EDITS_ (14/04/2023)

Updated code to use more modern asyncio APIs (TaskGroups, asyncio.run() etc)