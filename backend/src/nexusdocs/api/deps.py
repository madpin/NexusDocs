"""Dependency wiring for routers."""


from fastapi import Request

from ..config import Settings
from ..graph.repository import GraphRepository
from ..llm.client import LLMClient


def get_repository(request: Request) -> GraphRepository:
    return request.app.state.repository


def get_llm(request: Request) -> LLMClient:
    return request.app.state.llm


def get_settings_dep(request: Request) -> Settings:
    return request.app.state.settings


def get_app_state(request: Request):
    return request.app.state
