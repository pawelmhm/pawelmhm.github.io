import asyncio
from aiohttp import ClientSession

async def hello(url: str):
    async with ClientSession() as session:
        async with session.get(url) as response:
            return await response.read()


async def main():
    tasks = []
    # I'm using test server localhost, but you can use any url
    url = "http://localhost:8000/{}"
    async with asyncio.TaskGroup() as group:
        for i in range(10):
            group.create_task(hello(url.format(i)))


asyncio.run(main()) 