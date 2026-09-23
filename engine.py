from __future__ import annotations

import hashlib
import json
import math
import random
import re
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

COLOR_NAME = {"W":"Bianco","U":"Blu","B":"Nero","R":"Rosso","G":"Verde"}
COLOR_ORDER = "WUBRG"
BASIC_TO_COLOR = {"Pianura":"W","Isola":"U","Palude":"B","Montagna":"R","Foresta":"G"}
RARITY_NAME = {"C":"Comune","U":"Non comune","R":"Rara","M":"Mitica","SPG":"Special Guest"}

# 43 Echoed Pairs, 86 carte #195–280.
ECHO_PAIRS = [
    (195,242),(196,227),(197,260),(198,230),(199,248),(200,231),(201,217),
    (202,234),(203,275),(204,236),(205,214),(206,253),(207,238),(208,255),
    (209,269),(210,226),(211,243),(212,244),(213,258),(215,271),(216,276),
    (218,235),(219,265),(220,251),(221,252),(222,280),(223,254),(224,267),
    (225,241),(228,245),(229,259),(232,262),(233,274),(237,266),(240,256),
    (246,261),(247,273),(249,263),(250,264),(257,270),(272,279),(277,278),
    (239,268),
]

# Play Booster, gameplay-identity model.
# Echo rarity: Arena pubblica upgrade U->R ~1:10 e R->M ~1:5.7. Collassando i trattamenti
# sull'identità della carta: U≈90%, R≈8.246%, M≈1.754%.
ECHO_RARITY = {"U":0.9000, "R":0.08246, "M":0.01754}
# Slot R/M del Play Booster: sommando le categorie pubblicate e il residuo di arrotondamento.
MAIN_RM = {"R":0.833, "M":0.167}
# Foil: 97.2% esplicitamente pubblicato + 2.8% Booster Fun con rarità <1%; stima centrale.
FOIL_RARITY = {
    "C":0.495,
    "U":0.405 + 0.028*(2/9),
    "R":0.060 + 0.028*(4/9),
    "M":0.012 + 0.028*(3/9),
}
# Promo prerelease: extra R/M garantita, rapporto non pubblicato. Assunzione esplicita.
PROMO_RM = {"R":0.831, "M":0.169}

# Elenco ufficiale Wizards delle 34 key-removal / interaction cards della guida Prerelease.
OFFICIAL_KEY_INTERACTION = {
    15,17,18,22,24,
    25,30,31,35,36,46,
    50,54,56,58,66,67,68,233,235,240,
    74,82,84,89,94,95,96,255,
    99,101,102,115,269,
}

# Archetipi ufficiali della guida Prerelease. I pesi sono un modello interno di "fit",
# non una tier list e non un'affermazione Wizards sulla forza relativa.
ARCHETYPES = {
    "WU": {
        "name":"Bianco–Blu Fatorocca — aggro sorvegliare",
        "colors":("W","U"),
        "plan":"Curva aggressiva, sorvegliare/scry, pedine Jace e payoff che trasformano selezione e informazione in pressione.",
        "tags":{"Sorvegliare":2.0,"Jace":1.6,"Evasione":0.8,"Pedine":0.6,"Segnalini +1/+1":0.4},
        "anchors":[24,39,129,133,146,218],
    },
    "UB": {
        "name":"Blu–Nero Teorix — cimitero e soglia",
        "colors":("U","B"),
        "plan":"Riempire il cimitero in modo utile, raggiungere sette carte e convertire soglia/recursion in vantaggio.",
        "tags":{"Cimitero":2.2,"Sorvegliare":1.1,"Vantaggio carte":0.7,"Morte/Recupero":0.8},
        "anchors":[46,70,143,156,240],
    },
    "BR": {
        "name":"Nero–Rosso Pennarguta — danno non da combattimento",
        "colors":("B","R"),
        "plan":"Rimozioni e burn che alimentano payoff da danno non da combattimento e chiudono la partita mentre controllano il board.",
        "tags":{"Danno non da combattimento":2.4,"Interazione":1.1,"Magie non creatura":0.6},
        "anchors":[82,84,136,150,151,164],
    },
    "RG": {
        "name":"Rosso–Verde Konstrari — ramp",
        "colors":("R","G"),
        "plan":"Accelerare il mana con Duramen/ramp, tollerare più top-end e sfruttare creature ad alto impatto prima del normale.",
        "tags":{"Ramp/Fixing":2.5,"Top-end":1.0,"Creatura":0.3},
        "anchors":[119,127,139,165,167],
    },
    "GW": {
        "name":"Verde–Bianco Germoglioterso — vita e segnalini",
        "colors":("G","W"),
        "plan":"Guadagnare vita ripetutamente, convertire il life gain in segnalini/valore e mantenere pressione sul board.",
        "tags":{"Guadagno vita":2.0,"Segnalini +1/+1":1.8,"Creatura":0.3},
        "anchors":[10,124,130,161],
    },
    "WB": {
        "name":"Bianco–Nero — attrito di Liliana",
        "colors":("W","B"),
        "plan":"Piccole creature, scambi, morte e recupero: trasformare risorse consumabili in vantaggio progressivo.",
        "tags":{"Morte/Recupero":2.1,"Cimitero":1.0,"Interazione":0.7,"Pedine":0.4},
        "anchors":[4,61,158,270],
    },
    "UR": {
        "name":"Blu–Rosso — prodezza / spellslinger di Chandra",
        "colors":("U","R"),
        "plan":"Alta densità di magie non creatura economiche, tempo e payoff che crescono o generano valore lanciando spell.",
        "tags":{"Magie non creatura":2.3,"Interazione":0.8,"Vantaggio carte":0.6,"Sorvegliare":0.3},
        "anchors":[46,89,126,253,256,275],
    },
    "BG": {
        "name":"Nero–Verde — bestiario di Garruk",
        "colors":("B","G"),
        "plan":"Creature che producono valore entrando/morendo, removal e recursion: midrange resistente agli scambi.",
        "tags":{"Morte/Recupero":1.6,"Interazione":0.9,"Creatura":0.7,"Vantaggio carte":0.5},
        "anchors":[62,144,236,271],
    },
    "RW": {
        "name":"Rosso–Bianco — esercito di Ajani",
        "colors":("R","W"),
        "plan":"Curva bassa, pedine Cadet, segnalini e pressione; chiudere prima che il top-end avversario domini.",
        "tags":{"Pedine":1.8,"Segnalini +1/+1":1.5,"Creatura":0.5,"Combat trick":0.5},
        "anchors":[12,163,245,274],
    },
    "GU": {
        "name":"Verde–Blu — maestria di Jace",
        "colors":("G","U"),
        "plan":"Rafforzare Jace ripetutamente e monetizzare la pedina planeswalker con payoff e protezione.",
        "tags":{"Jace":2.4,"Sorvegliare":0.8,"Vantaggio carte":0.6,"Ramp/Fixing":0.4},
        "anchors":[25,109,141,273],
    },
}

