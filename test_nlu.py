import asyncio
import os
import sys

# Configure mock paths to import local modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "services", "orchestrator")))

from services.orchestrator.nlu import get_parser

async def main():
    parser = get_parser()
    res = await parser.parse("Yeah, sure. Just one.", "entrance_decor.name_board", {})
    print("res 1:", res)
    res2 = await parser.parse("go for lights", "backdrop_decor.types", {})
    print("res 2:", res2)

if __name__ == "__main__":
    asyncio.run(main())
