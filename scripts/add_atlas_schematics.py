"""Add missing, original SVG diagrams without replacing existing Atlas artwork.

Illustrations follow each entry's morphology text. Shared forms intentionally do
not imply species-level separation. Run from any directory; --preview creates a
Pillow contact sheet from the same vector primitives for layout inspection.
"""
import argparse
from html import escape
import json
import math
from pathlib import Path
import textwrap

ROOT = Path(__file__).resolve().parents[1]
INK, EDGE, FILL = '#203C36', '#8C663B', '#F3DFB5'
BLUE, PALE, PURPLE = '#426FA5', '#E3EEF8', '#7754A0'


class Canvas:
    """Small SVG scene writer; optional raster preview uses identical coordinates."""
    def __init__(self, title, description, preview=False):
        self.parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="900" height="560" viewBox="0 0 900 560" role="img" aria-labelledby="title desc"><title id="title">{escape(title)}</title><desc id="desc">{escape(description)}</desc>']
        self.image = self.draw = None
        if preview:
            from PIL import Image, ImageDraw
            self.image = Image.new('RGB', (900,560), '#F4F7F2')
            self.draw = ImageDraw.Draw(self.image)
        self.rect(0,0,900,560,'#F4F7F2')

    def ellipse(self,x,y,rx,ry,fill=FILL,stroke=EDGE,width=3):
        self.parts.append(f'<ellipse cx="{x}" cy="{y}" rx="{rx}" ry="{ry}" fill="{fill}" stroke="{stroke}" stroke-width="{width}"/>')
        if self.draw:
            self.draw.ellipse((x-rx,y-ry,x+rx,y+ry),fill=None if fill=='none' else fill,outline=None if stroke=='none' else stroke,width=width)

    def line(self,points,color=EDGE,width=3,closed=False,fill='none'):
        tag = 'polygon' if closed else 'polyline'
        coords = ' '.join(f'{x:.2f},{y:.2f}' for x,y in points)
        self.parts.append(f'<{tag} points="{coords}" fill="{fill}" stroke="{color}" stroke-width="{width}" stroke-linejoin="round" stroke-linecap="round"/>')
        if self.draw:
            if closed:
                self.draw.polygon(points,fill=None if fill=='none' else fill)
            self.draw.line(points + ([points[0]] if closed else []),fill=color,width=width,joint='curve')

    def rect(self,x,y,w,h,fill,stroke='none',width=1):
        self.parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="{stroke}" stroke-width="{width}"/>')
        if self.draw:
            self.draw.rectangle((x,y,x+w,y+h),fill=fill,outline=None if stroke=='none' else stroke,width=width)

    def text(self,x,y,value,size=20,color=INK):
        self.parts.append(f'<text x="{x}" y="{y}" font-family="Arial, sans-serif" font-size="{size}" fill="{color}">{escape(value)}</text>')
        if self.draw:
            from PIL import ImageFont
            font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf',size)
            self.draw.text((x,y),value,font=font,fill=color,anchor='ls')

    def svg(self):
        return ''.join(self.parts)+'</svg>\n'


def circle(c,x,y,r,fill=FILL,stroke=EDGE,width=3):
    c.ellipse(x,y,r,r,fill,stroke,width)


def oval_points(cx,cy,rx,ry,count=60):
    return [(cx+rx*math.cos(i*2*math.pi/count),cy+ry*math.sin(i*2*math.pi/count)) for i in range(count)]


def nucleus(c,x,y,kind='fine',r=18):
    circle(c,x,y,r,'#EFE7F6',PURPLE,2)
    if kind in ('fine','coarse'):
        for i in range(10):
            a=i*math.tau/10
            circle(c,x+(r-4)*math.cos(a),y+(r-4)*math.sin(a),1.5 if kind=='fine' else 2.5,PURPLE,'none',1)
    if kind=='fragmented':
        for dx,dy in [(-4,-3),(4,-3),(-2,4),(5,4)]:
            circle(c,x+dx,y+dy,2.5,PURPLE,'none',1)
    else:
        circle(c,x+(5 if kind=='coarse' else 0),y,4 if kind=='fine' else 7,PURPLE,'none',1)


