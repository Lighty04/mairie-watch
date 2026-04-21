#!/usr/bin/env python3
"""CLI script to run the MairieWatch pipeline (for cron)."""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.scheduler import run_pipeline

async def main():
    result = await run_pipeline()
    print(f"Pipeline complete: {result}")
    return 0 if result.get("scraped", 0) >= 0 else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
