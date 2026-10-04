#!/usr/bin/env python3
"""Extract per-article and per-recital plain-text files from EUR-Lex CONVEX XHTML.

Lane used: Cellar content negotiation (publications.europa.eu/resource/celex/<CELEX>,
Accept: application/xhtml+xml, Accept-Language: eng) which serves the same CONVEX
XHTML manifestation as eur-lex.europa.eu /legal-content/EN/TXT/HTML/.
"""
import html as htmllib
import html.entities
import os
import re
import sys
import xml.etree.ElementTree as ET

XH = '{http://www.w3.org/1999/xhtml}'
ACTS = {
    '32016R0679': ('gdpr', 'GDPR', 'Regulation (EU) 2016/679 (General Data Protection Regulation)'),
    '32024R1689': ('ai-act', 'AI Act', 'Regulation (EU) 2024/1689 (Artificial Intelligence Act)'),
    '32022R2065': ('dsa', 'DSA', 'Regulation (EU) 2022/2065 (Digital Services Act)'),
    '32022R1925': ('dma', 'DMA', 'Regulation (EU) 2022/1925 (Digital Markets Act)'),
    '32022L2555': ('nis2', 'NIS2', 'Directive (EU) 2022/2555 (NIS 2 Directive)'),
}
FETCH_DATE = '2026-10-04'
CELLAR_URL = 'http://publications.europa.eu/resource/celex/'
HUMAN_URL = 'https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:'


def parse_xhtml(path):
    raw = open(path, 'rb').read().decode('utf-8')
    raw = re.sub(r'<!DOCTYPE[^>]*>', '', raw, count=1)
    # map HTML named entities that are not predefined in XML
    def ent(m):
        name = m.group(1)
        if name in html.entities.html5:
            v = html.entities.html5[name]
            return v if m.group(0).endswith(';') else v
        return m.group(0)
    raw = re.sub(r'&([a-zA-Z][a-zA-Z0-9]*);', ent, raw)
    return ET.fromstring(raw)


def norm(s):
    s = s.replace('\xa0', ' ')
    return re.sub(r'\s+', ' ', s).strip()


def cell_text(td):
    parts = []
    for p in td.iter():
        if p.tag == f'{XH}p':
            t = norm(''.join(p.itertext()))
            if t:
                parts.append(t)
    if not parts:
        t = norm(''.join(td.itertext()))
        return t
    return ' '.join(parts)


LABEL = re.compile("[‘'\"“]?\\((?:[0-9]+[a-z]?|[a-z]+)\\)[’'\"”]?|[—–-]")


def render_table(tbl, out):
    rows = []
    # only rows whose nearest table is this one (nested tables render inline
    # via cell_text, so their text is not lost — nor duplicated)
    trs = tbl.findall(f'{XH}tr')
    for sect in ('thead', 'tbody', 'tfoot'):
        trs.extend(tbl.findall(f'{XH}{sect}/{XH}tr'))
    for tr in trs:
        cells = [cell_text(td) for td in tr if td.tag in (f'{XH}td', f'{XH}th')]
        cells = [c for c in cells if c]
        if not cells:
            continue
        rows.append(cells)
    # enumeration layout: every row is a "(label)" cell plus one text cell
    if rows and all(len(r) == 2 and LABEL.fullmatch(r[0]) for r in rows):
        for r in rows:
            out.append(r[0] + ' ' + r[1])
        return
    for r in rows:
        out.append(' | '.join(r))


def render_block(el, out):
    """Render children of a container element to text lines."""
    for ch in el:
        tag = ch.tag
        if tag == f'{XH}p':
            cls = ch.attrib.get('class', '')
            if 'oj-ti-art' in cls or 'oj-sti-art' in cls:
                continue
            t = norm(''.join(ch.itertext()))
            if t:
                out.append(t)
        elif tag == f'{XH}table':
            render_table(ch, out)
        elif tag == f'{XH}div':
            cls = ch.attrib.get('class', '')
            if 'eli-title' in cls:
                continue
            render_block(ch, out)
        elif tag == f'{XH}ul' or tag == f'{XH}ol':
            for li in ch.findall(f'{XH}li'):
                t = norm(''.join(li.itertext()))
                if t:
                    out.append('- ' + t)
        elif tag == f'{XH}hr':
            continue
        else:
            t = norm(''.join(ch.itertext()))
            if t:
                out.append(t)


