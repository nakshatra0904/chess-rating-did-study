"""Collect a deterministic cohort of public Chess.com archives, serially."""
import argparse, gzip, hashlib, json, time, urllib.request, urllib.error
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / 'outputs' / 'chess-rating-study'
if (ROOT / 'data' / 'raw').exists(): PROJECT = ROOT
RAW = PROJECT / 'data' / 'raw'
UA = 'ChessRatingStudy/1.0 (public reproducible statistical research; serial requests)'

def get(url, filename):
    path = RAW / filename
    if path.exists():
        return json.loads(gzip.decompress(path.read_bytes()))
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'application/json'})
            with urllib.request.urlopen(req, timeout=60) as response:
                body = response.read()
                status = response.status
            data = json.loads(body)
            path.write_bytes(gzip.compress(body, mtime=0))
            log = {'url': url, 'file': str(path.relative_to(PROJECT)).replace('\\','/'),
                   'retrieved_utc': datetime.now(timezone.utc).isoformat(), 'status': status,
                   'sha256_uncompressed': hashlib.sha256(body).hexdigest(), 'bytes': len(body)}
            with (PROJECT/'data'/'request_log.jsonl').open('a', encoding='utf-8') as f:
                f.write(json.dumps(log)+'\n')
            time.sleep(0.15)
            return data
        except urllib.error.HTTPError as e:
            if e.code in (404, 410):
                data = {'games': [], 'request_error': str(e)}
                path.write_bytes(gzip.compress(json.dumps(data).encode(), mtime=0))
                with (PROJECT/'data'/'request_log.jsonl').open('a', encoding='utf-8') as f:
                    f.write(json.dumps({'url':url,'file':str(path.relative_to(PROJECT)).replace('\\','/'),'status':e.code,'retrieved_utc':datetime.now(timezone.utc).isoformat()})+'\n')
                return data
            if attempt == 3: raise
            time.sleep(3 * 2**attempt)
        except (OSError, ValueError):
            if attempt == 3: raise
            time.sleep(3 * 2**attempt)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--n', type=int, default=256)
    args=parser.parse_args()
    RAW.mkdir(parents=True, exist_ok=True)
    frame=get('https://api.chess.com/pub/titled/GM','titled_GM.json.gz')['players']
    ordered=sorted(set(p.lower() for p in frame), key=lambda p:hashlib.sha256(('chess-policy-2020-v1|'+p).encode()).hexdigest())
    selected=ordered[:args.n]
    meta={'sampling_frame':'Chess.com current GM endpoint at retrieval; historical survivor sample',
          'seed_string':'chess-policy-2020-v1','frame_n':len(frame),'screened_n':len(selected),
          'screen_month':'2020-07','selected':selected,'months':['2020-06','2020-07','2020-08','2020-09','2020-10']}
    (PROJECT/'data'/'cohort.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
    active=[]
    for i, player in enumerate(selected):
        data=get(f'https://api.chess.com/pub/player/{player}/games/2020/07',f'{player}_2020_07.json.gz')
        if any(g.get('rated') and g.get('rules')=='chess' and g.get('time_class') in ('bullet','blitz','rapid') for g in data.get('games',[])):
            active.append(player)
        if (i+1)%8==0: print(f'Screened {i+1}/{len(selected)}; July-active accounts {len(active)}',flush=True)
    meta['july_active']=active
    (PROJECT/'data'/'cohort.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
    for i, player in enumerate(active):
        total=0
        for month in (6,8,9,10):
            data=get(f'https://api.chess.com/pub/player/{player}/games/2020/{month:02d}',f'{player}_2020_{month:02d}.json.gz')
            total+=len(data.get('games',[]))
        print(f'Completed account {i+1}/{len(active)}; other-month archive records {total}',flush=True)
    print(json.dumps({'frame_n':len(frame),'screened':len(selected),'active':len(active),'raw_files':len(list(RAW.glob('*.gz')))}),flush=True)

if __name__=='__main__': main()
