const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType,
  Table, TableRow, TableCell, WidthType, ShadingType, BorderStyle,
  LevelFormat, convertInchesToTwip,
} = require("docx");
const fs = require("fs");

const TEAL = "0F6E78";
const INK  = "12262B";
const GREY = "4A5A5F";
const MINT = "E6F4F1";
const SAND = "FFF6E5";

// ── helpers ────────────────────────────────────────────────────────────────
const p = (text, o = {}) => new Paragraph({
  spacing: { after: o.after ?? 140, line: 300 },
  alignment: o.align,
  children: [new TextRun({ text, size: o.size ?? 22, color: o.color ?? INK,
    bold: o.bold, italics: o.italics, font: "Calibri" })],
});

// A paragraph made of several differently-formatted pieces.
const rich = (runs, o = {}) => new Paragraph({
  spacing: { after: o.after ?? 140, line: 300 },
  children: runs.map(r => new TextRun({
    text: r.t, bold: r.b, italics: r.i, size: r.size ?? 22,
    color: r.c ?? INK, font: "Calibri",
  })),
});

const h1 = t => new Paragraph({
  heading: HeadingLevel.HEADING_1, spacing: { before: 380, after: 170 },
  children: [new TextRun({ text: t, size: 32, bold: true, color: TEAL, font: "Calibri" })],
});
const h2 = t => new Paragraph({
  heading: HeadingLevel.HEADING_2, spacing: { before: 260, after: 120 },
  children: [new TextRun({ text: t, size: 25, bold: true, color: INK, font: "Calibri" })],
});

const bullet = (text, o = {}) => new Paragraph({
  numbering: { reference: "bullets", level: 0 },
  spacing: { after: 90, line: 300 },
  children: [new TextRun({ text, size: 22, color: o.color ?? INK, font: "Calibri", bold: o.bold })],
});

// Shaded callout box for the ideas that matter most.
const callout = (title, body, fill = MINT) => new Table({
  width: { size: 9360, type: WidthType.DXA },
  columnWidths: [9360],
  borders: {
    top:    { style: BorderStyle.SINGLE, size: 1, color: fill },
    bottom: { style: BorderStyle.SINGLE, size: 1, color: fill },
    left:   { style: BorderStyle.SINGLE, size: 1, color: fill },
    right:  { style: BorderStyle.SINGLE, size: 1, color: fill },
    insideHorizontal: { style: BorderStyle.NONE, size: 0, color: fill },
    insideVertical:   { style: BorderStyle.NONE, size: 0, color: fill },
  },
  rows: [new TableRow({ cantSplit: true, children: [new TableCell({
    width: { size: 9360, type: WidthType.DXA },
    shading: { type: ShadingType.CLEAR, fill },
    margins: { top: 200, bottom: 200, left: 220, right: 220 },
    children: [
      new Paragraph({ spacing: { after: 90 }, children: [
        new TextRun({ text: title, bold: true, size: 23, color: TEAL, font: "Calibri" })] }),
      ...body.map(t => new Paragraph({ spacing: { after: 80, line: 300 }, children: [
        new TextRun({ text: t, size: 21, color: INK, font: "Calibri" })] })),
    ],
  })] })],
});

// Simple table with a header row.
const table = (headers, rows, widths) => new Table({
  width: { size: 9360, type: WidthType.DXA },
  columnWidths: widths,
  rows: [
    new TableRow({
      tableHeader: true,
      cantSplit: true,
      children: headers.map((htxt, i) => new TableCell({
        width: { size: widths[i], type: WidthType.DXA },
        shading: { type: ShadingType.CLEAR, fill: TEAL },
        margins: { top: 110, bottom: 110, left: 130, right: 130 },
        children: [new Paragraph({ children: [
          new TextRun({ text: htxt, bold: true, size: 21, color: "FFFFFF", font: "Calibri" })] })],
      })),
    }),
    ...rows.map((row, ri) => new TableRow({
      cantSplit: true,
      children: row.map((cell, i) => new TableCell({
        width: { size: widths[i], type: WidthType.DXA },
        shading: { type: ShadingType.CLEAR, fill: ri % 2 ? "F4F8F8" : "FFFFFF" },
        margins: { top: 100, bottom: 100, left: 130, right: 130 },
        children: [new Paragraph({ children: [
          new TextRun({ text: cell, size: 21, color: INK, font: "Calibri",
            bold: i === 0 || /^0\.8|^8\.2|^98|^60%/.test(cell) })] })],
      })),
    })),
  ],
});