def hooks(c,cx,cy,scale=1):
    for offset in (-14,0,14):
        for direction in (-1,1):
            c.line([(cx+offset*scale,cy-12*scale),(cx+(offset+direction*5)*scale,cy+9*scale),(cx+(offset+direction*10)*scale,cy+3*scale)],PURPLE,2)


def granules(c,cx,cy,rx,ry,color='#C3A474',count=30):
    for i in range(count):
        a=i*2.39996
        f=math.sqrt((i+.5)/count)*.85
        circle(c,cx+rx*f*math.cos(a),cy+ry*f*math.sin(a),3+(i%2),color,'none',1)


def egg(c,kind):
    if kind in ('hookworm','trichostrongylus'):
        if kind=='hookworm':
            c.ellipse(245,290,128,78,'#FBF8EB',EDGE,3)
        else:
            pts=oval_points(245,290,148,66)
            pts[0]=(410,290)
            c.line(pts,EDGE,3,True,'#FBF8EB')
        cells=[(210,266),(257,268),(214,309),(263,309)]
        if kind=='trichostrongylus':
            cells += [(304,269),(306,312)]
        for x,y in cells:
            c.ellipse(x,y,24,23,'#DFCBB0','#B29B78',2)
    elif kind=='enterobius':
        # D-shaped, elongated egg: straight left side, curved right.
        pts=[(190,185),(190,395)]+[(190+100*math.sin(i*math.pi/60),290+105*math.cos(i*math.pi/60)) for i in range(61)]
        c.line(pts,EDGE,3,True,'#F8EBCF')
        c.line([(224+20*math.sin(i*.13),215+i*2.9) for i in range(51)],'#B69C6F',10)
    elif kind=='capillaria':
        pts=[(245+130*math.cos(i*math.tau/80),290+65*math.sin(i*math.tau/80)*(1-.2*math.cos(2*i*math.tau/80))) for i in range(80)]
        c.line(pts,EDGE,5,True,FILL)
        for i in range(-5,6):
            x=245+i*19
            extent=65*math.sqrt(1-(i*19/130)**2)*.85
            c.line([(x,290-extent),(x,290+extent)],'#C1A074',2)
        c.ellipse(112,290,7,22,'#FDF3DA',EDGE,3)
        c.ellipse(378,290,7,22,'#FDF3DA',EDGE,3)
        c.ellipse(245,290,80,36,'#D7BD8C','#B59668',2)
    elif kind=='taenia':
        circle(c,245,290,106,FILL,EDGE,4)
        circle(c,245,290,78,'#FCF4DF',EDGE,3)
        for i in range(44):
            a=i*math.tau/44
            c.line([(245+82*math.cos(a),290+82*math.sin(a)),(245+102*math.cos(a),290+102*math.sin(a))],EDGE,3)
        hooks(c,245,290,1.6)
    elif kind in ('h_nana','h_diminuta'):
        c.ellipse(245,290,115,105,'#FAF4DD',EDGE,3)
        c.ellipse(245,290,65,70,'#E9E5CF',EDGE,3)
        hooks(c,245,290,1.3)
        if kind=='h_nana':
            for sy in (220,360):
                circle(c,245,sy,5,EDGE,'none',1)
                for direction in (-1,1):
                    for offset in (0,12):
                        pts=[(245+direction*(t*68),sy+(1 if sy==220 else -1)*(20+offset)*math.sin(t*math.pi)) for t in [i/25 for i in range(26)]]
                        c.line(pts,BLUE,2)
    elif kind=='dipylidium':
        c.line(oval_points(245,290,150,116),EDGE,3,True,'#FAF1D9')
        for x,y in [(170,255),(245,225),(320,255),(205,325),(285,330)]:
            circle(c,x,y,34,'#EFE0BC',EDGE,2)
            hooks(c,x,y,.75)
    else:
        # Vertical operculated forms and round nonoperculated schistosome eggs.
        is_schisto=kind=='schistosoma'
        rx,ry=(107,99) if is_schisto else (82,122)
        c.ellipse(245,290,rx,ry,FILL,EDGE,6 if kind=='paragonimus' else 3)
        if is_schisto:
            c.line([(347,273),(359,278),(349,283)],EDGE,3,True,FILL)
            c.ellipse(240,294,61,72,'#D3BD8C','#B09A6B',2)
            granules(c,240,294,52,61,count=16)
        else:
            y=199
            c.line([(190,y),(215,y+8),(245,y+10),(275,y+8),(300,y)],EDGE,4)
            if kind=='clonorchis':
                c.line([(185,208),(190,198),(202,197)],EDGE,4)
                c.line([(288,197),(300,198),(305,208)],EDGE,4)
            if kind in ('clonorchis','dibothriocephalus'):
                circle(c,245,414,5,EDGE,'none',1)
            if kind in ('small_fluke','clonorchis'):
                c.ellipse(245,302,44,65,'#C8B287','#A99065',2)
                granules(c,245,302,38,55,count=12)
            else:
                granules(c,245,296,65,84,count=45)
            if kind in ('paragonimus','echinostoma'):
                c.line([(219,403),(245,409),(271,403)],EDGE,7)


