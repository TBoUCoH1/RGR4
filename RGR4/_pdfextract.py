import re, sys, zlib

path = sys.argv[1]
data = open(path, 'rb').read()

# ---------- object table ----------
objs = {}
for m in re.finditer(rb'(?<![0-9])(\d+)\s+(\d+)\s+obj\b', data):
    num = int(m.group(1))
    start = m.end()
    e = data.find(b'endobj', start)
    s = re.search(rb'\bstream\r?\n', data[start:e if e != -1 else len(data)])
    if s is None:
        sfull = re.search(rb'\bstream\r?\n', data[start:])
        if sfull and (e == -1 or start + sfull.start() < e):
            s = sfull
    if s is not None and re.search(rb'\bstream\r?\n', data[start:e if e != -1 else len(data)]) is None:
        es = data.find(b'endstream', start)
        if es != -1:
            e = data.find(b'endobj', es)
    if e == -1:
        e = len(data)
    objs[num] = data[start:e]


def resolve(tok):
    if tok is None:
        return None
    m = re.match(rb'\s*(\d+)\s+\d+\s+R\b', tok)
    if m:
        return objs.get(int(m.group(1)))
    return tok


def stream_bytes(body):
    m = re.search(rb'\bstream\r?\n', body)
    if not m:
        return None
    raw = body[m.end():]
    i = raw.rfind(b'endstream')
    if i != -1:
        raw = raw[:i]
    for cand in (raw, raw.rstrip(b'\r\n')):
        try:
            return zlib.decompress(cand)
        except Exception:
            try:
                return zlib.decompressobj().decompress(cand)
            except Exception:
                pass
    return raw


def dict_get(body, key):
    """Return raw token for /key inside a dict body."""
    i = body.find(b'/' + key)
    while i != -1:
        after = body[i + 1 + len(key):]
        if not re.match(rb'[A-Za-z0-9]', after[:1] or b' '):
            j = 0
            while j < len(after) and after[j:j + 1] in b' \r\n\t':
                j += 1
            rest = after[j:]
            if rest[:1] == b'<' and rest[1:2] == b'<':
                depth, k = 0, 0
                while k < len(rest):
                    if rest[k:k + 2] == b'<<':
                        depth += 1; k += 2; continue
                    if rest[k:k + 2] == b'>>':
                        depth -= 1; k += 2
                        if depth == 0:
                            return rest[:k]
                        continue
                    k += 1
                return rest
            if rest[:1] == b'[':
                k = rest.find(b']')
                return rest[:k + 1]
            m = re.match(rb'(\d+\s+\d+\s+R|/[^\s/\[\]<>()]+|[-\d.]+|\S+)', rest)
            if m:
                return m.group(1)
            return None
        i = body.find(b'/' + key, i + 1)
    return None


# ---------- ToUnicode CMaps ----------
def uni(hexstr):
    try:
        b = bytes.fromhex(hexstr.decode('ascii'))
    except Exception:
        return ''
    if len(b) % 2:
        b += b'\x00'
    try:
        return b.decode('utf-16-be', 'ignore')
    except Exception:
        return ''


