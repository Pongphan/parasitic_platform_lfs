"""Add Thailand-focused learning entries without overwriting existing content."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Descriptions are concise teaching summaries; sources are recorded per entry.
ENTRIES = [
    ("necator_americanus", "Necator americanus", "Human hookworm", "Nematodes", "hookworm",
     "A human intestinal hookworm; infective larvae penetrate skin.",
     ["Thin-shelled eggs contain cleavage-stage cells.", "Eggs cannot reliably distinguish Necator from Ancylostoma."],
     "Adult attachment can cause blood loss and iron deficiency anemia.",
     [("Soil", "Eggs hatch and larvae mature."), ("Skin", "Infective larvae penetrate exposed skin."), ("Migration", "Larvae pass through lungs and are swallowed."), ("Intestine", "Adults attach and produce eggs.")],
     [("Which stage penetrates skin?", ["Filariform larva", "Egg", "Cyst"], 0, "The filariform larva is infective."),
      ("Which complication follows blood loss?", ["Anemia", "Cysticercosis", "Malaria"], 0, "Adult attachment can cause chronic blood loss."),
      ("Can eggs reliably identify the hookworm species?", ["Yes", "No"], 1, "Hookworm eggs overlap morphologically.")]),
    ("ancylostoma_ceylanicum", "Ancylostoma ceylanicum", "Zoonotic intestinal hookworm", "Nematodes", "hookworm",
     "A zoonotic hookworm of particular relevance to Southeast Asia; humans, dogs and cats can be hosts.",
     ["Routine egg morphology does not establish species identity."],
     "Interpret hookworm eggs at group level unless species is confirmed by additional methods.",
     [("Environment", "Eggs pass into soil."), ("Larvae", "Larvae develop to infectivity."), ("Exposure", "Skin penetration or ingestion can transmit larvae."), ("Intestine", "Adults establish and shed eggs.")],
     [("Which animals can host this parasite?", ["Dogs and cats", "Fish only", "Snails only"], 0, "Dogs and cats can be hosts."),
      ("Which region is especially relevant?", ["Southeast Asia", "Antarctica"], 0, "This species is endemic across much of Southeast Asia."),
      ("What can routine egg morphology establish?", ["Hookworm group", "Definite species identity"], 0, "Egg morphology overlaps between hookworms.")]),
    ("taenia_spp", "Taenia spp.", "T. saginata, T. solium and T. asiatica", "Cestodes", "taeniasis",
     "A species-group entry for intestinal tapeworms. T. asiatica occurs in Thailand. Egg appearance does not resolve species.",
     ["Round eggs have a radially striated embryophore and a six-hooked oncosphere.", "Use suitable proglottid, scolex or molecular findings to resolve species."],
     "Taeniasis follows ingestion of cysticerci in meat. Ingestion of T. solium eggs can instead cause cysticercosis; these transmission routes must not be confused.",
     [("Egg shedding", "Humans pass eggs or proglottids."), ("Animal host", "Cattle or pigs ingest eggs."), ("Larval stage", "Cysticerci develop in the intermediate host."), ("Human intestine", "Ingested cysticerci develop into adult tapeworms.")],
     [("Which egg feature supports Taenia recognition?", ["Radial striations", "Polar plugs", "Opercular shoulders"], 0, "The embryophore is radially striated."),
      ("What exposure can cause cysticercosis?", ["T. solium eggs", "Beef cysticerci", "Fish metacercariae"], 0, "T. solium egg ingestion may produce tissue infection."),
      ("Can eggs distinguish T. saginata from T. solium?", ["Yes", "No"], 1, "Taenia eggs are morphologically indistinguishable.")]),
    ("fasciolopsis_buski", "Fasciolopsis buski", "Giant intestinal fluke", "Trematodes", "fasciolopsiasis",
     "An intestinal fluke transmitted by metacercariae on aquatic plants. Humans and pigs are definitive hosts.",
     ["Large, broadly oval operculated eggs.", "Eggs measure about 130–150 × 60–90 µm and resemble Fasciola eggs."],
     "Heavy infections may cause diarrhea, abdominal pain or obstruction. Egg microscopy alone cannot reliably separate Fasciolopsis from Fasciola.",
     [("Water", "Eggs embryonate and release miracidia."), ("Snail", "Larval stages develop in a snail."), ("Plants", "Cercariae encyst on aquatic vegetation."), ("Intestine", "Ingested metacercariae mature into intestinal adults.")],
     [("Which exposure transmits infection?", ["Aquatic plants with metacercariae", "Mosquito bite", "Undercooked beef"], 0, "Metacercariae encyst on aquatic plants."),
      ("Where do adults live?", ["Intestine", "Bile ducts", "Blood cells"], 0, "F. buski is an intestinal fluke."),
      ("Which egg resembles F. buski?", ["Fasciola", "Trichuris", "Taenia"], 0, "These large operculated eggs can be indistinguishable.")]),
    ("strongyloides_stercoralis", "Strongyloides stercoralis", "Intestinal threadworm", "Nematodes", "strongyloidiasis",
     "A soil-transmitted nematode capable of autoinfection and long-term persistence in a host.",
     ["Rhabditiform larvae, rather than eggs, are usually detected in stool.", "A short buccal cavity and prominent genital primordium help distinguish rhabditiform larvae from hookworm larvae."],
     "Immunosuppression can permit hyperinfection or dissemination. A negative routine stool examination does not exclude infection.",
     [("Soil", "Larvae develop through direct or free-living pathways."), ("Skin", "Filariform larvae penetrate skin."), ("Intestine", "Parasitic females produce eggs that hatch."), ("Persistence", "Larvae leave in stool or participate in autoinfection.")],
     [("What is usually found in stool?", ["Rhabditiform larvae", "Operculated eggs", "Proglottids"], 0, "Larvae are the usual stool diagnostic stage."),
      ("Which process permits prolonged persistence?", ["Autoinfection", "Fish encystation", "Mosquito transmission"], 0, "Autoinfection can maintain infection."),
      ("Which context increases hyperinfection concern?", ["Immunosuppression", "Normal eyesight", "Blood group O alone"], 0, "Immunosuppression can permit severe disease.")]),
]

ART = {
    "hookworm": '<ellipse cx="250" cy="160" rx="110" ry="70" fill="#F2E5CC" stroke="#826A42" stroke-width="3"/>' + ''.join(f'<circle cx="{x}" cy="{y}" r="23" fill="#CEC09C" stroke="#958460" stroke-width="2"/>' for x,y in [(219,138),(269,138),(219,185),(269,185)]),
    "taeniasis": '<circle cx="250" cy="160" r="85" fill="#E6CCAA" stroke="#876C4A" stroke-width="14" stroke-dasharray="3 4"/><circle cx="250" cy="160" r="65" fill="#EFE5D3" stroke="#876C4A" stroke-width="3"/>' + ''.join(f'<path d="M{x} 145 q-12 20 0 30" fill="none" stroke="#876C4A" stroke-width="3"/>' for x in [225,235,245,255,265,275]),
    "fasciolopsiasis": '<ellipse cx="250" cy="160" rx="85" ry="108" fill="#EBD7B0" stroke="#897046" stroke-width="4"/><path d="M194 78 Q250 97 306 78" fill="none" stroke="#897046" stroke-width="3"/>' + ''.join(f'<circle cx="{x}" cy="{y}" r="9" fill="#BEA477"/>' for x,y in [(225,120),(268,135),(217,169),(259,181),(235,212)]),
    "strongyloidiasis": '<path d="M135 190 C165 70 320 75 350 160 S250 275 215 223" fill="none" stroke="#9A9770" stroke-width="20" stroke-linecap="round"/><path d="M135 190 C165 70 320 75 350 160 S250 275 215 223" fill="none" stroke="#D6D8B8" stroke-width="13" stroke-linecap="round"/>',
}

def main():
    for sid, name, common, group, source, description, morphology, clinical, steps, questions in ENTRIES:
        folder = ROOT / "pages" / "parasites" / sid
        folder.mkdir(parents=True, exist_ok=True)
        quiz_folder = ROOT / "pages" / "parasites_quiz" / sid
        quiz_folder.mkdir(parents=True, exist_ok=True)
        entry = {"schema_version":1, "id":sid, "name":name, "common_name":common, "group":group, "description":description, "morphology":morphology, "clinical_significance":clinical,
                 "life_cycle":[{"stage":stage,"detail":detail} for stage,detail in steps],
                 "images":[{"file":"morphology.svg","caption":"Original schematic — not to scale; not a microscopy image.","credit":"Parasitic Platform 2027","license":"CC0-1.0"}],
                 "references":[{"title":f"CDC DPDx — {source.capitalize()}","url":f"https://www.cdc.gov/dpdx/{source}/index.html"}], "reviewed_on":"2026-09-07"}
        quiz = {"schema_version":1,"species_id":sid,"questions":[{"id":f"q{i}","question":q,"options":options,"correct_answer":answer,"explanation":explanation} for i,(q,options,answer,explanation) in enumerate(questions,1)]}
        for i, q in enumerate(quiz["questions"]):
            q["options"] = list(q["options"])
            target, previous = i % len(q["options"]), q["correct_answer"]
            q["options"][target], q["options"][previous] = q["options"][previous], q["options"][target]
            q["correct_answer"] = target
        if sid in {"necator_americanus", "ancylostoma_ceylanicum"}:
            entry["references"].append({"title":"Molecular detection of hookworms in Thailand (2014)","url":"https://pmc.ncbi.nlm.nih.gov/articles/PMC3916468/"})
        if sid == "fasciolopsis_buski":
            entry["references"].append({"title":"Fasciolopsis buski in an endemic area in Thailand (2002)","url":"https://pubmed.ncbi.nlm.nih.gov/12466749/"})
        svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="500" height="350" viewBox="0 0 500 350" role="img" aria-label="{name} schematic"><rect width="500" height="350" rx="24" fill="#EFF3EA"/>{ART[source]}<text x="250" y="320" text-anchor="middle" font-family="sans-serif" font-size="12" fill="#536B63">SCHEMATIC · NOT TO SCALE</text></svg>'
        for path, text in [(folder/"content.json",json.dumps(entry,ensure_ascii=False,indent=2)), (quiz_folder/"quiz.json",json.dumps(quiz,ensure_ascii=False,indent=2)), (folder/"morphology.svg",svg)]:
            if not path.exists():
                path.write_text(text+"\n",encoding="utf-8")
    for path in (ROOT/"pages"/"parasites").glob("*/content.json"):
        entry=json.loads(path.read_text(encoding="utf-8"))
        entry.setdefault("classification_label", entry["id"].replace("_", " "))
        entry.setdefault("classifier_labels", ["opisthorchis viverrini egg"] if entry["id"] == "opisthorchis_viverrini" else [])
        path.write_text(json.dumps(entry,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")

if __name__ == "__main__":
    main()
