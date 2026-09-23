from __future__ import annotations

import random
from collections import Counter, defaultdict
from pathlib import Path

import streamlit as st

import engine

ROOT = Path(__file__).resolve().parent
DATA_FILE = ROOT / "data" / "fra_cards.json"
IMAGE_DIR = ROOT / "assets" / "cards"
APP_TITLE = "Reality Fracture — Ultimate Prerelease Trainer"

st.set_page_config(page_title=APP_TITLE, page_icon="🃏", layout="wide")


st.markdown("""
<style>
/* sfondo generale */
.stApp {
    background: #F7F4EE;
    color: #1F2933;
}

/* contenitore principale */
.block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
    max-width: 1350px;
}

/* titolo */
h1, h2, h3 {
    color: #18222C;
    letter-spacing: -0.02em;
}

/* tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 0.4rem;
    border-bottom: 1px solid #DDD4C7;
}
.stTabs [data-baseweb="tab"] {
    background: transparent;
    border-radius: 10px 10px 0 0;
    padding: 0.55rem 0.9rem;
    color: #4A5563;
}
.stTabs [aria-selected="true"] {
    color: #2F6F6D !important;
    border-bottom: 2px solid #2F6F6D;
    font-weight: 600;
}

/* sidebar */
section[data-testid="stSidebar"] {
    background: #F2ECE2;
    border-right: 1px solid #E1D9CC;
}
section[data-testid="stSidebar"] .stButton > button {
    border-radius: 12px;
}

/* card pool/build/report */
.rf-card {
    background: #FFFFFF;
    border: 1px solid #E4DBCF;
    border-radius: 18px;
    overflow: hidden;
    box-shadow: 0 4px 14px rgba(28, 39, 49, 0.06);
    margin-bottom: 1rem;
}

.rf-card img {
    display: block;
    width: 100%;
}

.rf-card-body {
    padding: 0.9rem 0.95rem 1rem 0.95rem;
    border-top: 1px solid #EEE5D8;
    background: #FFFDFC;
}

.rf-card-title {
    font-size: 1.02rem;
    font-weight: 700;
    line-height: 1.2;
    color: #16202A;
    margin-bottom: 0.3rem;
}

.rf-card-meta {
    font-size: 0.82rem;
    color: #6A7380;
    line-height: 1.35;
    margin-bottom: 0.55rem;
}

.rf-card-text {
    font-size: 0.88rem;
    line-height: 1.45;
    color: #29323B;
    white-space: pre-line;
}

/* metriche / box */
div[data-testid="metric-container"] {
    background: #FFFFFF;
    border: 1px solid #E4DBCF;
    border-radius: 14px;
    padding: 0.8rem 0.9rem;
    box-shadow: 0 2px 8px rgba(28, 39, 49, 0.04);
}

/* bottoni */
.stButton > button {
    background: #FFFFFF;
    color: #1F2933;
    border: 1px solid #D7CEC1;
    border-radius: 12px;
    padding: 0.55rem 1rem;
}
.stButton > button:hover {
    border-color: #2F6F6D;
    color: #2F6F6D;
}

/* checkbox */
.stCheckbox label p {
    font-size: 0.9rem;
}

/* expander */
.streamlit-expanderHeader {
    font-weight: 600;
    color: #22303C;
}
</style>
""", unsafe_allow_html=True)



@st.cache_data
def load_data():
    return engine.load_cards(DATA_FILE)

CARDS, BY_N = load_data()
POOLS = engine.prepare_pools(CARDS, BY_N)


def image_path(c):
    n=c.get("n",0)
    if not n: return None
    for ext in ("png","jpg","jpeg","webp"):
        p=IMAGE_DIR/("%03d.%s"%(n,ext))
        if p.exists(): return p
    return None


def render_card(c, compact=False, selectable_key=None):
    p=image_path(c)
    if st.session_state.get("show_images",True) and p:
        st.image(str(p), use_container_width=True)
    foil=" · foil" if c.get("foil") else ""
    txt=(c.get("text") or "").replace("<","&lt;").replace(">","&gt;")
    html=(
        '<div class="rf-card c%s">'%c.get("rarity","C")+
        '<div class="rf-name">%s</div>'%c.get("name","?")+
        '<div class="rf-meta">%s · %s · %s%s · %s</div>'%(
            c.get("mana") or "—", c.get("type") or "", engine.RARITY_NAME.get(c.get("rarity"),c.get("rarity")),
            foil, engine.color_label(c))
    )
    if not compact and not (st.session_state.get("show_images",True) and p):
        html += '<div class="rf-text">%s</div>'%txt
    tagtxt=" · ".join(engine.tags(c)) or "—"
    html += '<div class="rf-tags">%s</div></div>'%tagtxt
    st.markdown(html,unsafe_allow_html=True)
    if selectable_key:
        st.checkbox("Nel mazzo",key=selectable_key)


