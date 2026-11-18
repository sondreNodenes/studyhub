"""Match note blocks to slide pages, so the page can show "slide N" links.

Each heading, paragraph, table and top-level bullet of a lecture's notes gets the PDF page whose
text is most similar (TF-IDF cosine), with a Viterbi pass that prefers keeping slide order.
Keys mirror slideKey() in index.html: lowercase, letters/digits only, first 60 characters.
Needs `pdftotext` (poppler); without it, or without the PDF, the lecture simply gets no links.
"""
import re, math, subprocess, os, json, unicodedata
STOP=set("the and for are with that this from into over have has was were will can its not but per all any each one two more than less when what which who how why also only use used using based between they them their there then than such may must should would could about other some most very much many both same each where while does done been being out off our your you had his her she him because these those it's into upon via within without under above after before again further here once only own just too nor yes no".split())
def norm_key(t):
    t=re.sub(r'!\[.*?\]\(.*?\)','',t)
    return re.sub(r'[^a-z0-9]','',t.lower())[:60]
def toks(t):
    t=t.lower().replace('’',"'")
    out=[]
    for w in re.findall(r"[a-z][a-z\-']+|\d[\d,\.]*\d|\d+",t):
        w=w.strip("-'").replace(',','')
        if not w: continue
        if w[0].isdigit():
            if len(w)>=2: out.append('#'+w)
            continue
        if len(w)<3 or w in STOP: continue
        w=re.sub(r"(ies)$","y",w); w=re.sub(r"(?<=[a-z]{3})s$","",w)
        out.append(w)
    return out
def pages_of(pdf):
    try:
        r=subprocess.run(['pdftotext','-enc','UTF-8',pdf,'-'],capture_output=True,text=True,timeout=60)
    except (OSError, subprocess.SubprocessError):
        return []
    ps=r.stdout.split('\f')
    if ps and not ps[-1].strip(): ps=ps[:-1]
    return ps