SPG = [
    {"name":"Eye of Ugin","mana":"","mv":0,"type":"Legendary Land","text":"Colorless Eldrazi spells you cast cost {2} less to cast. {7}, {T}: Search your library for a colorless creature card, reveal it, put it into your hand, then shuffle.","colors":[]},
    {"name":"Austere Command","mana":"4WW","mv":6,"type":"Sorcery","text":"Choose two — destroy all artifacts; destroy all enchantments; destroy all creatures with mana value 3 or less; destroy all creatures with mana value 4 or greater.","colors":["W"]},
    {"name":"Flesh Duplicate","mana":"UU","mv":2,"type":"Creature — Shapeshifter Rebel","text":"You may have this creature enter as a copy of any creature on the battlefield, except it has vanishing 3 if that creature doesn't have vanishing. 0/0","colors":["U"]},
    {"name":"Consign to Memory","mana":"U","mv":1,"type":"Instant","text":"Replicate {1}. Counter target triggered ability or colorless spell.","colors":["U"]},
    {"name":"Sublime Epiphany","mana":"4UU","mv":6,"type":"Instant","text":"Choose one or more — counter target spell; counter target activated or triggered ability; return target nonland permanent to its owner's hand; create a token copy of target creature you control; target player draws a card.","colors":["U"]},
    {"name":"Consider","mana":"U","mv":1,"type":"Instant","text":"Surveil 1. Draw a card.","colors":["U"]},
    {"name":"Necrodominance","mana":"BBB","mv":3,"type":"Legendary Enchantment","text":"Skip your draw step. At the beginning of your end step, you may pay any amount of life. If you do, draw that many cards. Your maximum hand size is five. If a card or token would be put into your graveyard from anywhere, exile it instead.","colors":["B"]},
    {"name":"Mind Twist","mana":"XB","mv":1,"type":"Sorcery","text":"Target player discards X cards at random.","colors":["B"]},
    {"name":"Splinter Twin","mana":"2RR","mv":4,"type":"Enchantment — Aura","text":"Enchant creature. Enchanted creature has “{T}: Create a token that's a copy of this creature, except it has haste. Exile that token at the beginning of the next end step.”","colors":["R"]},
    {"name":"Root Maze","mana":"G","mv":1,"type":"Enchantment","text":"Artifacts and lands enter the battlefield tapped.","colors":["G"]},
]


def load_cards(path):
    rows = json.loads(Path(path).read_text(encoding="utf-8"))
    by_n = {c["n"]: c for c in rows}
    # Correzioni di source production non estraibili bene dal PDF testuale.
    for n, produces in {187:["G"],188:list(COLOR_ORDER),191:["U"]}.items():
        if n in by_n:
            by_n[n]["produces"] = produces
            if n == 188:
                by_n[n]["flex_source"] = True
    return rows, by_n


def weighted_key(rng, weights):
    return rng.choices(list(weights), weights=list(weights.values()), k=1)[0]


def is_land(c):
    return "land" in (c.get("type") or "").lower() or c.get("basic", False)


def is_creature(c):
    return "creature" in (c.get("type") or "").lower()


def is_planeswalker(c):
    return "planeswalker" in (c.get("type") or "").lower()


def is_artifact(c):
    return "artifact" in (c.get("type") or "").lower()


def main_cost(c):
    return (c.get("mana") or "").split("//")[0].strip()


def color_label(c):
    if is_land(c):
        p = c.get("produces") or []
        if p:
            if c.get("flex_source"):
                return "Terra (qualsiasi colore)"
            return "Terra (" + "/".join(COLOR_NAME[x] for x in p) + ")"
        return "Terra"
    cs = c.get("colors") or []
    if not cs:
        return "Incolore"
    return "/".join(COLOR_NAME[x] for x in cs)


def text_lower(c):
    return (c.get("text") or "").lower()


def type_lower(c):
    return (c.get("type") or "").lower()


def card_features(c):
    text = text_lower(c)
    typ = type_lower(c)
    f = set()
    n = c.get("n", 0)

    if is_creature(c): f.add("Creatura")
    if is_planeswalker(c): f.add("Planeswalker")
    if is_land(c): f.add("Terra")
    if "legendary" in typ: f.add("Leggendaria")
    if is_artifact(c): f.add("Artefatto")

    if n in OFFICIAL_KEY_INTERACTION:
        f.add("Interazione")
        f.add("Interazione ufficiale")

    if re.search(r"destroy target", text) or re.search(r"exile target", text):
        f.update(["Interazione","Hard removal"])
    if re.search(r"deals? \d+ damage to target (?:creature|planeswalker|creature or planeswalker|any target)", text):
        f.update(["Interazione","Damage removal","Danno non da combattimento"])
    if re.search(r"all creatures get -\d+/-\d+", text) or ("destroy all creatures" in text) or ("exile all creatures" in text):
        f.update(["Interazione","Sweeper"])
    if "counter target spell" in text or "counter target triggered ability" in text:
        f.update(["Interazione","Counterspell"])
    if re.search(r"return target (?:creature|nonland permanent|permanent).*hand", text):
        f.update(["Interazione","Bounce"])
    if "deals damage equal to its power to target creature or planeswalker" in text or "fight target" in text:
        f.update(["Interazione","Fight/Bite"])
    if "destroy target creature with flying" in text:
        f.update(["Interazione","Anti-volante"])
    if "destroy target artifact or enchantment" in text:
        f.update(["Interazione","Odio artefatto/incantesimo"])
    if "discard" in text and ("opponent" in text or "each opponent" in text or "target player" in text):
        f.add("Scarto")
    if "gets -" in text and "target creature" in text:
        f.update(["Interazione","Debuff"])

    if any(x in text for x in ["draw a card","draw two cards","draw three cards","draw cards equal","put that card into your hand","put it into your hand"]):
        f.add("Vantaggio carte")
    if any(x in text for x in ["surveil", "scry", "draw a card, then discard", "discard a card: draw", "exile the top card of your library"]):
        f.add("Selezione carte")

    if any(x in text for x in ["flying","menace","can't be blocked"]): f.add("Evasione")
    if "trample" in text: f.add("Travolgere")
    if "deathtouch" in text: f.add("Tocco letale")
    if "lifelink" in text: f.add("Legame vitale")
    if "vigilance" in text: f.add("Cautela")
    if "haste" in text: f.add("Rapidità")
    if "reach" in text: f.add("Raggiungere")
    if "ward" in text: f.add("Protezione")

    if "empower jace" in text or "jace token" in text: f.add("Jace")
    if "surveil" in text: f.add("Sorvegliare")
    if "threshold" in text: f.add("Soglia")
    if "mill " in text or "graveyard" in text: f.add("Cimitero")
    if "whenever you surveil" in text: f.add("Payoff sorvegliare")
    if "seven or more cards in your graveyard" in text or "threshold" in text: f.add("Payoff cimitero")
    if "mill " in text or "surveil" in text: f.add("Enabler cimitero")

    if "noncombat damage" in text or "damage to each opponent" in text or "damage to target player" in text:
        f.add("Danno non da combattimento")
    if "whenever" in text and "noncombat damage" in text:
        f.add("Payoff danno non-combat")

    if (("gain" in text and "life" in text) or "lifelink" in text): f.add("Guadagno vita")
    if "whenever you gain life" in text: f.add("Payoff vita")
    if "+1/+1 counter" in text: f.add("Segnalini +1/+1")
    if "if one or more +1/+1 counters" in text or "with a +1/+1 counter" in text:
        f.add("Payoff segnalini")

    if "heartwood" in text: f.update(["Ramp/Fixing","Duramen"])
    if "basic landcycling" in text: f.update(["Fixing","Ciclo terra base"])
    if "search your library for a basic land" in text:
        if "battlefield tapped" in text: f.update(["Ramp/Fixing","Ramp"])
        else: f.update(["Fixing","Ciclo/terra in mano"])
    if "add one mana of any color" in text or "add one mana" in text or re.search(r": add\s*\.?", text):
        if not is_land(c): f.add("Ramp/Fixing")
    if is_land(c) and len(c.get("produces") or []) >= 2: f.add("Fixing")
    if c.get("flex_source"): f.add("Fixing")

    if any(x in text for x in ["return target creature card from your graveyard","return target permanent card from your graveyard","from your graveyard to the battlefield"]):
        f.update(["Morte/Recupero","Recursion"])
    if "whenever a creature you control dies" in text or "whenever another creature you control dies" in text:
        f.update(["Morte/Recupero","Payoff morte"])
    if "sacrifice" in text: f.add("Sacrificio")

    if "prowess" in text or "whenever you cast a noncreature spell" in text:
        f.update(["Magie non creatura","Payoff noncreature"])
    if not is_creature(c) and not is_land(c):
        f.add("Magia non creatura")

    if "cadet" in text or "creature token" in text or "create a token" in text:
        f.add("Pedine")
    if "whenever" in text and "token" in text: f.add("Payoff pedine")

    if "prepared" in text: f.add("Preparato")
    if "becomes prepared" in text or "target creature becomes prepared" in text: f.add("Ri-prepara")

    # Combat tricks: pump/keyword fino a fine turno, salvo removal già classificato.
    if "until end of turn" in text and any(x in text for x in ["gets +","gains flying","gains reach","gains trample","gains first strike","gains deathtouch"]):
        f.add("Combat trick")

    mv = c.get("mv", 0)
    if is_creature(c) and mv <= 2: f.add("Drop precoce")
    if mv >= 5 and (is_creature(c) or is_planeswalker(c)): f.add("Top-end")
    if mv >= 6: f.add("Costosa")

    # Threat markers: descriptive, not a full tier list.
    if is_planeswalker(c): f.add("Minaccia ad alto impatto")
    if is_creature(c) and mv >= 4 and ("Evasione" in f or "Travolgere" in f or "Protezione" in f):
        f.add("Finisher")
    if c.get("rarity") in {"R","M"} and ("Vantaggio carte" in f or "Interazione" in f or "Finisher" in f or is_planeswalker(c)):
        f.add("Minaccia ad alto impatto")

    return f


