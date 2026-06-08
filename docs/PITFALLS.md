# PITFALLS — Le bestiaire des bugs

> Tous les pièges rencontrés sur les 25+ versions du projet Interlaken. Lis ça AVANT de démarrer un nouveau projet, ça te fera économiser ~5h.

Format de chaque entrée :
- **Symptôme** — ce que tu vois
- **Cause** — pourquoi
- **Diagnostic** — comment confirmer
- **Fix** — comment réparer
- **Évitement** — comment ne plus jamais le faire

---

## 1. 4K render produit du 640×360 (LE bug critique)

- **Symptôme** : `QUALITY=final python3 my_project.py` finit, le fichier dit `3840×2160` dans le log, mais `ffprobe` sur le fichier rendu dit `640×360`. La vidéo finale est un master 4K avec du contenu 640×360 letterboxé.
- **Cause** : les `clip_NN_*.mp4` cachés en `/tmp/<project>/` viennent du précédent run `QUALITY=preview`. Le nom du fichier ne dépend PAS de la résolution. Le script vérifie `os.path.exists(out_path)` → cache hit → réutilise le clip preview en input du concat final, qui produit du 4K avec du contenu redimensionné.
- **Diagnostic** :
  ```bash
  ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=p=0 /tmp/<project>/clip_00_0.mp4
  ```
- **Fix** : purger le cache avant tout switch preview ↔ final :
  ```bash
  python3 scripts/validate_cache.py /tmp/<project> --quality final
  ```
- **Évitement** : utilise `validate_cache.py` systématiquement avant un render. Ou nomme le cache par résolution : `clip_NN_J_640x360.mp4`.

---

## 2. `rm *.foo` échoue silencieusement sous zsh

- **Symptôme** : tu lances `rm /tmp/proj/*.foo` pour purger un type de fichier, le shell répond `(eval): no matches found`, et **tous les autres rm de la même ligne ne s'exécutent pas non plus**. Cache pas du tout vidé.
- **Cause** : zsh active `NOMATCH` par défaut. Un glob qui ne matche rien échoue toute la commande au lieu de juste skipper.
- **Diagnostic** : la ligne `rm` retourne un exit non-zéro et `ls` montre que les autres fichiers sont toujours là.
- **Fix** :
  ```bash
  find /tmp/proj -maxdepth 1 -type f \( -name "*.foo" -o -name "*.bar" \) -delete
  ```
- **Évitement** : utilise `find -delete` au lieu de `rm GLOB` dès qu'il y a un risque de no-match. Ou `setopt -u NOMATCH`. Ou ajoute `2>/dev/null || true` (mais ça masque les vrais bugs).

---

## 3. Drift cumulatif invisible (source insuffisante)

- **Symptôme** : ton plan #8 dans le master fait 8.667s au lieu des 8.700s demandés. Les plans après sont décalés de quelques ms. Ça s'accumule sur 22 plans : ~800ms de drift en fin de timeline → ta sync musicale est foutue.
- **Cause** : pour le plan #8 tu as demandé `out_dur=8.700, speed=0.55, src_start=4.5`. Source consommée = `8.700 × 0.55 = 4.785s`. Mais la source ne fait que `4.872s` à partir de `src_start=4.5` → il reste `0.372s` de marge. **ffmpeg lit moins de frames** et le sub-clip rendu est plus court → les frames manquantes sont absorbées en sortie.
- **Diagnostic** : `ffprobe -show_entries format=duration` sur chaque `clip_NN_0.mp4` vs `out_dur` demandé.
- **Fix** :
  ```bash
  python3 scripts/validate_edit.py my_project.py
  ```
- **Évitement** : toujours laisser ≥0.5s de marge entre `src_start + out_dur × speed` et `source_duration`. Le validator le check.

---

## 4. Cache transition `trans_*.mp4` obsolète

- **Symptôme** : tu changes l'EDIT (nouvelle source, nouveau speed), tu re-rends, mais à `t=N` dans le master tu vois un plan que tu n'as PAS dans l'EDIT actuel — un fragment d'un plan supprimé.
- **Cause** : `render_xfade_pair()` génère des transitions A→B dans `trans_NN_pair.mp4` et check `os.path.exists` pour décider de réutiliser. Quand tu changes A ou B, le hash du contenu change mais pas le nom du fichier → vieille transition réutilisée.
- **Diagnostic** : compare le mtime des `trans_*.mp4` avec celui des `clip_*.mp4` adjacents.
- **Fix** : `rm /tmp/<project>/trans_*.mp4` après tout changement structurel de l'EDIT.
- **Évitement** : soit hasher le contenu dans le nom (`trans_NN_<hash>.mp4`), soit supprimer **toujours** les trans en début de render.

