from __future__ import annotations

from typing import get_args, get_origin

from starlette.types import (
    ASGIApp as StarletteASGIApp,
    Message as StarletteMessage,
    Receive as StarletteReceive,
    Scope as StarletteScope,
    Send as StarletteSend,
)

from markr.api.body_cap import (
    ASGIApp as LocalASGIApp,
    Message as LocalMessage,
    Receive as LocalReceive,
    Scope as LocalScope,
    Send as LocalSend,
)


def describe(name: str, local: object, starlette: object) -> None:
    print(f"{name}:")
    print(f"  local     = {local!r}")
    print(f"  starlette = {starlette!r}")
    print(f"  equal     = {local == starlette}")
    print(f"  origins   = {get_origin(local)!r} / {get_origin(starlette)!r}")
    print(f"  args      = {get_args(local)!r} / {get_args(starlette)!r}")


def main() -> None:
    describe("Scope", LocalScope, StarletteScope)
    describe("Message", LocalMessage, StarletteMessage)
    describe("Receive", LocalReceive, StarletteReceive)
    describe("Send", LocalSend, StarletteSend)
    describe("ASGIApp", LocalASGIApp, StarletteASGIApp)


if __name__ == "__main__":
    main()