def tags(c):
    # Compact set for UI.
    preferred = [
        "Interazione","Vantaggio carte","Evasione","Jace","Sorvegliare","Cimitero",
        "Danno non da combattimento","Guadagno vita","Segnalini +1/+1","Ramp/Fixing",
        "Morte/Recupero","Magie non creatura","Pedine","Preparato","Planeswalker",
        "Combat trick","Fixing","Ciclo terra base"
    ]
    f = card_features(c)
    return [x for x in preferred if x in f]


def quality(c):
    """Heuristic Limited structural value. Not a definitive card tier."""
    f = card_features(c)
    s = 50.0
    s += {"C":0,"U":2,"R":4,"M":6,"SPG":4}.get(c.get("rarity"),0)
    if "Interazione" in f: s += 12
    if "Hard removal" in f: s += 3
    if "Sweeper" in f: s += 5
    if "Vantaggio carte" in f: s += 7
    if "Evasione" in f: s += 4
    if "Planeswalker" in f: s += 7
    if "Ramp/Fixing" in f: s += 3
    if "Minaccia ad alto impatto" in f: s += 4
    if is_creature(c) and 2 <= c.get("mv",0) <= 4: s += 3
    if c.get("mv",0) >= 7 and "Ramp/Fixing" not in f: s -= 3
    if "Combat trick" in f and "Vantaggio carte" not in f: s -= 1
    return s


def clone(c, uid, pack, slot, foil=False):
    x = dict(c)
    x.update(uid=uid, pack=pack, slot=slot, foil=foil, basic=False)
    return x


def basic(name, uid=None):
    return {
        "n":0,"name":name,"mana":"","mv":0,"colors":[],"type":"Basic Land",
        "text":"","rarity":"C","echoed":False,"common_dual":False,
        "produces":[BASIC_TO_COLOR[name]],"uid":uid or "BASIC-"+name,"pack":0,
        "slot":"Terra base","foil":False,"basic":True,
    }


def spg_card(rng, pack):
    x = dict(rng.choice(SPG))
    x.update(n=0,rarity="SPG",echoed=False,common_dual=False,produces=[],
             uid="P%s-SPG-%s"%(pack,rng.random()),pack=pack,slot="Special Guest",foil=False,basic=False)
    return x


def prepare_pools(cards, by_n):
    common = [c for c in cards if c["rarity"]=="C" and not c["common_dual"]]
    uncommon = [c for c in cards if c["rarity"]=="U" and c["n"]<=194]
    rare = [c for c in cards if c["rarity"]=="R" and c["n"]<=194]
    mythic = [c for c in cards if c["rarity"]=="M" and c["n"]<=194]
    duals = [c for c in cards if c["common_dual"]]
    echo = {r:[c for c in cards if c["echoed"] and c["rarity"]==r] for r in ("U","R","M")}
    pair_by_rarity = defaultdict(list)
    for a,b in ECHO_PAIRS:
        ca, cb = by_n[a], by_n[b]
        if ca["rarity"] != cb["rarity"]:
            raise RuntimeError("Echo pair rarity mismatch: %s/%s"%(a,b))
        pair_by_rarity[ca["rarity"]].append((ca,cb))
    foil = {
        "C":common,
        "U":[c for c in cards if c["rarity"]=="U"],
        "R":[c for c in cards if c["rarity"]=="R"],
        "M":[c for c in cards if c["rarity"]=="M"],
    }
    checks = (len(common),len(uncommon),len(rare),len(mythic),len(duals),len(echo["U"]),len(echo["R"]),len(echo["M"]))
    if checks != (71,43,50,20,10,66,14,6):
        raise RuntimeError("Sanity check database fallito: %r"%(checks,))
    return dict(common=common,uncommon=uncommon,rare=rare,mythic=mythic,duals=duals,echo=echo,pairs=pair_by_rarity,foil=foil)


def simulate_pack(rng, packno, pools):
    out = []
    commons = rng.sample(pools["common"],6)
    spg_index = rng.randrange(6) if rng.random() < 1/55 else None
    for i,c in enumerate(commons):
        if i == spg_index:
            out.append(spg_card(rng,packno))
        else:
            out.append(clone(c,"P%s-C%s-%s"%(packno,i,rng.random()),packno,"Comune"))
    out.append(clone(rng.choice(pools["uncommon"]),"P%s-U-%s"%(packno,rng.random()),packno,"Non comune"))
    cu_pool = pools["common"] if rng.random() < 0.23 else pools["uncommon"]
    out.append(clone(rng.choice(cu_pool),"P%s-CU-%s"%(packno,rng.random()),packno,"Comune/Non comune"))
    er = weighted_key(rng,ECHO_RARITY)
    a,b = rng.choice(pools["pairs"][er])
    out.append(clone(a,"P%s-PAIR-A-%s"%(packno,rng.random()),packno,"Coppia Eco"))
    out.append(clone(b,"P%s-PAIR-B-%s"%(packno,rng.random()),packno,"Coppia Eco"))
    er3 = weighted_key(rng,ECHO_RARITY)
    out.append(clone(rng.choice(pools["echo"][er3]),"P%s-E3-%s"%(packno,rng.random()),packno,"Eco singola"))
    rr = weighted_key(rng,MAIN_RM)
    out.append(clone(rng.choice(pools["rare"] if rr=="R" else pools["mythic"]),
                     "P%s-RM-%s"%(packno,rng.random()),packno,"Rara/Mitica"))
    fr = weighted_key(rng,FOIL_RARITY)
    out.append(clone(rng.choice(pools["foil"][fr]),"P%s-FOIL-%s"%(packno,rng.random()),packno,"Foil",foil=True))
    if rng.random() < 0.545:
        out.append(clone(rng.choice(pools["duals"]),"P%s-LAND-%s"%(packno,rng.random()),packno,"Terra doppia"))
    else:
        out.append(basic(rng.choice(list(BASIC_TO_COLOR)),uid="P%s-BASIC-%s"%(packno,rng.random())))
    return out


