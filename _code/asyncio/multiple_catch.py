import asyncio
from aiohttp import ClientSession
import json

async def hello(url: str, results: list):
    async with ClientSession() as session:
        async with session.get(url) as response:
            results.append({"response": await response.text(), "url": url})


async def main():
    tasks = []
    # I'm using test server localhost, but you can use any url
    url = "http://localhost:8000/{}"
    results = []
    async with asyncio.TaskGroup() as group:
        for i in range(10):
            group.create_task(hello(url.format(i), results))
    print(json.dumps(results))


asyncio.run(main()) 