def protozoan(c,kind):
    if kind=='balantioides':
        for i in range(60):
            a=i*math.tau/60
            c.line([(245+92*math.cos(a),290+124*math.sin(a)),(245+108*math.cos(a+.035),290+141*math.sin(a+.035))],BLUE,2)
        c.ellipse(245,290,92,124,PALE,BLUE,3)
        kidney=[(221,231),(241,226),(261,235),(274,252),(280,279),(277,310),(265,336),(245,350),(225,346),(214,333),(221,320),(240,306),(245,287),(239,268),(221,253)]
        c.line(kidney,PURPLE,3,True,'#B9A4D3')
        c.line([(311,214),(293,246),(314,259)],BLUE,5)
    elif kind=='blastocystis':
        circle(c,245,290,114,PALE,BLUE,3)
        circle(c,245,290,91,'#FBFCF9','#AFBFCC',3)
        for a in (.5,2.6,4.4):
            nucleus(c,245+103*math.cos(a),290+103*math.sin(a),'blot',8)
    elif kind in ('cryptosporidium','cyclospora','cystoisospora'):
        c.ellipse(245,290,86 if kind=='cystoisospora' else 112,133 if kind=='cystoisospora' else 112,'#F5E9F0','#9B6587',4)
        if kind=='cryptosporidium':
            for x,y in [(210,249),(272,258),(208,315),(277,325)]:
                c.line([(x-12,y+20),(x-4,y),(x+10,y-15)],PURPLE,10)
        else:
            # Freshly passed, unsporulated oocyst; do not mix mature anatomy.
            circle(c,245,290,55,'#D7BED6','#9B6587',3)
            granules(c,245,290,42,42,'#A98CB4',15)
    elif kind=='dientamoeba':
        pts=[(245+(111+8*math.sin(5*a))*math.cos(a),290+(94+6*math.cos(4*a))*math.sin(a)) for a in [i*math.tau/80 for i in range(80)]]
        c.line(pts,BLUE,3,True,PALE)
        nucleus(c,205,286,'fragmented',27)
        nucleus(c,281,290,'fragmented',27)
    else:
        c.ellipse(245,290,113,105,'#E9F0DD','#5B7F65',3)
        if kind=='iodamoeba':
            nucleus(c,194,264,'blot',25)
            c.ellipse(276,302,52,62,'#C09A57','#8E703A',3)
        else:
            count=8 if kind=='entamoeba_coli' else 4
            for i in range(count):
                a=i*math.tau/count-math.pi/4
                nucleus(c,245+65*math.cos(a),290+61*math.sin(a),'coarse' if count==8 else ('blot' if kind=='endolimax' else 'fine'),18)
            if kind=='entamoeba_complex':
                c.line([(226,285),(262,302)],PURPLE,12)


