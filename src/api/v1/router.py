# -*- coding: utf-8 -*-
from fastapi import APIRouter

from src.api.v1 import health, channels, documents, chat, capacity

api_router = APIRouter()

# Health check
api_router.include_router(health.router, tags=["health"])

# Document upload (must come before channels due to path parameter conflict)
# Documents uses /channels/{channel_id}/documents which would be matched by
# channels' /{channel_id:path} if channels came first
api_router.include_router(documents.router)

# Chat API
api_router.include_router(chat.router)

# Capacity API
api_router.include_router(capacity.router)

# Channel CRUD
api_router.include_router(channels.router)
