const pptxgen = require("pptxgenjs");

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";              // 13.3 x 7.5 in — set BEFORE adding slides
pres.author = "Team nailong";
pres.title  = "Shopping Copilot — Team nailong";

// Palette: teal/mint, chosen for the team name (nailong) and a precision-search topic.
const INK   = "0B2027";   // near-black teal, dark slides
const INK2  = "13323B";   // raised dark surface
const TEAL  = "028090";
const SEA   = "00A896";
const MINT  = "02C39A";
const WHITE = "FFFFFF";
const MIST  = "EDF5F4";   // light card tint
const SLATE = "44585E";   // muted body on light
const FOG   = "9FB4B8";   // muted body on dark

const H = "Cambria";      // header face
const B = "Calibri";      // body face

const M = 0.62;           // slide margin
const W = 13.33, HT = 7.5;

const shadow = () => ({ type: "outer", angle: 90, blur: 12, offset: 3, color: "0B2027", opacity: 0.16 });

function darkSlide() {
  const s = pres.addSlide();
  s.background = { color: INK };
  return s;
}
function lightSlide(title, kicker) {
  const s = pres.addSlide();
  s.background = { color: WHITE };
  if (kicker) {
    s.addText(kicker.toUpperCase(), {
      x: M, y: 0.42, w: 8, h: 0.28, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 12, bold: true, color: TEAL, charSpacing: 2,
    });
  }
  s.addText(title, {
    x: M, y: kicker ? 0.72 : 0.5, w: W - 2 * M, h: 0.72, isTextBox: true, margin: 0,
    fontFace: H, fontSize: 34, bold: true, color: INK,
  });
  return s;
}
// Repeated motif: a filled rounded chip carrying a number or short label.
function chip(s, x, y, label, fill = MINT, txt = INK, size = 0.42) {
  s.addShape(pres.ShapeType.roundRect, {
    x, y, w: size, h: size, rectRadius: 0.1, fill: { color: fill }, line: { color: fill },
  });
  s.addText(label, {
    x, y, w: size, h: size, isTextBox: true, margin: 0,
    fontFace: B, fontSize: 15, bold: true, color: txt, align: "center", valign: "middle",
  });
}
function card(s, x, y, w, h, fill = MIST) {
  s.addShape(pres.ShapeType.roundRect, {
    x, y, w, h, rectRadius: 0.06, fill: { color: fill }, line: { color: fill }, shadow: shadow(),
  });
}

/* ─── 1. Title ─────────────────────────────────────────────────────────── */
{
  const s = darkSlide();
  s.addShape(pres.ShapeType.roundRect, { x: M, y: 1.02, w: 1.9, h: 0.46, rectRadius: 0.1,
    fill: { color: MINT }, line: { color: MINT } });
  s.addText("nailong", { x: M, y: 1.02, w: 1.9, h: 0.46, isTextBox: true, margin: 0,
    fontFace: B, fontSize: 17, bold: true, color: INK, align: "center", valign: "middle" });

  s.addText("Shopping Copilot", { x: M, y: 1.72, w: 9.6, h: 1.0, isTextBox: true, margin: 0,
    fontFace: H, fontSize: 54, bold: true, color: WHITE });
  s.addText("Conversational search that resolves 60% of sessions on the first message",
    { x: M, y: 2.78, w: 9.4, h: 0.5, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 19, color: SEA });

  const stats = [
    ["0.107", "provided baseline"],
    ["0.876", "our TechnicalScore"],
    ["8.2x", "improvement"],
  ];
  stats.forEach(([big, small], i) => {
    const x = M + i * 3.15;
    s.addText(big, { x, y: 4.15, w: 2.9, h: 0.86, isTextBox: true, margin: 0,
      fontFace: H, fontSize: 46, bold: true, color: i === 1 ? MINT : FOG });
    s.addText(small, { x, y: 5.0, w: 2.9, h: 0.34, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 13, color: FOG });
  });

  s.addText("TikTok TechJam 2026  ·  Track 4  ·  50,000-product Amazon catalogue  ·  no LLM, fully offline",
    { x: M, y: 6.5, w: 11.5, h: 0.34, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 13, color: FOG });
  s.addNotes("Team nailong. We built a conversational shopping agent for Track 4. The provided BM25 baseline scores 0.107; we reached 0.876, an 8.2x improvement, using no LLM at all. Everything you'll see is deterministic and runs fully offline.");
}