def blood(c,kind):
    if kind in ('brugia','wuchereria'):
        points=[(100+i*2.85,280+55*math.sin(i*math.pi/60)) for i in range(101)]
        def outline(radius):
            left,right=[],[]
            for i,(x,y) in enumerate(points):
                dy=55*math.pi/60*math.cos(i*math.pi/60)
                norm=math.hypot(2.85,dy)
                width=radius*min(1,(101-i)/17)
                left.append((x-dy/norm*width,y+2.85/norm*width))
                right.append((x+dy/norm*width,y-2.85/norm*width))
            return left+list(reversed(right))
        c.line(outline(16),'#AFBBCD',2,True,'#F9FBFC')
        c.line(outline(10),BLUE,2,True,'#DCE7F1')
        circle(c,*points[0],10,'#DCE7F1',BLUE,2)
        # Nuclear column ends before the tail; Brugia adds two separated nuclei.
        for i in range(9,79,4):
            x,y=points[i]
            circle(c,x,y,3.3,PURPLE,'none',1)
        if kind=='brugia':
            for i in (87,95):
                x,y=points[i]
                circle(c,x,y,2.7,PURPLE,'none',1)
        return
    def rbc(x,y,rx=87,ry=87,stippling=False,fimbriated=False):
        if fimbriated:
            pts=[(x+(rx+(4 if i%2 else -3))*math.cos(i*math.tau/80),y+ry*math.sin(i*math.tau/80)) for i in range(80)]
            c.line(pts,'#CE949D',3,True,'#FAE1E3')
        else:
            c.ellipse(x,y,rx,ry,'#FAE1E3','#CE949D',3)
        if stippling:
            granules(c,x,y,rx,ry,'#C67F93',42)
    if kind=='babesia':
        rbc(160,285,84,84); rbc(355,285,69,69)
        for angle in (0,math.pi/2,math.pi,math.pi*1.5):
            points=[(160+3*math.cos(angle),285+3*math.sin(angle)),(160+37*math.cos(angle+.26),285+37*math.sin(angle+.26)),(160+43*math.cos(angle),285+43*math.sin(angle)),(160+37*math.cos(angle-.26),285+37*math.sin(angle-.26))]
            c.line(points,PURPLE,3,True,'#C3B3D6')
        c.ellipse(337,279,12,19,'none',BLUE,4)
        c.ellipse(368,286,12,19,'none',BLUE,4)
    elif kind=='falciparum':
        rbc(167,283,88,88)
        for x,y in [(140,261),(196,300)]:
            circle(c,x,y,18,'none',BLUE,3)
            circle(c,x-12,y-13,4,PURPLE,'none',1)
        # Separate mature crescent gametocyte, outside the ring-stage panel.
        pts=[(354+43*math.cos(a),281+78*math.sin(a)) for a in [(-math.pi/2)+i*math.pi/40 for i in range(41)]]
        pts += [(354+17*math.cos(a),281+78*math.sin(a)) for a in [(math.pi/2)-i*math.pi/40 for i in range(41)]]
        c.line(pts,BLUE,3,True,'#ACB8D6')
        circle(c,378,281,11,PURPLE,'none',1)
    elif kind in ('malariae','knowlesi'):
        rbc(163,283,83,83)
        c.line([(91,271),(231,279),(231,299),(91,291)],BLUE,3,True,'#B7B5D3')
        nucleus(c,192,285,'blot',9)
        rbc(355,283,66,66)
        if kind=='malariae':
            for i in range(8):
                a=i*math.tau/8
                c.ellipse(355+38*math.cos(a),283+38*math.sin(a),11,13,'#B9BAD7',BLUE,2)
                circle(c,355+38*math.cos(a),283+38*math.sin(a),4,PURPLE,'none',1)
            circle(c,355,283,12,'#977B56','none',1)
        else:
            circle(c,354,280,20,'none',BLUE,3)
            circle(c,341,265,5,PURPLE,'none',1)
    else:
        rbc(238,290,118 if kind=='ovale' else 116,96 if kind=='ovale' else 116,True,kind=='ovale')
        if kind=='vivax':
            pts=[(238+(51+14*math.sin(5*a))*math.cos(a),290+(46+17*math.sin(4*a))*math.sin(a)) for a in [i*math.tau/90 for i in range(90)]]
            c.line(pts,BLUE,4,True,'#BBC5DC')
            circle(c,224,270,15,PURPLE,'none',1)
            c.ellipse(253,306,19,15,'#F9E0E3','none',1)
        else:
            c.ellipse(240,290,40,43,'#B6C3D9',BLUE,3)
            circle(c,230,275,12,PURPLE,'none',1)