def card_names(cards):
    return ", ".join(c["name"] for c in cards)


def reset_draw_state():
    for k in ["draw_signature","draw_order","draw_pos","draw_mulligans","draw_seed"]:
        st.session_state.pop(k,None)


def reset_prerelease():
    for k in list(st.session_state.keys()):
        if k.startswith(("pick_","basic_")) or k in {
            "submitted","submitted_ids","submitted_basics","lab_result"
        }:
            del st.session_state[k]
    reset_draw_state()
    st.session_state.seed=random.randrange(1,2_000_000_000)
    st.session_state.submitted=False


def submitted_build(build_pool):
    if not st.session_state.get("submitted"): return [],{}
    ids=set(st.session_state.get("submitted_ids",[]))
    selected=[c for c in build_pool if c.get("uid") in ids]
    basics=st.session_state.get("submitted_basics",{})
    return selected,basics


def gameplan_text(rep):
    spells=rep["spells_list"]
    early=sorted([c for c in spells if c.get("mv",0)<=2],key=engine.quality,reverse=True)[:4]
    mid=sorted([c for c in spells if 3<=c.get("mv",0)<=4],key=engine.quality,reverse=True)[:5]
    late=sorted([c for c in spells if c.get("mv",0)>=5],key=engine.quality,reverse=True)[:5]
    top=rep["archetypes"][0] if rep["archetypes"] else None
    paragraphs=[]
    if top:
        paragraphs.append("Il guscio assomiglia soprattutto a **%s** (indice di coerenza %.1f/10). %s"%(top["name"],top["score"],top["plan"]))
    if early:
        paragraphs.append("**Primi turni:** le carte che più probabilmente stabilizzano o mettono pressione sono %s. L'obiettivo è usare il mana ogni turno senza sacrificare le risposte necessarie."%card_names(early))
    if mid:
        paragraphs.append("**Medio gioco:** %s costituiscono il ponte principale fra sviluppo e vantaggio. Qui conviene sequenziare le minacce in modo da non sprecare rimozioni o payoff."%card_names(mid))
    if late:
        paragraphs.append("**Chiusura:** %s sono il top-end naturale. Se una di queste è la tua principale condizione di vittoria, proteggila o forza prima le risposte avversarie con minacce secondarie."%card_names(late))
    if rep["interaction"]>=6:
        paragraphs.append("Con **%d interazioni** puoi permetterti di giocare in modo più reattivo del normale: non è necessario usare una rimozione sul primo bersaglio legale; preserva le risposte premium per le minacce che superano davvero il tuo board."%rep["interaction"])
    return paragraphs


def mana_narrative(rep,basics):
    lines=[]
    if rep["sources"]:
        lines.append("Le fonti naturali attuali sono " + ", ".join("**%d %s**"%(n,engine.COLOR_NAME[c]) for c,n in rep["sources"].items() if n) + ".")
    if rep["pips"]:
        lines.append("Il carico di simboli colorati è " + ", ".join("%s %.1f"%(engine.COLOR_NAME[c],n) for c,n in rep["pips"].most_common()) + ".")
    deficits=[]
    for col,target in rep["mana_targets"].items():
        src=rep["sources"][col]
        if src<target:
            card=rep["demanding"].get(col)
            deficits.append("%s: %d fonti vs ~%d per lanciare con regolarità %s on curve"%(engine.COLOR_NAME[col],src,target,card["name"] if card else "le magie più esigenti"))
    if deficits:
        lines.append("Punti critici: " + "; ".join(deficits) + ".")
    else:
        lines.append("Non emergono deficit evidenti rispetto al benchmark dell'85% sulle magie più esigenti per simboli colorati.")
    if rep["ramp"]:
        lines.append("**Ramp vero:** %s."%card_names(rep["ramp"]))
    if rep["cyclers"]:
        lines.append("**Ciclo/fixing di terra:** %s. Queste carte riducono il rischio di screw anche se non contano come terre nella probabilità ipergeometrica pura."%card_names(rep["cyclers"]))
    rec=rep["recommended_basics"]
    if rec:
        lines.append("Come punto di partenza il modello userebbe **%d terre** totali e, mantenendo le terre non base già scelte, circa %s."%(rep["recommended_lands"],", ".join("%d %s"%(n,k) for k,n in rec.items())))
    return lines



