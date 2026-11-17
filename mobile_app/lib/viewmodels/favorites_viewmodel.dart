import '../models/interaction.dart';
import '../models/recipe.dart';
import '../services/backend.dart';
import 'base.dart';

class FavoritesViewModel extends BaseViewModel {
  FavoritesViewModel(this._interactions);

  final InteractionApi _interactions;

  List<Collection> collections = [];
  bool loading = true;
  String? error;

  Future<void> load() async {
    loading = true;
    error = null;
    notifyListeners();
    try {
      collections = await _interactions.collections();
    } catch (e) {
      error = errorText(e);
    }
    loading = false;
    notifyListeners();
  }

  Future<String?> create(String name) async {
    try {
      final c = await _interactions.createCollection(name);
      collections = [...collections, c];
      notifyListeners();
      return null;
    } catch (e) {
      return errorText(e);
    }
  }

  Future<String?> remove(Collection c) async {
    try {
      await _interactions.deleteCollection(c.id);
      collections = collections.where((x) => x.id != c.id).toList();
      notifyListeners();
      return null;
    } catch (e) {
      return errorText(e);
    }
  }
}

/// Receitas de uma lista de favoritos. Os ids vêm do Interaction Service; os dados das receitas do Recipe Service.
class CollectionViewModel extends BaseViewModel {
  CollectionViewModel(this.collection, this._recipes, this._interactions);

  Collection collection;
  final RecipeApi _recipes;
  final InteractionApi _interactions;

  List<Recipe> recipes = [];
  bool loading = true;
  String? error;

  Future<void> load() async {
    loading = true;
    error = null;
    notifyListeners();
    try {
      if (collection.recipeIds.isEmpty) {
        recipes = [];
      } else {
        final ids = collection.recipeIds.take(50).toList();
        final page = await _recipes.list(ids: ids, limit: 50, sort: 'recent');
        final byId = {for (final r in page.items) r.id: r};
        // Mantém a ordem da lista (mais recentes primeiro); receitas apagadas simplesmente não aparecem.
        recipes = [
          for (final id in ids)
            if (byId.containsKey(id)) byId[id]!
        ];
      }
    } catch (e) {
      error = errorText(e);
    }
    loading = false;
    notifyListeners();
  }

  Future<String?> removeRecipe(Recipe recipe) async {
    try {
      await _interactions.removeFromCollection(collection.id, recipe.id);
      recipes = recipes.where((r) => r.id != recipe.id).toList();
      collection = Collection(
        id: collection.id,
        name: collection.name,
        recipeIds: collection.recipeIds.where((id) => id != recipe.id).toList(),
      );
      notifyListeners();
      return null;
    } catch (e) {
      return errorText(e);
    }
  }
}
