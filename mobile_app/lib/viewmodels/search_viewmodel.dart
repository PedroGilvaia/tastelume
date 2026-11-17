import '../models/recipe.dart';
import '../models/user.dart';
import '../services/backend.dart';
import 'base.dart';

enum SearchMode { recipes, users }

class SearchViewModel extends BaseViewModel {
  SearchViewModel(this._recipes, this._users);

  final RecipeApi _recipes;
  final UsersApi _users;

  SearchMode mode = SearchMode.recipes;
  bool byIngredient = false;
  String query = '';

  List<Recipe> recipeResults = [];
  int recipeTotal = 0;
  List<UserProfile> userResults = [];
  bool loading = false;
  bool loadingMore = false;
  bool searched = false;
  String? error;
  int _generation = 0;

  bool get hasMoreRecipes => recipeResults.length < recipeTotal;

  void setMode(SearchMode value) {
    if (value == mode) return;
    mode = value;
    search();
  }

  void setByIngredient(bool value) {
    byIngredient = value;
    search();
  }

  Future<void> search([String? text]) async {
    if (text != null) query = text;
    final gen = ++_generation;
    final q = query.trim();
    if (q.isEmpty) {
      recipeResults = [];
      userResults = [];
      recipeTotal = 0;
      searched = false;
      loading = false;
      error = null;
      notifyListeners();
      return;
    }
    loading = true;
    error = null;
    notifyListeners();
    try {
      if (mode == SearchMode.recipes) {
        final page = await _recipes.list(
            q: byIngredient ? '' : q,
            ingredient: byIngredient ? q : '',
            sort: 'popular');
        if (gen != _generation) return;
        recipeResults = page.items;
        recipeTotal = page.total;
      } else {
        final users = await _users.search(q);
        if (gen != _generation) return;
        userResults = users;
      }
      searched = true;
    } catch (e) {
      if (gen != _generation) return;
      error = errorText(e);
    }
    loading = false;
    notifyListeners();
  }

  Future<void> loadMore() async {
    if (mode != SearchMode.recipes || loading || loadingMore || !hasMoreRecipes)
      return;
    final gen = _generation;
    final q = query.trim();
    loadingMore = true;
    notifyListeners();
    try {
      final page = await _recipes.list(
        q: byIngredient ? '' : q,
        ingredient: byIngredient ? q : '',
        sort: 'popular',
        offset: recipeResults.length,
      );
      if (gen == _generation) {
        recipeResults = [...recipeResults, ...page.items];
        recipeTotal = page.total;
      }
    } catch (_) {
      // Mantém os resultados já carregados.
    }
    loadingMore = false;
    notifyListeners();
  }
}
