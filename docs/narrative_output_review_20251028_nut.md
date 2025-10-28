# Narrative output QA — 28 Oct 2025 (profile: Nut)

## Rating
- **Score:** 8/10 (two correctness defects keep this from a perfect mark)

## Findings
1. **Transit references mirror the feed correctly.** The copy echoes the Sun–Pluto (0.39° applying), Mercury–Saturn (1.73° applying), Mercury–Sun (1.90° applying), Mercury–Ascendant (0.87° separating), Mercury–Chiron (1.00° separating), Venus–Mars (1.55° separating), and Venus–Uranus (1.03° applying) entries with the right signs and aspect directions.
2. **"Applying/separating exact" is self-contradictory.** "Exact" appears alongside non-zero orbs (e.g., "applying exact conjunction at 1.90°" or "separating exact conjunction at 1.55°"), overstating precision versus the metadata, which only calls them applying/separating.
3. **Keyword stems surface verbatim in bullets.** Lines such as "Focus on harmonizing openings innovation" or "Choose radiant drive personal power" are stitched together from taxonomy stems, not fully inflected language, so the guidance reads unedited and unclear.

## Corrections required for 10/10 accuracy & polish
- **Strip misleading "exact" modifiers.** Remove "exact" (and similar intensifiers) whenever the orb is not effectively zero; instead, mirror the event `note` phrasing such as "separating conjunction at 1.55° orb" or "applying conjunction at 1.90° orb." This keeps the copy aligned with the transit metadata.
- **Regenerate bullet and list language with production templates.** Run every bullet and checklist item (career, health, finance, do/avoid lists, remedies) through the inflection layer that restores natural syntax (e.g., "Focus on innovative, supportive openings" / "Choose grounded personal power to steady your finances"). This eliminates the raw stem collisions now present in the output.
- **QA check for similar hybrids across sections.** After the formatter fix, sweep the narrative for other templated hybrids—"pressing square," "opens your Uranus," "curious inner conversations," "radiant drive personal power," etc.—and confirm each matches a supported phrase or re-inflect as needed. Cover every section that draws from the same stem library so no lingering hybrids slip through.
