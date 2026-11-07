"""Publicador de Instagram para mootle (@mootle_es).

Usa la Instagram Graph API (graph.instagram.com) con el token del entorno
INSTAGRAM_TOKEN_MOOTLE. Publica una imagen suelta o un carrusel; las imágenes
deben estar en una URL pública (las servimos desde mootle.es/marketing/...).

CLI:
  python -m scraper.social image  <image_url> "<caption>"
  python -m scraper.social carousel "<caption>" <url1> <url2> ...
  python -m scraper.social whoami
"""
import os
import sys
import time
import json
import urllib.parse
import urllib.request

GRAPH = "https://graph.instagram.com"


def _token():
    t = os.environ.get("INSTAGRAM_TOKEN_MOOTLE")
    if not t:
        raise RuntimeError("Falta INSTAGRAM_TOKEN_MOOTLE en el entorno")
    return t


def _get(path, params):
    url = f"{GRAPH}/{path}?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.load(r)


def _post(path, params):
    data = urllib.parse.urlencode(params).encode()
    with urllib.request.urlopen(f"{GRAPH}/{path}", data=data, timeout=120) as r:
        return json.load(r)


def me():
    tok = _token()
    return _get("me", {"fields": "id,username,account_type,media_count", "access_token": tok})


def _wait_ready(cid, tok, tries=20):
    """Espera a que un contenedor esté FINISHED antes de publicar."""
    for _ in range(tries):
        st = _get(cid, {"fields": "status_code,status", "access_token": tok})
        if st.get("status_code") == "FINISHED":
            return True
        if st.get("status_code") == "ERROR":
            raise RuntimeError(f"contenedor en ERROR: {st}")
        time.sleep(3)
    return False


def publish_image(image_url, caption):
    tok = _token()
    uid = me()["id"]
    cont = _post(f"{uid}/media", {"image_url": image_url, "caption": caption, "access_token": tok})
    cid = cont["id"]
    _wait_ready(cid, tok)
    out = _post(f"{uid}/media_publish", {"creation_id": cid, "access_token": tok})
    return out


def publish_carousel(image_urls, caption):
    tok = _token()
    uid = me()["id"]
    children = []
    for u in image_urls:
        c = _post(f"{uid}/media", {"image_url": u, "is_carousel_item": "true", "access_token": tok})
        children.append(c["id"])
    for cid in children:
        _wait_ready(cid, tok)
    cont = _post(f"{uid}/media", {"media_type": "CAROUSEL", "children": ",".join(children),
                                  "caption": caption, "access_token": tok})
    cid = cont["id"]
    _wait_ready(cid, tok)
    out = _post(f"{uid}/media_publish", {"creation_id": cid, "access_token": tok})
    return out


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    cmd = sys.argv[1]
    if cmd == "whoami":
        print(json.dumps(me(), ensure_ascii=False))
    elif cmd == "image":
        print(publish_image(sys.argv[2], sys.argv[3]))
    elif cmd == "carousel":
        print(publish_carousel(sys.argv[3:], sys.argv[2]))
    else:
        print("comando desconocido:", cmd)


if __name__ == "__main__":
    main()