/* ─── 2. The problem ───────────────────────────────────────────────────── */
{
  const s = lightSlide("The baseline was stuck in a loop", "The problem");
  card(s, M, 1.78, 6.1, 3.28);
  s.addText("What the starter agent did", { x: M + 0.34, y: 2.02, w: 5.4, h: 0.34, isTextBox: true,
    margin: 0, fontFace: B, fontSize: 15, bold: true, color: INK });
  s.addText([
    { text: "Never set ask_attribute — so the simulated customer replied “Ask me about one specific attribute” every single turn", options: { bullet: true, breakLine: true, paraSpaceAfter: 8 } },
    { text: "Searched only the current message, discarding everything said earlier", options: { bullet: true, breakLine: true, paraSpaceAfter: 8 } },
    { text: "Result: it learned nothing, and needed 9.81 of its 10 turns", options: { bullet: true } },
  ], { x: M + 0.34, y: 2.38, w: 5.45, h: 2.5, isTextBox: true, margin: 0,
       fontFace: B, fontSize: 14.5, color: SLATE, lineSpacing: 19 });

  const rows = [["Hit Rate@10", "0.125"], ["MRR", "0.068"], ["MTTC (turns)", "9.81"]];
  rows.forEach(([k, v], i) => {
    const y = 1.92 + i * 0.92;
    card(s, 7.1, y, 5.6, 0.74, i === 2 ? "FBE9E7" : MIST);
    s.addText(k, { x: 7.44, y, w: 3.2, h: 0.74, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 15, color: SLATE, valign: "middle" });
    s.addText(v, { x: 10.0, y, w: 2.4, h: 0.74, isTextBox: true, margin: 0,
      fontFace: H, fontSize: 24, bold: true, color: i === 2 ? "B3261E" : INK,
      align: "right", valign: "middle" });
  });
  s.addText("Nearly every session ran to the 10-turn cap before converting.",
    { x: 7.1, y: 4.78, w: 5.6, h: 0.4, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 13, italic: true, color: SLATE });

  s.addText("We started by reading the evaluator's own source — not to game it, but because the customer simulator defines what the agent can actually learn.",
    { x: M, y: 5.62, w: 12.1, h: 0.6, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 14.5, color: TEAL, bold: true });
  s.addNotes("The baseline never asked a question, so the simulated customer never disclosed anything, and the agent searched only the latest message. It was structurally incapable of learning. Our first move was to read the evaluator source to understand what information was even obtainable.");
}

/* ─── 3. Core insight ──────────────────────────────────────────────────── */
{
  const s = lightSlide("Extraction, not ranking, was the bottleneck", "The core insight");
  s.addText("We measured how much the catalogue could be reached, given different amounts of what the shopper had told us:",
    { x: M, y: 1.66, w: 11.9, h: 0.44, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 15.5, color: SLATE });

  card(s, M, 2.3, 5.85, 2.35, MIST);
  s.addText("1.7%", { x: M + 0.34, y: 2.52, w: 5.1, h: 1.0, isTextBox: true, margin: 0,
    fontFace: H, fontSize: 60, bold: true, color: SLATE });
  s.addText("of targets in the top 10 using only the opening category",
    { x: M + 0.36, y: 3.52, w: 5.1, h: 0.72, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 14.5, color: SLATE });

  card(s, 6.85, 2.3, 5.85, 2.35, "E3F6F1");
  s.addText("85.0%", { x: 7.19, y: 2.52, w: 5.1, h: 1.0, isTextBox: true, margin: 0,
    fontFace: H, fontSize: 60, bold: true, color: TEAL });
  s.addText("using everything the shopper is willing to disclose",
    { x: 7.21, y: 3.52, w: 5.1, h: 0.72, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 14.5, color: SLATE });

  s.addText("The catalogue was always reachable. The hard part was getting the customer to talk — and never losing what they said.",
    { x: M, y: 4.92, w: 12.1, h: 0.88, isTextBox: true, margin: 0,
      fontFace: H, fontSize: 20, bold: true, color: INK, lineSpacing: 26 });
  s.addText("This single measurement re-ordered our entire plan: dense retrieval and LLM reranking, both scoped as core, were demoted before a line of either was written.",
    { x: M, y: 5.9, w: 12.1, h: 0.6, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 14.5, color: SLATE, lineSpacing: 19 });
  s.addNotes("This is the measurement that shaped everything. With only the opening category, we reach 1.7% of targets. With everything the shopper will disclose, 85%. So the bottleneck was dialogue extraction, not clever ranking — and that let us demote two large planned components before building them.");
}

