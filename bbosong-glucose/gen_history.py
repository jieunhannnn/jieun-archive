#!/usr/bin/env python3
"""전체 리브레 CSV에서 상세기간(7/11) 이전의 '일별 요약'을 뽑아 history.js를 만든다.
사용법: python3 gen_history.py <CSV경로>
필드: date, avg, max, min, tir(100~300 비율%), stable(30분 보폭 ±35 완만%), lowsR/lowsC(진짜/압박의심 저혈당), hp(30분 간격 곡선)
"""
import csv, json, sys, os
from datetime import datetime
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
DETAIL_START = '2026-07-09'   # 이 날짜부터는 data.js(상세)가 담당

def main():
    if len(sys.argv) < 2:
        print("사용법: python3 gen_history.py <CSV경로>"); sys.exit(1)
    rt = defaultdict(dict); hist = defaultdict(dict)
    with open(sys.argv[1], encoding='utf-8') as f:
        r = csv.reader(f); next(r); next(r)
        for row in r:
            if len(row) < 6: continue
            ts = row[2]; d = ts[:10]
            if d >= DETAIL_START or d < '2026-01-01': continue
            try: dt = datetime.strptime(ts, '%Y-%m-%d %H:%M')
            except ValueError: continue
            m = dt.hour*60 + dt.minute
            if row[3] == '1' and row[5].strip(): rt[d][m] = int(row[5])
            elif row[3] == '0' and row[4].strip(): hist[d][m] = int(row[4])

    out = []
    for d in sorted(set(rt) | set(hist)):
        R, H = rt[d], hist[d]
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
            if v is not None: pts.append((m/60.0, v))
        if len(pts) < 100:  # 8시간 이상 커버된 날만
            continue
        vals = [v for _, v in pts]
        avg = round(sum(vals)/len(vals))
        tir = round(100*sum(1 for v in vals if 100 <= v <= 300)/len(vals))
        # 보폭 안정률 (30분 ±35)
        ok = tot = 0
        for i, (t, v) in enumerate(pts):
            q = next((p for p in pts[i+1:] if t+0.45 <= p[0] <= t+0.55), None)
            if not q: continue
            tot += 1
            if abs(q[1]-v) <= 35: ok += 1
        stable = round(100*ok/tot) if tot else 0
        # 저혈당 구간 + 압박 의심 (원시값 기준, 회복측 15분 내 +100 반등)
        raw = sorted({**H, **R}.items())
        lowsR = lowsC = 0; lows = []
        i = 0
        while i < len(raw):
            if raw[i][1] < 70:
                j = i; lo = raw[i]
                while j < len(raw) and raw[j][1] < 70:
                    if raw[j][1] < lo[1]: lo = raw[j]
                    j += 1
                rebound = any(m2 > lo[0] and m2 <= lo[0]+15 and v2 >= lo[1]+100 for m2, v2 in raw)
                if rebound: lowsC += 1
                else: lowsR += 1
                lows.append({'t': round(lo[0]/60, 3), 'val': lo[1], 'comp': bool(rebound)})
                i = j
            else: i += 1
        hp = [[round(t,2), v] for t, v in pts if abs((t*60) % 30) < 3]  # 30분 간격 곡선 (월간 그래프용)
        rec = {'date': d, 'avg': avg, 'max': max(vals), 'min': min(vals), 'tir': tir, 'stable': stable, 'hp': hp}
        if lowsR: rec['lowsR'] = lowsR
        if lowsC: rec['lowsC'] = lowsC
        if lows: rec['lows'] = lows
        out.append(rec)

    hdr = ("/* 뽀송이 과거 일별 요약 (상세기간 이전: ~%s 전날) — gen_history.py로 생성\n"
           " * avg/max/min, tir=목표(100~300)%%, stable=30분 보폭 ±35 완만%%, lowsR=진짜 저혈당, lowsC=센서 압박 의심 */\n"
           % DETAIL_START)
    with open(os.path.join(HERE, 'history.js'), 'w', encoding='utf-8') as f:
        f.write(hdr + 'window.GLUCOSE_HISTORY = ' + json.dumps(out, ensure_ascii=False, separators=(',', ':')) + ';\n')
    months = defaultdict(int)
    for o in out: months[o['date'][:7]] += 1
    print('생성:', len(out), '일 →', dict(sorted(months.items())))
    lr = sum(o.get('lowsR', 0) for o in out); lc = sum(o.get('lowsC', 0) for o in out)
    print('저혈당: 진짜', lr, '구간 / 압박 의심', lc, '구간')

if __name__ == '__main__':
    main()