def simulate_prerelease(seed, cards, pools):
    rng = random.Random(seed)
    packs = [simulate_pack(rng,i,pools) for i in range(1,7)]
    pr = weighted_key(rng,PROMO_RM)
    promo_pool = [c for c in cards if c["rarity"]==pr]
    promo = clone(rng.choice(promo_pool),"PROMO-%s"%rng.random(),0,"Promo Prerelease",foil=True)
    return packs,promo


def comb_prob_at_least(deck_n, success_n, draws, k=1):
    if success_n <= 0: return 0.0
    draws = min(draws, deck_n)
    den = math.comb(deck_n,draws)
    p = 0.0
    for i in range(k,min(success_n,draws)+1):
        if draws-i <= deck_n-success_n:
            p += math.comb(success_n,i)*math.comb(deck_n-success_n,draws-i)/den
    return p


def prob_exact_success(deck_n, success_n, draws, k):
    if k<0 or k>success_n or k>draws or draws-k>deck_n-success_n: return 0.0
    return math.comb(success_n,k)*math.comb(deck_n-success_n,draws-k)/math.comb(deck_n,draws)


def prob_land_range(lands, low, high, hand=7):
    return sum(prob_exact_success(40,lands,hand,k) for k in range(low,high+1))


def pips(cards):
    out = Counter()
    for c in cards:
        m = main_cost(c)
        for a,b in re.findall(r"([WUBRG])/([WUBRG])",m):
            out[a] += 0.5; out[b] += 0.5
        m2 = re.sub(r"[WUBRG]/[WUBRG]","",m)
        m2 = re.sub(r"2/[WUBRG]","",m2)
        for col in COLOR_ORDER:
            out[col] += m2.count(col)
    return out


def colored_requirement(c):
    """Return list of requirement sets, one per colored pip; hybrid => {A,B}."""
    m = main_cost(c)
    req = []
    for a,b in re.findall(r"([WUBRG])/([WUBRG])",m):
        req.append({a,b})
    m = re.sub(r"[WUBRG]/[WUBRG]","",m)
    # two-brid can be paid with color OR two generic: do not force as a colored requirement.
    m = re.sub(r"2/[WUBRG]","",m)
    for ch in m:
        if ch in COLOR_ORDER: req.append({ch})
    return req


def source_counts(lands, basics):
    src = Counter({BASIC_TO_COLOR[k]:int(v) for k,v in basics.items()})
    flexible = 0
    for c in lands:
        if c.get("flex_source"):
            flexible += 1
        for col in c.get("produces") or []:
            src[col] += 1
    return src, flexible


def nonland_mana_tools(spells):
    ramp=[]; fixing=[]; cyclers=[]
    for c in spells:
        f=card_features(c)
        if "Ramp" in f or "Duramen" in f:
            ramp.append(c)
        if "Ramp/Fixing" in f or "Fixing" in f:
            fixing.append(c)
        if "Ciclo terra base" in f:
            cyclers.append(c)
    return ramp,fixing,cyclers


def engine_counts(spells):
    feat=Counter()
    for c in spells:
        for t in card_features(c): feat[t]+=1
    return {
        "Jace / Sorvegliare":feat["Jace"]+feat["Sorvegliare"],
        "Cimitero / Soglia":feat["Cimitero"]+feat["Soglia"],
        "Danno non da combattimento":feat["Danno non da combattimento"]+feat["Payoff danno non-combat"],
        "Guadagno vita / Segnalini":feat["Guadagno vita"]+feat["Segnalini +1/+1"]+feat["Payoff vita"],
        "Ramp / Fixing":feat["Ramp/Fixing"]+feat["Ciclo terra base"],
        "Morte / Recupero":feat["Morte/Recupero"]+feat["Payoff morte"],
        "Magie non creatura":feat["Magia non creatura"]+feat["Payoff noncreature"],
        "Pedine":feat["Pedine"]+feat["Payoff pedine"],
        "Preparato":feat["Preparato"]+feat["Ri-prepara"],
    }


def archetype_fit(cards):
    result=[]
    card_nums={c.get("n") for c in cards}
    feat=Counter()
    for c in cards:
        for t in card_features(c): feat[t]+=1
    for key,a in ARCHETYPES.items():
        colors=set(a["colors"])
        oncolor=sum(1 for c in cards if not c.get("colors") or set(c.get("colors") or []).issubset(colors))
        offcolor=max(0,len(cards)-oncolor)
        raw=0.0
        evidence=[]
        for tag,w in a["tags"].items():
            n=feat[tag]
            if n:
                raw += min(n,6)*w
                evidence.append("%s ×%d"%(tag,n))
        anchors=[n for n in a["anchors"] if n in card_nums]
        raw += 2.0*len(anchors)
        if anchors: evidence.append("carte-segnale ×%d"%len(anchors))
        raw += min(oncolor,23)*0.05
        raw -= offcolor*0.6
        score=max(0.0,min(10.0,raw/2.5))
        result.append({"key":key,"name":a["name"],"colors":a["colors"],"plan":a["plan"],"score":score,"evidence":evidence,"anchors":anchors})
    return sorted(result,key=lambda x:x["score"],reverse=True)


def speed_profile(spells):
    if not spells: return "Indefinito"
    curve=Counter("6+" if c.get("mv",0)>=6 else str(c.get("mv",0)) for c in spells)
    low=sum(c.get("mv",0)<=3 for c in spells)
    high=sum(c.get("mv",0)>=5 for c in spells)
    creatures=sum(is_creature(c) for c in spells)
    interaction=sum("Interazione" in card_features(c) for c in spells)
    if low>=15 and high<=3 and creatures>=14:
        return "Aggro / tempo"
    if interaction>=6 and high>=4 and creatures<=14:
        return "Midrange-control"
    if high>=5 and sum("Ramp/Fixing" in card_features(c) for c in spells)>=3:
        return "Ramp midrange"
    return "Midrange"


def source_target_for_spell(c, target_prob=0.85):
    req=colored_requirement(c)
    if not req: return {}
    mv=max(1,int(c.get("mv",0)))
    turn=max(1,min(6,mv))
    seen=7 if turn==1 else 6+turn  # on play, precombat main: T2=8, T3=9...
    by_color=Counter()
    for r in req:
        if len(r)==1:
            by_color[next(iter(r))]+=1
    targets={}
    for col,k in by_color.items():
        for sources in range(k,18):
            if comb_prob_at_least(40,sources,seen,k)>=target_prob:
                targets[col]=sources; break
        if col not in targets: targets[col]=17
    return targets


def mana_targets(spells, target_prob=0.85):
    targets=Counter()
    demanding={}
    for c in spells:
        st=source_target_for_spell(c,target_prob)
        for col,n in st.items():
            if n>targets[col]:
                targets[col]=n; demanding[col]=c
    return targets,demanding


def recommended_land_count(spells):
    if not spells: return 17
    avg=sum(c.get("mv",0) for c in spells)/len(spells)
    high=sum(c.get("mv",0)>=5 for c in spells)
    six=sum(c.get("mv",0)>=6 for c in spells)
    early=sum(c.get("mv",0)<=2 for c in spells)
    ramp=sum("Ramp" in card_features(c) or "Duramen" in card_features(c) for c in spells)
    cyclers=sum("Ciclo terra base" in card_features(c) for c in spells)
    if avg<=2.65 and high<=2 and early>=7:
        return 16
    if (avg>=3.55 or high>=6 or six>=3) and ramp<3 and cyclers<2:
        return 18
    return 17


