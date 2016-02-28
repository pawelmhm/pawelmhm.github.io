---
layout: post
title:  "Making 1 million requests with python-asyncio"
date:   2016-02-27 6:00
categories: asyncio python
author: Pawel Miech
keywords: asyncio, aiohttp, python
---

Async IO is one of the trending topics in Python now, as you may know Python 3.4
adds async library to Standard Library so you no longer need to install some 
special package to use it.

Asyncio is not that easy to get started with though. [Official docs](https://docs.python.org/3/library/asyncio.html)
are very terse and contain only basic examples. There are some Stack Overflow questions 
but not [that many](http://stackoverflow.com/questions/tagged/python-asyncio?sort=votes&pageSize=50)
only 367 as of time of writing (compare with [2 517 questions tagged with twisted](http://stackoverflow.com/questions/tagged/twisted)
There are couple of nice blog posts about asyncio
over there such as [this](http://aosabook.org/en/500L/a-web-crawler-with-asyncio-coroutines.html),
[that](http://www.snarky.ca/how-the-heck-does-async-await-work-in-python-3-5), [that](http://sahandsaba.com/understanding-asyncio-node-js-python-3-4.html) or perhaps even [this](https://community.nitrous.io/tutorials/asynchronous-programming-with-python-3)
or [this](https://compiletoi.net/fast-scraping-in-python-with-asyncio/)

Aiohttp is overall well documented and also has pretty good [examples](https://github.com/KeepSafe/aiohttp/blob/master/examples/crawl.py)

### Difficulties getting started with asyncio

It's not that easy to get started with asyncio. First reason is that there are changes
in asyncio itself between different version.

In version 3.4 you create asynchronous function with @asyncio.couroutine decorator and
yield [from syntax](https://docs.python.org/3.4/library/asyncio-task.html#example-chain-coroutines),
so your code may look like this:

{% highlight python %}

import asyncio

@asyncio.coroutine
def compute(x, y):
    print("Compute %s + %s ..." % (x, y))
    yield from asyncio.sleep(1.0)
    return x + y

@asyncio.coroutine
def print_sum(x, y):
    result = yield from compute(x, y)
    print("%s + %s = %s" % (x, y, result))

loop = asyncio.get_event_loop()
loop.run_until_complete(print_sum(1, 2))
loop.close()

{% endhighlight %}

If you're used to Python 2 above code may look bizarre. First of there is [yield from
expression](https://docs.python.org/3/whatsnew/3.3.html#pep-380). There is also return
inside generator, which is something that was not allowed in Python 2. Now before
you go on and start learning those new nice things you need to realize that it is 
already outdated for asyncio. Turns out that developers of asyncio realized
that yield from syntax is not good fit for their needs and it was replaced with new
[async - await syntax](https://docs.python.org/3.5/library/asyncio-task.html#example-chain-coroutines)
Of course yield from is still part of Python and is still good thing to know but it is
no longer recommended way to create asynchronous coroutines in Python 3.5

> The async def type of coroutine was added in Python 3.5, and is recommended if there is no need to support older Python versions.

This is bit unfortunate in my opinion. First off it means that all blog posts, code
samples etc and documentation written @asyncio.coroutine becomes outdated. Of course
code will not be broken, decorator syntax will still be supported, but it's no longer
"recommended" way. This is sad news for all those blog writers out there, 
most of their posts written about Python 3.4 asyncio will now confuse people trying to learn. 
Someone trying to figure out what asyncio is will see some people using async await 
and others using yield from with decorator, it will increase learning curve for them. 

The benefit of async await is that it is significantly shorter, and if you think about
it for a while it also looks better. There are some clear and convincing benefits of using
[async-wait over decorators](https://www.python.org/dev/peps/pep-0492/#asyncio)

After refactoring to use async - await our example from above looks like this:

{% highlight python %}

import asyncio

async def compute(x, y):
    print("Compute %s + %s ..." % (x, y))
    await asyncio.sleep(1.0)
    return x + y

async def print_sum(x, y):
    result = await compute(x, y)
    print("%s + %s = %s" % (x, y, result))

loop = asyncio.get_event_loop()
loop.run_until_complete(print_sum(1, 2))
loop.close()

{% endhighlight %}


## hello aiohttp 

Now that we have all details ready we can move on to creating some simple asyncio-aiohttp
crawler. Let's start with simple HTTP hello world - just making GET and fetching one
single HTTP response. One warning before we start: please prepare yourself for bit complex
code. 

In synchronous world you just do

{% highlight python %}

import requests

def hello()
    return requests.get("http://httpbin.org/get")

print(hello())



{% endhighlight %}

How does that look in aiohttp?

{% highlight python %}

#!/usr/local/bin/python3.5
import asyncio
from aiohttp import ClientSession

async def hello():
    async with ClientSession() as session:
        async with session.get("http://httpbin.org/headers") as response:
            response = await response.read()
            print(response)

loop = asyncio.get_event_loop()

loop.run_until_complete(hello())

{% endhighlight %}

whoah that's a lot of code for such a simple task isn't it? It definitely is, and the code
is also much more complex. you have "async def" and "async with" and two "awaits" here. It
seems really confusing at first sight, let's try to explain it then. 

Actually some of the differences are related more to how aiohttp works and less to async nature of the code.
You make your function asynchronous by using async keyword before function definition and using await
keyword. There are actually two asynchronous operations that our hello() function performs. First
it fetches response asynchronously, second it reads response body in asynchronous manner.

Aiohttp recommends to use ClientSession as primary interface to make requests. ClientSession
allows you to store cookies between requests and keeps objects that are common for
all requests (event loop, connection and other things). Session needs to be closed after using it,
and closing session is another asynchronous operation, this is why you need async with
every time you deal with sessions.

After you open client session you can use it to make requests. This is where another asynchronous
operation starts, downloading request. Just as in case of client sessions responses must be closed
explicitly, and "with" statement assures you it will be closed.

To start your program you need to run it in event loop, so you need to create instance of asyncio
loop and put task into this loop.

To sum up it's bit difficult but not that complex.

## fetch multiple urls

Now let's try to do something more interesting, fetching multiple urls one after another.
With synchronous code you would do just:

{% highlight python %}

for url in urls:
    print(requests.get(url).text)

{% endhighlight %}

this is really quick and easy, async will not be that easy, so you should always consider if something more complex
is actually necessary for your needs. If your app works nice with synchronous code maybe there
is no need to bother with async code? If you do need to bother with async code here's how you do
that. Our hell() async function stays the same but we need to wrap it in asyncio Future object
and pass whole lists of Future objects as tasks to be executed in the loop.

{% highlight python %}

loop = asyncio.get_event_loop()

tasks = []
# I'm using test server localhost, but you can use any url
url = "http://localhost:8080/{}"
for i in range(5):
    task = asyncio.ensure_future(hello(url.format(i)))
    tasks.append(task)
loop.run_until_complete(asyncio.wait(tasks))

{% endhighlight %}

Now let's say we want to collect all responses in one list and do some 
postprocessing on them. At the moment we're not keeping response body
anywhere, we just print it, let's return this response, keep it in list, and 
print all responses at the end.

To collect bunch of responses you probably need to write something along the lines of:

{% highlight python %}

#!/usr/local/bin/python3.5
import asyncio
from aiohttp import ClientSession

async def fetch(url):
    async with ClientSession() as session:
        async with session.get(url) as response:
            return await response.read()

async def run(loop,  r):
    url = "http://localhost:8080/{}"
    tasks = []
    for i in range(r):
        task = asyncio.ensure_future(fetch(url.format(i)))
        tasks.append(task)

    responses = await asyncio.gather(*tasks)
    print(responses)

def print_responses(result):
    print(result)

loop = asyncio.get_event_loop()
future = asyncio.ensure_future(run(loop, 4))
loop.run_until_complete(future)

{% endhighlight %}

Notice usage of asuncio.gather(), this collects bunch of Future objects in one place
and waits for all of them to finish. 

### Common gotchas

now let's simulate learning and let's make mistake in above script and try to debug it,
this should be really helpful for demonstration purposes.

Let's break our fetch() function

{% highlight python %}
# WARNING! BROKEN CODE DO NOT COPY PASTE
async def fetch(url):
    async with ClientSession() as session:
        async with session.get(url) as response:
            return response.read()

{% endhighlight %}

Above version of fetch() is broken, but it's not that easy to figure out why
if you dont know much about asyncio. Even if you know Python well but you dont
know asyncio or aiohttp well you'll be in trouble to figure out what happens.

What is output of above function?

It produces following output:

{% highlight python %}

pawel@pawel-VPCEH390X ~/p/l/benchmarker> ./bench.py 
[<generator object ClientResponse.read at 0x7fa68d465728>, <generator object ClientResponse.read at 0x7fa68cdd9468>, <generator object ClientResponse.read at 0x7fa68d4656d0>, <generator object ClientResponse.read at 0x7fa68cdd9af0>]

{% endhighlight %}

what happens here? You expected to get response objects after all processing is done, but here you actually get
bunch of generators, why is that? It happens because as I've mentioned earlier response.read() is async
operation, this means that in asyncio it returns generator. This generator still needs to be called and
executed, and this does not happen by default. yield from in Python 3.4 and await in Python 3.5 were
added exactly for this purpose: to actually iterate over generator function. Fix to above error
is just adding await before response.read().

Let's break our code in some other way.

{% highlight python %}

# WARNING! BROKEN CODE DO NOT COPY PASTE
async def run(loop,  r):
    url = "http://localhost:8080/{}"
    tasks = []
    for i in range(r):
        task = asyncio.ensure_future(fetch(url.format(i)))
        tasks.append(task)

    responses = asyncio.gather(*tasks)
    print(responses)

{% endhighlight %}

Again above code is broken but it's not easy to figure out why if you're just
learning asyncio.

Above produces following output:

{% highlight python %}
pawel@pawel-VPCEH390X ~/p/l/benchmarker> ./bench.py 
<_GatheringFuture pending>
Task was destroyed but it is pending!
task: <Task pending coro=<fetch() running at ./bench.py:7> wait_for=<Future pending cb=[Task._wakeup()]> cb=[gather.<locals>._done_callback(0)() at /usr/local/lib/python3.5/asyncio/tasks.py:602]>
Task was destroyed but it is pending!
task: <Task pending coro=<fetch() running at ./bench.py:7> wait_for=<Future pending cb=[Task._wakeup()]> cb=[gather.<locals>._done_callback(1)() at /usr/local/lib/python3.5/asyncio/tasks.py:602]>
Task was destroyed but it is pending!
task: <Task pending coro=<fetch() running at ./bench.py:7> wait_for=<Future pending cb=[Task._wakeup()]> cb=[gather.<locals>._done_callback(2)() at /usr/local/lib/python3.5/asyncio/tasks.py:602]>
Task was destroyed but it is pending!
task: <Task pending coro=<fetch() running at ./bench.py:7> wait_for=<Future pending cb=[Task._wakeup()]> cb=[gather.<locals>._done_callback(3)() at /usr/local/lib/python3.5/asyncio/tasks.py:602]>

{% endhighlight %}

What happens here? If you examine your localhost logs you may see that requests are not reaching
your server at all. Clearly no requests are performed. Print statement prints that
responses variable contains `<_GatheringFuture pending>` object, and later it alerts that
pending tasks were destroyed. Why is it happening? Again you forgot about await

faulty line is this

{% highlight python %}
    responses = asyncio.gather(*tasks)
{% endhighlight %}

it should be:

{% highlight python %}
    responses = await asyncio.gather(*tasks)
{% endhighlight %}


## Trash localhost

Finally time for some fun. Let's check if async is really worth the hassle. What's the
difference in efficiency between asynchronous client and blocking client? How many
requests per minute can I send with my async client? With this questions in mind
I set up simple (async) aiohttp server. It is going to imitate real network conditions. 
My server is going to read full html text of Frankenstein by Marry Shelley. It will
add random delays between responses. Some responses will have zero delay, and some will
have maxium of 4 seconds delay.

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
    name = request.match_info.get("name", "foo")
    n = datetime.now().isoformat()
    delay = random.randint(0, 3)
    await asyncio.sleep(delay)
    headers = {"content_type": "text/html", "delay": str(delay)}
    with open("frank.html", "rb") as html_body:
        print("{}: {} delay: {}".format(n, request.path, delay))
        response = web.Response(body=html_body.read(), headers=headers)
    return response

app = web.Application()
app.router.add_route("GET", "/{name}", hello)
web.run_app(app)

{% endhighlight %}

Synchronous client is like this

{% highlight python %}

import requests
r = 100

url = "http://localhost:8080/{}"
for i in range(r):
    res = requests.get(url.format(i))
    delay = res.headers.get("DELAY")
    d = res.headers.get("DATE")
    print("{}:{} delay {}".format(d, res.url, delay))

{% endhighlight %}

How long will it take to run this? On my machine running above synchronous client
took 2:45.54 minutes. How long will async client take? Well on my machine it took
0:03.48 seconds. It is interesting that it took exactly as long as longest delay 
from my server. If you look into messages printed by client script you can see how
great async HTTP client is. Some responses got 3 seconds delay. In synchronous client
they would be blocking and waiting, your machine would simply stay idle for this time. 
Async client does not waste it's time, when something is delayed it simply does
something else, processes all other responses. You can see this clearly in logs, first there
are responses with 0 delay, then after they arrrived you can see responses with 1 seconds delay, 
and so on until most delayed responses arrive. 

## Testing the limits

Now that we know our async client is better let's try to test its limits and try to crash our
localhost. I'm going to start with sending 1k async requests. I'm curious how many requests
my client can handle.

So 1k requests take 7 seconds, pretty nice! How about 10k? Trying to make 10k requests 
unfortunatenly fails with 


{% highlight python %}

responses are <_GatheringFuture finished exception=ClientOSError(24, 'Cannot connect to host localhost:8080 ssl:False [Can not connect to localhost:8080 [Too many open files]]')>
Traceback (most recent call last):
  File "/home/pawel/.local/lib/python3.5/site-packages/aiohttp/connector.py", line 581, in _create_connection
  File "/usr/local/lib/python3.5/asyncio/base_events.py", line 651, in create_connection
  File "/usr/local/lib/python3.5/asyncio/base_events.py", line 618, in create_connection
  File "/usr/local/lib/python3.5/socket.py", line 134, in __init__
OSError: [Errno 24] Too many open files

{% endhighlight %}

That's bad, seems like I stumbled across 10k connections problem. How many files
are too many? I checked with python resource module and it seems like it's around 1024.
How can we bypass this? Primitive way is just increasing limit of open files. But this
is probably not the good way to go. Much better way is just adding some synchronization
in your client limiting number of concurrent requests it can process. I'm going to do this
by adding asyncio.Sempaphore() with max tasks of 1000 (so close to open files limit).


Modified run() function looks like this now:

{% highlight python %}
async def run(loop,  r):
    url = "http://localhost:8080/{}"
    tasks = []
    sem = asyncio.Semaphore(1000)
    for i in range(r):
        task = asyncio.ensure_future(fetch(url.format(i)))
        await sem.acquire()
        task.add_done_callback(lambda t: sem.release())
        tasks.append(task)

    responses = asyncio.gather(*tasks)
    responses.add_done_callback(print_responses)
    await responses

{% endhighlight %}

At this point I can process 10k urls. It takes 23 seconds, so pretty nice.

How about trying 100 000? This really makes my computer work hard but it
actually seems pretty nice. Server turns out to be suprisingly stable although
you can see that ram usage gets pretty high at this point, cpu usage is around 
100% all the time. What I find interesting is that my server takes significantly less cpu than client.
Overall there is 1k connections is zero problem for my test server, here's snapshot
of ps output.

{% highlight python %}

pawel@pawel-VPCEH390X ~/p/l/benchmarker> ps ua | grep python
pawel     2447 56.3  1.0 216124 64976 pts/9    Sl+  21:26   1:27 /usr/local/bin/python3.5 ./test_server.py
pawel     2527  101  3.5 674732 212076 pts/0   Rl+  21:26   2:30 /usr/local/bin/python3.5 ./bench.py

{% endhighlight %}

Overall it took around 5 minutes before it crashed for some
reason, since it generated around 100k lines of output it's not that easy
to pinpoint traceback, seems like some responses are not closed, whether this 
is because of some error from my server or something in client?

After scrolling for couple of seconds I found this exception

{% highlight python %}

  File "/usr/local/lib/python3.5/asyncio/futures.py", line 387, in __iter__
    return self.result()  # May raise too.
  File "/usr/local/lib/python3.5/asyncio/futures.py", line 274, in result
    raise self._exception
  File "/usr/local/lib/python3.5/asyncio/selector_events.py", line 411, in _sock_connect
    sock.connect(address)
OSError: [Errno 99] Cannot assign requested address

{% endhighlight %}

My hypothesis is that test server went down for some split second,
and this caused some client error that was printed at the end, 
so probably I need to add errbacks to aiohttp requests. Overall it's really
not bad though, 5 minutes for 100 000 requests? this makes around 20k
requests per minute. Pretty powerful if you ask me.

Finally I'm going to try 1 million requests. I really hope my laptop is not going
to explode and burn when processing that. For this amount of requests I reduced
delays to range between 0 and 1.

I know at this point I should probably think about adding some rate limit in my test server.
Seems like it does run into some trouble once in a while.

1 000 000 requests finished in 52 minutes

{% highlight shell %}
1913.06user 1196.09system 52:06.87elapsed 99%CPU (0avgtext+0avgdata 5194260maxresident)k
265144inputs+0outputs (18692major+2528207minor)pagefaults 0swaps

{% endhighlight %}

so it means my client made around 19230 requests per minute. Not bad isn't it? Note that
capabilities of my client are limited by server responding with delay of 0 and 1 in this 
scenario, seems like my test server also crashed silently couple of times. I wonder
how it compares to other languages and async frameworks?

