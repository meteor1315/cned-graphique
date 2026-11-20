# cned-graphique
Graphique de progression des devoirs CNED généré depuis Notion

`moyennes.html` présente une moyenne arithmétique par matière et une moyenne
générale non pondérée (poids égal entre matières). Ce calcul est indicatif et
ne constitue pas une moyenne officielle du bac. Les notes absentes sont
ignorées, tandis que les zéros réels sont conservés.

Pour générer la page, l'automatisation GitHub Actions utilise uniquement le
secret `NOTION_TOKEN`. La base Notion **Notes** doit être partagée avec
l'intégration associée à ce secret. Seules les moyennes agrégées et les noms
des matières sont publiés. La publication de cette page sur GitHub Pages
rendra ces informations publiques.
