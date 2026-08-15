"""Local static site for the web suite.

Serving real HTML over real HTTP — rather than injecting markup with `set_content` — keeps
navigation, relative URLs and asset loading in the picture, which is where timing bugs live.
And because it is local, CI never goes red because someone else's site was down.
"""

import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

PAGES = Path(__file__).parent / "pages"


class _QuietHandler(SimpleHTTPRequestHandler):
    """Same as the default handler, without one stderr line per request."""

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        pass


@pytest.fixture(scope="session")
def local_site() -> str:
    """Serve `pages/` and yield its base URL.

    Port 0 lets the OS pick a free one, so parallel xdist workers never collide.
    """
    handler = partial(_QuietHandler, directory=str(PAGES))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