def sequencing_notes(rep):
    notes=[]
    feat=Counter()
    for c in rep["spells_list"]:
        for f in engine.card_features(c): feat[f]+=1
    if feat["Preparato"]:
        notes.append("**Preparato:** se una creatura è già preparata, usa prima la copia della sua magia quando è utile; dopo averla lanciata la creatura si sprepara e gli effetti che la preparano di nuovo tornano ad avere valore. Evita di sprecare un effetto di ri-preparazione su una creatura già preparata.")
    if feat["Jace"]:
        notes.append("**Jace:** la fedeltà è una risorsa: −1 migliora la qualità delle pescate con sorvegliare, −3 converte fedeltà in una carta. Se il mazzo contiene payoff che richiedono Jace/Planeswalker, non consumare automaticamente tutta la fedeltà appena disponibile.")
    if feat["Soglia"] or feat["Payoff cimitero"]:
        notes.append("**Soglia/cimitero:** conta quante carte mancano alle sette prima di spendere self-mill o sorvegliare. Se la soglia è già attiva, gli enabler puri perdono valore relativo e puoi privilegiare interazione/pressione.")
    if feat["Payoff noncreature"]:
        notes.append("**Spellslinger/prodezza:** se una magia non creatura aumenta forza o genera un trigger offensivo, valuta di lanciarla prima del combattimento; se è una risposta istantanea, non sacrificare il valore di tenerla aperta solo per innescare il payoff.")
    if feat["Danno non da combattimento"]:
        notes.append("**Danno non da combattimento:** quando il mazzo premia il burn, l'ordine conta. Un danno pre-combat può accendere payoff e cambiare blocchi; una rimozione tenuta fino a dopo i blocchi può invece creare un 2-per-1. Scegli in base al board, non al trigger in astratto.")
    if feat["Ciclo terra base"]:
        notes.append("**Ciclo di terra base:** nelle mani da due terre o con colori incompleti trattalo spesso come una terra virtuale; quando il mana è già stabile conserva la carta come spell. Questo rende le probabilità di land drop del report volutamente conservative.")
    if feat["Ramp"] or feat["Duramen"]:
        notes.append("**Ramp:** il vantaggio del ramp è anticipare il top-end, non giustificare automaticamente una mano senza terre. Sequenzia gli acceleratori prima delle minacce costose quando non perdi troppo tempo sul board.")
    if feat["Guadagno vita"] and feat["Payoff vita"]:
        notes.append("**Life gain:** prova ad abbinare la fonte di vita allo stesso turno del payoff quando possibile; una fonte incidentale su una carta già giocabile vale molto più di una carta debole giocata solo per attivare il tema.")
    if feat["Segnalini +1/+1"]:
        notes.append("**Segnalini +1/+1:** distribuiscili pensando a rimozioni e combattimento: concentrare tutto su una sola creatura aumenta la pressione ma espone di più a una singola risposta; distribuirli rende il board più resiliente.")
    if any("if you control a legendary" in (c.get("text") or "").lower() for c in rep["spells_list"]):
        legends=[c for c in rep["spells_list"] if "Leggendaria" in engine.card_features(c)]
        notes.append("**Leggendari:** alcune magie cambiano costo/efficienza se controlli una permanente leggendaria. Con %d leggendari nel mazzo, pianifica il turno in modo da mettere prima il leggendario quando questo sblocca lo sconto o l'effetto."%len(legends))
    return notes

def report_strengths(rep):
    strengths=[]
    if rep["interaction"]>=5: strengths.append("densità di interazione alta")
    if rep["early"]>=5: strengths.append("buona presenza nei primi turni")
    if rep["walkers"]>=1: strengths.append("Planeswalker come minacce/engine")
    if rep["ramp"] and rep["high"]>=3: strengths.append("ramp realmente collegato al top-end")
    if rep["echoed"]>=5: strengths.append("forte contributo delle carte Coppia Eco")
    best_engine=max(rep["engines"].items(),key=lambda x:x[1]) if rep["engines"] else None
    if best_engine and best_engine[1]>=5: strengths.append("motore %s molto denso"%best_engine[0])
    return strengths


if "seed" not in st.session_state:
    st.session_state.seed=random.randrange(1,2_000_000_000)
if "submitted" not in st.session_state:
    st.session_state.submitted=False
if "show_images" not in st.session_state:
    st.session_state.show_images=True

PACKS,PROMO=engine.simulate_prerelease(st.session_state.seed,CARDS,POOLS)
ALL_PHYSICAL=[c for p in PACKS for c in p]+[PROMO]
# Le basic land aperte sono irrilevanti per il deckbuilding perché le basic sono illimitate.
BUILD_POOL=[c for c in ALL_PHYSICAL if not c.get("basic",False)]

st.title(APP_TITLE)


with st.sidebar:
    st.toggle("Mostra immagini",key="show_images")
    has_images=sum(1 for c in CARDS if image_path(c))
    st.write("Immagini locali: **%d/280**"%has_images)
    if st.button("🎲 Nuovo Prerelease",use_container_width=True):
        reset_prerelease(); st.rerun()
    st.divider()
    st.caption("Database FRA incorporato. L'app non usa API esterne durante l'uso.")

