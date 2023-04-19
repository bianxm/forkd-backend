# Forkd: A Recipe Journal and (soft) Version Control System

An app where users can save, record 'experiments', and track edits for recipes

This is the backend repo corresponding to the frontend [here](https://github.com/bianxm/forkd-frontend) (still under construction)

## Technologies Used
- PostgreSQL database
- Flask backend
- [Spoonacular API](https://spoonacular.com/food-api) 

## Data Model

[Here](https://dbdiagram.io/d/6428e0565758ac5f1725ff32), 5 tables
* Users table - email, password, username
* Recipes table - title, description, some metadata
* Experiments table -  title, dates, notes
* Edits table - historical data for recipe edits
* Permissions table - associating a recipe and a user, and the user's permission level for that recipe

## Roadmap

### MVP

- [x] Users can login to see their saved recipes and the corresponding "experiments"
- [x] Users can add "experiments" under each recipe, where they can log:
  - when
  - what they did different
  - the outcome
  - photos? 
- [x] Users can add "edits" under each recipe, which tracks the changes they've made to the recipe
  - [JSDiff](https://github.com/kpdecker/jsdiff) to get diffs
  - [Diff2HTML](https://github.com/rtfpessoa/diff2html) to display diffs
- [x] Fork a recipe (that you can then add your own experiments to)
- [x] Spoonacular API: Get a recipe from the internet


### 2.0
- [x] Rewrite backend as RESTful API
- [x] Add permissions and sharing functionality to backend
  - Users can view other users' public recipes, but not their experiments!
  - set all your experiments for a recipe to be public as well
  - share your recipe with a different user, and they can add experiments to the recipe 
- [ ] Test coverage (currently 57%)
- [ ] React SPA frontend ([in progress](https://github.com/bianxm/forkd-frontend))

### Nice-to-haves
- Recipe tagging
- Migrate to SQLAlchemy v2.x