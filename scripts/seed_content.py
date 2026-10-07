"""Rebuild bundled educational JSON and original SVG learning illustrations."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = [
    {
        "id": "opisthorchis_viverrini", "name": "Opisthorchis viverrini", "common_name": "Southeast Asian liver fluke", "group": "Trematodes",
        "description": "A fish-borne liver fluke associated with the lower Mekong region. Adult worms inhabit the biliary system.",
        "morphology": ["Small eggs with an operculum, shoulders, and a knob at the opposite pole.", "Opisthorchis eggs measure approximately 19–30 × 10–20 µm.", "Eggs resemble Clonorchis eggs; morphology alone may not resolve species."],
        "clinical_significance": "Infection may be silent. Biliary inflammation and obstruction can occur; chronic infection is associated with cholangiocarcinoma. Microscopic egg detection in stool requires careful interpretation alongside exposure history.",
        "steps": [("Eggs in stool", "Eggs leave the definitive host in feces."), ("Snail host", "A freshwater snail ingests eggs; larval stages develop."), ("Freshwater fish", "Cercariae leave the snail and encyst as metacercariae in fish."), ("Human host", "Eating infected undercooked fish introduces larvae that mature in bile ducts.")],
        "source": "opisthorchiasis",
        "questions": [
            ("Which food exposure transmits this parasite?", ["Undercooked freshwater fish", "Unwashed berries only", "Undercooked beef", "Mosquito bites"], 0, "Metacercariae in freshwater fish infect the definitive host when eaten."),
            ("Where do adult worms primarily reside?", ["Blood cells", "Bile ducts", "Skeletal muscle", "Urinary bladder"], 1, "The adult fluke lives in the biliary system."),
            ("Which egg feature supports recognition?", ["Radial striations", "A lateral spine", "An operculum with shoulders", "Four nuclei"], 2, "The egg has an operculum and shoulders; related fluke eggs can look similar.")],
        "art": "fluke",
    },
    {
        "id": "ascaris_lumbricoides", "name": "Ascaris lumbricoides", "common_name": "Large intestinal roundworm", "group": "Nematodes",
        "description": "A large intestinal nematode transmitted by ingestion of infective eggs from a fecally contaminated environment.",
        "morphology": ["Fertilized eggs are thick-shelled, commonly with an outer mammillated coat.", "Fertilized eggs are approximately 45–75 µm long.", "Decorticated eggs lack the outer coat; unfertilized eggs are more elongated."],
        "clinical_significance": "Heavy worm burdens may produce intestinal obstruction and impaired growth. Migrating adults may obstruct biliary passages. Stool microscopy looks for characteristic eggs; unfertilized eggs are not infective.",
        "steps": [("Eggs in soil", "Eggs pass in stool; fertile eggs develop in suitable soil."), ("Ingestion", "A host swallows embryonated eggs."), ("Lung migration", "Larvae hatch, migrate to the lungs, ascend airways, and are swallowed."), ("Intestinal adults", "Adults mature in the small intestine and females produce eggs.")],
        "source": "ascariasis",
        "questions": [
            ("Which stage initiates infection?", ["Unfertilized egg", "Embryonated fertile egg", "Fish metacercaria", "Cercaria"], 1, "Infection follows ingestion of fertile eggs containing developed larvae."),
            ("Which organ is part of larval migration?", ["Lung", "Urinary bladder", "Retina only", "Thyroid"], 0, "Larvae pass through the lungs before being swallowed back into the intestine."),
            ("What does a decorticated egg lack?", ["All internal contents", "Its entire shell", "The outer mammillated coat", "A pair of polar plugs"], 2, "Decorticated Ascaris eggs lack the outer mammillated layer.")],
        "art": "ascaris",
    },
    {
        "id": "giardia_duodenalis", "name": "Giardia duodenalis", "common_name": "Giardia (G. lamblia / G. intestinalis)", "group": "Protozoa",
        "description": "An intestinal flagellate with a motile trophozoite and a resistant cyst stage. Transmission follows ingestion of cysts.",
        "morphology": ["Oval cysts measure approximately 8–19 µm.", "Mature cysts contain four nuclei; immature cysts have two.", "Trophozoites attach to the small-intestinal mucosa using a ventral disk."],
        "clinical_significance": "Presentations range from asymptomatic carriage to diarrhea, bloating, and malabsorption. Cysts and trophozoites may occur in stool. Fecal–oral transmission can involve water, food, hands, or fomites.",
        "steps": [("Cyst ingestion", "A host ingests cysts through fecal–oral exposure."), ("Excystation", "Cysts release trophozoites in the small intestine."), ("Multiplication", "Trophozoites multiply by binary fission."), ("Encystation", "Cysts form during intestinal transit and pass in stool, enabling transmission.")],
        "source": "giardiasis",
        "questions": [
            ("Which stage is chiefly responsible for transmission?", ["Egg", "Cyst", "Cercaria", "Microfilaria"], 1, "The resistant cyst survives outside the host and is ingested."),
            ("How many nuclei occur in a mature cyst?", ["One", "Two", "Four", "Eight"], 2, "Mature Giardia cysts have four nuclei."),
            ("Which clinical pattern fits giardiasis?", ["Biliary fluke obstruction", "Malabsorption with diarrhea", "Urinary egg shedding", "An adult tapeworm in muscle"], 1, "Giardiasis may cause diarrhea and impaired absorption in the intestine.")],
        "art": "giardia",
    },
    {
        "id": "trichuris_trichiura", "name": "Trichuris trichiura", "common_name": "Human whipworm", "group": "Nematodes",
        "description": "A soil-transmitted nematode whose adults live in the cecum and ascending colon, with their slender anterior ends embedded in mucosa.",
        "morphology": ["Eggs are barrel-shaped with a plug at each pole.", "Typical eggs measure approximately 50–55 × 20–25 µm.", "Eggs leave the host unembryonated and mature in soil."],
        "clinical_significance": "Light infections are often asymptomatic. Heavy infection, especially in children, may cause abdominal pain, diarrhea, growth impairment, or rectal prolapse. Stool microscopy detects eggs.",
        "steps": [("Egg shedding", "Unembryonated eggs pass in feces."), ("Soil development", "Eggs embryonate in the environment."), ("Ingestion", "A host swallows infective eggs from contaminated hands or food."), ("Colon adults", "Larvae hatch in the small intestine; adults establish in the colon.")],
        "source": "trichuriasis",
        "questions": [
            ("What is the characteristic egg feature?", ["Radial striations", "Four nuclei", "Bipolar plugs", "An operculum with shoulders"], 2, "Whipworm eggs have plugs at both ends of a barrel-shaped shell."),
            ("Where do adult whipworms primarily live?", ["Cecum and ascending colon", "Bile ducts", "Lung alveoli", "Red blood cells"], 0, "Adults establish in the cecum and ascending colon."),
            ("How are eggs typically passed in stool?", ["As cysts", "Already containing adult worms", "Unembryonated", "As swimming cercariae"], 2, "Eggs develop in soil after leaving the host.")],
        "art": "trichuris",
    },
]

ART = {
    "fluke": '<ellipse cx="250" cy="160" rx="66" ry="98" fill="#F1DDB6" stroke="#846238" stroke-width="5"/><path d="M201 96 Q250 114 299 96" fill="none" stroke="#846238" stroke-width="5"/><circle cx="250" cy="260" r="6" fill="#846238"/><ellipse cx="250" cy="175" rx="38" ry="50" fill="#C6B080" opacity=".6"/>',
    "ascaris": '<ellipse cx="250" cy="160" rx="110" ry="83" fill="#EAD6B6" stroke="#846238" stroke-width="12" stroke-dasharray="6 5"/><ellipse cx="250" cy="160" rx="95" ry="69" fill="none" stroke="#846238" stroke-width="4"/><ellipse cx="250" cy="160" rx="50" ry="43" fill="#B7A47B"/>',
    "giardia": '<ellipse cx="250" cy="160" rx="83" ry="106" fill="#DAE5D5" stroke="#547764" stroke-width="4"/><path d="M236 80 Q290 160 240 235 M255 80 Q210 160 275 235" fill="none" stroke="#829A75" stroke-width="3"/>' + ''.join(f'<circle cx="{x}" cy="{y}" r="14" fill="#829A75" stroke="#547764" stroke-width="3"/>' for x,y in [(225,125),(275,125),(225,188),(275,188)]),
    "trichuris": '<path d="M158 132 Q250 75 342 132 L342 188 Q250 245 158 188 Z" fill="#EAD6B6" stroke="#846238" stroke-width="6"/><ellipse cx="155" cy="160" rx="15" ry="29" fill="#F7EDD9" stroke="#846238" stroke-width="4"/><ellipse cx="345" cy="160" rx="15" ry="29" fill="#F7EDD9" stroke="#846238" stroke-width="4"/>',
}

def main():
    for record in DATA:
        entry = dict(record)
        sid = entry["id"]
        folder = ROOT / "pages" / "parasites" / sid
        folder.mkdir(parents=True, exist_ok=True)
        quiz_folder = ROOT / "pages" / "parasites_quiz" / sid
        quiz_folder.mkdir(parents=True, exist_ok=True)
        questions = entry.pop("questions")
        art = entry.pop("art")
        source = entry.pop("source")
        entry["life_cycle"] = [{"stage": stage, "detail": detail} for stage, detail in entry.pop("steps")]
        entry["schema_version"] = 1
        entry["reviewed_on"] = "2026-09-07"
        entry["images"] = [{"file": "morphology.svg", "caption": "Original schematic of a cyst or egg · not to scale; not a microscopy image.", "credit": "Parasitic Platform 2027", "license": "CC0-1.0"}]
        entry["references"] = [{"title": f"CDC DPDx — {source.capitalize()}", "url": f"https://www.cdc.gov/dpdx/{source}/index.html"}]
        (folder / "content.json").write_text(json.dumps(entry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="500" height="350" viewBox="0 0 500 350" role="img" aria-label="Schematic {entry["name"]} egg or cyst"><rect width="500" height="350" rx="24" fill="#EFF3EA"/>{ART[art]}<text x="250" y="317" text-anchor="middle" font-family="sans-serif" font-size="12" fill="#536B63">MORPHOLOGY STUDY · SCHEMATIC · NOT TO SCALE</text></svg>'
        (folder / "morphology.svg").write_text(svg, encoding="utf-8")
        quiz = {"schema_version": 1, "species_id": sid, "questions": [{"id": f"q{i}", "question": q, "options": opts, "correct_answer": answer, "explanation": explanation} for i,(q,opts,answer,explanation) in enumerate(questions,1)]}
        (quiz_folder / "quiz.json").write_text(json.dumps(quiz, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for path in (ROOT / "component_ai" / "keras").glob("*.keras"):
        contract = {"schema_version": 1, "labels": ["artifact", "opisthorchis viverrini egg", "minute intestinal fluke egg"], "preprocessing": "raw_0_255", "output": "sigmoid_scores", "provenance": "Class order and raw pixel preprocessing inherited from parasitic_platform_2026/pages/03_Parasitic_Vision.py; output activation inspected in saved model. Training provenance and external validation were not supplied."}
        path.with_suffix(".json").write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()