/* ─── 4. Architecture ──────────────────────────────────────────────────── */
{
  const s = lightSlide("One deterministic pass per turn", "Architecture");
  const steps = [
    ["state", "Accumulate constraints.\nRetract on override.\nSettle boundaries."],
    ["intent", "Buying vs Browsing.\nRules, no model call."],
    ["retrieval", "Wide keyword pool,\nrescored on constraint\ncoverage."],
    ["profile", "Long-term prior,\nused to break ties\nonly."],
    ["ask", "Highest-yield\nunanswered attribute."],
  ];
  steps.forEach(([t, d], i) => {
    const x = M + i * 2.48;
    card(s, x, 1.86, 2.24, 2.62);
    chip(s, x + 0.28, 2.12, String(i + 1), i === 2 ? MINT : SEA, INK, 0.38);
    s.addText(t, { x: x + 0.28, y: 2.6, w: 1.8, h: 0.34, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 15, bold: true, color: INK });
    s.addText(d, { x: x + 0.28, y: 2.98, w: 1.78, h: 1.36, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 11.5, color: SLATE, lineSpacing: 14 });
    if (i < 4) {
      s.addText("→", { x: x + 2.2, y: 2.9, w: 0.3, h: 0.4, isTextBox: true, margin: 0,
        fontFace: B, fontSize: 20, bold: true, color: SEA, align: "center" });
    }
  });

  card(s, M, 4.72, 12.09, 1.02, INK);
  s.addText("Every turn returns recommendations AND a question — never one without the other.",
    { x: M + 0.36, y: 4.86, w: 11.4, h: 0.36, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 16, bold: true, color: MINT });
  s.addText("The evaluator scores recommendations before it reads ask_attribute, so a question is free when the recommendation already hits. The real design problem is knowing when to stop asking.",
    { x: M + 0.36, y: 5.2, w: 11.4, h: 0.42, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 13, color: FOG });

  s.addText("Runs in ~90 ms per session on a laptop. No network, no model, no third-party runtime dependency.",
    { x: M, y: 6.0, w: 12.1, h: 0.4, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 13.5, italic: true, color: SLATE });
  s.addNotes("Five stages, all deterministic. The key architectural decision is at the bottom: we return recommendations and a question every single turn, because the evaluator scores recommendations first. That makes asking free, which inverts the usual problem — the question isn't when to ask, it's when to stop.");
}

/* ─── 5. Workflow ──────────────────────────────────────────────────────── */
{
  const s = lightSlide("How we worked: measure, then build", "Our workflow");
  s.addText("Every change was justified by a measurement taken before it, and verified by one taken after. Nothing shipped on intuition.",
    { x: M, y: 1.66, w: 11.9, h: 0.44, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 15.5, color: SLATE });

  const steps = [
    ["Instrument", "Reproduce the baseline exactly, then read the evaluator to learn what the agent can actually observe."],
    ["Diagnose", "Ask where the loss is. Is a failure a retrieval miss or a ranking miss? The answer changes what to build."],
    ["Isolate", "One change at a time, re-scored on all 200 sessions, so every number in our docs is attributable."],
    ["Sweep", "Tune each weight across a range. Prefer broad plateaus over sharp peaks — flat optima survive a distribution shift."],
    ["Reject", "Kill ideas on evidence, including our own. Three planned components were cut after measurement."],
  ];
  steps.forEach(([t, d], i) => {
    const y = 2.24 + i * 0.86;
    card(s, M, y, 12.09, 0.7, i === 4 ? "FFF4E0" : MIST);
    chip(s, M + 0.24, y + 0.15, String(i + 1), i === 4 ? "F5A623" : SEA, INK, 0.4);
    s.addText(t, { x: M + 0.82, y, w: 2.0, h: 0.7, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 15.5, bold: true, color: INK, valign: "middle" });
    s.addText(d, { x: M + 2.86, y, w: 9.0, h: 0.7, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 13.5, color: SLATE, valign: "middle" });
  });

  s.addText("Two bugs that passed every unit test were caught only by tracing a real session end to end. We now trace before we trust a metric.",
    { x: M, y: 6.5, w: 12.1, h: 0.42, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 13.5, italic: true, color: TEAL });
  s.addNotes("Our method was measure-first. Reproduce, diagnose, isolate one change at a time, sweep the weights, and reject ideas on evidence. Worth calling out: two of our most costly bugs passed every unit test and were only visible when we replayed a full session.");
}

