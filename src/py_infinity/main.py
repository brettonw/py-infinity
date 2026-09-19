"""Service entry point."""

from __future__ import annotations

import logging

from aiohttp import web

from .config import Settings
from .model import SystemState
from .mqtt import PahoStatePublisher
from .state import StateStore
from .web import create_app


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    settings = Settings.from_env()
    store = StateStore(SystemState.empty(settings.instance_id, settings.device_name))
    publisher = PahoStatePublisher(settings, store)
    web.run_app(
        create_app(store, publisher),
        host=settings.http_host,
        port=settings.http_port,
        access_log=logging.getLogger("py_infinity.access"),
    )


if __name__ == "__main__":
    main()