TABS=st.tabs(["📦 Pool","🧱 Costruisci 40","🧠 Report Ultimate","🎴 Simulatore pescata","🧪 Laboratorio 280","⚙️ Modello"])
tab_open,tab_build,tab_report,tab_draw,tab_lab,tab_model=TABS

with tab_open:
    st.subheader("Il tuo Prerelease")
    for i,pack in enumerate(PACKS,1):
        with st.expander("Busta %d"%i,expanded=(i==1)):
            cols=st.columns(4)
            for j,c in enumerate(pack):
                with cols[j%4]: render_card(c)
    st.markdown("### Promo Prerelease")
    cols=st.columns(4)
    with cols[0]: render_card(PROMO)

with tab_build:
    st.subheader("Costruisci il mazzo")
    st.write("Seleziona le carte dal pool e aggiungi le terre base con i contatori. Puoi inviare il mazzo solo a **40 carte esatte**.")
    bcols=st.columns(5)
    basics={}
    for i,name in enumerate(engine.BASIC_TO_COLOR):
        basics[name]=bcols[i].number_input(name,0,25,0,1,key="basic_%s"%name)

    selected=[c for c in BUILD_POOL if st.session_state.get("pick_%s"%c["uid"],False)]
    total=len(selected)+sum(int(v) for v in basics.values())
    land_total=sum(engine.is_land(c) for c in selected)+sum(int(v) for v in basics.values())
    m1,m2,m3,m4=st.columns(4)
    m1.metric("Totale","%d/40"%total)
    m2.metric("Dal pool",len(selected))
    m3.metric("Terre",land_total)
    m4.metric("Non terre",total-land_total)

    def grp(c):
        if engine.is_land(c): return "Terre non base"
        cs=c.get("colors") or []
        if not cs:return "Incolore"
        if len(cs)>1:return "Multicolore"
        return engine.COLOR_NAME[cs[0]]
    groups=defaultdict(list)
    for c in BUILD_POOL: groups[grp(c)].append(c)
    order=["Bianco","Blu","Nero","Rosso","Verde","Multicolore","Incolore","Terre non base"]
    for label in order:
        if not groups[label]: continue
        with st.expander("%s — %d"%(label,len(groups[label])),expanded=False):
            cols=st.columns(4)
            for j,c in enumerate(sorted(groups[label],key=lambda x:(x.get("mv",0),x["name"]))):
                with cols[j%4]:
                    render_card(c,compact=True,selectable_key="pick_%s"%c["uid"])

    selected=[c for c in BUILD_POOL if st.session_state.get("pick_%s"%c["uid"],False)]
    basics={x:int(st.session_state.get("basic_%s"%x,0)) for x in engine.BASIC_TO_COLOR}
    total=len(selected)+sum(basics.values())
    if total==40:
        if st.button("✅ Sottometti e genera il report Ultimate",type="primary",use_container_width=True):
            st.session_state.submitted=True
            st.session_state.submitted_ids=[c["uid"] for c in selected]
            st.session_state.submitted_basics=basics
            reset_draw_state()
            st.rerun()
    else:
        st.info("Mancano %d carte."%(40-total) if total<40 else "Hai %d carte di troppo."%(total-40))

