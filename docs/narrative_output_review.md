# Narrative output QA — 30 Oct 2025 sample

## Rating
- **Score:** 7/10

## Findings
1. **Bullet phrasing drifted into clipped fragments.** Career/finance bullets shortened core nouns (e.g., “Focus on sensitive to keep momentum...”), signalling our imperative formatter was stripping context from rule summaries.
2. **Indefinite articles misfired on vowel sounds.** Health optional sentences produced copy such as “Move with a energizing rhythm...”, breaking flow from the new storylet catalogue.
3. **Otherwise, core paragraph structure held.** Storylet openers, evidence clauses, and closers landed correctly with multi-event references, so the polish gaps were localized to microcopy.

## Fix summary
- Loosened the bullet formatter to preserve multi-word phrases, reinserted connective prepositions after “challenges,” and ignored trailing imperative verbs when extracting keywords.
- Added article heuristics shared between the language and rendering layers so optional sentences adjust “a/an” dynamically before vowel sounds.
