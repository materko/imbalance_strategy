"""Git status, pull a push histórie (`/api/git`)."""

from __future__ import annotations

from fastapi import APIRouter

from .. import gitsync
from .common import clean_user
from .context import AppContext
from .models import GitPushRequest


def build(ctx: AppContext) -> APIRouter:
    router = APIRouter()

    @router.get("/api/git/status")
    def git_status():
        return gitsync.status()

    @router.post("/api/git/pull")
    def git_pull():
        return gitsync.pull()

    @router.post("/api/git/push")
    def git_push(req: GitPushRequest | None = None):
        req = req or GitPushRequest()
        return gitsync.push(message=req.message, author=clean_user(req.author))

    return router
