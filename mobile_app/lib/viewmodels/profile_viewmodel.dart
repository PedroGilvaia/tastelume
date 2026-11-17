import '../models/recipe.dart';
import '../models/user.dart';
import '../services/backend.dart';
import 'base.dart';

class ProfileViewModel extends BaseViewModel {
  ProfileViewModel(this.userId, this._users, this._recipes, this.myId);

  final int userId;
  final UsersApi _users;
  final RecipeApi _recipes;
  final int myId;

  UserProfile? user;
  bool loading = true;
  String? error;

  List<Recipe> recipes = [];
  int recipeTotal = 0;
  String? recipesError;
  bool loadingMore = false;
  bool followBusy = false;

  bool get isMe => userId == myId;
  bool get hasMore => recipes.length < recipeTotal;

  Future<void> load() async {
    loading = true;
    error = null;
    notifyListeners();
    try {
      user = await _users.user(userId);
    } catch (e) {
      error = errorText(e);
      loading = false;
      notifyListeners();
      return;
    }
    loading = false;
    notifyListeners();
    await loadRecipes();
  }

  /// As receitas pertencem a outro serviço: se falharem, o perfil continua visível.
  Future<void> loadRecipes() async {
    try {
      final page = await _recipes.byUser(userId);
      recipes = page.items;
      recipeTotal = page.total;
      recipesError = null;
    } catch (e) {
      recipesError = errorText(e);
    }
    notifyListeners();
  }

  Future<void> loadMore() async {
    if (loadingMore || !hasMore) return;
    loadingMore = true;
    notifyListeners();
    try {
      final page = await _recipes.byUser(userId, offset: recipes.length);
      recipes = [...recipes, ...page.items];
      recipeTotal = page.total;
    } catch (_) {}
    loadingMore = false;
    notifyListeners();
  }

  Future<String?> toggleFollow() async {
    final u = user;
    if (u == null || followBusy || isMe) return null;
    followBusy = true;
    final following = u.isFollowing ?? false;
    notifyListeners();
    try {
      if (following) {
        await _users.unfollow(userId);
      } else {
        await _users.follow(userId);
      }
      user = u.copyWith(
        isFollowing: !following,
        followersCount: u.followersCount + (following ? -1 : 1),
      );
      return null;
    } catch (e) {
      return errorText(e);
    } finally {
      followBusy = false;
      notifyListeners();
    }
  }
}