def artifacts(c):
    circle(c,140,260,62,'#FDFDFB','#90AAB2',7)
    c.ellipse(129,249,43,39,'none','#C6D7DC',3)
    for x,y in [(230,220),(294,220),(230,284),(294,284)]:
        c.rect(x,y,62,62,'#E7EACD','#879867',3)
    c.ellipse(190,376,28,20,'#E0D5EC',PURPLE,3)
    c.ellipse(221,360,16,13,'#E0D5EC',PURPLE,3)


# Entry-specific stage and feature labels. Identical shared morphology is deliberate.
SPECS = {}
def register(ids, family, kind, stage, features, note):
    for species in ids.split():
        SPECS[species]=(family,kind,stage,features,note)

register('ancylostoma_duodenale','egg','hookworm','Cleavage-stage egg',
         ['Thin, oval shell','Cleavage-stage blastomeres','Clear space inside the shell'],
         'Hookworm eggs overlap in appearance; this diagram does not establish species.')
register('trichostrongylus_spp','egg','trichostrongylus','Cleavage-stage egg',
         ['Elongated, thin shell','Tapering end','Multiple cleavage cells'],
         'Hookworm-like eggs overlap; specimen context and further identification matter.')
register('enterobius_vermicularis','egg','enterobius','Embryonated egg',
         ['One flattened side','Asymmetric, colorless shell','Developing larva'], 'Orientation and preparation can alter the apparent outline.')
register('capillaria_philippinensis','egg','capillaria','Egg',
         ['Peanut-like outline','Striated shell','Relatively flattened polar plugs'], 'Compare with other bipolar-plugged eggs; not a measurement reference.')
register('taenia_asiatica taenia_saginata taenia_solium','egg','taenia','Taenia-type egg',
         ['Radially striated embryophore','Round, thick-walled profile','Six-hooked oncosphere'], 'Human Taenia species cannot be distinguished reliably by their eggs.')
register('hymenolepis_nana','egg','h_nana','Egg',
         ['Outer membrane and inner embryophore','Six embryonic hooks','Polar filaments'], 'Internal structures are simplified and enlarged for learning.')
register('hymenolepis_diminuta','egg','h_diminuta','Egg',
         ['Round to oval outer shell','Six-hooked embryo','No polar filaments'], 'Do not infer biological size from the displayed drawing.')
register('dipylidium_caninum','egg','dipylidium','Egg packet',
         ['Packet enclosing several eggs','Separate embryonic envelopes','Six-hooked embryos'], 'The number and arrangement of eggs in a packet vary.')
register('clonorchis_sinensis','egg','clonorchis','Embryonated egg',
         ['Operculum with shoulders','Embryonic contents','Small opposite-end knob'], 'Egg morphology overlaps Opisthorchis and other small operculated flukes.')
register('haplorchis_taichui heterophyes_heterophyes metagonimus_yokogawai minute_intestinal_flukes','egg','small_fluke','Small operculated egg',
         ['Small oval profile','Operculum at one pole','Embryonated contents'], 'Shared fluke-egg appearance is not a species-level identification key.')
register('fasciola_hepatica fasciola_gigantica','egg','large_fluke','Unembryonated egg',
         ['Large oval profile','Thin shell with operculum','Unembryonated granular contents'], 'Fasciola species and Fasciolopsis eggs overlap; size alone is insufficient.')
register('echinostoma_spp','egg','echinostoma','Operculated egg',
         ['Oval egg with subtle operculum','Granular internal contents','Possible opposite-end thickening'], 'Echinostome species vary; this is a representative genus-level sketch.')
register('paragonimus_spp','egg','paragonimus','Representative P. westermani-type egg',
         ['Thick shell and operculum','Unembryonated contents','Opposite-end shell thickening'], 'Species vary in outline and size; the illustration simplifies the profile.')
register('dibothriocephalus_latus','egg','dibothriocephalus','Unembryonated egg',
         ['Oval, operculated shell','Granular internal contents','Possible small opposite-end knob'], 'Operculated eggs require comparison with other cestodes and trematodes.')
