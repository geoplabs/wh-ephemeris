# Yearly PDF Layout & Structure Improvements

## Implementation Plan

### A. Global Layout & Structure

#### 1. Enhanced Cover Page ✓ (Ready to implement)
**Current Issues:**
- Too bare & generic
- No name, sign, or natal chart details
- Duplicate "2025 Yearly Forecast" lines

**Improvements:**
```
Title: 2025 Personalized Yearly Forecast
Subtitle: Prepared for [Name] ([Sun Sign]) • WhatHoroscope.com
Details: Based on natal chart: [Date] • [Time] • [Place]
NO page number on cover
Add WhatHoroscope logo/branding
Use brand crimson colors
```

**Implementation:**
- Update `_render_cover_page()` function
- Extract birth details from `meta['birth_info']` or chart_input
- Add sun sign calculation/display
- Remove page number from cover page

---

#### 2. Headers & Footers ✓ (Ready to implement)
**Current Issues:**
- No headers or footers
- No page numbers
- No brand identity on inner pages

**Improvements:**
```
Header: [Current Section Name] (left-aligned, small, gray)
Footer (left): WhatHoroscope.com
Footer (center): 2025 Yearly Forecast for [Name]
Footer (right): Page X of Y
```

**Implementation:**
- Add `_render_header()` function
- Add `_render_footer()` function
- Track current section name in `PAGE_TRACKER['current_section']`
- Calculate total pages (may require two-pass rendering)
- Apply to all pages except cover

---

#### 3. Table of Contents ✓ (Ready to implement)
**Current Issues:**
- Missing completely
- Hard to navigate long report

**Improvements:**
```
TABLE OF CONTENTS
- Year at a Glance ............................ 3
- Top Events .................................. 5
- Eclipses & Lunations ........................ 7
- January 2025 ................................ 9
- February 2025 ............................... 15
- ... (all months)
- Appendices .................................. 145
  - Glossary .................................. 145
  - Interpretation Index ...................... 147
```

**Implementation:**
- Add `_render_table_of_contents()` function
- Track TOC entries in `PAGE_TRACKER['toc_entries']` as [(title, page_number), ...]
- Add entries via `_add_toc_entry(title, page_number)`
- Render after cover page (page 2)
- Make entries clickable with PDF bookmarks

---

#### 4. Section Hierarchy & Visual Styles ✓ (Ready to implement)
**Current Issues:**
- All text looks similar
- ### style headings not visually strong enough
- No consistent spacing

**Improvements:**
```python
H1 (Section): 
  - Font: Helvetica-Bold, 22pt
  - Color: Crimson
  - Space before: 1.5cm, after: 1.0cm
  - Full-width crimson background bar
  - Examples: "Year at a Glance", "January 2025"

H2 (Subsection):
  - Font: Helvetica-Bold, 16pt  
  - Color: Crimson
  - Space before: 1.2cm, after: 0.6cm
  - Examples: "Top Events", "Career & Finance"

H3 (Inner heading):
  - Font: Helvetica-Bold, 13pt
  - Color: Crimson
  - Space before: 0.8cm, after: 0.4cm
  - Examples: "High Energy Days", "Navigate With Care"

Body text:
  - Font: Helvetica, 10pt
  - Leading: 14pt
  - Color: Dark gray

Bullets:
  - Crimson colored bullets
  - 0.3cm indent

Callout boxes:
  - Light crimson background (#fef2f2)
  - Crimson border
  - Used for action plans, warnings
```

**Implementation:**
- Define STYLES dictionary with all typography settings
- Create helper functions:
  - `_draw_h1(c, x, y, text)` -> returns new y position
  - `_draw_h2(c, x, y, text)` -> returns new y position  
  - `_draw_h3(c, x, y, text)` -> returns new y position
  - `_draw_body(c, x, y, text, width)` -> returns new y position
  - `_draw_bullet_list(c, x, y, items, width)` -> returns new y position
- Update all rendering functions to use these helpers
- Ensure consistent spacing before/after all elements

---

### B. Content Improvements (Future Phase)

#### 5. Better Event Formatting
- Use tables for aspect grids
- Visual timeline for eclipses
- Icons for planet symbols

#### 6. Enhanced Monthly Sections  
- Month overview box at top
- Visual separators between subsections
- Key dates calendar view

#### 7. Appendix Improvements
- Multi-column glossary
- Categorized interpretation index
- Quick reference charts

---

## Implementation Order

1. **Phase 1 (Current):** Layout & Structure (Points 1-4)
   - Enhanced cover page
   - Headers & footers
   - Table of contents
   - Section hierarchy

2. **Phase 2 (Future):** Content Polish (Points 5-7)
   - Better formatting
   - Visual enhancements
   - Reference materials

---

## Testing Checklist

After implementation:
- [ ] Cover page shows all required info (name, sign, birth details)
- [ ] Cover page has no page number
- [ ] All other pages have header with section name
- [ ] All other pages have footer with WhatHoroscope.com • Name • Page X of Y
- [ ] TOC is present on page 2
- [ ] TOC entries match actual page numbers
- [ ] Section headers (H1) are visually prominent with crimson background
- [ ] Subsection headers (H2) are clearly differentiated
- [ ] Inner headings (H3) maintain hierarchy
- [ ] Body text is readable with proper line spacing
- [ ] Consistent margins throughout (2cm all sides)
- [ ] No orphaned headings (heading at bottom of page with no content)
- [ ] PDF metadata is set correctly (title, author, subject)

---

## Files to Modify

- `api/services/yearly_pdf_enhanced.py` (main implementation)
- Test files to verify output

## Estimated Implementation Time

- Enhanced cover page: 30 minutes
- Headers & footers: 45 minutes  
- Table of contents: 1 hour
- Section hierarchy refactoring: 1.5 hours
- Testing & fixes: 1 hour

**Total: ~4-5 hours**

