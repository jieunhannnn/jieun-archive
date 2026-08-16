#!/usr/bin/env node
/* 대시보드 데이터 의미 검증 — 배포 전 자동 실행 (deploy.sh)
 *
 * 헤드리스 실행 검증은 "터지냐"만 본다. 여기서는 "말이 되냐"를 본다.
 * 실제로 놓쳤던 것들: 시트 62% 누락(레귤러 하루 1회), 곡선 공백 미분리, 표 순서 오류.
 *
 * 경고만 출력하고 배포는 막지 않는다(종료 0). 판단은 사람이 한다.
 * 단, 데이터 구조가 깨진 경우(중복/겹침)는 ERROR로 종료 1.
 */
const path = require('path');
const HERE = __dirname;
global.window = {};
require(path.join(HERE, 'history.js'));
require(path.join(HERE, 'shots_history.js'));
require(path.join(HERE, 'data.js'));

const detail  = window.GLUCOSE || [];
const history = window.GLUCOSE_HISTORY || [];
const shotsH  = window.SHOTS_HISTORY || [];

// 이미 확인된 예외 — 시트 원본이 실제로 그러함 (2026-08-05 지은님과 확인)
const KNOWN_GLARGINE_EXCEPTIONS = new Set([
  '2026-04-04', // 기록 시작일, 23:00 하나뿐
  '2026-04-05', '2026-04-19', '2026-05-01', '2026-05-08', '2026-05-10', '2026-06-23', // 실제 1회
  '2026-04-21', // 3회 (레버미어 전환 무렵)
]);

const errors = [], warns = [], notes = [];
const E = m => errors.push(m), W = m => warns.push(m), N = m => notes.push(m);

// dayShots — index.html과 같은 분류 규칙 (아침 8시경·저녁 8시경 최근접 = 글라진)
function dayShots(d) {
  const arr = (d.shots || []).map(s => {
    const [t, k] = s.split('|'); const [h, m] = t.split(':').map(Number);
    return { t, h: h + m / 60, k: k || null, reg: k === 'g' };
  });
  [[8, 4, 12], [20, 16, 24]].forEach(([a, lo, hi]) => {
    if (arr.some(sh => sh.k === 'g' && sh.h >= lo && sh.h < hi)) return;
    const c = arr.filter(sh => !sh.k && sh.h >= lo && sh.h < hi);
    if (c.length) c.reduce((x, y) => Math.abs(y.h - a) < Math.abs(x.h - a) ? y : x).reg = true;
  });
  return arr;
}

// ── 1. 구조: 날짜 중복 / 두 층 겹침 ──
const dup = a => { const s = new Set(), d = []; a.forEach(x => s.has(x.date) ? d.push(x.date) : s.add(x.date)); return d; };
dup(detail).forEach(x => E(`data.js에 날짜 중복: ${x}`));
dup(history).forEach(x => E(`history.js에 날짜 중복: ${x}`));
const dset = new Set(detail.map(d => d.date));
history.filter(h => dset.has(h.date)).forEach(h => E(`history.js와 data.js가 겹침(이중 집계): ${h.date}`));

// ── 2. 날짜 연속성 ──
const sorted = detail.map(d => d.date).sort();
for (let i = 1; i < sorted.length; i++) {
  const gap = (new Date(sorted[i]) - new Date(sorted[i - 1])) / 86400000;
  if (gap > 1) W(`상세 데이터에 ${gap - 1}일 빈 구간: ${sorted[i - 1]} → ${sorted[i]}`);
}

// ── 3. 혈당 값 범위·커버리지 ──
detail.forEach(d => {
  const vs = (d.pts || []).map(p => p[1]);
  if (!vs.length) { E(`${d.date}: pts가 비어 있음`); return; }
  const bad = vs.filter(v => v < 20 || v > 600);
  if (bad.length) W(`${d.date}: 범위 밖 혈당 ${bad.length}개 (${bad.slice(0, 3).join(',')}…)`);
  if (d.max !== Math.max(...vs, d.max)) W(`${d.date}: max 필드(${d.max})가 실제 최고보다 작음`);
  const cov = Math.round(vs.length / 288 * 100);
  if (cov < 70) N(`${d.date}: 커버리지 ${cov}% (${Math.round(vs.length * 5 / 60)}시간) — 센서 교체일 등`);
});

// ── 4. 주사: 글라진 2회 / 레귤러 범위 ──
detail.filter(d => (d.shots || []).length).forEach(d => {
  const sh = dayShots(d);
  const g = sh.filter(x => x.reg).length, r = sh.length - g;
  if (g !== 2 && !KNOWN_GLARGINE_EXCEPTIONS.has(d.date)) W(`${d.date}: 글라진 ${g}회 (보통 2회)`);
  if (r > 6) W(`${d.date}: 레귤러 ${r}회 — 이례적으로 많음`);
});
// 실측 범위를 넘어선(아직 오지 않은) 주사 기록 — 자동 채움이 미래를 찍는 사고 방지
detail.forEach(d => {
  if (!d.pts || !d.pts.length) return;
  const last = d.pts[d.pts.length - 1][0];
  (d.shots || []).forEach(s => {
    const h = +s.split(':')[0];
    if (h > last + 0.5) E(`${d.date}: 주사 ${s.split('|')[0]}이 실측 종료(${Math.floor(last)}시) 이후 — 미래 기록`);
  });
});

const noShot = detail.filter(d => !(d.shots || []).length).map(d => d.date.slice(5));
if (noShot.length) N(`주사 기록 없는 날 ${noShot.length}일: ${noShot.join(', ')}`);

shotsH.forEach(x => {
  if (x.g !== 2 && !KNOWN_GLARGINE_EXCEPTIONS.has(x.date)) W(`${x.date}: 지속형 ${x.g}회 (시트, 보통 2회)`);
  if (x.r > 8) W(`${x.date}: 레귤러 ${x.r}회 (시트) — 이례적`);
});

// ── 5. 월간 주사 막대가 그려질 수 있는지 (데이터 소스 존재 확인) ──
const months = [...new Set([...history, ...detail].map(d => d.date.slice(0, 7)))].sort();
months.forEach(mk => {
  const hasDetail = detail.some(d => d.date.slice(0, 7) === mk && (d.shots || []).length);
  const hasSheet  = shotsH.some(x => x.date.slice(0, 7) === mk);
  if (!hasDetail && !hasSheet) N(`${mk}: 주사 기록 없음 (월간 막대가 빈 상태로 표시됨)`);
});

// ── 출력 ──
const line = (icon, arr) => arr.forEach(m => console.log(`  ${icon} ${m}`));
console.log(`\n📋 의미 검증 — 상세 ${detail.length}일 · 히스토리 ${history.length}일 · 시트주사 ${shotsH.length}일`);
if (errors.length) { console.log('\n❌ ERROR (구조가 깨짐):'); line('·', errors); }
if (warns.length)  { console.log('\n⚠️  경고 (확인 필요):');   line('·', warns); }
if (notes.length)  { console.log('\nℹ️  참고:');               line('·', notes); }
if (!errors.length && !warns.length) console.log('  ✅ 이상 없음');
process.exit(errors.length ? 1 : 0);