def split_subdivisions(root):
    arts, recs, others = {}, {}, []
    for div in root.iter(f'{XH}div'):
        if div.attrib.get('class') != 'eli-subdivision':
            continue
        did = div.attrib.get('id', '')
        m = re.fullmatch(r'art_(\d+)', did)
        if m:
            arts[int(m.group(1))] = div
            continue
        m = re.fullmatch(r'rct_(\d+)', did)
        if m:
            recs[int(m.group(1))] = div
            continue
        others.append(did)
    return arts, recs, others


def article_header(div):
    num, title = None, None
    for p in div.findall(f'{XH}p'):
        if 'oj-ti-art' in p.attrib.get('class', ''):
            num = norm(''.join(p.itertext()))
            break
    for t in div.findall(f'{XH}div'):
        if 'eli-title' in t.attrib.get('class', ''):
            tt = norm(''.join(t.itertext()))
            if tt:
                title = tt
    return num, title


def doc_header(root):
    """Return (formal long title, OJ reference string) from the OJ header block."""
    title, oj, date = None, None, None
    for p in root.iter(f'{XH}p'):
        cls = p.attrib.get('class', '')
        t = norm(''.join(p.itertext()))
        if cls == 'oj-hd-date' and date is None:
            date = t
        elif cls == 'oj-hd-oj' and oj is None:
            oj = t
    for div in root.iter(f'{XH}div'):
        if div.attrib.get('class') == 'eli-main-title':
            parts = [norm(''.join(p.itertext())) for p in div.findall(f'{XH}p')]
            title = ' '.join(x for x in parts if x)
            break
    ojref = None
    if oj:
        # "L 119/1" -> "OJ L 119, 4.5.2016, p. 1"
        m = re.fullmatch(r'([A-Z]\s*\d+)\s*/\s*(\d+)', oj)
        if m and date:
            series = re.sub(r'\s+', ' ', m.group(1))
            ojref = f'OJ {series}, {date}, p. {m.group(2)}'
        else:
            ojref = oj
    return title, ojref


def main(srcdir, outdir):
    summary = []
    for celex, (slug, short, formal) in ACTS.items():
        path = os.path.join(srcdir, celex + '.xhtml')
        root = parse_xhtml(path)
        arts, recs, others = split_subdivisions(root)
        doc_title, ojref = doc_header(root)
        adir = os.path.join(outdir, slug)
        for sub in ('',):
            os.makedirs(adir, exist_ok=True)
        big = []
        for n, div in sorted(arts.items()):
            num, title = article_header(div)
            lines = []
            render_block(div, lines)
            body = '\n'.join(lines).strip()
            head = [f'{short} — Article {n}']
            if title:
                head.append(title)
            head.append(f'{formal} | CELEX:{celex}' + (f' | {ojref}' if ojref else ''))
            head.append(f'Source: EUR-Lex (Cellar XHTML, eli-subdivision id="art_{n}"); fetched {FETCH_DATE}')
            text = '\n'.join(head) + '\n\n' + body + '\n'
            if len(body.encode('utf-8')) > 40000:
                big.append((n, len(body.encode('utf-8'))))
            with open(os.path.join(adir, f'art-{n}.txt'), 'w', encoding='utf-8') as f:
                f.write(text)
        for n, div in sorted(recs.items()):
            lines = []
            render_block(div, lines)
            body = '\n'.join(lines).strip()
            head = [
                f'{short} — Recital {n}',
                f'{formal} | CELEX:{celex}' + (f' | {ojref}' if ojref else ''),
                f'Source: EUR-Lex (Cellar XHTML, eli-subdivision id="rct_{n}"); fetched {FETCH_DATE}',
            ]
            with open(os.path.join(adir, f'recital-{n}.txt'), 'w', encoding='utf-8') as f:
                f.write('\n'.join(head) + '\n\n' + body + '\n')
        summary.append((celex, slug, len(arts), min(arts), max(arts), len(recs), min(recs), max(recs), sorted(set(others)), big, doc_title, ojref))
    for s in summary:
        celex, slug, na, a0, a1, nr, r0, r1, others, big, title, ojref = s
        print(f'{slug} ({celex}): articles {na} (art {a0}..{a1}), recitals {nr} (rct {r0}..{r1}); other subdivisions: {others}; oversize: {big}')
        print(f'   ojref: {ojref}')
        print(f'   title: {(title or "")[:180]}')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
