#!/usr/bin/env python3
"""Генератор APT-репозитория (Cydia/Sileo/Zebra) для GitHub Pages.
Кладёте .deb в папку debs/, запускаете ./update.sh -> получаете Packages, Release, index.html.
Нужен только python3 (dpkg-deb понадобится лишь для .deb со сжатием zstd)."""
import os, io, gzip, bz2, lzma, hashlib, tarfile, subprocess, html, email.utils, datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
DEBS = os.path.join(ROOT, "debs")

# ================= ИЗМЕНИТЕ ПОД СЕБЯ =================
REPO_NAME = "Guppy's Repo"
REPO_DESC = "just simple tweaks"
REPO_URL  = "https://eipsealon.github.io/repo/"   # со слэшем на конце
# =====================================================


def read_ar(path):
    with open(path, "rb") as f:
        if f.read(8) != b"!<arch>\n":
            raise ValueError("not an ar archive")
        while True:
            h = f.read(60)
            if len(h) < 60:
                break
            name = h[:16].decode().strip().rstrip("/")
            size = int(h[48:58].decode().strip())
            data = f.read(size)
            if size % 2:
                f.read(1)
            yield name, data


def read_control(path):
    try:
        for name, data in read_ar(path):
            if name.startswith("control.tar") and not name.endswith(".zst"):
                with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as t:
                    for m in t.getmembers():
                        if os.path.basename(m.name) == "control" and m.isfile():
                            return t.extractfile(m).read().decode("utf-8")
    except Exception:
        pass
    r = subprocess.run(["dpkg-deb", "-f", path], capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit("Не удалось прочитать control из " + path)
    return r.stdout


def parse_fields(text):
    fields = {}
    for line in text.strip().splitlines():
        if line[:1] in (" ", "\t") and fields:
            last = list(fields)[-1]
            fields[last] += "\n" + line
        elif ":" in line:
            k, v = line.split(":", 1)
            fields[k.strip()] = v.strip()
    return fields


def hashes(path):
    md5, sha1, sha256 = hashlib.md5(), hashlib.sha1(), hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            md5.update(chunk); sha1.update(chunk); sha256.update(chunk)
    return md5.hexdigest(), sha1.hexdigest(), sha256.hexdigest()


def main():
    pkgs = []
    for fn in sorted(os.listdir(DEBS)):
        if not fn.endswith(".deb"):
            continue
        if " " in fn:
            raise SystemExit("В имени файла нет пробелов, пожалуйста: " + fn)
        p = os.path.join(DEBS, fn)
        fields = parse_fields(read_control(p))
        for k in ("Filename", "Size", "MD5sum", "SHA1", "SHA256"):
            fields.pop(k, None)
        md5, sha1, sha256 = hashes(p)
        fields["Filename"] = "debs/" + fn
        fields["Size"] = str(os.path.getsize(p))
        fields["MD5sum"] = md5
        fields["SHA1"] = sha1
        fields["SHA256"] = sha256
        pkgs.append(fields)
    pkgs.sort(key=lambda d: (d.get("Package", ""), d.get("Version", "")))

    entries = []
    for d in pkgs:
        entries.append("\n".join("%s: %s" % (k, v) for k, v in d.items()))
    packages = ("\n\n".join(entries) + "\n").encode("utf-8") if entries else b""

    files = {
        "Packages": packages,
        "Packages.gz": None,
        "Packages.bz2": bz2.compress(packages, 9),
        "Packages.xz": lzma.compress(packages),
    }
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0) as g:
        g.write(packages)
    files["Packages.gz"] = buf.getvalue()
    for name, data in files.items():
        with open(os.path.join(ROOT, name), "wb") as f:
            f.write(data)

    def block(algo):
        lines = []
        for name, data in files.items():
            lines.append(" %s %d %s" % (algo(data).hexdigest(), len(data), name))
        return "\n".join(lines)

    release = (
        "Origin: %s\nLabel: %s\nSuite: stable\nVersion: 1.0\nCodename: ios\n"
        "Architectures: iphoneos-arm\nComponents: main\nDescription: %s\nDate: %s\n"
        "MD5Sum:\n%s\nSHA256:\n%s\n"
    ) % (REPO_NAME, REPO_NAME, REPO_DESC,
         email.utils.format_datetime(datetime.datetime.now(datetime.timezone.utc), usegmt=True),
         block(hashlib.md5), block(hashlib.sha256))
    with open(os.path.join(ROOT, "Release"), "w", encoding="utf-8") as f:
        f.write(release)

    write_index(pkgs)
    print("Готово: %d пакет(ов)" % len(pkgs))
    for d in pkgs:
        print("  %s %s" % (d.get("Package"), d.get("Version")))


def write_index(pkgs):
    e = html.escape
    rows = ""
    for d in pkgs:
        size = int(d["Size"]) / 1024 / 1024
        rows += (
            '<a class="pkg" href="%s"><b>%s</b> <i>%s</i><span>%s</span>'
            '<small>%s · %.1f МБ</small></a>\n'
        ) % (e(d["Filename"]), e(d.get("Name", d["Package"])), e(d.get("Version", "")),
             e(d.get("Description", "")), e(d.get("Section", "")), size)
    if not rows:
        rows = '<p class="hint">Пакетов пока нет.</p>'
    u = REPO_URL
    page = """<!doctype html><html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>%(name)s</title>
<style>
:root{color-scheme:dark}
body{margin:0;background:#0e1014;color:#fff;font:16px -apple-system,system-ui,sans-serif;padding:24px;max-width:640px;margin:auto}
h1{font-size:30px;margin:8px 0 4px}p{color:#8a90a0}
.btns{display:flex;flex-wrap:wrap;gap:10px;margin:18px 0}
.btns a{background:#4c8dff;color:#fff;text-decoration:none;padding:11px 16px;border-radius:12px;font-weight:600}
.btns a.s{background:#2a2e38}
code{display:block;background:#11141a;padding:12px;border-radius:12px;word-break:break-all;color:#b8bdc9}
h2{font-size:12px;letter-spacing:1px;color:#8a90a0;margin:28px 0 10px}
.pkg{display:block;background:#1a1d24;border-radius:16px;padding:14px 16px;margin-bottom:10px;color:#fff;text-decoration:none}
.pkg i{color:#8a90a0;font-style:normal;margin-left:6px}.pkg span{display:block;color:#b8bdc9;margin-top:4px;font-size:14px}
.pkg small{display:block;color:#5c6270;margin-top:6px}.hint{color:#5c6270}
</style></head><body>
<h1>%(name)s</h1><p>%(desc)s</p>
<div class="btns">
<a href="sileo://source/%(url)s">Добавить в Sileo</a>
<a class="s" href="zbra://sources/add/%(url)s">Zebra</a>
<a class="s" href="cydia://url/https://cydia.saurik.com/api/share#?source=%(url)s">Cydia</a>
</div>
<code>%(url)s</code>
<h2>ПАКЕТЫ</h2>
%(rows)s
</body></html>""" % {"name": e(REPO_NAME), "desc": e(REPO_DESC), "url": e(u), "rows": rows}
    with open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8") as f:
        f.write(page)


if __name__ == "__main__":
    main()
