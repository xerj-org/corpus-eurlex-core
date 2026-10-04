# corpus-eurlex-core — five core EU acts, per-article and per-recital

Plain-text mirror of the five EU acts an agent actually gets asked about, built for
the XERJ corpus hub:

| Act | CELEX | Directory | Articles | Recitals |
|---|---|---|---|---|
| General Data Protection Regulation (GDPR) | 32016R0679 | `gdpr/` | 99 (1–99) | 173 |
| Artificial Intelligence Act (AI Act) | 32024R1689 | `ai-act/` | 113 (1–113) | 180 |
| Digital Services Act (DSA) | 32022R2065 | `dsa/` | 93 (1–93) | 156 |
| Digital Markets Act (DMA) | 32022R1925 | `dma/` | 54 (1–54) | 109 |
| NIS 2 Directive | 32022L2555 | `nis2/` | 46 (1–46) | 144 |

Total: 405 article files + 762 recital files = 1,167 files.

**Scope choice (deliberate, demand-driven):** acts, articles and recitals only.
Recitals are where the interpretive answers live, so they are first-class files.
**Annexes are NOT included** in this mirror: the source manifestations carry
13 annexes for the AI Act and 3 for NIS2 (none for GDPR/DSA/DMA). In particular,
AI Act Annex III (high-risk AI systems) and Annex I are not here — extend
`tools/extract.py` to the `eli-container` divisions if annex coverage is needed.

## Layout

- `<act>/art-N.txt` — one file per article. Header: act, article number, article
  title, CELEX + OJ reference, source division id. Body: verbatim article text.
- `<act>/recital-N.txt` — one file per recital, verbatim, opening with `(N)`.

No article exceeded the 40 KB split threshold (largest: an AI Act article at
~17.5 KB), so no sub-article splitting was needed.

## Extraction lane

Fetched 2026-10-04 via **EUR-Lex Cellar content negotiation**:

```
curl -L -H "Accept: application/xhtml+xml" -H "Accept-Language: eng" \
     http://publications.europa.eu/resource/celex/<CELEX>
```

This returns the same CONVEX-generated XHTML full-text manifestation that
`https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:<CELEX>` renders.
The direct eur-lex.europa.eu URL worked for one fetch but then began returning
`HTTP 202` with `x-amzn-waf-action: challenge` (AWS WAF bot challenge, empty body)
to plain curl; the Cellar endpoint is the durable machine lane and was used for all
five acts. Article divisions are `div.eli-subdivision[id=art_N]`, recitals
`div.eli-subdivision[id=rct_N]`; the TOC part of the document is never extracted.
Human-readable copies: `https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:<CELEX>`.

Rebuild: put the five fetched `.xhtml` files in `_src/` (not committed) and run
`python3 tools/extract.py _src .`

## Licence

EU reuse policy — reuse permitted with attribution. Verified at fetch time
(https://commission.europa.eu/legal-notice_en, European Commission legal notice):

> The Commission's reuse policy is implemented by the Commission Decision of
> 12 December 2011 on the reuse of Commission documents. Unless otherwise
> indicated (e.g. in individual copyright notices), content owned by the EU on
> this website is licensed under the Creative Commons Attribution 4.0
> International (CC BY 4.0) licence. This means that reuse is allowed, provided
> appropriate credit is given and changes are indicated.

EU legal acts as published in the Official Journal carry no individual copyright
notice restricting reuse beyond that policy. Attribution for this mirror:
European Union, EUR-Lex, CELEX numbers as listed above, fetched 2026-10-04.
This mirror makes no additional claim on the text.