def recommend_basics(spells, nonbasic_lands, target_lands=None):
    """Recommend a basic-land split by optimizing average colored castability.

    A single GGGG/UUU bomb should matter, but it should not erase the color demands of
    the other 22 spells. We therefore enumerate all basic splits and score the whole deck.
    """
    if target_lands is None: target_lands=recommended_land_count(spells)
    slots=max(0,target_lands-len(nonbasic_lands))
    if slots<=0: return {},target_lands
    active=[]
    for c in spells:
        for col in c.get("colors") or []:
            if col not in active: active.append(col)
    if not active:
        return {"Pianura":slots},target_lands
    # Se il mazzo ha 4+ colori, limitiamo l'ottimizzatore ai tre con più pips: il report
    # segnalerà comunque che la struttura di mana è rischiosa.
    pip=pips(spells)
    if len(active)>3:
        active=sorted(active,key=lambda c:pip[c],reverse=True)[:3]
    existing,_=source_counts(nonbasic_lands,{k:0 for k in BASIC_TO_COLOR})

    def compositions(total,n,prefix=()):
        if n==1:
            yield prefix+(total,); return
        for i in range(total+1):
            for rest in compositions(total-i,n-1,prefix+(i,)):
                yield rest

    def spell_color_prob(c,src):
        req=colored_requirement(c)
        mono=Counter()
        hybrids=[]
        for r in req:
            if len(r)==1: mono[next(iter(r))]+=1
            else: hybrids.append(r)
        turn=max(1,min(6,int(c.get("mv",0))))
        seen=7 if turn==1 else 6+turn
        probs=[]
        for col,k in mono.items():
            probs.append(comb_prob_at_least(40,src[col],seen,k))
        # Each hybrid pip can use the better available color. This is an approximation,
        # but behaves correctly for land-split optimization.
        for r in hybrids:
            best=max((src[x] for x in r),default=0)
            probs.append(comb_prob_at_least(40,best,seen,1))
        return min(probs) if probs else 1.0

    best=None
    for comp in compositions(slots,len(active)):
        alloc=dict(zip(active,comp))
        src=Counter(existing)
        for c,n in alloc.items(): src[c]+=n
        total_score=0.0; weight_sum=0.0
        for card in spells:
            req=colored_requirement(card)
            if not req: continue
            # Early spells and higher-impact cards matter slightly more, but no single bomb dominates.
            w=1.0
            if card.get("mv",0)<=3: w+=0.20
            if "Interazione" in card_features(card): w+=0.10
            if "Minaccia ad alto impatto" in card_features(card): w+=0.10
            total_score += w*spell_color_prob(card,src)
            weight_sum += w
        # Small global pip-balance term.
        pip_total=sum(pip[c] for c in active) or 1.0
        balance=0.0
        for c in active:
            desired=(pip[c]/pip_total)*slots
            balance -= 0.003*(alloc[c]-desired)**2
        avg=(total_score/weight_sum if weight_sum else 1.0)+balance
        # Prevent accidental zero-basic support for a genuine main color unless nonbasics cover it.
        penalty=0.0
        for c in active:
            if pip[c]>=3 and src[c]<5: penalty += 0.05*(5-src[c])
        avg-=penalty
        if best is None or avg>best[0]: best=(avg,alloc)
    alloc=best[1]
    inv={v:k for k,v in BASIC_TO_COLOR.items()}
    return {inv[c]:n for c,n in alloc.items() if n},target_lands

def land_source_sets(deck_card):
    if not is_land(deck_card): return None
    p=set(deck_card.get("produces") or [])
    if deck_card.get("flex_source"): return set(COLOR_ORDER)
    return p


def can_pay_colored_requirements(requirements, land_sources):
    # Bipartite matching by backtracking, <=5 colored pips in ordinary Limited costs.
    req=sorted(requirements,key=lambda s:len(s))
    used=[False]*len(land_sources)
    def rec(i):
        if i==len(req): return True
        for j,src in enumerate(land_sources):
            if not used[j] and req[i] & src:
                used[j]=True
                if rec(i+1): return True
                used[j]=False
        return False
    return rec(0)


def can_cast_from_lands(spell, lands):
    mv=int(spell.get("mv",0))
    if len(lands)<mv: return False
    req=colored_requirement(spell)
    if not req: return True
    sources=[land_source_sets(x) or set() for x in lands]
    return can_pay_colored_requirements(req,sources)


def deck_signature(selected, basics):
    parts=sorted(c.get("uid",str(c.get("n"))) for c in selected)
    parts += ["%s:%s"%(k,int(v)) for k,v in sorted(basics.items())]
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]


def materialize_deck(selected, basics):
    deck=[dict(c) for c in selected]
    for name,n in basics.items():
        for i in range(int(n)):
            deck.append(basic(name,uid="BASIC-%s-%d"%(name,i)))
    return deck


def consistency_simulation(deck, spells, trials=8000, seed=12345):
    rng=random.Random(seed)
    n=len(deck)
    if n!=40:
        return {}
    land_dist=Counter(); both_main=0; early_open=0; t3_land=0; t4_land=0; t5_land=0; flood12=0; screw10=0
    colors=Counter()
    for c in spells:
        for col in c.get("colors") or []: colors[col]+=1
    main_cols=[c for c,_ in colors.most_common(2)]
    early_uids={c.get("uid") for c in spells if c.get("mv",0)<=2 and (is_creature(c) or "Interazione" in card_features(c))}
    for _ in range(trials):
        sample=rng.sample(deck,n)
        opening=sample[:7]
        lands7=[c for c in opening if is_land(c)]
        land_dist[len(lands7)]+=1
        if any(c.get("uid") in early_uids for c in opening): early_open+=1
        if len(main_cols)>=2:
            ok=True
            for col in main_cols:
                if not any(col in (land_source_sets(c) or set()) for c in lands7): ok=False
            if ok: both_main+=1
        if sum(is_land(c) for c in sample[:9])>=3: t3_land+=1
        if sum(is_land(c) for c in sample[:10])>=4: t4_land+=1
        if sum(is_land(c) for c in sample[:11])>=5: t5_land+=1
        if sum(is_land(c) for c in sample[:12])>=6: flood12+=1
        if sum(is_land(c) for c in sample[:10])<=2: screw10+=1
    return {
        "trials":trials,
        "land_dist":{k:v/trials for k,v in sorted(land_dist.items())},
        "healthy_open":sum(v for k,v in land_dist.items() if 2<=k<=5)/trials,
        "both_main":both_main/trials if len(main_cols)>=2 else None,
        "early_open":early_open/trials,
        "t3_land":t3_land/trials,"t4_land":t4_land/trials,"t5_land":t5_land/trials,
        "flood12":flood12/trials,"screw10":screw10/trials,
        "main_cols":main_cols,
    }


def castability_simulation(deck, spells, trials=3500, seed=54321):
    rng=random.Random(seed)
    if len(deck)!=40: return []
    candidates=[c for c in spells if 1<=c.get("mv",0)<=6 and colored_requirement(c)]
    out=[]
    for spell in candidates:
        turn=max(1,min(6,int(spell.get("mv",0))))
        seen=7 if turn==1 else 6+turn
        success=0
        # Condition on having this physical spell available: draw the other seen-1 cards
        # from the remaining 39-card deck.
        uid=spell.get("uid")
        remainder=[]
        removed=False
        for x in deck:
            if not removed and uid is not None and x.get("uid")==uid:
                removed=True
                continue
            remainder.append(x)
        if not removed:
            remainder=list(deck)
        other_seen=max(0,seen-1)
        for _ in range(trials):
            draw=rng.sample(remainder,min(other_seen,len(remainder)))
            lands=[c for c in draw if is_land(c)]
            if can_cast_from_lands(spell,lands): success+=1
        out.append({"card":spell,"turn":turn,"p":success/trials})
    return sorted(out,key=lambda x:x["p"])


