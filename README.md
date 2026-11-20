# cned-graphique
Graphiques CNED générés depuis Notion :

- `index.html` : progression des devoirs ;
- `moyennes.html` : moyennes par matière.

## Partage de la base Notion

La base **Notes**, identifiée par l'ID `41e864f0-8119-8054-be00-d06839d4c5ec`, doit être partagée avec l'intégration Notion correspondant au secret GitHub Actions `NOTION_TOKEN`.

Dans les paramètres de l'intégration, autorisez l'accès à cette base puis ajoutez `NOTION_TOKEN` dans **Settings > Secrets and variables > Actions** du dépôt. Le jeton n'est utilisé que par les workflows GitHub Actions ; il ne doit jamais être écrit dans une page HTML ou dans les journaux.

## Calcul

Pour chaque matière, le script calcule la moyenne arithmétique des notes valides. La moyenne générale est ensuite la moyenne à poids égaux des moyennes de matière : elle n'est pas pondérée par le nombre de devoirs. Les notes absentes sont ignorées, les valeurs 0 sont conservées, et les valeurs non finies ou hors de l'intervalle `[0,20]` sont rejetées. Ce calcul ne constitue pas une moyenne officielle du bac.

Le site publié contient uniquement les moyennes agrégées et les noms de matières. Il ne publie pas les notes individuelles ni d'autres informations personnelles. **Lors du déploiement GitHub Pages, ces moyennes deviennent publiques.**