const spacer = () => new Paragraph({ text: "", spacing: { after: 170 } });

// ── content ────────────────────────────────────────────────────────────────
const body = [];

// Cover
body.push(new Paragraph({ spacing: { before: 900, after: 90 }, children: [
  new TextRun({ text: "TEAM NAILONG", bold: true, size: 24, color: TEAL, font: "Calibri" })] }));
body.push(new Paragraph({ spacing: { after: 140 }, children: [
  new TextRun({ text: "Shopping Copilot", bold: true, size: 62, color: INK, font: "Calibri" })] }));
body.push(p("A plain-English explanation of what we built, why we built it that way, and what we found out along the way.",
  { size: 26, color: GREY, after: 340 }));
body.push(p("TikTok TechJam 2026 — Track 4: AI Conversational Search and Recommendations", { size: 21, color: GREY, after: 90 }));
body.push(p("Written for readers with no technical background. Every specialist term is explained the first time it appears.",
  { size: 21, color: GREY, italics: true, after: 500 }));

body.push(callout("The short version", [
  "We built a shopping assistant that chats with a customer and works out which product they want.",
  "The starter version we were given found the right product 12.5% of the time, and usually needed 10 messages to do it.",
  "Ours finds it 98.5% of the time, and 6 times out of 10 it gets there from the customer's very first message.",
  "On the competition's overall score, that is 0.107 out of 1 for the starter version, and 0.876 for ours — about 8 times better.",
]));

body.push(new Paragraph({ children: [], pageBreakBefore: true }));

// 1. The problem
body.push(h1("1. What we were asked to build"));
body.push(p("Imagine walking into a very large clothing shop — one with fifty thousand different items — and being met by a shop assistant. You say something vague like “I'm looking for shorts.” The assistant's job is to work out exactly which pair of shorts you have in mind, by asking you a few questions."));
body.push(p("That is the task. We had to build that assistant as a piece of software. The competition gives it a customer to talk to, and checks whether it can find the one product that customer actually wanted."));

body.push(h2("The rules"));
body.push(bullet("The assistant gets at most 10 messages per customer. Go over, and that customer counts as a total failure."));
body.push(bullet("Each time it replies, it can show a shortlist of up to 10 products, ask the customer one question, or do both."));
body.push(bullet("The product list is fixed and cannot be changed. Fifty thousand clothing, shoes and jewellery items from Amazon."));
body.push(bullet("Fewer messages is better. An assistant that interrogates you for ten minutes is a bad assistant, even if it eventually gets the right answer."));

body.push(h2("A few words we cannot avoid"));
body.push(p("These five terms appear throughout. Nothing else in this document assumes any technical knowledge."));
body.push(spacer());
body.push(table(
  ["Term", "What it actually means"],
  [
    ["Catalogue", "The fixed list of 50,000 products the assistant can choose from."],
    ["Session", "One complete conversation with one customer, from their first message until the product is found or the assistant runs out of messages."],
    ["Turn", "One exchange: the customer says something, the assistant replies. A session can have at most 10 turns."],
    ["The target", "The one product the customer actually wanted. The competition knows it in advance; the assistant has to find it."],
    ["The evaluator", "The competition's own program. It plays the part of the customer, then marks the assistant's performance. We could read it but not change it."],
  ],
  [1900, 7460],
));

