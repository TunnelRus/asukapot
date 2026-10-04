import os
import logging
from aiohttp import web

logger = logging.getLogger("WebServer")

async def health_check(request):
    """Responds to UptimeRobot pings to keep Render awake."""
    return web.Response(text="Honeypot is online and watching.", status=200)

async def start_web_server():
    """Starts the lightweight HTTP server on the port assigned by Render."""
    app = web.Application()
    app.router.add_get("/", health_check)
    app.router.add_get("/health", health_check)

    # Render automatically injects the PORT environment variable (default: 10000)
    port = int(os.environ.get("PORT", 10000))
    runner = web.AppRunner(app)
    await runner.setup()
    
    # 0.0.0.0 binds to all external network interfaces so Render can route to it
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"Keep-alive web server is listening on port {port}")