import '../models/recipe.dart';
import '../services/backend.dart';
import 'base.dart';

class FeedViewModel extends BaseViewModel {
  FeedViewModel(this._recipes);

  final RecipeApi _recipes;

  List<Category> categories = [];
  String? category;
  String sort = 'popular';
  bool personalized = false;

  List<Recipe> items = [];
  int total = 0;
  bool loading = false;
  bool loadingMore = false;
  String? error;
  String? loadMoreError;
  int _generation = 0;

  bool get hasMore => items.length < total;

  Future<void> start() async {
    loadCategories();
    await refresh();
  }

  Future<void> loadCategories() async {
    try {
      categories = await _recipes.categories();
      notifyListeners();
    } catch (_) {
      // Sem categorias o feed continua a funcionar; apenas não há filtros.
    }
  }

  Future<void> refresh() async {
    final gen = ++_generation;
    loading = true;
    error = null;
    loadMoreError = null;
    notifyListeners();
    try {
      final page = await _recipes.list(
          category: category, sort: sort, personalized: personalized);
      if (gen != _generation) return;
      items = page.items;
      total = page.total;
    } catch (e) {
      if (gen != _generation) return;
      error = errorText(e);
    }
    loading = false;
    notifyListeners();
  }

  Future<void> loadMore() async {
    if (loading || loadingMore || !hasMore) return;
    final gen = _generation;
    loadingMore = true;
    loadMoreError = null;
    notifyListeners();
    try {
      final page = await _recipes.list(
          category: category,
          sort: sort,
          personalized: personalized,
          offset: items.length);
      if (gen == _generation) {
        items = [...items, ...page.items];
        total = page.total;
      }
    } catch (e) {
      if (gen == _generation) loadMoreError = errorText(e);
    }
    loadingMore = false;
    notifyListeners();
  }

  void _changed() {
    items = [];
    total = 0;
    refresh();
  }

  void setCategory(String? slug) {
    if (slug == category) return;
    category = slug;
    _changed();
  }

  void setSort(String value) {
    if (value == sort) return;
    sort = value;
    _changed();
  }

  void setPersonalized(bool value) {
    if (value == personalized) return;
    personalized = value;
    _changed();
  }
}
