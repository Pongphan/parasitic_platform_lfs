# Complete Atlas schematic coverage

Every one of the 50 Atlas entries now has a local SVG illustration under
**Morphology & images → Schematic morphology**. Nine existing illustrations were
preserved. Forty-one entries received new stage-specific diagrams, including the
artifact reference group. External microscopy galleries remain available.

New images identify the illustrated stage, list three morphology features and
state the relevant identification limitation. They are original vector drawings,
not photographs, calibrated size references, model training labels or ground truth.
Closely related parasites intentionally share egg patterns where routine microscopy
does not establish species. Colors organize the diagrams rather than simulate a stain,
except where a caption explicitly discusses iodine-highlighted glycogen.

The diagrams follow the existing entry morphology and cited references. Additional
cross-checks used these primary CDC DPDx resources:

- [Comparative intestinal parasite morphology](https://www.cdc.gov/dpdx/diagnosticprocedures/stool/morphcomp.html)
- [Malaria stages and erythrocyte context](https://www.cdc.gov/dpdx/malaria/index.html)
- [Lymphatic filariasis and microfilarial tail nuclei](https://www.cdc.gov/dpdx/lymphaticfilariasis/index.html)
- [Babesia blood forms](https://www.cdc.gov/dpdx/babesiosis/index.html)

`scripts/add_atlas_schematics.py` generates the new `morphology_schematic.svg` assets
and adds missing image metadata. It does not replace the nine legacy images or
change parasite text, quizzes, translations, model mappings, or references. Repeated
runs rebuild only the generated assets and do not duplicate metadata. Unknown new
species without a specific drawing raise an error instead of receiving a generic icon.

```powershell
python scripts/add_atlas_schematics.py
# Optional developer-only raster contact sheets; uses Pillow and Windows Arial:
python scripts/add_atlas_schematics.py --preview
```

Raster contact sheets are generated from the same geometric primitives for visual
inspection under `.qa/atlas_schematics/`. Production needs only the checked-in SVGs;
no renderer or additional dependency is required. New labeled diagrams display at
up to 800 pixels; legacy unlabeled drawings keep their existing 420-pixel width.
