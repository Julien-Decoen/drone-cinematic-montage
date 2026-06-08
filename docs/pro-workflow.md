# Pro workflow — passages "amateur très soigné" → "creator pro"

> Ces 9 étapes transforment un montage déjà bon en un montage qui vend.
> Skill v3 capture ces étapes en scripts utilitaires.

## Vue d'ensemble — où chaque étape s'insère dans le workflow

```
[Pré-shoot]
  └─ shot list (manuel) — pas de script

[Post-shoot, jour J]
  └─ scripts/ingest.py        🆕  Pré-prod / DIT — backup + proxies + naming

[Pré-montage]
  └─ scripts/cull.py          🆕  Sélection 1-5 étoiles → select reel

[Pré-render (sur masters retenus)]
  └─ scripts/stabilize.py     🆕  vidstab 2-pass — élimine micro-jitter

[Pendant le montage]
  ├─ scripts/beat_sync.py     🆕  Snap cuts sur beats musicaux
  ├─ scripts/reference_grade.py 🆕  Extrait palette d'une référence → LUT custom
  └─ scripts/bezier_ramp.py   🆕  (opt-in) Cubic ease pour speed ramps

[Post-render master]
  ├─ scripts/master_audio_lufs.py    🆕  -14 LUFS pour YouTube/Spotify
  ├─ scripts/lcut_jcut.py           🆕  Audio bridging entre cuts (L/J)
  └─ scripts/multi_aspect_export.py 🆕  9:16, 1:1, 4:5 à partir du master 16:9
```

---

## Pré-prod / DIT (ingest.py)

Avant le V3, ingest était fait à la main : copier la carte SD, garder un seul backup, renommer dans Finder, mémoriser quel clip est lequel.

Le script automatise :

1. **Copie depuis source** (carte SD ou dossier) → dossier de travail
2. **Backup mirror** (règle 3-2-1 : 3 copies, 2 supports, 1 hors site)
3. **Génération de proxies** 240p H.264 (~50× plus léger que 4K) → édition rapide
4. **Renommage déterministe** : `DJI_0084.MP4` → `INT_D1_001.MP4`
5. **Metadata JSON** : durée, fps, résolution, slot pour rating + tags

```bash
python3 scripts/ingest.py \
  --source /Volumes/DJI_SD \
  --out ~/Documents/drone/MyProject \
  --project INT \
  --backup /Volumes/ExternalSSD/drone_backup \
  --day 2
```

Sortie :
```
~/Documents/drone/MyProject/
├── 01_masters/    INT_D2_001.MP4 ... INT_D2_087.MP4
├── 02_proxies/    INT_D2_001_proxy.mp4 ... (240p)
└── metadata.json  [tous les infos par clip]
```

---

## Sélection / culling (cull.py)

200 clips sur la carte → 22 dans le montage final.

Le script lance un loop interactif :
- Ouvre chaque proxy dans QuickTime
- Tu notes 0-5 (5 = hero, 0 = poubelle)
- Save après chaque rating (résumable, peut quitter avec `q`)

```bash
python3 scripts/cull.py ~/Documents/drone/MyProject/02_proxies/
# … rate chaque clip …
python3 scripts/cull.py ~/Documents/drone/MyProject/02_proxies/ --stats
python3 scripts/cull.py ~/Documents/drone/MyProject/02_proxies/ --filter 4 --copy ~/selects/
```

→ Tu obtiens un sous-ensemble "selects" de 30-50 clips pour démarrer ton EDIT.

---

## Stabilisation (stabilize.py)

Le gimbal DJI est bon mais pas parfait. Tout pro fait un pass `vidstab` 2-pass en post.

```bash
# Tout le dossier de selects
python3 scripts/stabilize.py ~/selects/ --smoothing 30
# → ~/selects/stabilized/ (à utiliser comme CLIPS dans my_project.py)
```

Paramètres :
- `--shakiness 1-10` : combien la source bouge (default 5, 1 = trépied, 10 = main levée)
- `--smoothing 10-100` : rayon de lissage des transforms (default 30)
- `--crop` : zoom léger pour cacher les bords noirs (default = bords noirs visibles)

Coût : ~1× temps réel par clip 4K (un clip 8s = 8s render).

---

## Beat-precise sync (beat_sync.py)

V25 calait les cuts sur des **peaks RMS** (= moments forts au sens énergie). Les pros calent sur les **beats musicaux** (= snare hits, downbeats).

```bash
# 1. Analyser la musique
python3 scripts/beat_sync.py music.mp3
# → 107.7 BPM, 174 beats, 44 downbeats, 312 onsets

# 2. Audit EDIT vs beats
python3 scripts/beat_sync.py music.mp3 --script my_project.py
# → table : pour chaque cut, le beat le plus proche + delta

# 3. Appliquer le snap (réécrit my_project.py, garde un .bak)
python3 scripts/beat_sync.py music.mp3 --script my_project.py --apply
```

Modes : `--use beats` (tous les beats), `--use downbeats` (downbeats seuls — plus marqué), `--use onsets` (accents rythmiques fins).

Requiert : `pip install librosa`.

---

## Reference-based grading (reference_grade.py)

Plutôt que de grader à l'œil + CLIP_GRADE empirique, choisis une **référence visuelle** (Wes Anderson, Sam Kolder, Apple ad) et matche dessus.