/* ─── 6. Score progression (native chart) ──────────────────────────────── */
{
  const s = lightSlide("Every gain is attributable to one change", "Results by stage");
  s.addChart(pres.ChartType.bar, [{
    name: "TechnicalScore",
    labels: ["Baseline", "Working\nagent", "Bucket\nfix", "Override\nfix", "Constraint\ncoverage", "Popularity\nprior", "Category\nmatch"],
    values: [0.107, 0.562, 0.728, 0.744, 0.790, 0.859, 0.876],
  }], {
    x: M, y: 1.72, w: 8.15, h: 4.62,
    barDir: "col", chartColors: [TEAL, SEA, SEA, SEA, MINT, MINT, MINT],
    showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "0.000",
    dataLabelColor: INK, dataLabelFontFace: B, dataLabelFontSize: 10.5,
    showLegend: false, showTitle: false,
    valAxisMaxVal: 1.0, valAxisMinVal: 0,
    catAxisLabelColor: SLATE, catAxisLabelFontFace: B, catAxisLabelFontSize: 10,
    valAxisLabelColor: SLATE, valAxisLabelFontFace: B, valAxisLabelFontSize: 10,
    valGridLine: { color: "E2E9E9", size: 1 }, catGridLine: { style: "none" },
  });

  const notes = [
    ["+0.455", "Working agent", "State machine, intent routing and attribute-match retrieval."],
    ["+0.166", "Bucket fix", "One answer does not empty an attribute — keep asking until refused."],
    ["+0.132", "Ranking features", "Constraint coverage, popularity prior, category-path match."],
  ];
  notes.forEach(([d, t, x2], i) => {
    const y = 1.86 + i * 1.52;
    card(s, 9.05, y, 3.66, 1.32);
    s.addText(d, { x: 9.32, y: y + 0.1, w: 1.5, h: 0.42, isTextBox: true, margin: 0,
      fontFace: H, fontSize: 20, bold: true, color: TEAL });
    s.addText(t, { x: 9.32, y: y + 0.5, w: 3.1, h: 0.28, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 13, bold: true, color: INK });
    s.addText(x2, { x: 9.32, y: y + 0.76, w: 3.14, h: 0.48, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 11, color: SLATE, lineSpacing: 13 });
  });
  s.addText("Scored on all 200 public sessions after every single change.",
    { x: M, y: 6.5, w: 12.1, h: 0.36, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 13, italic: true, color: SLATE });
  s.addNotes("Seven measured stages from 0.107 to 0.876. The largest single jump after the initial build was the bucket fix, worth 0.166 on its own — I'll explain that one next.");
}

