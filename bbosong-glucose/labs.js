/* 뽀송이 검사 기록 — 병원 검사 결과를 날짜별로 쌓는다.
 * v: 결과값, lo/hi: 정상 범위(없으면 참고치 없는 항목), note: 설명
 * flag는 자동 계산 (lo/hi 벗어나면 high/low)
 * 2026-09-14 경기동물의료원 */
window.LABS = [
  {
    date: '2026-09-14',
    place: '경기동물의료원',
    summary: '신장 수치 이상 — BUN·CREA 상승, 단백뇨(UPC 4.69)',
    groups: [
      { name: '신장', items: [
        { k: 'BUN',  v: 60.4, lo: 17.6, hi: 32.8, unit: 'mg/dL', note: '요소질소 — 신장 기능' },
        { k: 'CREA', v: 1.91, lo: 0.8,  hi: 1.8,  unit: 'mg/dL', note: '크레아티닌 — 신장 기능' },
        { k: 'BUN/CREA', v: 31.6, lo: 17.5, hi: 21.9, unit: '' },
        { k: 'UPC (요단백/크레아티닌)', v: 4.69, hi: 0.4, unit: '', note: '0.4↑ 단백뇨 · 2.0↑ 신장 손상 진행' },
        { k: 'PHOS', v: 5.6, lo: 2.6, hi: 6, unit: 'mg/dL', note: '인 — 신장병에서 중요, 상한 근처' },
      ]},
      { name: '대사', items: [
        { k: 'CHOL', v: 358, lo: 89, hi: 176, unit: 'mg/dL', note: '콜레스테롤 — 당뇨 조절 불량 시 상승' },
        { k: 'ALB',  v: 3.1, lo: 2.3, hi: 3.5, unit: 'g/dL' },
      ]},
      { name: '빈혈 (CBC)', items: [
        { k: 'HGB', v: 10.8, lo: 9.8,  hi: 16.2, unit: 'g/dL', note: '신장병 후기엔 빈혈 옴 — 아직 정상' },
        { k: 'HCT', v: 34.8, lo: 30.3, hi: 52.3, unit: '%' },
        { k: 'RBC', v: 7.62, lo: 6.54, hi: 12.2, unit: '10⁶/μL' },
      ]},
      { name: '염증·기타', items: [
        { k: 'WBC', v: 8.72, lo: 2.87, hi: 17.02, unit: '10³/μL', note: '백혈구 — 감염 징후 없음' },
        { k: 'PLT', v: 351,  lo: 151,  hi: 600,   unit: '10³/μL' },
        { k: 'K',   v: 4.17, lo: 3.3,  hi: 4.5,   unit: 'mmol/L' },
        { k: 'Na',  v: 152,  lo: 149,  hi: 157,   unit: 'mmol/L' },
      ]},
    ],
  },
];