```bash
python3 scripts/reference_grade.py kolder_still.jpg --strength 0.4
# → kolder_still_grade.cube (LUT 33³)
# → puis dans render_template.py : LUT_SRC = ".../kolder_still_grade.cube"
```

Options :
- `--palette N` : nb de couleurs dominantes à extraire (3-8, default 5)
- `--strength 0-1` : push intensity (0.3 subtle, 0.7 dramatique)
- `--preview master.mp4` : applique la LUT sur les 10 premières secondes pour vérifier

---

## Bezier ramp (bezier_ramp.py) — OPT-IN

⚠ **Performance warning** : 2-3× plus lent que la ramp linéaire de `render_template.py`. À tester sur 1 clip avant d'en abuser.

L'avantage : un cubic ease-in-out donne une accélération naturelle SANS le "stepping" visible des ramps linéaires découpées.

```bash
python3 scripts/bezier_ramp.py \
  source.mp4 output.mp4 \
  --ss 2.0 --src-dur 22.7 --out-dur 11.6 \
  --s-start 1.0 --s-end 2.0
```

Use case principal : le plan final accéléré du montage (riser dramatique), où tu veux vraiment une accélération douce continue.

---

## LUFS audio mastering (master_audio_lufs.py)

YouTube normalise à **-14 LUFS**, Spotify à -14, Apple à -16. Sans normalisation, ton mix sort à un niveau random → soit écrasé par la plateforme, soit absent vs autre contenu.

```bash
python3 scripts/master_audio_lufs.py master.mp4
# → master_lufs.mp4 (audio normalisé à -14 LUFS, vidéo copiée)
```

2-pass loudnorm. Pass 1 mesure (input_i, input_lra, input_tp), pass 2 applique linéairement.

Targets recommandés :
- `--target -14` YouTube / Spotify / TikTok / Instagram
- `--target -16` Apple Music / Apple TV
- `--target -23` Broadcast TV (EBU R128)

---

## L-cuts / J-cuts (lcut_jcut.py)

Hard cut audio = montage haché. Audio overlap = montage qui respire.

- **L-cut** : audio plan A continue 0.5s sur plan B (le son tire la nouvelle image)
- **J-cut** : audio plan B commence 0.5s avant la coupe (le son anticipe)

```bash
python3 scripts/lcut_jcut.py my_project.py \
  --sfx-dir ~/Documents/drone/MyProject/_sfx_real/ \
  --overlap 0.5 --mode mixed
# → _lcut_jcut_mix.mp3 (à muxer en remplacement du mix audio par défaut)
```

Modes :
- `--mode L` : tous les SFX en L-cut
- `--mode J` : tous en J-cut
- `--mode mixed` : alterne L et J selon la parité du plan

Tu remplaces ton mix audio par celui-ci dans le final mux.

---

## Multi-aspect-ratio export (multi_aspect_export.py)

Un master 16:9 → tous les deliverables sociaux d'un coup :

```bash
python3 scripts/multi_aspect_export.py master.mp4
# → master_multi/
#    ├── master_9x16_1080x1920.mp4   (Reels / TikTok / Shorts)
#    ├── master_1x1_1080x1080.mp4    (Instagram feed)
#    └── master_4x5_1080x1350.mp4    (Instagram portrait)
```

Options :
- `--aspects 9:16,1:1` : seulement ceux-là
- `--blur-bg` : fond flou style Instagram (vs center-crop par défaut)
- `--duration 60` : trim aux premières 60s (pour Shorts)
- `--saliency` : (TODO) reframing subject-aware avec saliency map — fallback center-crop pour l'instant

Le mode par défaut (center-crop) suffit pour 80% des plans drone (sujet central). Pour les plans avec sujet décalé, il faudrait un cropper saliency-aware — sur la roadmap.

---

## Recommandations d'utilisation

### Pour un projet "passion / partage" (= ton usage actuel)

Workflow minimal :
1. `ingest.py` (15 min) — DIT discipline
2. `cull.py` (30 min) — réduction 200 → 50 clips
3. `stabilize.py` (~30 min batch sur tes 50 selects)
4. Render normal avec `my_project.py`
5. `master_audio_lufs.py` (2 min) — toujours
6. `multi_aspect_export.py` (5 min) — pour publier sur Insta/TikTok

Total overhead vs V25.19 : ~1h de prep + 2 min de post = 1h pour un saut qualitatif net.

### Pour un projet "client / brand content / festival"

Ajouter :
7. `beat_sync.py` (15 min) — quand la musique a un beat clair
8. `reference_grade.py` (30 min) — pour matcher un look brand
9. `lcut_jcut.py` (30 min de réglages) — pour le polish audio
10. `bezier_ramp.py` (cas-par-cas) — uniquement sur les rampes signature

Total : +2-3h sur le master mais le résultat est 2× plus vendable.

---

## Ce qui n'est PAS dans v3 (pour référence)

- **Sidechain compression** (music ducking sous SFX) — skipped intentionally, faible ROI pour drone montage
- **Object removal** (drone shadow, branches) — trop complexe, nécessite ML/Mocha
- **5.1 surround mix** — overkill pour streaming
- **HDR pass** (HDR10/Dolby Vision) — peu de plateformes diffusent en HDR pour content créateur
- **Saliency-aware reframing** — TODO, requiert un modèle ML (placeholder dans multi_aspect_export.py)
- **Frame.io collaboration** — pas d'utilisateur unique justifie l'intégration