def blocks(summary):
    """mirror of mdBlock: returns list of (kind, key, text, section_idx)"""
    lines=summary.replace('\r','').split('\n'); i=0; out=[]; sec=-1; secs=[]
    isList=lambda l: re.match(r'^\s*([-*]|\d+\.)\s+',l)
    isStart=lambda l: re.match(r'^```|^>\s?|^!\[|^#{1,4}\s|^\|',l) or isList(l)
    while i<len(lines):
        l=lines[i]
        if l.startswith('```'):
            i+=1
            while i<len(lines) and not lines[i].startswith('```'): i+=1
            i+=1; continue
        if not l.strip(): i+=1; continue
        if l.startswith('!['): i+=1; continue
        if re.match(r'^>\s?',l):
            while i<len(lines) and re.match(r'^>\s?',lines[i]): i+=1
            continue
        m=re.match(r'^(#{1,4})\s+(.*)$',l)
        if m:
            secs.append([m.group(2),[]]); sec=len(secs)-1
            out.append(['h',norm_key(m.group(2)),m.group(2),sec]); i+=1; continue
        if l.startswith('|') and i+1<len(lines) and re.match(r'^\|?\s*:?-{2,}',lines[i+1]):
            buf=[l]; i+=2
            while i<len(lines) and lines[i].startswith('|'): buf.append(lines[i]); i+=1
            out.append(['t',norm_key(l),'\n'.join(buf),sec]); continue
        if isList(l):
            cur=None
            while i<len(lines) and (isList(lines[i]) or (re.match(r'^\s+\S',lines[i]) and cur is not None)):
                mm=re.match(r'^(\s*)([-*]|\d+\.)\s+(.*)$',lines[i])
                if mm and (len(mm.group(1))//2==0 or cur is None):
                    cur=['i' if len(mm.group(1))//2==0 else 'x',None,mm.group(3),sec]; out.append(cur)
                elif mm: cur[2]+='\n'+mm.group(3)
                else: cur[2]+=' '+lines[i].strip()
                i+=1
            continue
        buf=[l]; i+=1
        while i<len(lines) and lines[i].strip() and not isStart(lines[i]): buf.append(lines[i]); i+=1
        out.append(['p',None,' '.join(buf),sec])
    for b in out:
        if b[1] is None: b[1]=norm_key(b[2].split('\n')[0])
    return out,secs
def tfidf(pages):
    P=[toks(p) for p in pages]; N=len(P)
    df={}
    for ts in P:
        for w in set(ts): df[w]=df.get(w,0)+1
    idf={w:math.log((N+1)/(c+0.5)) for w,c in df.items()}
    vecs=[]
    for ts in P:
        tf={}
        for w in ts: tf[w]=tf.get(w,0)+1
        v={w:(1+math.log(c))*idf[w] for w,c in tf.items()}
        n=math.sqrt(sum(x*x for x in v.values())) or 1
        vecs.append({w:x/n for w,x in v.items()})
    return vecs,idf
def score(text,vecs,idf):
    ts=toks(text); tf={}
    for w in ts:
        if w in idf: tf[w]=tf.get(w,0)+1
    q={w:(1+math.log(c))*idf[w] for w,c in tf.items()}
    n=math.sqrt(sum(x*x for x in q.values())) or 1
    return [sum(q[w]*v.get(w,0) for w in q)/n for v in vecs]
def mapping(summary,pages,back=0.6,fwd=0.03,minraw=0.09):
    N=len(pages)
    if not N: return {},[],0
    vecs,idf=tfidf(pages)
    bl,secs=blocks(summary)
    if not bl or not N: return {},[],N
    sectext={}
    for b in bl: sectext.setdefault(b[3],[]).append(b[2])
    em=[]; raw=[]
    for b in bl:
        t=b[2]
        if b[0]=='h': t=b[2]+' '+b[2]+'\n'+'\n'.join(sectext.get(b[3],[]))
        sc=score(t,vecs,idf); m=max(sc) or 1
        raw.append(max(sc)); em.append([x/m if max(sc)>=minraw else 0.0 for x in sc])
    # Viterbi
    V=[em[0][:]]; B=[]
    for k in range(1,len(bl)):
        prev=V[-1]; row=[]; bp=[]
        best_sofar=None
        for p in range(N):
            bestv=-1e9; bestq=0
            for q in range(N):
                pen= fwd*(p-q) if p>=q else back+fwd*(q-p)*0.5
                v=prev[q]-pen
                if v>bestv: bestv=v; bestq=q
            row.append(bestv+em[k][p]); bp.append(bestq)
        V.append(row); B.append(bp)
    p=max(range(N),key=lambda x:V[-1][x]); path=[p]
    for bp in reversed(B): p=bp[p]; path.append(p)
    path.reverse()
    res={}; dbg=[]
    first={}
    for b,p,r in zip(bl,path,raw):
        if b[0]!='h' and r>=minraw and b[3] not in first: first[b[3]]=p
    for b,p,r in zip(bl,path,raw):
        if b[0]=='h' and b[3] in first: p=first[b[3]]; r=max(r,minraw)
        ok=r>=minraw
        dbg.append((b[0],round(r,2),p+1 if ok else None,b[2][:70].replace('\n',' / ')))
        if ok and b[1] and b[1] not in res: res[b[1]]=p+1
    return res,dbg,N

def summary_of(raw):
    """The Notes text exactly as parseLecture() in index.html collects it."""
    sec='head'; out=[]
    for line in raw.replace('\r','').split('\n'):
        if re.match(r'^\s*<!--.*-->\s*$',line): continue
        m=re.match(r'^##\s+(.+)$',line)
        if m:
            n=m.group(1).lower()
            sec=('highlights' if n.startswith('highlight') else 'explained' if n.startswith('explain') else 'examples' if n.startswith('example')
                 else 'cards' if n.startswith('flash') else 'quiz' if re.match(r'^(quiz|question)',n) else 'summary')
            if sec=='summary' and not re.match(r'^(summary|notes)',n): out.append(line)
            continue
        if sec=='summary': out.append(line)
    return '\n'.join(out).strip()

_cache=None
def _pages_cached(path,cache_file):
    global _cache
    if _cache is None:
        try: _cache=json.load(open(cache_file,encoding='utf-8'))
        except Exception: _cache={}
    st=os.stat(path); sig=f"{st.st_size}:{int(st.st_mtime)}"
    hit=_cache.get(path)
    if hit and hit.get('sig')==sig: return hit['pages']
    pages=pages_of(path)
    if pages:
        _cache[path]={'sig':sig,'pages':pages}
        try: json.dump(_cache,open(cache_file,'w',encoding='utf-8'))
        except Exception: pass
    return pages

def lecture_slides(raw,base_dir,cache_file,root=None):
    """{'pdf': 0, 'pages': N, 'map': {key: page}, 'text': [page text]} for the lecture's first local PDF, or None."""
    m=re.search(r'^pdf:\s*(.*)$',raw,re.M)
    if not m: return None
    first=[x.strip() for x in m.group(1).split('|') if x.strip()]
    if not first or first[0].startswith('idb:'): return None
    path=os.path.join(root if (root and first[0].startswith('slides/')) else base_dir,first[0])
    if not os.path.exists(path): return None
    pages=_pages_cached(path,cache_file)
    if not pages: return None
    summ=summary_of(raw)
    res=mapping(summ,pages)[0] if summ else {}
    # page text for the slide search (whitespace collapsed to keep data.js small)
    text=[re.sub(r'\s+',' ',unicodedata.normalize('NFKC',p)).strip() for p in pages]  # NFKC: maths italics -> plain letters
    return {'pdf':0,'pages':len(pages),'map':res,'text':text}