def synergy_reason(a,b):
    fa,fb=card_features(a),card_features(b)
    ta,tb=text_lower(a),text_lower(b)
    reasons=[]
    if ("Jace" in fa and ("jace" in tb or "planeswalker" in tb)) or ("Jace" in fb and ("jace" in ta or "planeswalker" in ta)):
        reasons.append("Jace: una carta crea/alimenta il planeswalker, l'altra lo sfrutta o lo protegge")
    if ("Enabler cimitero" in fa and "Payoff cimitero" in fb) or ("Enabler cimitero" in fb and "Payoff cimitero" in fa):
        reasons.append("cimitero/soglia: enabler + payoff")
    if ("Guadagno vita" in fa and "Payoff vita" in fb) or ("Guadagno vita" in fb and "Payoff vita" in fa):
        reasons.append("life gain: fonte di vita + payoff")
    if ("Segnalini +1/+1" in fa and "Payoff segnalini" in fb) or ("Segnalini +1/+1" in fb and "Payoff segnalini" in fa):
        reasons.append("segnalini +1/+1: enabler + payoff")
    if ("Danno non da combattimento" in fa and "Payoff danno non-combat" in fb) or ("Danno non da combattimento" in fb and "Payoff danno non-combat" in fa):
        reasons.append("danno non da combattimento: enabler + payoff")
    if (("Magia non creatura" in fa or "Interazione" in fa) and "Payoff noncreature" in fb) or (("Magia non creatura" in fb or "Interazione" in fb) and "Payoff noncreature" in fa):
        reasons.append("spellslinger: magia non creatura + payoff")
    if ("Pedine" in fa and "Payoff pedine" in fb) or ("Pedine" in fb and "Payoff pedine" in fa):
        reasons.append("pedine: generatore + payoff")
    if ("Ri-prepara" in fa and "Preparato" in fb) or ("Ri-prepara" in fb and "Preparato" in fa):
        reasons.append("preparato: effetto che ri-prepara + creatura con prepare")
    if ("Ramp/Fixing" in fa and b.get("mv",0)>=6) or ("Ramp/Fixing" in fb and a.get("mv",0)>=6):
        reasons.append("ramp: acceleratore/fixing + top-end")
    if ("Morte/Recupero" in fa and ("Creatura" in fb or "Payoff morte" in fb)) or ("Morte/Recupero" in fb and ("Creatura" in fa or "Payoff morte" in fa)):
        reasons.append("attrito/recursion: risorse che muoiono + recupero/payoff")
    if ("Leggendaria" in fa and "if you control a legendary" in tb) or ("Leggendaria" in fb and "if you control a legendary" in ta):
        reasons.append("leggendario: abilita la riduzione/condizione dell'altra carta")
    return reasons


def top_synergy_pairs(cards, limit=10):
    out=[]
    for a,b in combinations(cards,2):
        reasons=synergy_reason(a,b)
        if reasons:
            score=len(reasons)*3 + len(set(tags(a)) & set(tags(b)))*0.2
            out.append((score,a,b,reasons))
    return sorted(out,key=lambda x:x[0],reverse=True)[:limit]


def interaction_breakdown(spells):
    buckets=defaultdict(list)
    for c in spells:
        f=card_features(c)
        if "Hard removal" in f: buckets["Hard removal / esilio"].append(c)
        if "Damage removal" in f: buckets["Danno diretto a permanenti"].append(c)
        if "Counterspell" in f: buckets["Counterspell"].append(c)
        if "Bounce" in f: buckets["Bounce / tempo"].append(c)
        if "Fight/Bite" in f: buckets["Fight / bite"].append(c)
        if "Sweeper" in f: buckets["Sweeper"].append(c)
        if "Odio artefatto/incantesimo" in f: buckets["Artefatti / incantesimi"].append(c)
        if "Scarto" in f: buckets["Scarto"].append(c)
        if "Anti-volante" in f: buckets["Anti-volante"].append(c)
        if c.get("n") in OFFICIAL_KEY_INTERACTION and not any(c in v for v in buckets.values()):
            buckets["Altra interazione ufficiale"].append(c)
    return buckets


def deck_report(selected, basics):
    lands=[c for c in selected if is_land(c)]
    spells=[c for c in selected if not is_land(c)]
    land_n=len(lands)+sum(int(v) for v in basics.values())
    creature_n=sum(is_creature(c) for c in spells)
    walker_n=sum(is_planeswalker(c) for c in spells)
    interaction_cards=[c for c in spells if "Interazione" in card_features(c)]
    interaction_n=len(interaction_cards)
    early_cards=[c for c in spells if c.get("mv",0)<=2 and (is_creature(c) or "Interazione" in card_features(c))]
    high_cards=[c for c in spells if c.get("mv",0)>=6]
    noncreature_n=sum(not is_creature(c) for c in spells)
    echoed_n=sum(c.get("echoed",False) for c in spells)
    rarity=Counter(c.get("rarity") for c in spells)
    curve=Counter("6+" if c.get("mv",0)>=6 else str(c.get("mv",0)) for c in spells)
    colors=Counter()
    for c in spells:
        for x in c.get("colors") or []: colors[x]+=1
    src,flex=source_counts(lands,basics)
    pip=pips(spells)
    engines=engine_counts(spells)
    avg_mv=(sum(c.get("mv",0) for c in spells)/len(spells)) if spells else 0
    ramp,fixing,cyclers=nonland_mana_tools(spells)
    targets,demanding=mana_targets(spells,0.85)
    fits=archetype_fit(spells)
    speed=speed_profile(spells)
    recommended_lands=recommended_land_count(spells)
    rec_basics,_=recommend_basics(spells,lands,recommended_lands)

    score=100
    notes=[]
    if land_n==recommended_lands:
        notes.append(("ok","%d terre: coerenti con curva e profilo del mazzo."%land_n))
    elif abs(land_n-recommended_lands)==1:
        score-=4; notes.append(("warn","%d terre; il modello ne suggerisce %d come punto di partenza."%(land_n,recommended_lands)))
    else:
        score-=14; notes.append(("bad","%d terre; il modello ne suggerisce circa %d."%(land_n,recommended_lands)))

    if 14<=creature_n<=17:
        notes.append(("ok","%d creature: densità classica molto solida."%creature_n))
    elif 12<=creature_n<=19:
        score-=5; notes.append(("warn","%d creature: struttura plausibile, ma va compensata dal piano."%creature_n))
    else:
        score-=13; notes.append(("bad","%d creature: configurazione estrema per un normale Sealed."%creature_n))

    if interaction_n>=5:
        notes.append(("ok","%d pezzi di interazione/rimozione riconosciuti."%interaction_n))
    elif interaction_n>=3:
        score-=5; notes.append(("warn","%d interazioni: sufficiente ma non abbondante."%interaction_n))
    else:
        score-=13; notes.append(("bad","Solo %d interazioni riconosciute."%interaction_n))

    if len(early_cards)>=5:
        notes.append(("ok","%d giocate utili a costo 2 o meno."%len(early_cards)))
    elif len(early_cards)>=3:
        score-=6; notes.append(("warn","%d giocate iniziali: alcune mani partiranno lente."%len(early_cards)))
    else:
        score-=14; notes.append(("bad","Pochissime giocate utili nei primi due turni."))

    active=list(colors)
    fix_count=len(fixing)+sum(len(c.get("produces") or [])>=2 or c.get("flex_source") for c in lands)
    if len(active)<=2:
        notes.append(("ok","%d colori principali nelle magie."%len(active)))
    elif len(active)==3 and fix_count>=3:
        score-=4; notes.append(("warn","Tre colori con %d elementi di fixing/ramp."%fix_count))
    else:
        score-=13; notes.append(("bad","%d colori nelle magie con fixing non chiaramente sufficiente."%len(active)))

    for col,target in targets.items():
        sources=src[col]
        if sources+1 < target:
            score-=4; notes.append(("warn","%s: %d fonti naturali contro un benchmark on-curve di ~%d (85%%)."%(COLOR_NAME[col],sources,target)))

    if len(high_cards)>=4 and len(ramp)<2 and len(cyclers)<2:
        score-=5; notes.append(("warn","Top-end abbastanza pesante senza molto ramp/ciclo di terra."))
    if len(high_cards)>=4 and len(ramp)>=3:
        notes.append(("ok","Il top-end è sostenuto da %d veri acceleratori/ramp."%len(ramp)))

    score=max(0,min(100,score))
    return {
        "score":score,"lands":land_n,"spells":len(spells),"creatures":creature_n,"walkers":walker_n,
        "interaction":interaction_n,"interaction_cards":interaction_cards,"early":len(early_cards),"early_cards":early_cards,
        "high":len(high_cards),"high_cards":high_cards,"noncreature":noncreature_n,"echoed":echoed_n,
        "rarity":rarity,"curve":curve,"colors":colors,"sources":src,"flex_sources":flex,"pips":pip,
        "engines":engines,"avg_mv":avg_mv,"notes":notes,"spells_list":spells,"land_list":lands,
        "ramp":ramp,"fixing":fixing,"cyclers":cyclers,"mana_targets":targets,"demanding":demanding,
        "archetypes":fits,"speed":speed,"recommended_lands":recommended_lands,"recommended_basics":rec_basics,
        "interaction_breakdown":interaction_breakdown(spells),"synergy_pairs":top_synergy_pairs(spells,12),
    }


