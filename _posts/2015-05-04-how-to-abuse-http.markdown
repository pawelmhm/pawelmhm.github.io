---
layout: post
title:  "How to abuse HTTP?"
date:   2015-06-04 14:34:42
categories: http
author: Pawel Miech
keywords: HTTP
---

You'd think that HTTP is so common that most people should have no problem 
with getting basics of protocol right. Even if you know next to nothing about computers
you still probably heard about the meaning of basic HTTP codes such as 404 or 200. 
Despite its popularity, or maybe because of its popularity HTTP is one 
of the most frequently abused and misunderstood protocols. This is clearly 
paradoxical, every job ad these days speaks about REST-ful apis, there
are millions of apis deployed around the web, yet so many of them openly
violate semantics of HTTP. And those violations happen not only in some
small apps created by rookie web developes, even the biggest websites violate
standard sometimes.

Maybe one thing that plays a role here is popular misunderstanding that HTTP 
semantics is only important for API-s returning json or xml. Some people
seem to think that if they don't have api returning JSON they dont need to 
care about HTTP semantincs. This is clearly wrong. If you have a blog with 3 html pages you're usually 
serving it over HTTP so you should respect semantics of HTTP. 
Every web page should respect HTTP since this is the standard 
that powers the web.

In this post I'd like to take a look at most blatant and most frequent 
abuses of HTTP that I've found throughout last 1,5 years when building
web crawlers for various purposes (mostly indexing web).

## Use 200 instead of 404

Every child knows 404 means page not found. Every web developer should
know that there is a difference between showing huge sign "404" in html
body (with some optional cool humourous text or whatever) and returning
actual HTTP response with status code 404. What really matters here  
is not the body, but response status code. I lost track of how many
web pages return 200 with stupid 404 sign in html body do this. Even biggest US stores with millions of visitors return
do this. You can check this out yourself now,
go to your favorite websites, put some rubbish in url and see at response
status code.

I don't really know why people do this. Maybe someone with more knowledge about
this would tell me. I don't really see any reason why you would do this. 
(You can always return 404 response with same body no problem).
I see bunch of reasons why you should never do this. 

First thing that every search engine or bot checks is response status code, 
if status code is 200 it means "all clear this is best content I have under
requested resource location", this implies
lost of things. First off all it implies that this content should be indexed 
(assuming of course you want to be indexed). Do you
really want your cool "page not found" body to be treated as legit content?
It will be treated as legit content if you return response 200.
Response 200 also implies that content can and perhaps should be cached. 
This means that crawler will actually create cache of your cool
"page not found" response body, and it will keep cache for some specified
time. When you put valid content in this page later, bot may ignore it
and just take content from cache. 

## Use 200 instead of 5xx

Exceptions can always happen. Every server is down once in a while, every 
request may return error code once in a while. HTTP has specific semantics
to deal with that. When your server is down you should return one of 5xx codes
(500, 502, 503, 504)
Usually the best response is just 503 service unavailable with 'Retry-After' 
header. If you [check HTTP specs](http://www.w3.org/Protocols/rfc2616/rfc2616-sec10.html#sec10.5.4)
503 means that:

> The server is currently unable to handle the request due to a temporary overloading or maintenance of the server. The implication is that this is a temporary condition which will be alleviated after some delay. If known, the length of the delay MAY be indicated in a Retry-After header. If no Retry-After is given, the client SHOULD handle the response as it would for a 500 response.


This seems really simple, right? Why is it then that so many web sites
don't do that?

As with 404 most frequent abuse is returning 200 with some cool error message 
instead of proper response code. "Ooops something went wrong, we're working
hard to fix it" in html body. It's great you're working hard to fix it but
first thing you should fix is returning proper HTTP codes on errors. If 
you return 200 it communicates that there is no error. 
Most non-human visitors will think that this 'Oops something went wrong" 
is something you want to show to the world, some product you're selling or 
service you offer. Are you really selling "oopses"? 

When server responds with 5xx most clients are going to retry request
after some specified wait time. If you specify 'retry-after' headers
you're being really nice and most bots will retry after value from this
header. 90% of 5xx errors are temporary, and retry helps
most of the time. If you have responded with 200 retry 
is not going to happen. Content will be lost to bot, it will assume it got
content from your response and it will continue it's journey around the web
visiting other places.

## 302 instead of 5xx

Other frequent and irritating abuse of HTTP is redirect on exception. 
Server is going down for millisecond but instead of returning proper 500 on
url requested you respond with 301 or 302 with 'Location' header leading
to some generic error handling page 'http://www.example.com/errorpage/error".
This is bad and harmful for you. Most clients encountering
one of 5xx codes will retry request.
When you redirect to some errorpage with different url crawler is going
to retry this exact error page and not original page it requested. In worse
case when this happens frequently and you have lots of bots visiting your site
(which is generally sign that your site is really popular) you are creating
problems for yourself because bunch of bots can be retrying this stupid error
page instead of getting actual url they requested. 

## 5xx instead of 400

Many apis and webpages have some required parameters in url querystring part. 
If some required parameter is not present in querystring
server should return 400 Bad Request code with friendly error message
advising client what it did wrong. HTTP specs are clear on that

> The 4xx class of status code is intended for cases in which the client seems to have erred. Except when responding to a HEAD request, the server SHOULD include an entity containing an explanation of the error situation, and whether it is a temporary or permanent condition. These status codes are applicable to any request method. User agents SHOULD display any included entity to the user.

As usual this is simple, but so many developers forget that. Most frequent
abuse here is returning 500 server error when some url param is missing. This is
either intended or perhaps unintented (someone developing app forgot to check
required params in url handling function and server crashes when user mistypes
param name). You
should generally never trust user input, and url querystring is just a form
of user input. Everyone can manipulate your url in browser, and many web
clients will access your api if it's public. Web clients can get your url
params wrong. If you want to keep your web
clients happy please tell them what they are doing wrong. If they miss some
parameter give them proper 400 and tell them what they are missing. If you
are returning 500 you are telling clients that there is some temporary error
in your application. Faced with this message most clients will simply retry
after some delay. Do you really want them to retry request that was bad and
incorrect? 

## POST instead of GET

POST requests should be used for posting new data, GET requests should be used
to retrieve data. Most good crawlers will never use POST. I'm not talking about
spam bots or about some malicious bots scanning your site for vulnerabities. 
I'm talking about search engines (there are many, not only one) and bots indexing
content for all types of purposes. Legit bots will not use POST. If you use POST
for navigation or for retrieving content it's like putting a tag 'robots, no-follow'.

I'm pretty sure most developers know this, but I see suspiously large amount 
of sites that abuse POST. I noticed that this happens often with old .net applications.
Instead of proper GET to get resource they just use POST-s with some huge amount
of parameters in formbody. If you have this kind of application and you wonder
why you're doing poorly in search results look no further - you're practically
hiding your content from non-human visitors. 

## this ain't no rocket science man

HTTP is not rocket science, and you don't have to be genius to get it right. 
If you have still have 5 minutes now [go read all definitions of HTTP
status codes, and use them properly](http://www.w3.org/Protocols/rfc2616/rfc2616-sec10.html).
