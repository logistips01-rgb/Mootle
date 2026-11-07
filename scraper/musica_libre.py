"""Música libre de derechos para los Reels de mootle (igual que en Guitle).

Temas de Kevin MacLeod (incompetech.com), licencia CC BY 4.0: gratis y legales
citando al autor. La música de Instagram NO se puede añadir por API, y la comercial
da problemas de derechos; por eso se hornea una pista libre dentro del propio MP4.

- Se descarga cada tema una vez a una carpeta local (gitignored, ~8 MB cada uno).
- `poner()` mezcla el tema en el vídeo con ffmpeg (fades + volumen 0.85) y devuelve
  la línea de crédito, que HAY QUE poner al final del texto del Reel.
"""
import subprocess
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / ".cache_audio"
BASE = "https://incompetech.com/music/royalty-free/mp3-royaltyfree/"

# (título, segundo en que empieza para saltar la intro). Temas animados que pegan con moto.
TEMAS = [
    ("Funky Chunk", 6),
    ("Hep Cats", 4),
    ("Life of Riley", 2),
    ("Werq", 8),
    ("Pamgaea", 10),
]


def credito(titulo):
    return f'🎵 "{titulo}" Kevin MacLeod (incompetech.com) · CC BY 4.0'


def archivo(titulo):
    """Descarga (si hace falta) el mp3 del tema y devuelve su ruta local."""
    CACHE.mkdir(exist_ok=True)
    f = CACHE / (titulo + ".mp3")
    if f.exists() and f.stat().st_size > 100000:
        return f
    url = BASE + urllib.parse.quote(titulo) + ".mp3"
    with urllib.request.urlopen(url, timeout=120) as r:
        f.write_bytes(r.read())
    return f


def _dur(video):
    out = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                   "-of", "default=noprint_wrappers=1:nokey=1", str(video)])
    return float(out.decode().strip())


def pick(n=None):
    """Índice de tema: por fecha si no se pasa, para que varíe por día."""
    if n is None:
        n = date.today().toordinal()
    return n % len(TEMAS)


def poner(video_in, video_out, n=None):
    """Mezcla un tema libre de derechos en el vídeo. Devuelve la línea de crédito, o None
    si falla (para que el llamador use el vídeo original, nunca un Reel mudo roto)."""
    i = pick(n)
    titulo, inicio = TEMAS[i]
    try:
        mp3 = archivo(titulo)
        dur = _dur(video_in)
        fade_out_st = max(0.1, dur - 1.5)
        filt = (f"[1:a]atrim=0:{dur:.3f},afade=t=in:d=0.4,"
                f"afade=t=out:st={fade_out_st:.3f}:d=1.5,volume=0.85[a]")
        subprocess.run(["ffmpeg", "-y", "-i", str(video_in), "-ss", str(inicio), "-i", str(mp3),
                        "-filter_complex", filt, "-map", "0:v", "-map", "[a]",
                        "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", "-shortest", str(video_out)],
                       check=True, capture_output=True)
        return credito(titulo)
    except Exception as e:
        print("música: no se pudo mezclar (", e, ")")
        return None


if __name__ == "__main__":
    import sys
    cred = poner(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else None)
    print(cred or "sin música")
