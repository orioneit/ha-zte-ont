"""A fake ZTE F6005 web UI (plain HTTP) reproducing the quirks seen on the real one."""

from __future__ import annotations

import hashlib

from aiohttp import web

LOGIN_PAGE = """<html><script>
var pagename="login";
var XHasLogin = '{busy}';
</script></html>"""

DEVINFO = """<html><script type="text/javascript">
var pagename="devinfo";
var Model="";
var PonSerialNum="";
Model="F6005V6.0";
HardwareVer="F6005V6.0";
SoftwareVer="V6.0.10P2N19";
BootLoaderVer="V3.9.10";
PonSerialNum="ZTEG00000001";
</script></html>"""

GPONINFO = """<html><script type="text/javascript">
var pagename="gponinfo";
var ponStaIndex="";
var txpower="";
ponStaIndex="{state}";
txpower="{tx}";
rxpower="{rx}";
voltage="164";
current="20688";
temperature="19456";
</script></html>"""

MOVED = '<html><body>This document has moved to a new <a href="https://192.168.1.1/login.html">location</a>.</body></html>'


class FakeOnt:
    def __init__(self, username: str = "admin", password: str = "admin") -> None:
        self.cmt = hashlib.sha256(f"{username}97s{password}".encode()).hexdigest()
        self.logged_in = False
        self.other_user = False
        self.state, self.tx, self.rx = 5, 16097, 13354
        self.logins = 0
        self.logouts = 0
        self._runner: web.AppRunner | None = None
        self.port = 0

    def _check_host(self, request: web.Request) -> web.Response | None:
        if request.headers.get("Host") != "192.168.1.1":
            return web.Response(text="Access Error: Bad Request", status=400)
        return None

    async def _login_page(self, request: web.Request) -> web.Response:
        return self._check_host(request) or web.Response(
            text=LOGIN_PAGE.format(busy="1" if self.other_user else "0"), content_type="text/html"
        )

    async def _login(self, request: web.Request) -> web.Response:
        if bad := self._check_host(request):
            return bad
        form = await request.post()
        ok = (
            not self.other_user
            and request.headers.get("Referer", "").endswith("/login.html")
            and form.get("cmt") == self.cmt
            and len(form.get("nonce", "")) == 32
        )
        if not ok:
            return web.Response(text="<html>Unauthorized</html>", content_type="text/html")
        self.logged_in = True
        self.logins += 1
        return web.Response(text="var loginStatus = ok;", content_type="text/html")

    async def _logout(self, request: web.Request) -> web.Response:
        self.logged_in = False
        self.logouts += 1
        return web.Response(text=MOVED, content_type="text/html")

    def _page(self, body: str):
        async def handler(request: web.Request) -> web.Response:
            if bad := self._check_host(request):
                return bad
            if not self.logged_in:
                return web.Response(text=MOVED, content_type="text/html")
            return web.Response(text=body() if callable(body) else body, content_type="text/html")
        return handler

    async def start(self) -> None:
        app = web.Application()
        app.router.add_get("/login.html", self._login_page)
        app.router.add_post("/goform/LoginForm", self._login)
        app.router.add_post("/goform/LogoutForm", self._logout)
        app.router.add_get("/devinfo.html", self._page(DEVINFO))
        app.router.add_get(
            "/gponinfo.html",
            self._page(lambda: GPONINFO.format(state=self.state, tx=self.tx, rx=self.rx)),
        )
        self._runner = web.AppRunner(app)
        await self._runner.setup()
        site = web.TCPSite(self._runner, "127.0.0.1", 0)
        await site.start()
        self.port = site._server.sockets[0].getsockname()[1]

    async def stop(self) -> None:
        if self._runner:
            await self._runner.cleanup()
