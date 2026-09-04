#!/usr/bin/env python3
"""리브레 CSV에서 대시보드에 없는 새 날짜만 골라 data.js에 추가한다.
사용법:  python3 add_glucose.py <CSV경로> [--from 2026-07-09] [--redo 2026-08-04]
 - 기록유형 1(1분 실시간, 컬럼5) 우선, 없으면 유형 0(15분 과거, 컬럼4)
 - 5분 간격 리샘플 / 저혈당(70미만)·max·min 자동 / shots는 빈 배열(인슐린은 따로 입력)
 - 커버리지 2시간 이상이면 수록(센서 교체일 등 공백 큰 날도 빈 채로 들어감)
 - 이미 있는 날짜는 건너뜀. 새 날짜만 추가하고 날짜순 정렬해서 data.js를 다시 쓴다.
"""
import csv, json, sys, re, os
from datetime import datetime
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_LONG_U = '10'    # 글라진 기본 용량 (지은님 지정, 2026-09-03). 예외만 따로 알려줌
DEFAULT_FAST_U = '2.5'   # 레귤러 기본 용량
DATA_JS = os.path.join(HERE, 'data.js')

def load_existing():
    raw = open(DATA_JS, encoding='utf-8').read()
    i = raw.index('window.GLUCOSE')
    hdr = raw[:i]
    body = raw[i:]
    arr = json.loads(body[body.index('['):body.rindex(']')+1])
    return hdr, arr

def parse_csv(path, start):
    """혈당(유형 0·1)과 인슐린(유형 4)을 함께 읽는다.
    리브레 CSV에 주사 기록이 들어있다 — 컬럼 12/13=지속형(글라진), 7/8=초속효(레귤러).
    '단위' 칸이 비고 '비수치' 칸만 1이면 시각만 기록된 것 → 기본 용량을 쓴다."""
    RT = defaultdict(dict); HIST = defaultdict(dict); SHOTS = defaultdict(list)
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
            elif row[3] == '4' and len(row) > 12:
                hhmm = dt.strftime('%H:%M')
                # 0-based: 11=비수치적 지속형, 12=지속형(단위), 6=비수치적 초속효, 7=초속효(단위)
                long_u, long_f = row[12].strip(), row[11].strip()
                fast_u, fast_f = row[7].strip(),  row[6].strip()
                if long_u or long_f:
                    SHOTS[d].append((m, f"{hhmm}|g|{_num(long_u) or DEFAULT_LONG_U}"))
                elif fast_u or fast_f:
                    SHOTS[d].append((m, f"{hhmm}|r|{_num(fast_u) or DEFAULT_FAST_U}"))
    for d in SHOTS:
        SHOTS[d] = [s for _, s in sorted(SHOTS[d])]
    return RT, HIST, SHOTS

def _num(x):
    """'12.0' → '12', 빈 값 → None"""
    if not x: return None
    try:
        v = float(x)
        return str(int(v)) if v == int(v) else str(v)
    except ValueError:
        return None

def build_day(d, R, H, shots=None, recent_dose=DEFAULT_LONG_U):
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
    if len(pts) < 24:  # 최소 2시간(24칸)만 있으면 넣는다. 센서 교체일 등 공백 큰 날도 그대로 수록
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
    obj['shots'] = shots or []   # 리브레 CSV의 실제 주사 기록 (유형 4)
    # CSV에 정규 슬롯(아침 4~12시·저녁 16~24시) 기록이 없으면 8시/20시로 자동 보완.
    # 지은님 루틴이 오전·오후 8시 고정이라, 앱 입력을 빠뜨린 날을 메운다. (2026-09-03 지시)
    # ⚠️ 아직 오지 않은 시각은 넣지 않는다 — 그날 실측이 도달한 시각까지만.
    last_h = pts[-1][0] if pts else 0
    # 용량 우선순위: ① 그날 CSV에 기록된 글라진 용량 → ② 직전 날짜 용량
    known = [sh.split('|')[2] for sh in obj['shots']
             if len(sh.split('|')) > 2 and sh.split('|')[1] == 'g']
    dose = known[-1] if known else recent_dose
    for anchor, lo, hi in ((8, 4, 12), (20, 16, 24)):
        if anchor > last_h: continue
        h = lambda sh: int(sh[:2]) + int(sh[3:5]) / 60
        if any(lo <= h(sh) < hi and sh.split('|')[1] == 'g' for sh in obj['shots']): continue
        obj['shots'].append(f'{anchor:02d}:00|g|{dose}')
    obj['shots'].sort()
    return obj

def main():
    if len(sys.argv) < 2:
        print("사용법: python3 add_glucose.py <CSV경로> [--from YYYY-MM-DD]"); sys.exit(1)
    csv_path = sys.argv[1]
    start = '2026-07-09'
    if '--from' in sys.argv: start = sys.argv[sys.argv.index('--from')+1]

    hdr, arr = load_existing()
    # --redo YYYY-MM-DD : 이미 있는 날을 새 CSV로 다시 만든다 (주사 기록은 보존)
    redo = []
    while '--redo' in sys.argv:
        i = sys.argv.index('--redo'); redo.append(sys.argv[i+1]); del sys.argv[i:i+2]
    kept_shots = {}
    if redo:
        for d in arr:
            if d['date'] in redo: kept_shots[d['date']] = d.get('shots', [])
        arr = [d for d in arr if d['date'] not in redo]
        if redo and min(redo) < start: start = min(redo)

    have = {d['date'] for d in arr}
    RT, HIST, SHOTS = parse_csv(csv_path, start)

    added = []
    for d in sorted(set(RT) | set(HIST)):
        if d in have: continue
        # CSV 기록 + 기존(손으로 넣은) 기록을 합친다. 같은 슬롯이면 CSV가 우선.
        csv_shots = SHOTS.get(d) or []
        merged = list(csv_shots)
        for old_sh in kept_shots.get(d, []):
            oh = int(old_sh[:2]) + int(old_sh[3:5]) / 60
            dup = any(abs((int(c[:2]) + int(c[3:5]) / 60) - oh) <= 1 and
                      c.split('|')[1:2] == old_sh.split('|')[1:2] for c in csv_shots)
            if not dup: merged.append(old_sh)
        merged.sort()
        obj = build_day(d, RT[d], HIST[d], merged)   # 용량은 CSV값 → 없으면 기본 10u
        if obj:
            arr.append(obj); added.append(obj)

    if not added:
        print("새로 추가할 날짜 없음 (모두 이미 있음)."); return
    arr.sort(key=lambda x: x['date'])
    open(DATA_JS, 'w', encoding='utf-8').write(hdr + 'window.GLUCOSE = ' + json.dumps(arr, ensure_ascii=False) + ';\n')
    print(f"추가됨: {len(added)}일")
    for o in added:
        lw = ('저혈당 ' + ','.join(str(l['val']) for l in o['lows'])) if 'lows' in o else '저혈당없음'
        sh = ' 주사[' + ', '.join(o['shots']) + ']' if o['shots'] else ' 주사없음'
        print(f"  {o['date']}: {len(o['pts'])}pt 최고{o['max']} 최저{o['min']} {lw}{sh}")
    print(f"\n총 {len(arr)}일 ({arr[0]['date']}~{arr[-1]['date']})")

if __name__ == '__main__':
    main()