def parse_cmap(txt):
    mapping = {}
    width = 2
    cs = re.search(rb'begincodespacerange(.*?)endcodespacerange', txt, re.S)
    if cs:
        f = re.findall(rb'<([0-9A-Fa-f]+)>', cs.group(1))
        if f:
            width = max(1, len(f[0]) // 2)
    for m in re.finditer(rb'beginbfchar(.*?)endbfchar', txt, re.S):
        for a, b in re.findall(rb'<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]*)>', m.group(1)):
            mapping[int(a, 16)] = uni(b)
    for m in re.finditer(rb'beginbfrange(.*?)endbfrange', txt, re.S):
        for mm in re.finditer(
                rb'<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*(<[0-9A-Fa-f]*>|\[[^\]]*\])',
                m.group(1)):
            lo, hi, dst = int(mm.group(1), 16), int(mm.group(2), 16), mm.group(3)
            if hi - lo > 65535:
                continue
            if dst.startswith(b'['):
                for i, it in enumerate(re.findall(rb'<([0-9A-Fa-f]*)>', dst)):
                    mapping[lo + i] = uni(it)
            else:
                h = dst[1:-1]
                if not h:
                    continue
                base = int(h, 16)
                for i in range(hi - lo + 1):
                    mapping[lo + i] = chr(base + i) if base + i < 0x110000 else ''
    return mapping, width


font_cache = {}


def font_map(fontbody):
    key = id(fontbody)
    if key in font_cache:
        return font_cache[key]
    result = (None, 1)
    tu = dict_get(fontbody, b'ToUnicode')
    body = resolve(tu)
    if body:
        sd = stream_bytes(body)
        if sd:
            result = parse_cmap(sd)
    if result[0] is None:
        # descendant fonts (Type0) -> assume 2-byte identity
        enc = dict_get(fontbody, b'Encoding') or b''
        result = (None, 2 if b'Identity' in enc else 1)
    font_cache[key] = result
    return result


# ---------- content stream text ----------
STR_RE = re.compile(rb'\((?:\\.|[^\\()])*\)|<[0-9A-Fa-f\s]*>', re.S)


def unescape(s):
    out = bytearray()
    i = 1
    body = s[1:-1]
    while i - 1 < len(body):
        c = body[i - 1:i]
        if c == b'\\':
            n = body[i:i + 1]
            i += 2
            if n in b'nrtbf':
                out += {b'n': b'\n', b'r': b'\r', b't': b'\t', b'b': b'\b', b'f': b'\f'}[n]
            elif n.isdigit():
                oct_ = n
                while len(oct_) < 3 and body[i:i + 1].isdigit():
                    oct_ += body[i:i + 1]; i += 1
                out.append(int(oct_, 8) & 0xFF)
            else:
                out += n
        else:
            out += c
            i += 1
    return bytes(out)


def decode_str(raw, cmap, width):
    if raw[:1] == b'<':
        try:
            h = re.sub(rb'\s', b'', raw[1:-1])
            if len(h) % 2:
                h += b'0'
            b = bytes.fromhex(h.decode('ascii'))
        except Exception:
            return ''
    else:
        b = unescape(raw)
    out = []
    if width == 2:
        for i in range(0, len(b) - 1, 2):
            code = (b[i] << 8) | b[i + 1]
            out.append(cmap.get(code, '') if cmap else chr(code))
    else:
        for ch in b:
            if cmap:
                out.append(cmap.get(ch, bytes([ch]).decode('cp1251', 'ignore')))
            else:
                out.append(bytes([ch]).decode('cp1251', 'ignore'))
    return ''.join(out)


def page_text(content, fonts):
    cmap, width = None, 1
    out = []
    for m in re.finditer(
            rb'/([^\s/\[\]<>()]+)\s+[-\d.]+\s+Tf|(\[(?:[^\[\]\\]|\\.)*\])\s*TJ'
            rb'|(\((?:\\.|[^\\()])*\)|<[0-9A-Fa-f\s]*>)\s*(?:Tj|\'|")'
            rb'|(T\*|Td|TD|ET|TD)', content, re.S):
        if m.group(1):
            fb = fonts.get(m.group(1))
            if fb is not None:
                cmap, width = font_map(fb)
        elif m.group(2):
            for s in STR_RE.finditer(m.group(2)):
                out.append(decode_str(s.group(0), cmap, width))
        elif m.group(3):
            out.append(decode_str(m.group(3), cmap, width))
        else:
            out.append('\n')
    txt = ''.join(out)
    txt = re.sub(r'\n{3,}', '\n\n', txt)
    return txt


# ---------- walk pages ----------
pages = []
for num, body in objs.items():
    head = body[:body.find(b'stream')] if b'stream' in body else body
    if re.search(rb'/Type\s*/Page\b(?!s)', head):
        pages.append((num, body))
pages.sort()

for idx, (num, body) in enumerate(pages, 1):
    res = resolve(dict_get(body, b'Resources')) or b''
    fdict = resolve(dict_get(res, b'Font')) or b''
    fonts = {}
    for fm in re.finditer(rb'/([^\s/\[\]<>()]+)\s+(\d+)\s+\d+\s+R', fdict):
        fo = objs.get(int(fm.group(2)))
        if fo is not None:
            fonts[fm.group(1)] = fo
    cont = dict_get(body, b'Contents')
    chunks = []
    if cont and cont.startswith(b'['):
        for r in re.finditer(rb'(\d+)\s+\d+\s+R', cont):
            chunks.append(objs.get(int(r.group(1))))
    else:
        chunks.append(resolve(cont))
    text = ''
    for c in chunks:
        if c:
            sd = stream_bytes(c)
            if sd:
                text += page_text(sd, fonts)
    print(f'\n===== PAGE {idx} (obj {num}) =====')
    print(text.strip())