with tab_report:
    selected,basics=submitted_build(BUILD_POOL)
    if not selected:
        st.info("Prima costruisci e sottometti un mazzo da 40 carte.")
    else:
        rep=engine.deck_report(selected,basics)
        swaps,omitted=engine.improvement_suggestions(BUILD_POOL,selected,basics)
        sideboard=engine.sideboard_suggestions(BUILD_POOL,selected)
        deck=engine.materialize_deck(selected,basics)
        sig=engine.deck_signature(selected,basics)
        consistency=engine.consistency_simulation(deck,rep["spells_list"],trials=8000,seed=int(sig[:8],16))
        castability=engine.castability_simulation(deck,rep["spells_list"],trials=2500,seed=int(sig[8:],16))

        st.subheader("Report Ultimate")
        topfit=rep["archetypes"][0] if rep["archetypes"] else None
        strengths=report_strengths(rep)
        lead="Il mazzo è un **%s**"%rep["speed"]
        if topfit: lead += " con il fit più vicino a **%s** (%.1f/10)"%(topfit["name"],topfit["score"])
        lead += "."
        if strengths: lead += " I punti strutturali più evidenti sono " + ", ".join(strengths) + "."
        st.markdown(lead)

        cols=st.columns(8)
        cols[0].metric("Struttura","%d/100"%rep["score"])
        cols[1].metric("Terre",rep["lands"])
        cols[2].metric("Creature",rep["creatures"])
        cols[3].metric("Planeswalker",rep["walkers"])
        cols[4].metric("Interazioni",rep["interaction"])
        cols[5].metric("Giocate ≤2",rep["early"])
        cols[6].metric("Echoed",rep["echoed"])
        cols[7].metric("MV medio","%.2f"%rep["avg_mv"])

        st.markdown("### 1. Diagnosi strutturale")
        for lvl,msg in rep["notes"]:
            {"ok":st.success,"warn":st.warning,"bad":st.error}[lvl](msg)
        st.write("**Curva:** "+" · ".join("%s mana: **%d**"%(k,rep["curve"].get(k,0)) for k in ["0","1","2","3","4","5","6+"]))
        st.write("**Rarità nelle magie:** "+" · ".join("%s **%d**"%(engine.RARITY_NAME.get(k,k),v) for k,v in rep["rarity"].items()))
        st.write("**Magie non creatura:** %d · **Top-end 6+:** %d"%(rep["noncreature"],rep["high"]))

        st.markdown("### 2. Piano di gioco")
        for p in gameplan_text(rep): st.markdown(p)

        st.markdown("### 3. Archetipi e motori")
        afcols=st.columns(3)
        for i,a in enumerate(rep["archetypes"][:3]):
            with afcols[i]:
                st.metric(a["name"],"%.1f/10"%a["score"])
                st.caption(a["plan"])
                if a["evidence"]: st.caption("Segnali: "+", ".join(a["evidence"][:5]))
        engines=[(k,v) for k,v in sorted(rep["engines"].items(),key=lambda x:x[1],reverse=True) if v]
        st.write("**Densità motori:** "+(" · ".join("%s **%d**"%(k,v) for k,v in engines) if engines else "nessun motore evidente"))

        if rep["synergy_pairs"]:
            with st.expander("Interazioni e sinergie specifiche fra le tue carte",expanded=True):
                for _,a,b,reasons in rep["synergy_pairs"][:8]:
                    st.markdown("**%s + %s** — %s."%(a["name"],b["name"],"; ".join(reasons)))

        st.markdown("### 4. Interazione: quantità e qualità")
        if rep["interaction_breakdown"]:
            for cat,cards in rep["interaction_breakdown"].items():
                st.write("**%s (%d):** %s"%(cat,len(cards),card_names(cards)))
        official=[c for c in rep["spells_list"] if c.get("n") in engine.OFFICIAL_KEY_INTERACTION]
        extra=[c for c in rep["interaction_cards"] if c.get("n") not in engine.OFFICIAL_KEY_INTERACTION]
        st.caption("Interazioni presenti nella lista ufficiale Wizards: %d. Ulteriori interazioni riconosciute dal testo: %d."%(len(official),len(extra)))

        st.markdown("### 5. Mana, fixing, ramp e castabilità")
        for p in mana_narrative(rep,basics): st.markdown(p)
        if castability:
            with st.expander("Carte più difficili da lanciare on curve — simulazione mana",expanded=True):
                st.caption("Monte Carlo sul mana naturale del mazzo; ignora intenzionalmente ramp, ciclo di terra e pescate extra, quindi è conservativo per i mazzi che li usano.")
                for x in castability[:8]:
                    st.write("**%s** — turno teorico %d: **%.1f%%** di avere mana naturale sufficiente"%(x["card"]["name"],x["turn"],100*x["p"]))

        st.markdown("### 6. Consistenza delle pescate")
        if consistency:
            pcols=st.columns(6)
            pcols[0].metric("Apertura 2–5 terre","%.1f%%"%(100*consistency["healthy_open"]))
            pcols[1].metric("Giocata ≤2 in 7","%.1f%%"%(100*consistency["early_open"]))
            if consistency["both_main"] is not None:
                pcols[2].metric("Entrambi colori in 7","%.1f%%"%(100*consistency["both_main"]))
            else:
                pcols[2].metric("Colori","mono/incolore")
            pcols[3].metric("3ª terra entro T3","%.1f%%"%(100*consistency["t3_land"]))
            pcols[4].metric("4ª terra entro T4","%.1f%%"%(100*consistency["t4_land"]))
            pcols[5].metric("5ª terra entro T5","%.1f%%"%(100*consistency["t5_land"]))
            st.caption("8.000 simulazioni; on the play; nessun mulligan. Flood indicativo entro 12 carte: %.1f%% · screw indicativo (≤2 terre nelle prime 10): %.1f%%."%(100*consistency["flood12"],100*consistency["screw10"]))

        st.markdown("### 7. Regole, sequencing e micro-decisioni")
        seq=sequencing_notes(rep)
        if seq:
            for n in seq: st.markdown(n)
        else:
            st.write("Nessuna meccanica del mazzo richiede una nota di sequencing particolarmente specifica oltre alle normali priorità di Limited.")

        st.markdown("### 8. Migliorie concrete nel tuo pool")
        if swaps:
            for x in swaps:
                st.markdown("**Prova %s → fuori %s.** %s."%(x["in"]["name"],x["out"]["name"],"; ".join(x["reasons"])))
        else:
            st.write("Il modello non trova uno scambio abbastanza netto da proporre automaticamente nello stesso guscio di colori.")
        if omitted:
            st.write("**Carte lasciate fuori da ricontrollare:** "+", ".join(c["name"] for c in omitted[:8])+".")

        st.markdown("### 9. Piano sideboard")
        if sideboard:
            for matchup,cards in sideboard.items():
                if cards: st.write("**%s:** %s"%(matchup,card_names(cards)))
        else:
            st.write("Nessuna carta situazionale particolarmente evidente nel pool residuo.")
        st.caption("In Sealed il pool non usato è il tuo sideboard: tra le partite puoi cambiare carte e terre base del mazzo.")

        st.markdown("### 10. Alternative del pool")
        shells=engine.candidate_shells(BUILD_POOL)[:4]
        for s in shells:
            pair=" + ".join(engine.COLOR_NAME[c] for c in s["pair"])
            with st.expander("%s — %d creature, %d interazioni, %d giocate ≤2"%(pair,s["creatures"],s["interaction"],s["early"]),expanded=False):
                st.write("Fit principale: **%s %.1f/10**."%(s["fit"]["name"],s["fit"]["score"]))
                st.write("23 candidate: "+", ".join(c["name"] for c in s["cards"]))
                nb=[c for c in BUILD_POOL if engine.is_land(c) and set(c.get("produces") or []).intersection(set(s["pair"]))]
                rb,_=engine.recommend_basics(s["cards"],nb[:3],engine.recommended_land_count(s["cards"]))
                if rb: st.caption("Base di mana indicativa con le prime terre non base compatibili: "+", ".join("%d %s"%(n,k) for k,n in rb.items()))
        st.caption("Sono gusci da ricontrollare, non una verità assoluta: il motore non sostituisce la valutazione contestuale carta-per-carta durante una partita.")

        st.markdown("### 11. Lista completa")
        with st.expander("Vedi le 40 carte"):
            for c in sorted(selected,key=lambda x:(engine.is_land(x),x.get("mv",0),x["name"])):
                st.write("• %s — %s — %s — %s"%(c["name"],c.get("mana") or "terra",engine.RARITY_NAME.get(c.get("rarity"),c.get("rarity")),", ".join(engine.tags(c)) or "—"))
            for b,n in basics.items():
                if n: st.write("• %s ×%d"%(b,n))

        md=engine.report_markdown(rep,basics,swaps)
        st.download_button("Scarica report .md",data=md,file_name="reality_fracture_report.md",mime="text/markdown",use_container_width=True)