def deck_fit_score(c, report):
    s=quality(c)
    f=card_features(c)
    top_engines=[k for k,v in sorted(report["engines"].items(),key=lambda x:x[1],reverse=True)[:2] if v>=3]
    engine_map={
        "Jace / Sorvegliare":{"Jace","Sorvegliare"},
        "Cimitero / Soglia":{"Cimitero","Soglia","Recursion"},
        "Danno non da combattimento":{"Danno non da combattimento","Payoff danno non-combat"},
        "Guadagno vita / Segnalini":{"Guadagno vita","Segnalini +1/+1","Payoff vita","Payoff segnalini"},
        "Ramp / Fixing":{"Ramp/Fixing","Ciclo terra base","Ramp"},
        "Morte / Recupero":{"Morte/Recupero","Recursion","Payoff morte"},
        "Magie non creatura":{"Payoff noncreature","Magia non creatura"},
        "Pedine":{"Pedine","Payoff pedine"},
        "Preparato":{"Preparato","Ri-prepara"},
    }
    for e in top_engines:
        if f & engine_map.get(e,set()): s+=4
    if report["creatures"]<14 and is_creature(c): s+=4
    if report["interaction"]<5 and "Interazione" in f: s+=5
    if report["early"]<5 and c.get("mv",0)<=2 and (is_creature(c) or "Interazione" in f): s+=4
    if report["high"]>=4 and c.get("mv",0)>=6 and "Ramp/Fixing" not in f: s-=4
    return s


def improvement_suggestions(build_pool, selected, basics, max_swaps=6):
    rep=deck_report(selected,basics)
    ids={c.get("uid") for c in selected}
    chosen_colors=set()
    for c in rep["spells_list"]: chosen_colors.update(c.get("colors") or [])
    omitted=[]
    for c in build_pool:
        if c.get("uid") in ids or is_land(c): continue
        cs=set(c.get("colors") or [])
        if not cs or not chosen_colors or cs.issubset(chosen_colors):
            omitted.append(c)
    omitted=sorted(omitted,key=lambda c:deck_fit_score(c,rep),reverse=True)
    selected_spells=sorted(rep["spells_list"],key=lambda c:deck_fit_score(c,rep))
    swaps=[]
    used_out=set()
    for inc in omitted[:12]:
        for out in selected_spells:
            if out.get("uid") in used_out: continue
            gain=deck_fit_score(inc,rep)-deck_fit_score(out,rep)
            if gain<4: continue
            reasons=[]
            fi,fo=card_features(inc),card_features(out)
            if "Interazione" in fi and "Interazione" not in fo: reasons.append("aumenta l'interazione")
            if is_creature(inc) and rep["creatures"]<14 and not is_creature(out): reasons.append("alza il numero di creature")
            if inc.get("mv",0)<=2 and out.get("mv",0)>=5: reasons.append("abbassa e stabilizza la curva")
            shared=[]
            for _,a,b,rs in top_synergy_pairs(rep["spells_list"]+[inc],20):
                if a.get("uid")==inc.get("uid") or b.get("uid")==inc.get("uid"):
                    shared.extend(rs)
            if shared: reasons.append(shared[0])
            if not reasons: reasons.append("fit strutturale/sinergico superiore nel modello")
            swaps.append({"in":inc,"out":out,"gain":gain,"reasons":reasons})
            used_out.add(out.get("uid")); break
        if len(swaps)>=max_swaps: break
    return swaps,omitted[:10]


def sideboard_suggestions(build_pool, selected):
    ids={c.get("uid") for c in selected}
    omitted=[c for c in build_pool if c.get("uid") not in ids and not is_land(c)]
    out=defaultdict(list)
    for c in omitted:
        f=card_features(c)
        if "Anti-volante" in f or "Raggiungere" in f: out["Contro volanti"].append(c)
        if "Odio artefatto/incantesimo" in f: out["Contro artefatti/incantesimi"].append(c)
        if "Counterspell" in f or "Scarto" in f: out["Contro bombe / mazzi lenti"].append(c)
        if c.get("mv",0)<=2 and (is_creature(c) or "Interazione" in f or "Guadagno vita" in f): out["Contro aggro"].append(c)
        if "Cimitero" in f and "exile" in text_lower(c): out["Contro cimitero"].append(c)
    for k in list(out):
        out[k]=sorted(out[k],key=quality,reverse=True)[:5]
    return out


def pair_candidate_deck(pool, pair):
    colors=set(pair)
    spells=[c for c in pool if not is_land(c) and (not c.get("colors") or set(c.get("colors") or []).issubset(colors))]
    if len(spells)<20: return []
    fit_key="".join(pair)
    if fit_key not in ARCHETYPES: fit_key="".join(reversed(pair))
    def sc(c):
        s=quality(c)
        f=card_features(c)
        if fit_key in ARCHETYPES:
            for tag,w in ARCHETYPES[fit_key]["tags"].items():
                if tag in f: s+=2*w
            if c.get("n") in ARCHETYPES[fit_key]["anchors"]: s+=5
        return s
    ranked=sorted(spells,key=sc,reverse=True)
    chosen=ranked[:23]
    # Repair basic structural minima.
    for _ in range(10):
        cr=sum(is_creature(c) for c in chosen)
        inter=sum("Interazione" in card_features(c) for c in chosen)
        early=sum(c.get("mv",0)<=2 and (is_creature(c) or "Interazione" in card_features(c)) for c in chosen)
        if cr>=14 and inter>=3 and early>=4: break
        outside=ranked[23:]
        need_creature=cr<14; need_inter=inter<3; need_early=early<4
        cand=next((c for c in outside if (need_creature and is_creature(c)) or (need_inter and "Interazione" in card_features(c)) or (need_early and c.get("mv",0)<=2)),None)
        if not cand: break
        victim=min(chosen,key=sc)
        if sc(cand)+6<sc(victim): break
        chosen.remove(victim); chosen.append(cand)
    return sorted(chosen,key=lambda c:(c.get("mv",0),c.get("name","")))