body.push(new Paragraph({ children: [], pageBreakBefore: true }));
body.push(h2("How the assistant is scored"));
body.push(p("Three things are measured, then combined into one number between 0 and 1. Higher is better."));
body.push(spacer());
body.push(table(
  ["Measure", "The question it asks", "Weight"],
  [
    ["Hit Rate", "Did the right product appear in the shortlist of 10 at any point?", "50%"],
    ["MRR", "When it appeared, was it at the top of the list or buried near the bottom?", "30%"],
    ["Efficiency", "How many messages did it take? Fewer is better.", "20%"],
  ],
  [1500, 6360, 1500],
));
body.push(spacer());
body.push(p("MRR is the only piece of jargon here. It stands for Mean Reciprocal Rank, and it simply rewards putting the right answer first. If the correct product is 1st in the list you score 1; 2nd scores a half; 5th scores a fifth. Being right but ranking it 10th barely counts.",
  { color: GREY }));

// 2. The starter
body.push(h1("2. The version we started from, and why it barely worked"));
body.push(p("The competition provides a basic assistant to build on. It scored 0.107 out of 1. Before improving it, we wanted to understand precisely why it was so poor — and the reason turned out to be more interesting than “it isn't very clever.”"));
body.push(p("The starter assistant never asked the customer anything. It simply searched using whatever the customer had just said and showed its best guesses."));
body.push(p("That mattered enormously, because of how the competition's customer behaves. The customer only volunteers information when asked a direct question. If the assistant asks nothing, the customer replies, every single time:"));
body.push(p("“Those options are not quite right yet. Ask me about one specific attribute.”", { italics: true, color: TEAL, after: 140 }));
body.push(p("So the starter assistant was trapped. It never asked, so it never learned anything new, so its next guess was identical to its last one. It repeated the same failed guess ten times and ran out of messages. That is why it needed 9.81 messages on average — it was almost always running to the limit."));
body.push(spacer());
body.push(callout("Our first real decision", [
  "Before writing any code, we read the competition's own scoring program to understand what the customer would and would not tell us.",
  "This was not about finding loopholes. It was about answering a basic question: what information can this assistant actually obtain? You cannot design a good conversation without knowing what the other person is willing to say.",
], SAND));

body.push(new Paragraph({ children: [], pageBreakBefore: true }));

// 3. The discovery
body.push(h1("3. The discovery that redirected the whole project"));
body.push(p("Our original plan assumed the hard part would be choosing well — sorting through thousands of similar products to pick the right one. Most of our planned effort was aimed at that."));
body.push(p("Before building any of it, we ran a simple test. We asked: if the assistant knew nothing but the customer's opening line, how often could it find the right product? And if it knew everything the customer was willing to say, how often then?"));
body.push(spacer());
body.push(table(
  ["What the assistant knows", "How often it finds the right product"],
  [
    ["Only the customer's opening line", "1.7 out of every 100 conversations"],
    ["Everything the customer will disclose", "85 out of every 100 conversations"],
  ],
  [4680, 4680],
));
body.push(spacer());
body.push(p("The gap is enormous, and it pointed somewhere we were not looking. Finding the product was never really the difficulty — the information needed to find it was simply never being collected."));
body.push(p("Put in shop terms: the assistant did not need better judgement. It needed to ask better questions, and to remember the answers."));
body.push(spacer());
body.push(callout("Why this mattered so much", [
  "This single test changed our plan before we wrote a line of the work it made unnecessary.",
  "Two large components we had scheduled as essential — both aimed at choosing better — were demoted on the spot. We never built either, and our final system does not need them.",
  "Measuring first saved us roughly half the work we had planned.",
]));

body.push(new Paragraph({ children: [], pageBreakBefore: true }));

// 4. How it works
body.push(h1("4. How our shopping assistant works"));
body.push(p("Every time the customer says something, the assistant runs through the same five steps. There is no artificial intelligence model involved at any point — the whole thing is ordinary, predictable logic, which turns out to matter later."));