with tab_draw:
    selected,basics=submitted_build(BUILD_POOL)
    if not selected:
        st.info("Sottometti prima un mazzo da 40 carte: il simulatore pesca esattamente da quella lista.")
    else:
        rep=engine.deck_report(selected,basics)
        deck=engine.materialize_deck(selected,basics)
        sig=engine.deck_signature(selected,basics)
        if st.session_state.get("draw_signature")!=sig:
            st.session_state.draw_signature=sig
            st.session_state.draw_seed=random.randrange(1,2_000_000_000)
            rng=random.Random(st.session_state.draw_seed)
            st.session_state.draw_order=rng.sample(deck,len(deck))
            st.session_state.draw_pos=7
            st.session_state.draw_mulligans=0

        st.subheader("Simulatore di pescata")
        mode=st.radio("Posizione",["Inizio io (play)","Pesco io per primo (draw)"],horizontal=True,key="draw_mode")
        b1,b2,b3=st.columns(3)
        if b1.button("🔀 Nuova mano da 7",use_container_width=True):
            st.session_state.draw_seed=random.randrange(1,2_000_000_000)
            rng=random.Random(st.session_state.draw_seed)
            st.session_state.draw_order=rng.sample(deck,len(deck))
            st.session_state.draw_pos=7
            st.session_state.draw_mulligans=0
            st.rerun()
        if b2.button("↩️ Mulligan: nuove 7",use_container_width=True):
            st.session_state.draw_seed=random.randrange(1,2_000_000_000)
            rng=random.Random(st.session_state.draw_seed)
            st.session_state.draw_order=rng.sample(deck,len(deck))
            st.session_state.draw_pos=7
            st.session_state.draw_mulligans=st.session_state.get("draw_mulligans",0)+1
            st.rerun()
        if b3.button("➕ Pesca la prossima",use_container_width=True,disabled=st.session_state.draw_pos>=40):
            st.session_state.draw_pos+=1
            st.rerun()

        order=st.session_state.draw_order
        pos=st.session_state.draw_pos
        opening=order[:7]
        drawn=order[7:pos]
        assess=engine.hand_assessment(opening,rep["spells_list"])
        st.markdown("### Mano iniziale")
        cols=st.columns(4)
        for i,c in enumerate(opening):
            with cols[i%4]: render_card(c,compact=True)
        status={"Strutturalmente sana":st.success,"Alto rischio":st.error,"Borderline / dipende dal piano":st.warning}
        status[assess["label"]]("%s — %d terre; %d giocate a costo ≤2, di cui %d già castabili con le terre in mano."%(assess["label"],assess["lands"],len(assess["early"]),len(assess["castable_early"])))
        if assess["missing"]:
            st.caption("Colori del mazzo non ancora rappresentati dalle terre della mano: "+", ".join(engine.COLOR_NAME[c] for c in assess["missing"]))
        mulls=st.session_state.get("draw_mulligans",0)
        if mulls:
            st.info("London mulligan: hai mulligato %d volta/e. In una partita reale, dopo aver deciso di tenere, metteresti in fondo %d carta/e dalla mano di sette."%(mulls,mulls))

        if drawn:
            st.markdown("### Pescate successive")
            for i,c in enumerate(drawn,1):
                if mode.startswith("Inizio"):
                    turn=i+1
                else:
                    turn=i
                st.write("**Turno %d — pescata %d:** %s"%(turn,i,c["name"]))
            with st.expander("Mostra le carte pescate"):
                cols=st.columns(4)
                for i,c in enumerate(drawn):
                    with cols[i%4]: render_card(c,compact=True)

        st.markdown("### Statistiche della lista")
        cons=engine.consistency_simulation(deck,rep["spells_list"],trials=10000,seed=int(sig[:8],16))
        cc=st.columns(5)
        cc[0].metric("Mano 2–5 terre","%.1f%%"%(100*cons["healthy_open"]))
        cc[1].metric("Giocata ≤2 in 7","%.1f%%"%(100*cons["early_open"]))
        if cons["both_main"] is not None: cc[2].metric("Entrambi colori in 7","%.1f%%"%(100*cons["both_main"]))
        else: cc[2].metric("Entrambi colori","—")
        cc[3].metric("4ª terra entro T4","%.1f%%"%(100*cons["t4_land"]))
        cc[4].metric("Screw ≤2/10","%.1f%%"%(100*cons["screw10"]))

