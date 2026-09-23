
from pathlib import Path
import shutil
import sys
import fitz

HERE = Path(__file__).resolve().parent
DOWNLOADS = Path.home() / "Downloads"
OUT = HERE / "assets" / "cards"
OUT.mkdir(parents=True, exist_ok=True)

patterns = [
    "FRA 1–280 completo immagini.pdf",
    "FRA 1-280 completo immagini.pdf",
    "*FRA*1*280*immagini*.pdf",
    "*FRA*1*280*image*.pdf",
]

def find_pdf():
    for pat in patterns:
        p=DOWNLOADS/pat
        if "*" not in pat and p.exists(): return p
    for pat in patterns:
        for p in DOWNLOADS.rglob(pat):
            if p.is_file(): return p
    return None

pdf=find_pdf()
if not pdf:
    print("ERRORE: non trovo 'FRA 1–280 completo immagini.pdf' in Downloads.")
    sys.exit(1)

print("PDF immagini:",pdf)
doc=fitz.open(pdf)
candidates=[]
for pno,page in enumerate(doc):
    for info in page.get_image_info(xrefs=True):
        bbox=info.get("bbox")
        xref=info.get("xref",0)
        w=info.get("width",0)
        h=info.get("height",0)
        if not bbox or not xref or w<120 or h<160:
            continue
        ratio=w/h
        if 0.62 <= ratio <= 0.80:
            candidates.append((pno,bbox[1],bbox[0],xref,w,h))

# Unique placements, sorted in reading order.
seen=set(); clean=[]
for item in sorted(candidates,key=lambda x:(x[0],x[1],x[2])):
    key=(item[0],round(item[1],1),round(item[2],1),item[3])
    if key not in seen:
        seen.add(key); clean.append(item)

print("Immagini con proporzioni da carta trovate:",len(clean))
if len(clean) < 280:
    print("\nNon estraggo nulla per evitare associazioni sbagliate.")
    print("Mandami questo numero e uno screenshot di una pagina del PDF immagini: adatteremo il ritaglio.")
    sys.exit(2)

# Prefer the first 280 in reading order. If your PDF contains exactly the 280 card images,
# this maps 001.png -> collector #1 ... 280.png -> collector #280.
for p in OUT.glob("*"):
    if p.is_file(): p.unlink()

for i,item in enumerate(clean[:280],start=1):
    xref=item[3]
    pix=fitz.Pixmap(doc,xref)
    if pix.alpha or pix.n>4:
        pix=fitz.Pixmap(fitz.csRGB,pix)
    target=OUT/f"{i:03d}.png"
    pix.save(target)

print("OK: create 280 immagini in",OUT)
print("Ora avvia l'app e controlla visivamente alcune carte: #1, #50, #100, #195, #244, #280.")