register('schistosoma_japonicum schistosoma_mekongi','egg','schistosoma','Embryonated egg',
         ['Rounded to oval shell; no operculum','Inconspicuous lateral knob','Miracidium inside the egg'], 'The knob is exaggerated for visibility; related species can appear similar.')
register('balantioides_coli','proto','balantioides','Trophozoite',
         ['Surface cilia','Kidney-shaped macronucleus','Cytostome near the anterior end'], 'Cilia and internal details depend on preparation and observation.')
register('blastocystis_spp','proto','blastocystis','Vacuolar form',
         ['Large central body','Thin peripheral cytoplasmic rim','Nuclei in the peripheral rim'], 'Other forms occur; preservation changes appearance.')
register('cryptosporidium_spp','proto','cryptosporidium','Sporulated oocyst',
         ['Round oocyst wall','Four sporozoites','No sporocysts'], 'Sporozoites are enlarged schematically; species are not resolved by oocyst shape.')
register('cyclospora_cayetanensis','proto','cyclospora','Unsporulated oocyst (freshly passed)',
         ['Spherical oocyst wall','Unsporulated internal contents','Mature sporocysts are not shown'], 'Maturation occurs outside the host; stain color is not simulated here.')
register('cystoisospora_belli','proto','cystoisospora','Immature oocyst (freshly passed)',
         ['Elongated oval wall','Single sporoblast illustrated','Mature sporocysts are not shown'], 'Oocyst maturation changes the internal structures.')
register('dientamoeba_fragilis','proto','dientamoeba','Binucleate trophozoite',
         ['Two nuclei in the common form','Fragmented karyosomal chromatin','No peripheral nuclear chromatin'], 'One-nucleated forms also occur; permanent stains reveal nuclear detail.')
register('endolimax_nana','proto','endolimax','Mature cyst',
         ['Four nuclei','Large, blot-like karyosomes','No peripheral nuclear chromatin'], 'Nuclear detail may be difficult to see in unstained preparations.')
register('entamoeba_coli','proto','entamoeba_coli','Mature cyst',
         ['Eight nuclei in the typical mature cyst','Coarse peripheral chromatin','Often eccentric karyosomes'], 'Immature cysts have fewer nuclei; the mature form is illustrated.')
register('entamoeba_histolytica_complex','proto','entamoeba_complex','Four-nucleated cyst',
         ['Four nuclei in the mature cyst','Fine chromatin and small karyosomes','Rounded-ended chromatoid material'], 'The complex cannot be resolved reliably to species by cyst morphology.')
register('iodamoeba_buetschlii','proto','iodamoeba','Cyst',
         ['Usually one nucleus','Prominent karyosome','Large glycogen vacuole'], 'Brown shading represents the glycogen mass highlighted by iodine.')
register('brugia_malayi','blood','brugia','Sheathed microfilaria',
         ['Sheath around the slender body','Column of somatic nuclei','Separated subterminal and terminal nuclei'], 'Tail nuclear arrangement is emphasized; the body is shortened schematically.')
register('wuchereria_bancrofti','blood','wuchereria','Sheathed microfilaria',
         ['Sheath around the slender body','Somatic nuclear column','Nuclei stop before the tail tip'], 'The clear tail tip is emphasized; the body is shortened schematically.')
register('babesia_spp','blood','babesia','Intraerythrocytic forms',
         ['Erythrocyte context','Occasional Maltese-cross tetrad (left)','Paired forms (right)'], 'A tetrad is not present in every infection; shapes vary by species and stage.')
register('plasmodium_falciparum','blood','falciparum','Ring stages and mature gametocyte',
         ['Delicate rings in a red blood cell (left)','More than one ring may occur','Separate crescent gametocyte (right)'], 'Different stages are shown separately; this is not a single-cell life cycle.')
register('plasmodium_malariae','blood','malariae','Band trophozoite and schizont',
         ['Band-like trophozoite (left)','Rosette of merozoites (right)','Pigment near the schizont center'], 'Two separate infected cells are shown; film findings require expert review.')
