---
layout: post
title:  "Create event-driven sales alert system with Faust and Aiohttp"
date:   2021-06-13 6:34:42
categories: python aiohttp python-faust event-driven
author: Paweł Miech
keywords: python aiohttp python-faust event-driven
---
In this post I'll write a simple python app that will post message to Slack when your users purchase a subscription. The web app will be a [aiohttp server](https://docs.aiohttp.org/en/stable/web_quickstart.html#run-a-simple-web-server) that will coordinate with Python-Faust to send Slack requests asynchronously in the background.  

[Faust](https://faust.readthedocs.io/en/latest/index.html) is a framework, that simplifies writing event-driven systems in Python. It allows you to use the power of Apache Kafka via Python. With Faust agents, you can create event handlers that will subscribe and publish to Kafka topics. You can send an event from your app to Kafka, return a response to your client. The event will be picked up and processed in the background without users bothering about it.

## Doing things vanilla way
To see the benefits of an event-driven system, you can write the code in a vanilla way without using any event handling, without Faust, Kafka or another similar tool. 

For example, let's say you have a web page where users are buying a premium subscription. For every subscription, you need to notify sales team. Your business is small, so you do it by Slacking your team. You would like to publish a message to Slack and tell your sales team that there is a new premium user. The sales team can then send a welcome e-mail and provide some help to new users.

I will use Aiohttp server to write demo code. We have one class-based view that supports two HTTP methods, GET and POST. GET handler will return an HTML page with the form. POST handler will send another HTTP request to Slack (I'll use httpbin for simplicity here). 

The code looks like this. [All code is available on github in this repo](https://github.com/pawelmhm/another-faust-example).

{% highlight python %}
# To run
# python blog/naive.py
# server will listen on localhost:8088
import aiohttp
import aiohttp_jinja2
import jinja2
from aiohttp import web


routes = web.RouteTableDef()


async def post_to_slack(username):
    async with aiohttp.ClientSession() as session:
        print(f"making request for {username}")
        # make request to httpbin endpoint that returns after 9 secs delay
        async with session.get('https://httpbin.org/delay/9') as res:
            return await res.json()


@routes.view("/")
class SubscriptionView(web.View):
    @aiohttp_jinja2.template('subscription.jinja2')
    async def get(self) -> web.StreamResponse:
        return {}

    async def post(self) -> web.StreamResponse:
        post_data = await self.request.post()
        username = post_data['username']
        await post_to_slack(username)
        return web.Response(text='thanks')


if __name__ == "__main__":
    app = web.Application()
    app.add_routes(routes)
    aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader('jinja_templates'))
    web.run_app(app)
{% endhighlight %}

The code is asynchronous, which is nice, but it is not 100% event-driven and still has some problems. First of all, it requires your users to wait until you inform your sales. You receive form input from a user. Then you make a Slack request inside POST handler while the user waits. It is probably fine if Slack responds quickly. But let's say Slack experiences some network problems, and it responds in 9 seconds. Now your user will have to gaze at the loading page for 9 seconds and wait for you to inform them you thank you for their purchase.  I illustrated it in code by adding a request to httpbin.org endpoint that returns a response after 9 seconds delay. When you test example in web browser (server runs on port 8088 )  you can see that you will have to wait 9 seconds before you get a response.

Another problem is error handling. For example, let's say Slack is having some severe problems and responds with HTTP 503 response. Now you have an exception in your POST handler. It means that you are likely losing a subscription because of an external service provider.

## Make it event-driven
To handle the problems outlined above, you need to use something to offload your Slack notifications to the background. You need to return a "thank you" response to the user and ask another system to send a Slack message to sales. If another system will fail or takes ages when sending a message to sales, it is not a user's problem. It will be your sales problem. Users will get their "thank you" responses and move on with their lives without losing precious seconds or minutes. 

Here is where you can utilize Faust. 

Before you can use Faust, you need to install and launch Apache Kafka. Instructions on how to do this are in [Apache Kafka docs](https://kafka.apache.org/quickstart). Once you have zoopeker and Kafka server running (each in separate terminal) you can write your Faust code. 

Faust's basic building blocks are agents. Agents are listening to Kafka topics, and they are continuously processing events sent to them. 
Your Faust app will consist of an HTTP request handler, same class based
view as in previous example just integrated with Slack. Aside from this we
will have Faust agent listening for events send by subscription handler
and sending notifications to Slack in the background.

Here is the code. [Full code available here](https://github.com/pawelmhm/another-faust-example)


{% highlight python %}
# To run
# faust -A blog.faust_view worker
# server will listen on localhost:6066
import time

import aiohttp
import aiohttp_jinja2
import faust
import jinja2
from faust import web

# create an instance of Faust app
app = faust.App('myapp', broker='kafka://localhost')


# This will be our main event class, created when user buys subscription
class Subscription(faust.Record, serializer='json'):
    username: str
    timestamp: float
    authorized: bool

# Define some Kafka topic for your agent
subscription_topic = app.topic('subscriptions', value_type=Subscription)


@app.agent(subscription_topic)
async def post_to_slack(subscriptions):
    async for subscription in subscriptions:
        async with aiohttp.ClientSession() as session:
            print(f"making request for {subscription.username}")
            async with session.get('https://httpbin.org/delay/9') as res:
                response = await res.json()
                print(response)


@app.page("/")
class SubscriptionView(web.View):
    @aiohttp_jinja2.template('subscription.jinja2')
    async def get(self, request):
        return {}

    async def post(self, request):
        post_data = await request.post()
        print(post_data)
        username = post_data['username']
        sub = Subscription(
            username=username,
            timestamp=time.time(),
            authorized=True
        )
        await post_to_slack.send(value=sub)
        return self.json({"thank you": "ok"})


# aiohttp app is available on app.web Faust app atribute
aiohttp_jinja2.setup(app.web.web_app, loader=jinja2.FileSystemLoader('jinja_templates'))

if __name__ == "__main__":
    app.main()


{% endhighlight %}

Now you can test this in a terminal. First, launch Faust app in one terminal window. You can do it by running faust -A blog.faust_view worker. 

Now launch another terminal, and you test with curl. You can also visit https://localhost:6066 in a browser window.  

Faust example is much quicker. You can see in logs that it returns after milliseconds without waiting for a response from httpbin. Now your request handler is just sending an event to the agent. The agent makes a request, handles response. It is all done without bothering your user.  

Now to add Slack integration, you only need to replace HTTP request to httpbin with Slack API call, for example something like this
(of course need to get proper Slack token):

{% highlight python %}
import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

async def post_to_slack():
    client = WebClient(token=os.environ['SLACK_BOT_TOKEN'])

    try:
        response = client.chat_postMessage(channel='#random', text="Hello world!")
        assert response["message"]["text"] == "Hello world!"
    except SlackApiError as e:
        # some error handling here
        print(f"Got an error: {e.response['error']}")

{% endhighlight %}

## Using Faust with Django or Tornado
If you'd like to test Faust with other Python web frameworks, there are examples in Faust docs. You can try Django, Tornado, or maybe some other framework.  Head to Faust [examples directory](https://github.com/robinhood/faust/tree/master/examples) to learn more. 