body.push(h2("Step 1 — Remember what has been said"));
body.push(p("The assistant keeps a running note of every requirement the customer has mentioned, across the whole conversation. This sounds obvious, but the starter version did not do it — it only ever looked at the most recent message and forgot the rest."));
body.push(p("It also handles two awkward situations. If the customer changes their mind (“actually, ignore what I said earlier”), the assistant drops that one retracted preference but keeps everything else they have said since. And if the customer says they have no opinion on something, it makes a note never to ask about that again."));

body.push(h2("Step 2 — Judge how decided the customer is"));
body.push(p("The assistant works out whether the customer sounds like they know exactly what they want (“I need black leather boots in a size 8”) or is still browsing (“I'm looking for shoes, but I'm still exploring”). This nudges how broadly it searches."));

body.push(h2("Step 3 — Search the catalogue"));
body.push(p("It searches all 50,000 products using everything the customer has said so far, then sorts the results. How that sorting works is where a lot of our improvement came from, and it is explained in section 5."));

body.push(h2("Step 4 — Consider what this customer usually likes"));
body.push(p("Each customer comes with a short summary of what they have cared about in past purchases — comfort, or durability, or style. The assistant uses this only to break ties between products it otherwise rates equally. Section 6 explains why we deliberately kept it that weak."));

body.push(h2("Step 5 — Ask the single most useful question"));
body.push(p("Finally, it picks one question to ask. Which question is far from arbitrary, and is covered in section 5."));

body.push(spacer());
body.push(callout("The one design choice that mattered most", [
  "Every time the assistant replies, it shows a shortlist AND asks a question. Never one without the other.",
  "We noticed the competition checks the shortlist before it processes the question. So if the shortlist is already correct, the conversation ends there and the question costs nothing at all.",
  "That means asking is free. Which turns the usual problem inside out: the difficult question is not when to ask, but when to stop asking.",
]));

body.push(new Paragraph({ children: [], pageBreakBefore: true }));

// 5. Improvements
body.push(h1("5. The improvements, one at a time"));
body.push(p("We changed one thing at a time and re-ran all 200 test conversations after each change, so we could tell exactly what every improvement was worth. Nothing was included on a hunch."));
body.push(spacer());
body.push(table(
  ["What we changed", "Score after", "Gained"],
  [
    ["The starter version we were given", "0.107", "—"],
    ["Built the assistant properly (steps 1–5 above)", "0.562", "+0.455"],
    ["Fixed the “one answer is enough” bug", "0.728", "+0.166"],
    ["Fixed how we handle a change of mind", "0.744", "+0.016"],
    ["Reward products that meet every requirement", "0.790", "+0.046"],
    ["Favour products people actually buy", "0.859", "+0.069"],
    ["Check the product's category properly", "0.876", "+0.017"],
  ],
  [5460, 1950, 1950],
));

body.push(h2("Asking the questions that actually get answers"));
body.push(p("The assistant can ask about ten things: category, material, colour, size, style, brand, budget, feature, use case, or “other”. We assumed all ten were worth asking. We checked, and they are not."));
body.push(p("We went through every test conversation and counted how often asking about each thing produced any new information at all:"));
body.push(spacer());
body.push(table(
  ["Asking about…", "How often the customer tells you something new"],
  [
    ["Features", "96 conversations out of 100"],
    ["Material", "76 out of 100"],
    ["Colour", "26 out of 100"],
    ["Style", "9 out of 100"],
    ["Size", "5 out of 100"],
    ["Budget, brand, or category", "Never. Not once."],
  ],
  [4680, 4680],
));
body.push(spacer());
body.push(p("Three of the ten questions are guaranteed to waste a message. The assistant now never asks them, and asks about features first. Because messages are limited and being counted, cutting three worthless questions was worth a great deal."));

body.push(h2("Our most expensive mistake"));
body.push(p("This one cost us more than any other single error, and it is worth explaining because the mistake was so reasonable."));
body.push(p("When the assistant asked about features and the customer answered, we recorded that features were now dealt with, and moved on to the next topic. That seems sensible. It was wrong."));
body.push(p("The customer only reveals up to two requirements per question, and holds the rest back. Asking once gets you a fraction of what they know. By treating one answer as the whole story, the assistant was walking away from information that was there for the asking."));
body.push(p("The fix was to keep asking about the same thing until the customer explicitly says they have nothing more to add. That one change took the score from 0.562 to 0.728 — the largest single improvement we made after the initial build.", { bold: true }));