register('plasmodium_knowlesi','blood','knowlesi','Band trophozoite and early ring',
         ['Band form resembling P. malariae (left)','Early ring resembling P. falciparum (right)','Erythrocyte context retained'], 'No single illustrated feature confirms P. knowlesi; species can be confused.')
register('plasmodium_vivax','blood','vivax','Developing trophozoite in an erythrocyte',
         ['Enlarged infected erythrocyte','Schuffner stippling','Amoeboid trophozoite'], 'Host-cell size is conceptual; the drawing is not a calibrated blood film.')
register('plasmodium_ovale_complex','blood','ovale','Trophozoite in an infected erythrocyte',
         ['Oval infected erythrocyte','Fimbriated edge and stippling','Compact developing trophozoite'], 'Cell distortion and staining affect these features; not all are always present.')
register('artifacts','artifact','artifacts','Representative non-parasitic mimics',
         ['Refractile air-bubble outline (left)','Regular plant-cell walls (right)','Budding yeast-like form (below)'], 'Illustrative mimics only; no single visual rule excludes a parasite.')


def build(entry, preview=False):
    family,kind,stage,features,note = SPECS[entry['id']]
    description = stage + '. ' + '; '.join(features) + '. ' + note + ' Schematic, not to scale; not a microscopy image.'
    c = Canvas(entry['name']+' — '+stage,description,preview)
    c.text(32,43,'MORPHOLOGY STUDY',16,'#58746B')
    c.text(32,83,entry['name'],28)
    c.text(32,115,stage,18,'#58746B')
    c.line([(32,135),(868,135)],'#D3DED5',2)
    {'egg':egg,'proto':protozoan,'blood':blood,'artifact':lambda canvas,kind:artifacts(canvas)}[family](c,kind)
    for index,feature in enumerate(features,1):
        y=198+(index-1)*85
        circle(c,480,y-7,15,'#DCE9F4','none',1)
        c.text(475,y-1,str(index),16,BLUE)
        for line_index,line in enumerate(textwrap.wrap(feature,31)):
            c.text(507,y+line_index*25,line,19)
    for i,line in enumerate(textwrap.wrap(note,100)):
        c.text(32,475+i*22,line,16,'#58746B')
    c.line([(32,518),(868,518)],'#D3DED5',2)
    c.text(32,545,'ORIGINAL SCHEMATIC  /  NOT TO SCALE  /  NOT A MICROSCOPY IMAGE',15,'#58746B')
    return c,stage


def main(preview=False):
    previews=[]
    added=0
    for path in sorted((ROOT/'pages/parasites').glob('*/content.json')):
        entry=json.loads(path.read_text(encoding='utf-8'))
        managed=[i for i in entry['images'] if i.get('file')=='morphology_schematic.svg']
        if entry['images'] and not managed:
            continue
        if entry['id'] not in SPECS:
            raise ValueError(f"No specific illustration defined for {entry['id']}")
        canvas,stage=build(entry,preview)
        asset=path.parent/'morphology_schematic.svg'
        asset.write_text(canvas.svg(),encoding='utf-8')
        if not managed:
            entry['images'].append({'file':asset.name,'caption':f"{stage}. Original educational schematic — not to scale; not a microscopy image.",
                                    'credit':'Parasitic Platform 2027','license':'CC0-1.0','kind':'schematic',
                                    'source_basis':'Morphology fields and cited references in this Atlas entry.'})
            path.write_text(json.dumps(entry,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
            added+=1
        if preview:
            previews.append((entry['id'],canvas.image))
    if preview:
        from PIL import Image
        target=ROOT/'.qa/atlas_schematics'
        target.mkdir(parents=True,exist_ok=True)
        for offset in range(0,len(previews),8):
            subset=previews[offset:offset+8]
            sheet=Image.new('RGB',(1800,560*math.ceil(len(subset)/2)),'white')
            for i,(sid,image) in enumerate(subset):
                sheet.paste(image,((i%2)*900,(i//2)*560))
                image.save(target/f'{sid}.png')
            sheet.save(target/f'contact_{offset//8+1}.png')
    print(f'Added schematic metadata to {added} entries; generated {len(SPECS)} managed SVG illustrations.')


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--preview',action='store_true')
    main(parser.parse_args().preview)
