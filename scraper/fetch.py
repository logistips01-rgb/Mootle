"""HTTP: sesión con UA de navegador, robots.txt y espera aleatoria entre peticiones."""
import random
import time
import urllib.robotparser
from urllib.parse import urlsplit

import requests

USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")
HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
}
TIMEOUT = 25
DELAY = (3.0, 6.0)


# Marcas de páginas anti-bot. "captcha" a secas no vale: muchas tiendas tienen reCAPTCHA en formularios.
CHALLENGE_MARKERS = ("just a moment", "cf-challenge", "challenge-platform", "verifying your connection",
                     "captcha-delivery", "datadome", "perimeterx", "access denied", "attention required")


def is_challenge(resp):
    """¿La respuesta es una página anti-bot (Cloudflare, DataDome...) y no contenido real?"""
    body = resp.text[:20000].lower()
    return any(m in body for m in CHALLENGE_MARKERS)


class Fetcher:
    def __init__(self, delay=DELAY):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.delay = delay
        self._robots = {}
        self._last = None

    def _wait(self):
        if self._last is not None:
            pause = random.uniform(*self.delay) - (time.monotonic() - self._last)
            if pause > 0:
                time.sleep(pause)
        self._last = time.monotonic()

    def robots(self, url):
        """RobotFileParser del dominio (misma semántica que urllib: 401/403 => todo prohibido, 4xx => todo permitido)."""
        parts = urlsplit(url)
        base = f"{parts.scheme}://{parts.netloc}"
        if base not in self._robots:
            rp = urllib.robotparser.RobotFileParser(base + "/robots.txt")
            info = "ok"
            try:
                self._wait()
                resp = self.session.get(base + "/robots.txt", timeout=TIMEOUT)
                if resp.status_code in (401, 403):
                    rp.disallow_all = True
                    info = f"robots.txt {resp.status_code}"
                    if is_challenge(resp):
                        info += " (challenge anti-bot)"
                elif 400 <= resp.status_code < 500:
                    rp.allow_all = True
                    info = f"robots.txt {resp.status_code} (sin reglas)"
                elif resp.status_code >= 500:
                    rp.disallow_all = True
                    info = f"robots.txt {resp.status_code}"
                else:
                    rp.parse(resp.text.splitlines())
            except requests.RequestException as exc:
                rp.allow_all = True
                info = f"robots.txt inaccesible ({type(exc).__name__})"
            self._robots[base] = (rp, info)
        return self._robots[base]

    def allowed(self, url):
        rp, info = self.robots(url)
        return rp.can_fetch(USER_AGENT, url), info

    def get(self, url):
        """Un reintento ante cortes de red o 5xx; los 403 no se reintentan.

        Sin caché: los listados de motos tienen miles de páginas de más de 1 MB.
        """
        for attempt in (1, 2):
            self._wait()
            try:
                resp = self.session.get(url, timeout=TIMEOUT, allow_redirects=True)
            except (requests.ConnectionError, requests.Timeout):
                if attempt == 2:
                    raise
                continue
            if resp.status_code < 500 or attempt == 2:
                return resp