def candidate_shells(pool):
    out=[]
    for pair in combinations(COLOR_ORDER,2):
        chosen=pair_candidate_deck(pool,pair)
        if len(chosen)<20: continue
        cr=sum(is_creature(c) for c in chosen)
        inter=sum("Interazione" in card_features(c) for c in chosen)
        early=sum(c.get("mv",0)<=2 and (is_creature(c) or "Interazione" in card_features(c)) for c in chosen)
        fit=archetype_fit(chosen)[0]
        metric=sum(quality(c) for c in chosen)+10*min(inter,6)+4*min(early,7)-4*abs(cr-15)+fit["score"]*8
        out.append({"metric":metric,"pair":pair,"cards":chosen,"creatures":cr,"interaction":inter,"early":early,"fit":fit})
    return sorted(out,key=lambda x:x["metric"],reverse=True)


def support_score(candidate, core, shell_colors=None):
    s=quality(candidate)
    fc=card_features(candidate)
    if shell_colors is not None:
        cc=set(candidate.get("colors") or [])
        if cc and not cc.issubset(set(shell_colors)): return -999
    pair_reasons=0
    for x in core:
        pair_reasons += len(synergy_reason(candidate,x))
    s += 6*pair_reasons
    core_feat=Counter()
    for x in core:
        for f in card_features(x): core_feat[f]+=1
    if core_feat["Jace"] and "Jace" in fc: s+=3
    if core_feat["Cimitero"] and ("Cimitero" in fc or "Recursion" in fc): s+=3
    if core_feat["Guadagno vita"] and ("Payoff vita" in fc or "Guadagno vita" in fc): s+=3
    if core_feat["Segnalini +1/+1"] and ("Payoff segnalini" in fc or "Segnalini +1/+1" in fc): s+=3
    if core_feat["Payoff noncreature"] and "Magia non creatura" in fc: s+=2
    if core_feat["Danno non da combattimento"] and "Danno non da combattimento" in fc: s+=3
    return s


def lab_report(core, all_cards):
    if not core: return {}
    colors=Counter()
    for c in core:
        for x in c.get("colors") or []: colors[x]+=1
    fits=archetype_fit(core)
    top=fits[0]
    shell_colors=top["colors"] if top["score"]>=1.5 else tuple(c for c,_ in colors.most_common(2))
    selected_n={c.get("n") for c in core}
    candidates=[c for c in all_cards if c.get("n") not in selected_n]
    ranked=sorted(candidates,key=lambda c:support_score(c,core,shell_colors),reverse=True)
    ranked=[c for c in ranked if support_score(c,core,shell_colors)>-900]
    feat=Counter()
    for c in core:
        for f in card_features(c): feat[f]+=1
    categories=defaultdict(list)
    for c in ranked:
        f=card_features(c)
        if any(synergy_reason(c,x) for x in core) and len(categories["Supporto sinergico"])<8:
            categories["Supporto sinergico"].append(c)
        if "Interazione" in f and len(categories["Interazione"])<6:
            categories["Interazione"].append(c)
        if ("Ramp/Fixing" in f or "Fixing" in f) and len(categories["Mana / fixing"])<5:
            categories["Mana / fixing"].append(c)
        if is_creature(c) and c.get("mv",0)<=3 and len(categories["Curva / creature efficienti"])<6:
            categories["Curva / creature efficienti"].append(c)
        if ("Minaccia ad alto impatto" in f or "Finisher" in f) and len(categories["Top-end / chiusure"])<5:
            categories["Top-end / chiusure"].append(c)
    return {
        "colors":colors,"fits":fits,"top_fit":top,"shell_colors":shell_colors,"features":feat,
        "synergy_pairs":top_synergy_pairs(core,12),"categories":categories,
        "recommended_support":ranked[:15],
    }


def hand_assessment(hand, deck_spells):
    lands=[c for c in hand if is_land(c)]
    spells=[c for c in hand if not is_land(c)]
    sources=set()
    for c in lands: sources.update(land_source_sets(c) or set())
    early=[c for c in spells if c.get("mv",0)<=2]
    castable_early=[]
    for c in early:
        if can_cast_from_lands(c,lands): castable_early.append(c)
    colors_needed=set()
    for c in deck_spells:
        colors_needed.update(c.get("colors") or [])
    missing=sorted(colors_needed-sources)
    land_n=len(lands)
    if 2<=land_n<=4 and castable_early and len(missing)<=1:
        label="Strutturalmente sana"
    elif land_n in (0,1,6,7):
        label="Alto rischio"
    else:
        label="Borderline / dipende dal piano"
    return {"lands":land_n,"spells":len(spells),"sources":sources,"missing":missing,"early":early,"castable_early":castable_early,"label":label}


def report_markdown(rep, basics, swaps=None):
    lines=[]
    lines.append("# Reality Fracture — Report Sealed")
    lines.append("")
    lines.append("## Sintesi")
    lines.append("- Punteggio strutturale: **%d/100**"%rep["score"])
    lines.append("- Profilo: **%s**"%rep["speed"])
    if rep["archetypes"]:
        lines.append("- Fit archetipico principale: **%s (%.1f/10)**"%(rep["archetypes"][0]["name"],rep["archetypes"][0]["score"]))
    lines.append("- %d terre, %d creature, %d interazioni, %d Planeswalker"%(rep["lands"],rep["creatures"],rep["interaction"],rep["walkers"]))
    lines.append("")
    lines.append("## Curva")
    lines.append("- "+"; ".join("%s mana: %d"%(k,rep["curve"].get(k,0)) for k in ["0","1","2","3","4","5","6+"]))
    lines.append("- MV medio magie: %.2f"%rep["avg_mv"])
    lines.append("")
    lines.append("## Mana")
    lines.append("- Fonti: "+", ".join("%s %d"%(COLOR_NAME[c],n) for c,n in rep["sources"].items() if n))
    lines.append("- Terre base: "+", ".join("%s %d"%(k,v) for k,v in basics.items() if v))
    lines.append("- Suggerimento: "+", ".join("%s %d"%(k,v) for k,v in rep["recommended_basics"].items() if v)+"; totale terre %d"%rep["recommended_lands"])
    lines.append("")
    lines.append("## Diagnostica")
    for lvl,msg in rep["notes"]: lines.append("- [%s] %s"%(lvl.upper(),msg))
    lines.append("")
    lines.append("## Motori")
    for k,v in sorted(rep["engines"].items(),key=lambda x:x[1],reverse=True):
        if v: lines.append("- %s: %d"%(k,v))
    if swaps:
        lines.append("")
        lines.append("## Possibili cambi")
        for x in swaps:
            lines.append("- Considera **%s** al posto di **%s**: %s."%(x["in"]["name"],x["out"]["name"],"; ".join(x["reasons"])))
    return "\n".join(lines)
