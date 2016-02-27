---
layout: post
title:  "Load testing asyncio"
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
over there. I would start with following:

http://aosabook.org/en/500L/a-web-crawler-with-asyncio-coroutines.html
http://www.snarky.ca/how-the-heck-does-async-await-work-in-python-3-5
http://sahandsaba.com/understanding-asyncio-node-js-python-3-4.html
https://community.nitrous.io/tutorials/asynchronous-programming-with-python-3
https://compiletoi.net/fast-scraping-in-python-with-asyncio/

Seems like everyone are talking about asyncio and try to use it. Scrapy core contributors
were playing with replacing Twisted as [Scrapy engine](https://github.com/scrapy/scrapy/pull/1455)
and using asyncio. 

Examples from aiohttp:
https://github.com/KeepSafe/aiohttp/blob/master/examples/crawl.py

## What is asynchronous in 3 sentences or less

### syntax confusion between 3.4 and 3.5

It's not that easy to get started with asyncio. First reason is that there are changes
in asyncio itself between different version.

In version 3.4 you create asynchronous function with @asyncio.couroutine decorator and
yield [from syntax](https://docs.python.org/3.4/library/asyncio-task.html#example-chain-coroutines),
so your code may look like this:

{% highlight python3 %}

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




{% highlight python %}

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
