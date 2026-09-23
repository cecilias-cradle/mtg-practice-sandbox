# Reality Fracture — Ultimate Prerelease Trainer

Versione **offline/deploy-ready** del trainer per il Prerelease Sealed di Reality Fracture.

## Funzioni

- Simula **6 Play Booster + 1 promo foil R/M** per Prerelease.
- Modella separatamente comuni, non comune, C/U, 3 Echoed Pair, R/M, foil, terra e Special Guest.
- Mantiene la correlazione delle Echoed Pair: 2 carte della stessa coppia e stessa rarità.
- Costruzione mazzo da **40 carte esatte** con contatori separati per Pianure, Isole, Paludi, Montagne e Foreste.
- Report Ultimate con:
  - curva e profilo aggro/midrange/control/ramp;
  - creature, Planeswalker, top-end, rarità ed Echoed Pair;
  - interazioni divise in hard removal, burn, counter, bounce, fight/bite, sweeper, anti-volante, ecc.;
  - confronto con le 34 key-interaction ufficiali della guida Prerelease;
  - analisi mana: fonti, pips, benchmark on-curve, doppio/triplo simbolo, fixing, ramp, landcycling;
  - simulazione Monte Carlo della castabilità on-curve delle magie color-intensive;
  - 8.000 simulazioni di consistenza delle pescate;
  - fit verso i 10 archetipi ufficiali di Reality Fracture;
  - sinergie specifiche fra coppie di carte;
  - sequencing e note pratiche su Jace, Prepared, threshold, noncreature, burn, ramp, ecc.;
  - cambi consigliati con carte precise del pool;
  - piano sideboard;
  - alternative di colore/guscio da ricontrollare;
  - report scaricabile in Markdown.
- **Simulatore di pescata**:
  - mano iniziale da 7;
  - nuove mani/mulligan;
  - pescate turno dopo turno;
  - differenza play/draw;
  - valutazione strutturale della mano;
  - statistiche 10.000 mani della lista.
- **Laboratorio 280**:
  - selezioni liberamente qualsiasi gruppo di carte dell'espansione;
  - il programma identifica colori, archetipi, motori e sinergie;
  - suggerisce carte specifiche dell'intero set come supporto, interazione, fixing, curva e finisher;
  - produce un blueprint Limited su come costruire attorno al nucleo.

## File

- `app.py` — interfaccia Streamlit
- `engine.py` — simulazione, probabilità e motore strategico
- `data/fra_cards.json` — database locale delle 280 carte
- `assets/cards/` — immagini opzionali #001–#280
- `prepare_images.py` — estrattore locale dal PDF immagini
- `requirements.txt` — per eseguire l'app
- `requirements-local-images.txt` — solo per preparare le immagini

## Avvio sul Mac

Se hai già creato `~/Downloads/.venv`:

```bash
cd ~/Downloads/Reality_Fracture_Trainer_Ultimate
../.venv/bin/python3 -m streamlit run app.py
```

Se parti da zero:

```bash
cd ~/Downloads/Reality_Fracture_Trainer_Ultimate
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 -m streamlit run app.py
```

## Immagini

Se hai `FRA 1–280 completo immagini.pdf` in Downloads:

```bash
cd ~/Downloads/Reality_Fracture_Trainer_Ultimate
../.venv/bin/python3 -m pip install -r requirements-local-images.txt
../.venv/bin/python3 prepare_images.py
```

Se l'estrattore riconosce correttamente il layout deve stampare `OK: create 280 immagini`.

## Deploy Streamlit Community Cloud

Il deploy non richiede i PDF originali: `fra_cards.json` è già incluso.

1. Carica questa cartella in un repository GitHub.
2. Apri Streamlit Community Cloud.
3. Seleziona repository e `app.py`.
4. Deploy.

Le immagini sono opzionali: se vuoi che compaiano online, carica anche `assets/cards/*.png` nel repository.

## Precisione / assunzioni dichiarate

La struttura Play Booster deriva dai dati pubblicati da Wizards per Reality Fracture. Alcune categorie Booster Fun sono pubblicate solo come **“less than 1%”**, quindi la loro distribuzione identitaria non è ricostruibile al decimale. Il trainer usa una stima centrale solo per quel residuo.

Per le Echoed Pair il trainer usa anche i drop rate pubblicati da MTG Arena: una Echoed Pair non comune sale a rara circa 1 volta ogni 10; una rara sale a mitica circa 1 volta ogni 5,7. Questo corrisponde, a livello di rarità funzionale, a circa 90,0% U / 8,25% R / 1,75% M.

La promo del Prerelease è garantita R/M, ma Wizards non pubblica nel dettaglio il suo rapporto R/M: il simulatore usa 83,1/16,9 come assunzione esplicita.

Gli score del report sono **euristiche di deckbuilding**, non rating ufficiali Wizards e non una tier list assoluta.