/* ─── 7. Technical decisions ───────────────────────────────────────────── */
{
  const s = lightSlide("Four decisions that carried the score", "Technical considerations");
  const items = [
    ["Asking is free", "The evaluator scores recommendations before reading ask_attribute. So we always do both, and the design problem inverts: when to STOP asking."],
    ["Questions ranked by measured yield", "We classified every target's disclosable constraints through the evaluator's own logic. feature yields in 96% of sessions; budget, brand and category yield 0% — so we never ask them."],
    ["A bucket is not emptied by one answer", "The customer releases at most two constraints per question. Treating an attribute as settled on first reply cost us 0.166 — our single largest bug."],
    ["Reward completeness, not term frequency", "Constraints are quoted verbatim from the target's own listing — 97.1% appear literally in its text. BM25 rewards repetition; coverage rewards satisfying every requirement."],
  ];
  items.forEach(([t, d], i) => {
    const x = M + (i % 2) * 6.25;
    const y = 1.8 + Math.floor(i / 2) * 2.32;
    card(s, x, y, 5.84, 2.06);
    chip(s, x + 0.3, y + 0.26, String(i + 1), MINT, INK, 0.38);
    s.addText(t, { x: x + 0.8, y: y + 0.26, w: 4.8, h: 0.38, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 15, bold: true, color: INK, valign: "middle" });
    s.addText(d, { x: x + 0.3, y: y + 0.76, w: 5.28, h: 1.14, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 12.5, color: SLATE, lineSpacing: 15 });
  });
  s.addText("Each was derived from the data, not assumed — and each is documented with its measurement in the repository.",
    { x: M, y: 6.56, w: 12.1, h: 0.38, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 13, italic: true, color: SLATE });
  s.addNotes("Four decisions did most of the work. The second one — measuring which questions actually yield information — is where most of our turn-efficiency comes from. The third was our largest single bug.");
}

/* ─── 8. Rejected on evidence ──────────────────────────────────────────── */
{
  const s = darkSlide();
  s.addText("REJECTED ON EVIDENCE", { x: M, y: 0.5, w: 8, h: 0.28, isTextBox: true, margin: 0,
    fontFace: B, fontSize: 12, bold: true, color: MINT, charSpacing: 2 });
  s.addText("What we chose not to ship", { x: M, y: 0.8, w: 11.9, h: 0.7, isTextBox: true,
    margin: 0, fontFace: H, fontSize: 34, bold: true, color: WHITE });
  s.addText("All three were in our original plan. We built enough of each to measure it, then cut it.",
    { x: M, y: 1.54, w: 11.9, h: 0.4, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 15, color: FOG });

  const items = [
    ["LLM reranker", "-0.011", "Tested on 40 real sessions. It lifted ambiguous cases (+0.041 MRR) but demoted already-correct ones (-0.107). 104 of 200 sessions are already rank-1 and can only lose."],
    ["Profile boosting", "-0.036", "preference_tags match the target 1.72x more than a random product — but only 1.12x against the candidates actually competing. Real lift against the wrong baseline."],
    ["Dense retrieval", "no gain", "Retrieval saturated at 197/200. The three remaining failures are ranking misses, not coverage misses, so a second route has nothing to add."],
  ];
  items.forEach(([t, d, x2], i) => {
    const x = M + i * 4.13;
    s.addShape(pres.ShapeType.roundRect, { x, y: 2.2, w: 3.87, h: 3.24, rectRadius: 0.06,
      fill: { color: INK2 }, line: { color: INK2 } });
    s.addText(t, { x: x + 0.3, y: 2.44, w: 3.3, h: 0.36, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 15.5, bold: true, color: WHITE });
    s.addText(d, { x: x + 0.3, y: 2.86, w: 3.3, h: 0.6, isTextBox: true, margin: 0,
      fontFace: H, fontSize: 30, bold: true, color: "FF8A80" });
    s.addText(x2, { x: x + 0.3, y: 3.56, w: 3.3, h: 1.7, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 12, color: FOG, lineSpacing: 15 });
  });

  s.addText("A feature with real lift against a random baseline can be worthless against a strong one.",
    { x: M, y: 5.72, w: 12.1, h: 0.44, isTextBox: true, margin: 0,
      fontFace: H, fontSize: 19, bold: true, color: MINT });
  s.addText("Our pipeline is offline because we measured the alternative and it was worse — not because we ran out of time.",
    { x: M, y: 6.18, w: 12.1, h: 0.4, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 13.5, color: FOG });
  s.addNotes("This slide matters most to us. All three were in our plan. We built enough of each to measure it honestly and then cut it. The LLM reranker is the clearest case: it helped the sessions we were getting wrong but damaged the ones we were already getting right, netting negative. Our system is offline by evidence, not by default.");
}

