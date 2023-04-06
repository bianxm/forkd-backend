# Forkd: A Recipe Journal and (soft) Version Control System

An app where users can save, record 'experiments', and track edits for recipes 

## Technologies Required

- [JSDiff](https://github.com/kpdecker/jsdiff) to get diffs
- [Diff2HTML](https://github.com/rtfpessoa/diff2html) to display diffs
- (2.0 goal) [Spoonacular API](https://spoonacular.com/food-api) 
- (stretch goal) [Mergely](https://www.mergely.com/) for real-time diff highlighting

## Data Model

[Here](https://dbdiagram.io/d/6428e0565758ac5f1725ff32), 4-5 tables
* Users table - email, password, username
* Recipes table - title, description, some metadata
* Experiments table -  title, dates, notes
* Edits table, historical data for recipe edits
* (for stretch features) Permissions table

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


### 2.0

- [ ] Fork a different user's recipe (that you can then add your own experiments to)
- [ ] Spoonacular API: Get a recipe from the internet
- [ ] Add an experiment plan -- something to change, with results to be put in later

### Nice-to-haves

- React
- Permissions and sharing 
  - Users can view other users' recipes, but not their experiments!
  - set all your experiments for a recipe to be public as well
  - share your recipe with a different user, and they can add experiments to the recipe 
- Owner to approve edits from collaborators
- Recipe tagging
- Real-time diff highlighting ([Mergely](https://www.mergely.com/))
- Migrate to SQLAlchemy v2.x

## Notes

N/A