with tab_lab:
    st.subheader("Laboratorio sulle 280 carte")
    st.write("Seleziona qualsiasi gruppo di carte dell'espansione. Il laboratorio tratta quelle carte come un **nucleo** e cerca colori, motori, sinergie e supporti intelligenti nel resto di Reality Fracture.")
    options={"#%03d — %s"%(c["n"],c["name"]):c for c in CARDS}
    chosen_labels=st.multiselect("Carte del nucleo",list(options.keys()),placeholder="Scrivi il nome di una carta…")
    core=[options[x] for x in chosen_labels]
    if core:
        st.caption("Nucleo selezionato: %d carte."%len(core))
        with st.expander("Anteprima nucleo",expanded=False):
            cols=st.columns(4)
            for i,c in enumerate(core):
                with cols[i%4]: render_card(c,compact=True)
        if st.button("🧪 Analizza questo nucleo",type="primary",use_container_width=True):
            st.session_state.lab_result=[c["n"] for c in core]

    if st.session_state.get("lab_result"):
        core=[BY_N[n] for n in st.session_state.lab_result]
        lr=engine.lab_report(core,CARDS)
        st.markdown("### Scheda strategica")
        top=lr["top_fit"]
        st.markdown("Il nucleo ha il fit più vicino a **%s** con indice **%.1f/10**. %s"%(top["name"],top["score"],top["plan"]))
        if lr["shell_colors"]:
            st.write("**Guscio cromatico da provare per primo:** "+" + ".join(engine.COLOR_NAME[c] for c in lr["shell_colors"]))
        if lr["colors"]:
            st.write("**Colori richiesti dal nucleo:** "+" · ".join("%s %d"%(engine.COLOR_NAME[c],n) for c,n in lr["colors"].most_common()))

        if lr["synergy_pairs"]:
            st.markdown("#### Sinergie interne")
            for _,a,b,reasons in lr["synergy_pairs"][:8]:
                st.write("**%s + %s** — %s."%(a["name"],b["name"],"; ".join(reasons)))
        else:
            st.write("Le carte selezionate non formano ancora una combo/sinergia testuale forte: possono comunque essere un nucleo di pura potenza o curva.")

        st.markdown("#### Come costruire intorno a queste carte")
        feat=lr["features"]
        advice=[]
        if feat["Payoff noncreature"]: advice.append("Aumenta le magie non creatura economiche: i payoff spellslinger vogliono molte attivazioni senza perdere presenza sul board.")
        if feat["Payoff cimitero"] or feat["Soglia"]: advice.append("Aggiungi auto-mill/sorvegliare e carte economiche che finiscono naturalmente nel cimitero; evita enabler che non fanno altro.")
        if feat["Jace"]: advice.append("Cerca una massa critica di Rafforza Jace e almeno qualche carta che trasformi fedeltà/Jace in vantaggio reale.")
        if feat["Payoff vita"]: advice.append("Preferisci fonti di guadagno vita ripetibili o incidentali su carte già giocabili, non spell deboli che fanno solo vita.")
        if feat["Payoff segnalini"]: advice.append("Aumenta i modi ripetibili di mettere segnalini +1/+1 e le creature che sfruttano subito la crescita.")
        if feat["Payoff danno non-combat"]: advice.append("Il burn che rimuove creature è l'enabler migliore: fa progredire il motore senza sacrificare tempo o carte.")
        if feat["Top-end"]>=2: advice.append("Il nucleo è pesante: servono 17–18 terre oppure 3+ veri ramp/fixing/ciclo terra per non intasare la mano.")
        if not advice: advice.append("Costruisci prima una curva sana e abbastanza interazione; usa le sinergie come moltiplicatore, non come motivo per includere carte deboli.")
        for a in advice: st.write("• "+a)

        st.markdown("#### Carte dell'espansione che completano meglio il nucleo")
        for cat,cards in lr["categories"].items():
            if not cards: continue
            with st.expander("%s — %d suggerimenti"%(cat,len(cards)),expanded=(cat=="Supporto sinergico")):
                for c in cards:
                    reasons=[]
                    for x in core: reasons.extend(engine.synergy_reason(c,x))
                    suffix=(" — "+reasons[0]) if reasons else ""
                    st.write("**%s** (%s, %s)%s"%(c["name"],c.get("mana") or "—",engine.RARITY_NAME.get(c.get("rarity"),c.get("rarity")),suffix))

        st.markdown("#### Blueprint Limited")
        st.write("Per un mazzo da 40 costruito attorno a questo nucleo partirei da **17 terre, 14–17 creature, 4–6 interazioni**, poi modificherei la curva in base all'archetipo: più drop a 2 per aggro/tempo; più ramp e top-end per Konstrari; più spell economiche per prodezza; più enabler/payoff bilanciati per cimitero, Jace o life gain.")