---

## 5. cv2.VideoWriter crash sur timer overlay

- **Symptôme** : ton script `finalize.py` qui ajoute un timer en bas-droite crash avec `ImportError: numpy.core.multiarray failed to import` ou `cv2.VideoWriter` retourne `False` sur `isOpened()`.
- **Cause** : `opencv-python` (cv2) n'est pas compatible avec `numpy ≥ 2.0`. Brew installe numpy 2.x par défaut.
- **Diagnostic** : `python3 -c "import cv2"` → ImportError ou warning numpy.
- **Fix** :
  ```bash
  pip install --upgrade "numpy<2"
  ```
- **Évitement** : pin numpy<2 dans le `requirements.txt` du projet.

---

## 6. Ramp 1→2 fait sauter l'image (stepping perception)

- **Symptôme** : tu mets `speed=(1.0, 2.0)` sur un plan pour un effet d'accélération progressive. À la lecture, on voit clairement 5 « paliers » discrets de vitesse, ça fait saccadé.
- **Cause** : le script découpe la ramp en `n_sub=5` sous-segments avec des speeds discrètes (1.0, 1.2, 1.4, 1.6, 1.8). Chaque sous-segment a une vitesse constante, la transition entre sous-segments est dure. À l'œil c'est une « pulsation ».
- **Diagnostic** : visionne au ralenti, tu vois les 5 marches.
- **Fix** : remplace par une vitesse **constante** intermédiaire — souvent juste l'avg : `speed=1.5` au lieu de `(1.0, 2.0)`. Ou augmente `n_sub` à 15-20 (au prix du rendu).
- **Évitement** : pour les effets d'accélération vraiment fluides, fais le ramp en post avec un easing cubic continu (filtergraph `setpts=PTS*(1+t*0.5)`), pas en découpage.

---

## 7. Fadeout déclaré mais invisible

- **Symptôme** : tu ajoutes `"fadeout"` au champ `extra` du plan, le script le parse, mais à la lecture aucun fondu noir.
- **Cause** : le `fadeout_filter` est défini en début de `process_subseg()` mais doit être injecté dans `grade_chain`. Si tu modifies seulement la branche `if exposure_fix:` du grade et pas la branche `else:`, le fadeout n'est appliqué qu'aux plans en exposure_fix.
- **Diagnostic** : `grep "fadeout_filter" my_project.py` → vérifie qu'il apparaît dans **les deux** branches du if/else.
- **Fix** : `vignette=PI/4{fadeout_filter}[out]` dans les deux branches.
- **Évitement** : factorise le `vignette+fadeout` en variable commune utilisée par les deux branches.

---

## 8. Whites becoming grey on title overlay

- **Symptôme** : tu poses un titre PNG blanc sur une image, mais le titre apparaît gris une fois l'encodage final terminé.
- **Cause** : tu as un `eq=brightness=+0.X` quelque part dans le filtergraph qui lift le point noir et écrase les blancs.
- **Diagnostic** : compare le PNG source (blanc=255) et le frame final (blanc=220 ?).
- **Fix** : utilise `gamma` + `contrast` (préservent les blancs) au lieu de `brightness`. Pour assombrir les noirs sans toucher aux blancs, utilise `curves`.
- **Évitement** : règle de pouce — `brightness` est presque toujours mauvais. Préfère `curves` ou `eq=gamma`.

---

## 9. Scintillement (flicker) sur fond de ciel

- **Symptôme** : un grain animé sur fond uniforme (ciel, eau lisse) qui pulse rapidement → effet désagréable.
- **Cause** : `noise=allf=t+u` applique du grain avec composante temporelle (`t`), créant un pattern qui change à chaque frame.
- **Fix** : `noise=allf=u` seul (composante uniforme, pas temporelle).
- **Évitement** : si tu n'es pas SÛR d'avoir besoin du temporal, n'ajoute jamais le `t`.

---

## 10. Saccadé (judder) sur slowmo

- **Symptôme** : ton plan en slowmo 0.5× sur du 30fps fait du judder visible, image par image.
- **Cause** : 30fps × 0.5x speed = 15fps effectif. En dessous de 24fps, l'œil voit chaque frame.
- **Fix** : motion-compensated frame interpolation **avant** `setpts` :
  ```
  minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1,
  setpts=2.0*PTS
  ```
