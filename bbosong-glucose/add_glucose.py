#!/usr/bin/env python3
"""리브레 CSV에서 대시보드에 없는 새 날짜만 골라 data.js에 추가한다.
사용법:  python3 add_glucose.py <CSV경로> [--from 2026-07-09]
 - 기록유형 1(1분 실시간, 컬럼5) 우선, 없으면 유형 0(15분 과거, 컬럼4)
 - 5분 간격 리샘플 / 저혈당(70미만)·max·min 자동 / shots는 빈 배열(인슐린은 따로 입력)
 - 이미 있는 날짜는 건너뜀. 새 날짜만 추가하고 날짜순 정렬해서 data.js를 다시 쓴다.
"""
import csv, json, sys, re, os
from datetime import datetime
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_JS = os.path.join(HERE, 'data.js')

def load_existing():
    raw = open(DATA_JS, encoding='utf-8').read()
    i = raw.index('window.GLUCOSE')
    hdr = raw[:i]
    body = raw[i:]
    arr = json.loads(body[body.index('['):body.rindex(']')+1])
    return hdr, arr

def parse_csv(path, start):
    RT = defaultdict(dict); HIST = defaultdict(dict)
    with open(path, encoding='utf-8') as f:
        r = csv.reader(f); next(r); next(r)
        for row in r:
            if len(row) < 6: continue
            ts = row[2]; d = ts[:10]
            if d < start: continue
            try: dt = datetime.strptime(ts, '%Y-%m-%d %H:%M')
            except ValueError: continue
            m = dt.hour*60 + dt.minute
            if row[3] == '1' and row[5].strip(): RT[d][m] = int(row[5])
            elif row[3] == '0' and row[4].strip(): HIST[d][m] = int(row[4])
    return RT, HIST

def build_day(d, R, H):
    pts = []
    for m in range(0, 1440, 5):
        v = None
        for dm in (0, 1, -1, 2, -2):
            if m+dm in R: v = R[m+dm]; break
        if v is None:
            best = None
            for dm in range(-7, 8):
                if m+dm in H and (best is None or abs(dm) < abs(best[0])): best = (dm, H[m+dm])
            if best: v = best[1]
        if v is not None: pts.append([round(m/60, 3), v])
    if len(pts) < 200:  # 하루가 거의 다 차야 완결된 날로 인정 (부분 날 제외)
        return None
    raw = sorted({**H, **R}.items())
    vals = [v for _, v in raw]
    mx, mn = max(vals), min(vals)
    lows = []; i = 0
    while i < len(raw):
        if raw[i][1] < 70:
            j = i; lo = raw[i]
            while j < len(raw) and raw[j][1] < 70:
                if raw[j][1] < lo[1]: lo = raw[j]
                j += 1
            lows.append({'t': round(lo[0]/60, 3), 'val': lo[1]}); i = j
        else: i += 1
    obj = {'date': d, 'pts': pts, 'max': mx, 'min': mn}
    if lows: obj['lows'] = lows
    obj['shots'] = []
    return obj

def main():
    if len(sys.argv) < 2:
        print("사용법: python3 add_glucose.py <CSV경로> [--from YYYY-MM-DD]"); sys.exit(1)
    csv_path = sys.argv[1]
    start = '2026-07-09'
    if '--from' in sys.argv: start = sys.argv[sys.argv.index('--from')+1]

    hdr, arr = load_existing()
    have = {d['date'] for d in arr}
    RT, HIST = parse_csv(csv_path, start)

    added = []
    for d in sorted(set(RT) | set(HIST)):
        if d in have: continue
        obj = build_day(d, RT[d], HIST[d])
        if obj: arr.append(obj); added.append(obj)

    if not added:
        print("새로 추가할 날짜 없음 (모두 이미 있음)."); return
    arr.sort(key=lambda x: x['date'])
    open(DATA_JS, 'w', encoding='utf-8').write(hdr + 'window.GLUCOSE = ' + json.dumps(arr, ensure_ascii=False) + ';\n')
    print(f"추가됨: {len(added)}일")
    for o in added:
        lw = ('저혈당 ' + ','.join(str(l['val']) for l in o['lows'])) if 'lows' in o else '저혈당없음'
        print(f"  {o['date']}: {len(o['pts'])}pt 최고{o['max']} 최저{o['min']} {lw}")
    print(f"\n총 {len(arr)}일 ({arr[0]['date']}~{arr[-1]['date']})")

if __name__ == '__main__':
    main()