body.push(h2("Rewarding products that meet every requirement"));
body.push(p("Ordinary search engines reward repetition: a product description that says “mesh” five times looks more relevant than one that says it once. That is the wrong instinct here."));
body.push(p("We noticed that when the customer describes what they want, they use wording taken from the product's own description — we measured that 97 times out of 100, their exact words appear in the target product's text. So the right product is the one that satisfies every requirement, not the one that repeats one requirement loudest."));
body.push(p("We changed the sorting to count how many of the customer's stated requirements each product genuinely meets. That was worth +0.046."));

body.push(p("An example from our own test conversations. A shopper wants pyjamas, and across the conversation mentions four things: polyester; 95% polyester and 5% spandex; imported; and a button closure.", { after: 100 }));
body.push(p("Before the change, the search favoured listings that talked most enthusiastically about pyjamas. Its top three were a bamboo pyjama set, a lace-hem set, and a tie-dye set. The correct product sat at position 23 — far outside the shortlist of ten, so that conversation was a guaranteed failure.", { after: 100 }));
body.push(p("Those three results are not silly. They are all genuinely pyjamas, and one of them even has a button closure. But not one of them meets all four requirements: the bamboo set is not polyester, the lace-hem set has no button closure. They won on enthusiasm rather than on fit.", { after: 100 }));
body.push(p("After the change, the ranking counts how many of the four requirements each product actually meets. The correct product — a satin striped pyjama set that meets all four — moves from 23rd place to 1st."));

body.push(h2("Checking the product's category properly"));
body.push(p("A product description mentions all sorts of things the product is not. A men's hoodie listing might mention women, or gifts, or matching items. Search the whole description and those passing mentions look like matches."));
body.push(p("So this check ignores the description entirely and looks only at the shop's own filing label for the product — its category, such as “Novelty, Women, Hoodies”."));
body.push(p("Again, a real example. A shopper asks for women's hoodies. Before this check, the top result was an ASPCA logo hoodie — a real hoodie, with a well-matching description, but filed under men's. The product the shopper actually wanted, filed under women's, was down at position 16. Adding the check moved it up to 8, and into the shortlist."));
body.push(p("We should be honest about the size of this one. Across all 200 test conversations it improved the result in 3, made it worse in none, and changed nothing in the other 197. It earns its place because it never does harm and occasionally rescues a conversation — not because it is a major contributor.", { color: GREY }));

body.push(h2("Favouring products people actually buy"));
body.push(p("Products with more customer reviews have, by definition, been bought more often. Since we are trying to guess what someone bought, popularity is genuine evidence. Adding it was worth +0.069, our largest single ranking gain."));
body.push(p("We should be straightforward about one thing here: this works partly because of how the competition selected its test cases. Every target is something a real customer really did buy. We have written this caveat into our project notes rather than leaving it unsaid.", { color: GREY }));

body.push(new Paragraph({ children: [], pageBreakBefore: true }));

// 6. Rejected
body.push(h1("6. Three things we built, measured, and threw away"));
body.push(p("All three were in our original plan. We built enough of each to test it honestly, found each made things worse or made no difference, and removed them. We think this is the most interesting part of the project."));

body.push(h2("An AI language model to re-order the shortlist"));
body.push(p("This was the obvious modern approach, and we expected it to help. We tested it on 40 real conversations."));
body.push(p("It did improve the conversations we were getting wrong. But it also disturbed conversations we were already getting right — and since we were already correct in more than half of them, there was far more to lose than to gain. Overall it made the score worse, by about 0.011."));
body.push(p("We also checked the best possible version, where the AI is only ever consulted on conversations we were failing. Even then the gain was too small to matter. So we did not ship it.", { bold: true }));