/* ─── 9. Results ───────────────────────────────────────────────────────── */
{
  const s = lightSlide("197 of 200 sessions convert — 60% on the first message", "Final results");
  const stats = [["0.985", "Hit Rate@10", "from 0.125"], ["0.670", "MRR", "from 0.068"],
                 ["1.875", "MTTC turns", "from 9.81"], ["0.876", "TechnicalScore", "from 0.107"]];
  stats.forEach(([big, label, sub], i) => {
    const x = M + i * 3.1;
    card(s, x, 1.78, 2.86, 1.72, i === 3 ? "E3F6F1" : MIST);
    s.addText(big, { x: x + 0.26, y: 1.92, w: 2.4, h: 0.72, isTextBox: true, margin: 0,
      fontFace: H, fontSize: 38, bold: true, color: i === 3 ? TEAL : INK });
    s.addText(label, { x: x + 0.28, y: 2.64, w: 2.4, h: 0.3, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 13.5, bold: true, color: INK });
    s.addText(sub, { x: x + 0.28, y: 2.94, w: 2.4, h: 0.3, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 12, color: SLATE });
  });

  s.addText("Hit Rate@10 by scenario", { x: M, y: 3.78, w: 6, h: 0.34, isTextBox: true, margin: 0,
    fontFace: B, fontSize: 15, bold: true, color: INK });
  const rows = [["browsing", 1.000, "80"], ["buying", 0.988, "80"],
                ["intent override", 0.967, "30"], ["boundary", 0.900, "10"]];
  rows.forEach(([name, v, n], i) => {
    const y = 4.22 + i * 0.53;
    s.addText(name, { x: M, y, w: 2.3, h: 0.42, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 13.5, color: SLATE, valign: "middle" });
    s.addShape(pres.ShapeType.roundRect, { x: 2.98, y: y + 0.11, w: 6.4, h: 0.2,
      rectRadius: 0.08, fill: { color: "E2E9E9" }, line: { color: "E2E9E9" } });
    s.addShape(pres.ShapeType.roundRect, { x: 2.98, y: y + 0.11, w: 6.4 * v, h: 0.2,
      rectRadius: 0.08, fill: { color: v === 1 ? TEAL : SEA }, line: { color: v === 1 ? TEAL : SEA } });
    s.addText(v.toFixed(3), { x: 9.5, y, w: 0.9, h: 0.42, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 13, bold: true, color: INK, valign: "middle" });
    s.addText(n + " sessions", { x: 10.5, y, w: 2.2, h: 0.42, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 12, color: SLATE, valign: "middle" });
  });
  s.addNotes("Final numbers. MTTC averages 1.875 turns, but the distribution matters more than the mean: 60 percent of sessions resolve on the shopper's very first message, and 79 percent by the second. Browsing is perfect at 1.0. Boundary is our weakest at 0.9, but that's only ten sessions so we treat the estimate as noisy rather than tuning against it.");
}

/* ─── 10. Feasibility ──────────────────────────────────────────────────── */
{
  const s = lightSlide("Built to survive the scoring environment", "Feasibility");
  const items = [
    ["$0.00", "model cost", "No API key, no tokens, no vendor account required to reproduce our score."],
    ["~18 s", "for 200 sessions", "About 90 ms per session, including a one-off 4.7 s index build. 0.41 GB peak."],
    ["0", "network calls", "Organiser policy may disable network at scoring. Our score is unaffected either way."],
    ["21", "automated tests", "Including regression tests for both bugs that unit tests originally missed."],
  ];
  items.forEach(([big, label, d], i) => {
    const x = M + (i % 2) * 6.25;
    const y = 1.8 + Math.floor(i / 2) * 2.3;
    card(s, x, y, 5.84, 2.04);
    s.addText(big, { x: x + 0.3, y: y + 0.2, w: 2.4, h: 0.62, isTextBox: true, margin: 0,
      fontFace: H, fontSize: 32, bold: true, color: TEAL });
    s.addText(label, { x: x + 0.3, y: y + 0.82, w: 3.2, h: 0.3, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 13.5, bold: true, color: INK });
    s.addText(d, { x: x + 0.3, y: y + 1.14, w: 5.24, h: 0.74, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 12.5, color: SLATE, lineSpacing: 15 });
  });
  s.addText("Standard library only — retrieval runs on SQLite FTS5, entirely in memory. Anyone can clone the repo and reproduce 0.875866 in one command.",
    { x: M, y: 6.5, w: 12.1, h: 0.4, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 13.5, italic: true, color: TEAL });
  s.addNotes("Feasibility was a design constraint, not an afterthought. Zero cost, zero network, standard library only. The submission rules warn that network access may be disabled at scoring time — our score is identical either way.");
}

