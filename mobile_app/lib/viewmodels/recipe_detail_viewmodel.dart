import '../core/api_client.dart';
import '../models/interaction.dart';
import '../models/recipe.dart';
import '../services/backend.dart';
import 'base.dart';

/// Detalhe de uma receita. O conteúdo da receita (Recipe Service) e as interações (Interaction Service)
/// carregam separadamente: se um deles falhar, o outro continua visível.
class RecipeDetailViewModel extends BaseViewModel {
  RecipeDetailViewModel(
      this.recipeId, this._recipes, this._interactions, this.myId);

  final int recipeId;
  final RecipeApi _recipes;
  final InteractionApi _interactions;
  final int myId;

  Recipe? recipe;
  bool loadingRecipe = true;
  String? recipeError;

  InteractionSummary? summary;
  String? summaryError;

  List<Comment> comments = [];
  int commentsTotal = 0;
  String? commentsError;
  bool loadingMoreComments = false;

  List<Recipe> related = [];
  bool _viewRegistered = false;

  bool get isOwner => recipe != null && recipe!.authorId == myId;
  int get likeCount => summary?.likeCount ?? recipe?.likeCount ?? 0;
  int get commentCount => summary?.commentCount ?? recipe?.commentCount ?? 0;
  double? get ratingAverage =>
      summary != null ? summary!.rating.average : recipe?.ratingAvg;
  int get ratingCount =>
      summary != null ? summary!.rating.count : (recipe?.ratingCount ?? 0);
  bool get liked => summary?.myLike ?? false;
  int? get myScore => summary?.rating.myScore;
  bool get hasMoreComments => comments.length < commentsTotal;

  Future<void> load() async {
    loadingRecipe = true;
    recipeError = null;
    notifyListeners();
    try {
      recipe = await _recipes.detail(recipeId);
    } catch (e) {
      recipeError = errorText(e);
      loadingRecipe = false;
      notifyListeners();
      return;
    }
    loadingRecipe = false;
    notifyListeners();

    if (!_viewRegistered) {
      // Uma visualização por abertura do detalhe; falhar não afeta o ecrã.
      _viewRegistered = true;
      _recipes.registerView(recipeId).catchError((_) {});
    }
    await Future.wait([loadInteractions(), loadComments(), _loadRelated()]);
  }

  Future<void> loadInteractions() async {
    try {
      summary = await _interactions.summary(recipeId);
      summaryError = null;
    } catch (e) {
      summaryError = errorText(e);
    }
    notifyListeners();
  }

  Future<void> loadComments() async {
    try {
      final page = await _interactions.comments(recipeId);
      comments = page.items;
      commentsTotal = page.total;
      commentsError = null;
    } catch (e) {
      commentsError = errorText(e);
    }
    notifyListeners();
  }

  Future<void> loadMoreComments() async {
    if (loadingMoreComments || !hasMoreComments) return;
    loadingMoreComments = true;
    notifyListeners();
    try {
      final page =
          await _interactions.comments(recipeId, offset: comments.length);
      comments = [...comments, ...page.items];
      commentsTotal = page.total;
    } catch (_) {}
    loadingMoreComments = false;
    notifyListeners();
  }

  Future<void> _loadRelated() async {
    try {
      related = await _recipes.related(recipeId);
    } catch (_) {
      related = [];
    }
    notifyListeners();
  }

  // ---------- ações (devolvem uma mensagem de erro ou null) ----------

  Future<String?> toggleLike() async {
    final s = summary;
    if (s == null) return summaryError ?? 'As interações estão indisponíveis.';
    final wasLiked = s.myLike ?? false;
    summary = s.copyWith(
        myLike: !wasLiked, likeCount: s.likeCount + (wasLiked ? -1 : 1));
    notifyListeners();
    try {
      if (wasLiked) {
        await _interactions.unlike(recipeId);
      } else {
        await _interactions.like(recipeId);
      }
      loadInteractions();
      return null;
    } catch (e) {
      if (!wasLiked && e is ApiException && e.conflict)
        return null; // já tinha gostado noutro dispositivo
      summary = s;
      notifyListeners();
      return errorText(e);
    }
  }

  Future<String?> rate(int score) async {
    final s = summary;
    if (s == null) return summaryError ?? 'As interações estão indisponíveis.';
    try {
      final rating = await _interactions.rate(recipeId, score);
      summary = s.copyWith(rating: rating);
      notifyListeners();
      return null;
    } catch (e) {
      return errorText(e);
    }
  }

  Future<String?> addComment(String text) async {
    try {
      final c = await _interactions.addComment(recipeId, text);
      comments = [c, ...comments];
      commentsTotal += 1;
      final s = summary;
      if (s != null) summary = s.copyWith(commentCount: s.commentCount + 1);
      notifyListeners();
      return null;
    } catch (e) {
      return errorText(e);
    }
  }

  Future<String?> editComment(Comment comment, String text) async {
    try {
      final updated = await _interactions.editComment(comment.id, text);
      comments = [for (final c in comments) c.id == comment.id ? updated : c];
      notifyListeners();
      return null;
    } catch (e) {
      return errorText(e);
    }
  }

  Future<String?> deleteComment(Comment comment) async {
    try {
      await _interactions.deleteComment(comment.id);
      comments = comments.where((c) => c.id != comment.id).toList();
      commentsTotal = commentsTotal > 0 ? commentsTotal - 1 : 0;
      final s = summary;
      if (s != null && s.commentCount > 0)
        summary = s.copyWith(commentCount: s.commentCount - 1);
      notifyListeners();
      return null;
    } catch (e) {
      return errorText(e);
    }
  }

  Future<List<Collection>> fetchCollections() => _interactions.collections();

  Future<String?> addToCollection(int collectionId) async {
    try {
      await _interactions.addToCollection(collectionId, recipeId);
      return null;
    } catch (e) {
      return errorText(e);
    }
  }

  Future<String?> createCollectionAndAdd(String name) async {
    try {
      final c = await _interactions.createCollection(name);
      await _interactions.addToCollection(c.id, recipeId);
      return null;
    } catch (e) {
      return errorText(e);
    }
  }

  Future<String?> share(String username) async {
    try {
      await _interactions.share(
          recipeId, username.trim().replaceFirst('@', ''));
      return null;
    } catch (e) {
      return errorText(e);
    }
  }

  Future<String?> deleteRecipe() async {
    try {
      await _recipes.remove(recipeId);
      return null;
    } catch (e) {
      return errorText(e);
    }
  }

  void replaceRecipe(Recipe updated) {
    recipe = updated;
    notifyListeners();
  }
}
