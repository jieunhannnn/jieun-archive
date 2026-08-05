#!/usr/bin/env python3
"""구글시트 '인슐린/수액'에서 과거 주사 일별 집계를 뽑아 shots_history.js를 만든다.
사용법: python3 gen_shots_history.py

⚠️ 시트 형식 주의 — 같은 날 두 번째 기록부터는 날짜 칸을 비워둔다.
   (441행 중 275행이 빈 날짜) 그래서 날짜를 forward-fill 해야 하고,
   안 하면 하루 1건씩만 잡혀서 조용히 62%가 사라진다. 실제로 그런 적 있음.
   → 아래 '총량 검산'이 그 사고를 막는 장치다. 숫자가 안 맞으면 종료 코드 1.

출력 필드: date, g(지속형=글라진·레버미어), r(레귤러)
"""
import sys, os, re, json, warnings
warnings.filterwarnings('ignore')
sys.path.insert(0, '/Users/han/Documents')
from collections import defaultdict, Counter

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'shots_history.js')
YEAR = 2026
REGULAR_KEYS = ('레귤러', '속효')          # 이 단어가 들어가면 속효성, 나머지는 지속형


def main():
    import cat_record as cr
    rows = cr.open_sheet('인슐린/수액').get_all_values()

    # 원본에서 '종류가 적힌 행' 수 — 검산 기준
    expected = sum(1 for r in rows[1:] if len(r) > 3 and r[3].strip())

    agg = defaultdict(lambda: {'g': 0, 'r': 0})
    kinds = Counter()
    cur = None
    counted = 0
    orphan = 0          # 날짜를 한 번도 못 만난 채 나온 기록
    skipped_false = 0   # 투여 여부 FALSE

    for r in rows[1:]:
        r = (r + [''] * 6)[:6]
        date, _t, _dose, kind, _bg, done = (x.strip() for x in r)

        m = re.match(r'^(\d{1,2})/(\d{1,2})$', date)
        if m:
            cur = f'{YEAR}-{int(m.group(1)):02d}-{int(m.group(2)):02d}'
        if not kind:
            continue
        if cur is None:
            orphan += 1
            continue
        if done.upper() == 'FALSE':
            skipped_false += 1
            counted += 1          # 원본에는 있는 행이므로 검산 대상엔 포함
            continue

        kinds[kind] += 1
        key = 'r' if any(k in kind for k in REGULAR_KEYS) else 'g'
        agg[cur][key] += 1
        counted += 1

    # ── 총량 검산 ──
    print(f'원본 종류 기록: {expected}행 / 집계: {counted}행 → 누락 {expected - counted}건')
    if orphan:
        print(f'  ⚠️ 날짜 없이 시작된 기록 {orphan}건')
    if skipped_false:
        print(f'  · 투여 여부 FALSE로 제외: {skipped_false}건')
    if counted != expected:
        print('❌ 검산 실패 — 파싱이 행을 흘리고 있다. 시트 형식을 다시 확인할 것.')
        sys.exit(1)

    out = [{'date': k, **v} for k, v in sorted(agg.items())]
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write('/* 뽀송이 과거 주사 일별 집계 — gen_shots_history.py로 생성 (구글시트 인슐린/수액)\n')
        f.write(' * g=지속형(글라진·레버미어), r=레귤러\n')
        f.write(' * 시트는 같은 날 반복 시 날짜칸을 비움 → 스크립트가 forward-fill 함 */\n')
        f.write('window.SHOTS_HISTORY = ' + json.dumps(out, ensure_ascii=False, separators=(',', ':')) + ';\n')

    months = defaultdict(lambda: [0, 0, 0])
    for o in out:
        m = months[o['date'][:7]]
        m[0] += 1; m[1] += o['g']; m[2] += o['r']
    print(f'\n✅ 생성: {len(out)}일 ({out[0]["date"]}~{out[-1]["date"]})  종류 {dict(kinds)}')
    for k in sorted(months):
        n, g, r = months[k]
        print(f'   {k}: {n}일 · 지속형 {g} · 레귤러 {r} (하루 평균 {r/n:.1f}회)')


if __name__ == '__main__':
    main()
