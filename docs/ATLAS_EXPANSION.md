# Parasite Atlas expansion — 8 September 2026

The reference collection has grown from 9 to 50 entries: 13 trematode, 8 cestode,
9 nematode, 11 intestinal-protozoan, 8 blood-parasite and 1 artifact entries.
These counts include morphology groups and species complexes; they are not 50
independently distinguishable model classes. Check the discovered counts when
adding further records.

## Changes by requirement

1. **Broader coverage:** additional fish/plant-borne flukes, Asian schistosomes,
   Taenia species, hymenolepids, fish/flea tapeworms, hookworms, pinworm,
   capillariasis, intestinal coccidia/amoebae/ciliates, five malaria entries,
   lymphatic filariae and Babesia. OV, MIF and artifact references match the
   configured model vocabulary.
2. **Detailed entries:** all 50 JSON records include scientific/common names,
   lineage, synonyms, stage morphology with applicable size ranges, transmission,
   hosts, distribution, clinical significance, specimens, diagnostic methods,
   stains/magnification, look-alikes, source links and annotation guidance.
   Existing nine schematics and detailed life-cycle sequences are retained.
3. **Cards and index:** native bordered cards wrap across available width; the
   index is paginated eight at a time. The selected reference uses six consistent
   tabs. Name/synonym/content search combines with group, transmission and clinical
   filters. Comparisons include specimen, morphology, confusion and model scope.
4. **Reusable data:** per-entry JSON remains the source of truth. `content.py`
   validates records, filters them, resolves configured model labels, provides
   translation fallback and exports portable JSON. One entry, comparisons and
   the filtered collection can be downloaded without local filesystem paths.
5. **Learning and detection integration:** each new entry has a source-linked
   specimen/stage practice question. The original 27 questions remain, giving 68
   questions across 50 entries. Detector results can open exact matching Atlas
   references. Handoffs clear restrictive filters so the target is always visible.

## Files

- `pages/parasites/<id>/content.json`: 9 enriched and 41 new records.
- `pages/parasites_quiz/<id>/quiz.json`: 41 new introductory questions.
- `pages/atlas.py`: filters, cards, reference tabs, comparison and downloads.
- `content.py`: shared validation, search, translation and label resolution.
- `component_layout/detector.py`: source-linked reference navigation.
- `tests/test_content.py`, `tests/test_app.py`: data and UI regressions.

The Home and Examination discover the new records automatically. Inference,
weights, confidence defaults, model order and branded model names are unchanged.

## Content boundaries

This is an English source-compiled teaching collection, with translation-ready
fields, not a completed Thai translation or independently clinically validated
reference. CDC DPDx pages, malaria bench aids, WHO context and species-specific
publications are linked in the individual records. Microscopy galleries remain
external; captions explicitly distinguish existing schematic illustrations from
diagnostic photographs. Source image rights must be checked before dataset reuse.

`class_1` resolves to the OV egg entry and `class_2` to the MIF **group**.
`artifact` resolves to the mimic reference. `class_0` is deliberately unresolved.
Hookworm species, Taenia species, small operculated flukes and the E. histolytica
complex retain their microscopy limitations. Hd/Hn/Hw and OV variants need the
original dataset dictionary before being assigned biological identities.

New Atlas content never expands a model's trained vocabulary. Source-level PCR
confirmation of a mixed specimen does not label each pictured egg, and an image's
200–650 pixel dimensions do not supply µm calibration.

See [content authoring instructions](CONTENT_TEMPLATES.md) for the v2 schema.

## Verification

All 60 Python tests passed, including rendering every Atlas record, new practice
handoffs, combined filters, index pagination, navigation from filtered results,
portable exports, model alias resolution and translation fallback. Existing
detector regression tests passed. Browser-based visual inspection was unavailable
in this session; native wrapping containers provide the responsive card layout.
No model weights were changed or retrained for this content update.
