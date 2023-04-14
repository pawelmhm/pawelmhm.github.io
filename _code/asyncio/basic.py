#!/usr/local/bin/python3.5
import asyncio
from aiohttp import ClientSession

async def hello(url: str):
    async with ClientSession() as session:
        async with session.get(url) as response:
            response = await response.read()
            print(response)

asyncio.run(hello("http://httpbin.org/headers"))