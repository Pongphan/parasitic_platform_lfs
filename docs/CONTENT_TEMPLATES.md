# Extend the reference collection

The live collection contains 50 species/reference groups and 68 practice questions.
Copy an existing `pages/parasites/<id>/content.json` v2 record and revise every
field against appropriate primary sources. Keep the lowercase snake_case ID equal
to the folder name. Records are loaded locally; reference links require internet.

## Atlas schema v2

| Field | Type and purpose |
| --- | --- |
| `schema_version`, `id` | `2` and the stable record identifier |
| `name`, `common_name`, `aliases` | Scientific display name, common name, searchable synonyms |
| `entry_type` | `species` or `reference_group`; a complex/group is not a confirmed species |
| `group` | Nematodes, Cestodes, Trematodes, Protozoa, Blood parasites or Artifacts |
| `taxonomy` | `lineage`, nullable `genus`, `scientific_name`, nullable `species_epithet`, `rank_note` |
| `description`, `morphology` | Summary string and stage-specific morphology paragraphs as a string list |
| `transmission` | Object with stable `types` string list and explanatory `detail` |
| `life_cycle` | Ordered objects with `stage` and `detail` |
| `hosts`, `distribution` | Host roles/reservoirs and geographic context as strings |
| `clinical_significance`, `clinical_tags` | Narrative and searchable clinical categories |
| `specimen`, `diagnostics` | Diagnostic stages/specimen string and method/stain/magnification string list |
| `differential_diagnosis` | String list of look-alikes and limits of identification |
| `images` | Local illustration objects: `file`, `caption`, `credit`, `license`; may be empty when reference galleries exist |
| `reference_images` | Objects with `url`, `caption`, `kind`, `rights`; these are external links, not downloaded ground truth |
| `references` | Source objects with `title` and `url` |
| `reviewed_on`, `review_status` | Compilation date and honest editorial/validation status |
| `classification_label` | Educational label; does not alter model output |
| `classifier_labels` | Exact configured labels that resolve to this entry; empty for unsupported taxa |
| `model_mapping` | `exact_labels` matching the list above, nullable `related_atlas_id`, `status`, `note`, `configured_detector_aliases` |
| `annotation_guidance` | Stage/specimen/calibration/uncertainty/dataset preparation notes |
| `language`, `translations` | Base `en` and locale-keyed display overrides |

Do not map a genus-level morphology label to several species. Exact matches must
be unique across the collection; related references use `related_atlas_id`.
`atlas_for_model_label()` applies existing explicit aliases from the AI settings
and then exact label matching. It does not interpret numeric class IDs, partial
names or unexplained dataset codes. `class_0`, Hd/Hn/Hw remain unresolved.

Taxonomic lineage is separate from the browsing category: blood parasites include
both protozoa and nematodes. Do not force a protozoan clade into an unsupported
formal rank. For groups spanning genera, set `genus` to `null`.

## Translation example

Add reviewed Thai display text to an entry, retaining scientific and model IDs:

```json
{
  "language": "en",
  "translations": {
    "th": {
      "common_name": "ชื่อสามัญที่ผ่านการตรวจสอบ",
      "description": "คำอธิบายภาษาไทยที่อ้างอิงแหล่งข้อมูล",
      "morphology": ["ลักษณะระยะวินิจฉัยและขนาดเป็นไมโครเมตร"]
    }
  }
}
```

The language selector appears when a nonempty translation is available. Omitted
display fields fall back to English. `localized_entry()` only overrides approved
display fields, leaving taxonomic IDs and model mappings intact. Search includes
translations. The current release contains English content; it does not claim a
completed Thai translation. Filter vocabularies and shell labels remain English.

## Images and diagnostic labels

Keep local paths inside the species folder; path traversal is rejected. Describe
whether a local image is a schematic or true microscopy. Gallery links should
identify stage/species limitations, especially if showing a related group. Check
the original image attribution before reuse. Never label a generated illustration
as microscopy or use a crop's pixel count as its physical size.

Use calibrated µm ranges and record specimen, stage, stain, acquisition settings
and uncertainty. A molecular result on a mixed stool specimen is not automatically
object-level ground truth. Keep related crops within patient/specimen-level data
splits. Adding content does not add, reorder or validate trained model classes.

## Examination records

Create `pages/parasites_quiz/<id>/quiz.json` with a matching `species_id`:

```json
{
  "species_id": "species_name",
  "questions": [{
    "id": "diagnostic_stage",
    "question": "A source-grounded question about this entry",
    "options": ["Correct answer", "A plausible, unambiguously incorrect alternative"],
    "correct_answer": 0,
    "explanation": "Explain the distinction and its microscopy limitations.",
    "references": [{"title": "Supporting primary reference", "url": "https://www.cdc.gov/dpdx/"}]
  }]
}
```

Answer indices are zero-based; question IDs and options must be unique. Preserve
uncertainty in questions involving visually indistinguishable species. The
Examination discovers records automatically and revisions invalidate prior quiz
attempts. Each bundled entry has practice; new entries should include it too.

Use `export_atlas(entries)` for portable JSON without runtime filesystem paths.
Run `python -m pytest tests/test_content.py tests/test_app.py -q` after additions.

The old `scripts/seed_content.py` and `scripts/expand_content.py` describe the v1
baseline, not the current authoring schema. Do not reseed the v2 collection with
them: the original seed script overwrites records and model contracts. Current
per-entry JSON is the source of truth and needs no generation step at runtime.
