---
layout: post
title:  "Building Dropbox clone in Python and Raspi with pyftpdlib"
date:   2018-12-11
categories: python raspi
author: Pawel Miech
keywords: python raspi ftp
---
I was recently looking for alternatives to Dropbox on Linux and was somewhat tired
of trying different software. In the end while I was cleaning up old wardrobe I found
a bag with my old Raspberry PI. I bought it in 2013 and never really used for anything
meaningful. So I thought why not use it for building my own Dropbox?

The idea is simple. Raspi will lie under my communism era cupboard, my laptop and my
desktop and (perhaps in the future) my mobile devices will connect to Raspi and they will
sync files to Raspi. Sounds simple.


## Dusting off my Raspi

First I had to dust off my Raspi, plug it in, and see if it works. Turns out it works fine.

<a href='/assets/20181210_215619.jpg'><img src='/assets/raspi.jpg'></a>

I had to set up static ip address on my raspi so that machines will be able to
connect to constant address. Otherwise if you keep DHCP which is default option your router
will assign different ip to raspi on different occassions and your machines wont be able to find
it easy.

To get ip of your raspi use ifconfig command. Configuring static ip is done via /etc/network/interfaces
file.


## Setting up FTP server on Raspi

For file storage I decided to use simple, plain old FTP. I found out great library
for writing FTP server called [PyFTPdlib](https://pyftpdlib.readthedocs.io/en/latest/index.html). It has
impressive performance, according to author of library [it performs better than other common UNIX FTP
servers](https://github.com/giampaolo/pyftpdlib).

Writing FTP server in PyFTPdlib is easy. I ended up with something like this.

{% highlight python %}
from os import path
from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer

def main():
    authorizer = DummyAuthorizer()

    # we'll use directory called home/user/pendrive
    # this is how I mounted my pendrive on raspi
    directory = path.join(path.expanduser('~'), 'pendrive')

    authorizer.add_user('user', '12345', directory,
                        perm='elradfmwMT')
    handler = FTPHandler
    handler.authorizer = authorizer

    # server will run on post 2000 localhost
    address = ('', 2000)
    server = FTPServer(address, handler)
    server.serve_forever()

if __name__ == '__main__':
    main()

{% endhighlight %}

You can test your server with FTP client, I used FileZilla and it worked. I copy pasted
server file to raspi, created VirtualEnv, and installed PyFTPdlib and [Circus process manager](https://circus.readthedocs.io/en/0.8/) to 
control my server in case it fails.

Circus file looks like this


{% highlight python %}
# file ftp_server.ini
[watcher:ftp_server]
cmd = ftp/bin/python server.py
use_sockets = True

{% endhighlight %}

I then launch this file with circus puttin it into daemon mode so that I can log out
of raspi and it will run ad infinitum (or until raspi dies or the electricity cable is
plugged out).

{% highlight bash %}
>. /ftp/bin/circusd --daemon ftp_server.ini

{% endhighlight %}

Circus has nice command line API that allows you to see what is happening with your job
when it runs as daemon

{% highlight bash %}

> circusctl

circusctl 0.15.0
ftp_server: active
(circusctl) status
ftp_server: active
(circusctl) 

{% endhighlight %}

## Writing client

Now that we have our server running we need client application. It need to do two things.
One is monitoring some directory for file changes and see if some file changed. If this file
changed it should sync file to FTP server on raspi. 

First task: monitoring for file changes could be probably done by opening each file in directory,
computing some hash of it, and checking if it changed. But that doesnt seem very efficient, for large
directories it would be very inefficient. It would be easier to plug into operating system output
and try to see if operating system knows what is going on, get information about file changes from OS.

Turns out python allows you to easily check when file was modified by looking using 

{% highlight python %}
os.stat('server.py').st_mtime

{% endhighlight %}

This returns timestamp in milliseconds from unix epoch. Now you only need to keep some form
of database of file data, check which state of file is present on server and store new file
state when you detect old file is no longer there.
