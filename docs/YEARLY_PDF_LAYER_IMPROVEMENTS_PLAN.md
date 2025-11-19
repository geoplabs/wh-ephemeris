# Yearly PDF Layer & Text Generation Improvements

This document lists targeted upgrades for the yearly forecast pipeline so designers, engineers, and content editors share the same execution checklist. Improvements are grouped across layout, logic, UX, template, visual polish, and pipeline guardrails.

## A. Global Layout & Structure

1. **Cover Page Polish**
   - Title: `2025 Personalized Yearly Forecast`.
   - Subtitle: `Prepared for John (Taurus) • WhatHoroscope.com`.
   - Add natal-chart metadata: `Based on natal chart: 15 May 1990 • 14:30 • New Delhi (India)`.
   - Remove duplicate year labels and suppress page number on the cover.
   - Apply logo + brand colours, establish clear hierarchy (title, subtitle, metadata).

2. **Headers, Footers & Pagination**
   - Header carries current section label ("Year at a Glance", "January 2025 – Overview", etc.).
   - Footer format: `WhatHoroscope.com • 2025 Yearly Forecast for John • Page X of Y`.
   - Maintain consistent margins / safe zones for all pages.

3. **Table of Contents**
   - Auto-generate clickable entries for: Year at a Glance, Top Events, Eclipses & Lunations, monthly sections (Dec 2024 – Dec 2025), Appendices (Glossary, Interpretation Index, etc.).
   - Display page numbers with dotted leaders.

4. **Section Hierarchy**
   - Define styles for H1/H2/H3, body, bullets, and callouts.
   - Enforce consistent spacing before/after headings to keep structure obvious.

## B. Content Logic & Astrology Coherence

1. **Year Consistency**
   - Prevent 2024/2025 mix-ups; December 2024 copy should reflect "closing 2024" and "setting up 2025" while the remaining report focuses on 2025.
   - Add QA rules rejecting paragraphs that mention the wrong year.

2. **Transit-Specific Narratives**
   - Require every monthly overview to reference at least 2–3 concrete events from that month’s JSON payload (date, bodies, aspect, theme).
   - Include explicit transit references inside Career/Health/Relationship subsections.

3. **Top Events Formatting**
   - Use `YYYY-MM-DD • Event • Theme (Score: X.XX)` plus 2–3 lines of guidance without truncation or raw markers.

4. **Eclipses & Lunations Coverage**
   - Build a table/cards covering each eclipse/lunation with date, sign, house/life area, and 3–4 lines of Do/Don’t guidance.

5. **High Energy vs Navigate With Care**
   - Convert raw bullets into styled callout boxes.
   - Limit to top 3–5 dates, each with a short label and one-line guidance.

6. **Life-Area Mapping**
   - Tag key events with life areas (Career, Money, Home, Love, Health, Inner Growth, etc.).
   - Summarize monthly strengths/quiet zones for each area.

## C. Copywriting & UX

1. **Remove Chatty LLM Voice**
   - Strip fillers like “Absolutely!” and “Here are some…”. Start sections directly with useful insights.

2. **Reduce Repetition**
   - Introduce a single "How to use Health/Career sections" primer in front-matter. Subsequent months must tie advice to specific transits (e.g., Mars squares → burnout warnings).

3. **Action Plans with Dates**
   - Cap each action plan at 5–7 bullets; format `DD Mon – Action item (linked to transit)`.
   - Ensure complete sentences with < ~120 characters to avoid wrapping issues.

4. **Personalization Hooks**
   - Sprinkle references to the person’s natal placements (e.g., Taurus Sun, Virgo rising, Capricorn Moon) while keeping 90% of logic deterministic from JSON.

## D. Monthly Layout Template

1. **Readable Month Titles**
   - Title: `January 2025 – Month Overview`; subtitle line lists top themes ("Career • Relationships • Emotional Growth").

2. **Fixed Section Order**
   - Overview & Big Themes → High-Score Days → Career & Finance → Relationships & Family → Health & Energy → Action Plan → High Energy / Navigate With Care boxes.

3. **Key Dates Table**
   - Add `Date | Transit | Theme | Score | Guidance` table per month using sorted events above a score threshold.

4. **Monthly Heatbar**
   - Provide week-by-week 0–5 intensity dots/flames derived from average scores to visualize quiet vs busy weeks.

5. **Key Insight Callout**
   - Highlight one quote per month (e.g., “Late March is a powerful reset point for your career…”).

## E. Visual & Technical Polish

1. **Typography & Spacing**
   - Limit to two fonts (serif for headings, sans-serif for body). Increase line spacing for readability and add white space between sections.

2. **Highlighting & Callouts**
   - Use bordered quotes/callouts for insights, boxes for High Energy / Navigate With Care, and consistent iconography.

3. **Metadata & Accessibility**
   - Set PDF metadata (title, author, subject, keywords) and tag headings for screen-reader navigation if supported.

4. **Glossary & Interpretation Index**
   - Append concise definitions of aspects, houses, planets, plus a 1-line “Transit X to Natal Y usually means…” reference table.

## F. Pipeline & QA Guardrails

1. **Separate Data vs Essay Pages**
   - Present Top Events / Key Dates / Appendices as tables or cards, while overviews and relationship/health sections remain prose referencing those tables.

2. **Automated QA Filters**
   - Remove duplicate phrases, detect wrong year/month mentions, limit generic phrase count, and ensure bullets don’t end with ellipses.

3. **Paragraph-to-Event Mapping**
   - Internally tag each paragraph with the event IDs it interprets to improve traceability and template debugging.

4. **Pre-Render Validation**
   - Ensure each paragraph references at least one event, monthly sections meet minimum transit references, and callouts respect length/style guides before passing content to the renderer.