with tab_model:
    st.subheader("Cosa considera il modello")
    st.markdown("""
**Busta di gioco (14 carte):** 5–6 comuni; 1 non comune; 1 comune/non comune; 3 carte Coppia Eco; 1 rara/mitica; 1 foil; 1 terra. Una Special Guest sostituisce una comune in circa 1 busta su 55.

**Coppie Eco:** due delle tre carte Echoed sono le due metà della stessa coppia e della stessa rarità. Per la rarità funzionale il trainer usa gli upgrade pubblicati da Arena (~1 rara ogni 10 Echoed; una rara diventa mitica ~1 volta ogni 5,7), ottenendo circa 90,0% non comune / 8,25% rara / 1,75% mitica.

**Terra:** 43,6% dual nonfoil + 10,9% dual foil = **54,5% dual comune** nello slot terra.

**Prerelease:** 6 Play Booster + 1 promo foil; il mazzo Sealed usa **40 carte** e qualunque numero di terre base.

**Curva ufficiale di riferimento:** 1–2 carte a 1 mana; 7–8 a 2; 5–6 a 3; 3–4 a 4; 2–3 a 5; 0–1 a 6; 17 terre. Il trainer la tratta come riferimento, non come legge: ramp, ciclo di terra, aggro e controllo possono giustificare deviazioni.
""")
    st.markdown("### Cosa analizza nel mazzo")
    st.write("Curva, terre, fonti colorate, simboli di mana, richieste doppie/triple, ramp, fixing, ciclo di terra, creature, evasione, rimozioni, counter, bounce, fight/bite, sweeper, vantaggio carte, Planeswalker, top-end, sideboard, dieci archetipi ufficiali, enabler/payoff e sinergie specifiche fra coppie di carte.")
    st.markdown("### Limiti dichiarati")
    st.warning("Le categorie Booster Fun pubblicate da Wizards come “meno dell'1%” non consentono una collation identitaria perfetta al decimale. Anche la distribuzione R/M della promo Prerelease non è pubblicata nel dettaglio. Il trainer usa assunzioni centrali esplicite per quei soli pezzi.")
    st.caption("Il punteggio di struttura e gli indici di fit sono euristiche del trainer, non valutazioni ufficiali Wizards né una tier list definitiva.")
    st.markdown("Fonti ufficiali: [Collecting Reality Fracture](https://magic.wizards.com/en/news/feature/collecting-reality-fracture) · [Reality Fracture Prerelease Guide](https://magic.wizards.com/en/news/feature/reality-fracture-prerelease-guide) · [Reality Fracture Mechanics](https://magic.wizards.com/en/news/feature/reality-fracture-mechanics)")
