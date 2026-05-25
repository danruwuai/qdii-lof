import sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv('.env')
import asyncio
from main import app, lifespan

async def test():
    try:
        async with lifespan(app) as state:
            print('Lifespan OK')
    except Exception as e:
        print(f'Lifespan error: {e}')

asyncio.run(test())