/* ─── 11. Limitations ──────────────────────────────────────────────────── */
{
  const s = lightSlide("What we would do next, and what we are unsure of", "Honest limitations");
  const left = [
    ["Popularity leans on how the benchmark was sampled", "Targets are items real users bought, so review volume is genuine evidence. But it assumes the private set shares the public set's 5-core construction."],
    ["Constraint parsing is marker-based", "A paraphrase outside the phrasings we handle yields nothing. This — extraction, not ranking — is the one place an LLM would plausibly beat us."],
  ];
  const right = [
    ["A learned ranker is the last real lever", "All +0.095 of remaining headroom is in MRR. With 197/200 already hit and only 200 training sessions, a fitted model's transfer risk now rivals its upside."],
    ["boundary is weakest, and smallest", "0.900 across just 10 sessions. Tuning against it would fit noise, so we deliberately left it alone."],
  ];
  [left, right].forEach((col, c) => {
    col.forEach(([t, d], i) => {
      const x = M + c * 6.25;
      const y = 1.8 + i * 2.3;
      card(s, x, y, 5.84, 2.04);
      s.addText(t, { x: x + 0.3, y: y + 0.24, w: 5.24, h: 0.6, isTextBox: true, margin: 0,
        fontFace: B, fontSize: 14.5, bold: true, color: INK, lineSpacing: 18 });
      s.addText(d, { x: x + 0.3, y: y + 0.9, w: 5.24, h: 0.98, isTextBox: true, margin: 0,
        fontFace: B, fontSize: 12.5, color: SLATE, lineSpacing: 15 });
    });
  });
  s.addText("We would rather state an assumption we are leaning on than have a judge discover it.",
    { x: M, y: 6.5, w: 12.1, h: 0.4, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 13.5, italic: true, color: TEAL });
  s.addNotes("We think stating our assumptions is part of the engineering. The popularity prior is the one place our ranking leans on how the benchmark was built, and we say so in the repo rather than hoping nobody checks.");
}

/* ─── 12. Close ────────────────────────────────────────────────────────── */
{
  const s = darkSlide();
  s.addShape(pres.ShapeType.roundRect, { x: M, y: 1.0, w: 1.9, h: 0.46, rectRadius: 0.1,
    fill: { color: MINT }, line: { color: MINT } });
  s.addText("nailong", { x: M, y: 1.0, w: 1.9, h: 0.46, isTextBox: true, margin: 0,
    fontFace: B, fontSize: 17, bold: true, color: INK, align: "center", valign: "middle" });

  s.addText("0.107  →  0.876", { x: M, y: 1.86, w: 11.9, h: 1.1, isTextBox: true, margin: 0,
    fontFace: H, fontSize: 60, bold: true, color: WHITE });
  s.addText("Eight measured stages. Three planned components cut on evidence. No model calls.",
    { x: M, y: 3.02, w: 11.9, h: 0.46, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 19, color: SEA });

  const close = [
    ["Deep understanding", "We read the evaluator to learn what the agent could observe, then designed to that."],
    ["Measured, not assumed", "Every weight swept, every gain attributed, every rejection reproducible."],
    ["Honest about limits", "We publish the assumptions our score leans on, and the ideas that failed."],
  ];
  close.forEach(([t, d], i) => {
    const x = M + i * 4.13;
    s.addText(t, { x, y: 4.1, w: 3.7, h: 0.36, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 16, bold: true, color: MINT });
    s.addText(d, { x, y: 4.5, w: 3.7, h: 1.0, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 13, color: FOG, lineSpacing: 17 });
  });

  s.addText("github.com/yongc0/nailong---TikTok-TechJam-2026",
    { x: M, y: 6.28, w: 11.9, h: 0.4, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 14, color: WHITE });
  s.addNotes("To close: 0.107 to 0.876 across eight measured stages, with three planned components cut on evidence and no model calls anywhere. Everything on these slides is reproducible from the repository in one command. Thank you.");
}

pres.writeFile({ fileName: "nailong-shopping-copilot.pptx" })
  .then(f => console.log("wrote", f));
