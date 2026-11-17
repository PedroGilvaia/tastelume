import '../core/api_client.dart';
import '../models/recipe.dart';
import '../services/backend.dart';
import 'base.dart';

class SaveResult {
  const SaveResult({this.recipe, this.error, this.warning});

  final Recipe? recipe;

  /// A receita não foi guardada.
  final String? error;

  /// A receita foi guardada, mas algo secundário falhou (p. ex. o envio da foto).
  final String? warning;

  bool get ok => recipe != null;
}

class RecipeFormViewModel extends BaseViewModel {
  RecipeFormViewModel(this._recipes, {this.existing});

  final RecipeApi _recipes;
  final Recipe? existing;

  List<Category> categories = [];
  String? categoriesError;
  bool saving = false;

  bool get isEdit => existing != null;

  Future<void> loadCategories() async {
    try {
      categories = await _recipes.categories();
      categoriesError = null;
    } catch (e) {
      categoriesError = errorText(e);
    }
    notifyListeners();
  }

  /// Cria (ou atualiza) a receita e só depois envia a foto: se o envio falhar, a receita fica guardada
  /// e o utilizador é avisado em vez de perder o que escreveu.
  Future<SaveResult> save(RecipeDraft draft, {String? imagePath}) async {
    saving = true;
    notifyListeners();
    try {
      var recipe = isEdit
          ? await _recipes.update(existing!.id, draft)
          : await _recipes.create(draft);
      String? warning;
      if (imagePath != null) {
        try {
          recipe = await _recipes.uploadImage(recipe.id, imagePath);
        } on ApiException catch (e) {
          warning =
              'A receita foi guardada, mas a foto não foi enviada: ${e.message}';
        }
      }
      return SaveResult(recipe: recipe, warning: warning);
    } on ApiException catch (e) {
      return SaveResult(error: e.message);
    } finally {
      saving = false;
      notifyListeners();
    }
  }
}
