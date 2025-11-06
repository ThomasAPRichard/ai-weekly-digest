# AI Weekly Digest — Python + feedparser + SQLite + Email (GitHub Actions)

Un dépôt prêt à l’emploi pour **collecter chaque semaine** les nouveaux articles depuis 4 sources et **envoyer un email récap**.

**Sources incluses par défaut :**
- Hacker News (frontpage via hnrss)
- arXiv cs.AI (recent)
- The Neuron — Explainers (scraping)
- DataScientest — News (RSS)

> ✅ Fonctionne sans serveur : tout tourne dans **GitHub Actions**.

---

## 1) Installation

1. **Crée un repo** à partir de ces fichiers (bouton “Use this template” ou copie du dossier).
2. Dans le repo, va dans **Settings → Secrets and variables → Actions → New repository secret** et ajoute :

   - `SMTP_HOST` — ex. `smtp.gmail.com`
   - `SMTP_PORT` — ex. `587`
   - `SMTP_USER` — ton identifiant SMTP
   - `SMTP_PASS` — ton mot de passe/app password
   - `MAIL_FROM` — expéditeur (ex. `Thomas <thomas@exemple.com>`)
   - `MAIL_TO` — destinataires séparés par des virgules
   - *(optionnel)* `SMTP_STARTTLS` — `true` (défaut) ou `false`
   - *(optionnel)* `SUBJECT_PREFIX` — préfixe d’objet (défaut: `AI Weekly Digest`)

3. **(Optionnel)** Modifie le planning dans [`.github/workflows/weekly_digest.yml`](.github/workflows/weekly_digest.yml).
   - Par défaut : **tous les lundis à 07:30 Europe/Paris** (cron en UTC : `30 6 * * MON`).

---

## 2) Lancer en local (test rapide)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Variables d'env (exemple GMail)
export SMTP_HOST="smtp.gmail.com"
export SMTP_PORT="587"
export SMTP_USER="votre_user@gmail.com"
export SMTP_PASS="app_password"
export MAIL_FROM="AI Weekly Digest <votre_user@gmail.com>"
export MAIL_TO="vous@exemple.com"
export SUBJECT_PREFIX="AI Weekly Digest"

# Exécution (collecte + envoi email)
python -m src.run_digest --since-days 7 --send-email
```

Tu peux aussi exécuter sans envoi (`--send-email` absent) pour seulement **alimenter la base** et vérifier le **rendu HTML** affiché dans les logs.

La base SQLite est stockée dans `data/digest.db`.

---

## 3) Configurer les sources

Édite **`config/sources.yaml`** :

```yaml
sources:
  - name: "Hacker News (frontpage)"
    type: "rss"
    url: "https://hnrss.org/frontpage"

  - name: "arXiv cs.AI (recent)"
    type: "rss"
    url: "https://rss.arxiv.org/rss/cs.AI"

  - name: "The Neuron — Explainers"
    type: "html"
    url: "https://www.theneuron.ai/articles"
    strategy: "neuron_articles"

  - name: "DataScientest — News (EN)"
    type: "rss"
    url: "https://datascientest.com/en/category/news/feed"
```

- **rss** : lu avec `feedparser` (RSS/Atom).
- **html** : scraping léger avec `BeautifulSoup`. Pour The Neuron, on capture les **liens d'articles** (pas de date dans le HTML public), et on s’appuie sur `first_seen` pour le filtrage **7 jours**.

Tu peux ajouter d’autres sources (`type: rss` recommandé).

---

## 4) Comment ça marche

1. **Collecte** : lit chaque source (RSS ou HTML) → normalise `{title, url, published?, first_seen}`.
2. **Déduplication** : clé `(source, guid)` où `guid` vaut `entry.id` ou `link`.
3. **Stockage** : enregistre dans **SQLite** (`data/digest.db`).
4. **Sélection** : récupère les items dont `published` **ou** `first_seen` ∈ `[now-7j, now]`.
5. **Rendu** : `templates/digest.html.j2` (HTML) + version texte.
6. **Email** : via SMTP (`EMAIL+STARTTLS`).

---

## 5) Planification (GitHub Actions)

- Fichier : **`.github/workflows/weekly_digest.yml`**
- Par défaut : **lundi 06:30 UTC** (= 07:30 Europe/Paris en hiver)
- Tu peux déclencher manuellement depuis l’onglet **Actions**.

---

## 6) Notes utiles

- **Hacker News** : le frontpage RSS fiable passe par **hnrss** (meilleure flexibilité).
- **arXiv cs.AI** : flux officiel RSS par **subject class**.
- **The Neuron** : pas de flux RSS public pour /articles → scraping conservateur.
- **DataScientest** : on utilise le flux RSS de la catégorie *News* en version EN (fiable).

---

## 7) Licence

MIT.
