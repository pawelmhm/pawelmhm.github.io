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