- **Évitement** : règle automatique : applique `minterpolate` si `src_fps < 50 ET speed < 0.9`. Coûte ~3× plus cher en CPU mais c'est obligatoire en dessous.

---

## 11. Color mismatch entre clips adjacents

- **Symptôme** : deux plans qui devraient se suivre visuellement ont des saturations / tons très différents → coupure visible.
- **Cause** : LUT appliqué uniformément alors que les sources ont des baselines différentes (D-Log vs Rec709, soleil vs ombre, etc.).
- **Diagnostic** : `signalstats` sur 1s de chaque plan, compare `SATAVG` et `YAVG`.
- **Fix** : per-clip overrides via `CLIP_GRADE = {"filename_substr": {"lut": 0.40, "sat": 0.85, ...}}`.
- **Évitement** : extraire les frames de référence + `signalstats` dès la première itération preview pour identifier les outliers.

---

## 12. Cold cast / blacks lifted to grey

- **Symptôme** : plans tournés à l'ombre / par temps couvert qui ont un voile bleu-gris, les noirs sont gris au lieu d'être profonds.
- **Cause** : naïvement appliquer `eq=brightness=+0.X` lift les noirs (le 0 du signal devient 0.X) → noirs gris.
- **Fix** : `exposure_fix: True` dans `CLIP_GRADE` → applique S-curve qui compresse 0-0.05 vers le noir tout en lift mids + colorbalance warm shift :
  ```
  curves=master='0/0 0.05/0.02 0.20/0.27 0.50/0.62 0.80/0.88 1/1',
  colorbalance=bs=-0.05:bm=-0.03:bh=-0.02
  ```
- **Évitement** : pour les clips overcast, jamais de `brightness=+`. Toujours curves ou exposure_fix.

---

## 13. Music sync drifts after EDIT changes

- **Symptôme** : tes acts étaient calés sur la musique en V3, tu fais des changements de durée sur quelques plans en V4 et maintenant les peaks tombent sur des plans random.
- **Cause** : chaque modif de `output_dur` décale tous les plans qui suivent. Pas de notification.
- **Diagnostic** :
  ```bash
  python3 scripts/audit_timings.py my_project.py
  ```
- **Fix** : ajuste les `out_dur` voisins pour que les act boundaries retombent à ±1.5s des peaks.
- **Évitement** : lance `audit_timings.py` après CHAQUE série de modifs EDIT.

---

## 14. PNG title apparaît minuscule en 4K

- **Symptôme** : ton titre lisible en preview 640×360 devient quasi-invisible en 4K 3840×2160.
- **Cause** : taille du PNG codée en dur en pixels. Quand tu passes en 4K, le PNG (1280×156 par ex) reste petit sur un canvas 3840×2160.
- **Fix** : utiliser `S(x) = int(x * SCALE)` où `SCALE = OUT_W / 3840.0`. Le PNG titre est régénéré à chaque QUALITY avec la bonne taille.
- **Évitement** : le template `render_template.py` inclut cette helper, suis le pattern.

---

## 15. Nohup + & masque les notifications de fin

- **Symptôme** : tu lances `nohup ... &` pour un render 30 min, tu ne sais pas quand ça finit, le shell n'envoie aucune notif.
- **Cause** : nohup + detach = process orphelin, le harness Claude Code ne peut pas suivre.
- **Fix** : utiliser `Bash` avec `run_in_background: true` (harness-tracked) + monitor PID pour fire une notif à la fin.
- **Évitement** : pour tout job >5 min, lance via le harness `run_in_background`, pas `nohup &`.

---

## 16. Multiple changements en une itération → impossible de débugger

- **Symptôme** : tu fais 5 changements (color + timing + SFX + ramp + extras) en une itération, le résultat est pire, tu ne sais pas ce qui a causé quoi.
- **Cause** : pas de variable isolée → impossible d'attribuer un effet.
- **Évitement** : règle stricte — **une catégorie de changement par itération**. Catégories : A=structure, B=timing, C=color, D=motion, E=match-cuts, F=music-sync, G=SFX, H=overlays. Fais une preview après chaque catégorie.

---

## Récap : check-list pré-render

Avant tout `QUALITY=final python3 my_project.py`, lance :

```bash
python3 scripts/validate_edit.py my_project.py      # source capacity
python3 scripts/audit_timings.py my_project.py      # music sync
python3 scripts/validate_cache.py /tmp/<project> --quality final   # cache resolution
```

Si tout est ✅, tu peux lancer le 4K. Sinon, fix avant.
