# -*- coding: utf-8 -*-
from fastapi import APIRouter

from src.api.v1 import health

api_router = APIRouter()

# Health check
api_router.include_router(health.router, tags=["health"])

# TODO: Add more routers
# api_router.include_router(channels.router, prefix="/channels", tags=["channels"])
# api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
# api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