body.push(h2("Using the customer's past preferences to pick products"));
body.push(p("Each customer comes with tags describing what they usually value — comfort, fit, durability. Boosting products matching those tags seemed sensible, and at first the evidence supported it: such products were 1.7 times more likely to be the target than a product picked at random."));
body.push(p("But that was the wrong comparison. Our assistant is never choosing between a good product and a random one — it is choosing between products that already match what the customer asked for. Against those, the advantage shrank to almost nothing."));
body.push(spacer());
body.push(callout("The lesson we would highlight", [
  "A feature can look genuinely useful when measured against a weak comparison, and be worthless against a strong one.",
  "We now compare against the real alternatives, not a convenient baseline. This changed how we tested everything afterwards.",
], SAND));

body.push(h2("A second, different way of searching"));
body.push(p("We had planned a second search method to catch products the first one missed. By the time we came to build it, we checked whether it was needed — and found the assistant was already finding the right product in 197 of 200 conversations. The three failures were sorting problems, not searching problems. A second search method had nothing left to contribute."));

body.push(new Paragraph({ children: [], pageBreakBefore: true }));

// 7. Results
body.push(h1("7. Where we ended up"));
body.push(spacer());
body.push(table(
  ["Measure", "Starter version", "Ours", "In plain terms"],
  [
    ["Hit Rate", "0.125", "0.985", "Finds the right product in 98.5% of conversations, up from 12.5%"],
    ["MRR", "0.068", "0.669", "When found, it is usually at or near the top of the list"],
    ["Messages needed", "9.81", "1.875", "Under 2 messages on average, down from nearly 10"],
    ["Overall score", "0.107", "0.876", "About 8 times better"],
  ],
  [1750, 1500, 1200, 4910],
));
body.push(spacer());
body.push(p("Out of 200 test conversations, the assistant finds the right product in 197. In 120 of them — 6 out of every 10 — it gets there from the customer's very first message, without needing to ask anything at all."));

body.push(h2("It costs nothing to run"));
body.push(p("Our assistant uses no artificial intelligence service, needs no paid account, and never connects to the internet. It handles all 200 conversations in about 18 seconds on an ordinary laptop."));
body.push(p("This is not a limitation we settled for. The competition warns that internet access may be switched off when the final marking happens, so anything depending on an external service is a risk. We tested the AI-powered alternative, found it performed worse, and chose the simpler approach on the evidence.", { bold: true }));

body.push(h2("What we are less sure about"));
body.push(bullet("Our use of product popularity depends on the final test cases being chosen the same way as the practice ones. We expect they are, but we have not been able to confirm it."));
body.push(bullet("The assistant understands the customer's phrasing by recognising familiar patterns. A customer who phrases things very differently could confuse it. This is the one place we think an AI language model would genuinely help — understanding what was said, rather than choosing what to show."));
body.push(bullet("One of the four conversation types is handled slightly less well than the others, but there are only ten examples of it, so we may simply be seeing noise. We deliberately did not tune for it, because tuning against ten examples usually makes things worse, not better."));

body.push(callout("How we worked, in one sentence", [
  "Measure first, build second, and delete your own work when the measurement says it is not helping.",
  "Every number here came from the competition's own scoring program, run on all 200 practice conversations, and anyone can reproduce it.",
]));

// ── build ──────────────────────────────────────────────────────────────────
const doc = new Document({
  creator: "Team nailong",
  title: "Shopping Copilot — plain-English explainer",
  description: "TikTok TechJam 2026, Track 4",
  numbering: { config: [{
    reference: "bullets",
    levels: [{
      level: 0, format: LevelFormat.BULLET, text: "•",
      alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: convertInchesToTwip(0.32), hanging: convertInchesToTwip(0.2) } } },
    }],
  }] },
  sections: [{
    properties: { page: { margin: { top: 1080, right: 1080, bottom: 1080, left: 1080 } } },
    children: body,
  }],
});

Packer.toBuffer(doc).then(b => {
  fs.writeFileSync("Shopping-Copilot-Explained.docx", b);
  console.log("wrote Shopping-Copilot-Explained.docx");
});
