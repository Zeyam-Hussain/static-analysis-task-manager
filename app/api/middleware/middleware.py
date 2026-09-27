"""Request logging middleware and application logger."""

import logging
from fastapi import Request


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.FileHandler('info.log')
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


async def logging_middleware(request: Request, call_next):
    """Log request and response metadata around the downstream handler."""
    logger.info("Incoming request: %s %s", request.method, request.url.path)
    response = await call_next(request)
    logger.info("Outgoing response code: %s", response.status_code)
    return response
