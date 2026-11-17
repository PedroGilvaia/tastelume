import '../core/api_client.dart';
import '../core/config.dart';
import '../models/activity.dart';
import '../models/interaction.dart';
import '../models/recipe.dart';
import '../models/user.dart';

/// Os quatro clientes de API (um por microserviço). Só montam pedidos e convertem JSON em modelos;
/// a lógica de ecrã e o tratamento de erros ficam nos ViewModels.

class UsersApi {
  UsersApi(this._api, this._config);

  final ApiClient _api;
  final ApiConfig _config;

  Uri _u(String path, [Map<String, String>? q]) =>
      _config.uri(ApiConfig.usersPort, path, q);

  Future<String> login(String identifier, String password) async {
    final r = await _api.postPublic(_u('/auth/login'),
        body: {'identifier': identifier, 'password': password});
    return r.map['access_token'] as String;
  }

  Future<void> register(String username, String email, String password) async {
    await _api.postPublic(_u('/auth/register'),
        body: {'username': username, 'email': email, 'password': password});
  }

  Future<UserProfile> me() async =>
      UserProfile.fromJson((await _api.get(_u('/users/me'))).map);

  Future<UserProfile> updateMe(
      {String? description, List<String>? interests}) async {
    final body = <String, dynamic>{
      if (description != null) 'description': description,
      if (interests != null) 'interests': interests,
    };
    return UserProfile.fromJson(
        (await _api.patch(_u('/users/me'), body: body)).map);
  }

  Future<List<UserProfile>> search(String q, {int offset = 0}) async {
    final r = await _api
        .get(_u('/users', {'q': q, 'limit': '20', 'offset': '$offset'}));
    return r.list
        .map((e) => UserProfile.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<UserProfile> user(int id) async =>
      UserProfile.fromJson((await _api.get(_u('/users/$id'))).map);

  Future<void> follow(int id) async {
    await _api.post(_u('/users/$id/follow'));
  }

  Future<void> unfollow(int id) async {
    await _api.delete(_u('/users/$id/follow'));
  }

  Future<List<UserProfile>> followers(int id) async =>
      (await _api.get(_u('/users/$id/followers', {'limit': '50'})))
          .list
          .map((e) => UserProfile.fromJson(e as Map<String, dynamic>))
          .toList();

  Future<List<UserProfile>> following(int id) async =>
      (await _api.get(_u('/users/$id/following', {'limit': '50'})))
          .list
          .map((e) => UserProfile.fromJson(e as Map<String, dynamic>))
          .toList();
}

class RecipeApi {
  RecipeApi(this._api, this._config);

  final ApiClient _api;
  final ApiConfig _config;

  Uri _u(String path, [Map<String, String>? q]) =>
      _config.uri(ApiConfig.recipePort, path, q);

  Future<List<Category>> categories() async =>
      (await _api.get(_u('/categories')))
          .list
          .map((e) => Category.fromJson(e as Map<String, dynamic>))
          .toList();

  Future<PagedResult<Recipe>> list({
    String q = '',
    String ingredient = '',
    String? category,
    String sort = 'popular',
    bool personalized = false,
    List<int>? ids,
    int limit = 20,
    int offset = 0,
  }) async {
    final r = await _api.get(_u('/recipes', {
      if (q.trim().isNotEmpty) 'q': q.trim(),
      if (ingredient.trim().isNotEmpty) 'ingredient': ingredient.trim(),
      if (category != null) 'category': category,
      if (ids != null) 'ids': ids.join(','),
      'sort': sort,
      if (personalized) 'personalized': 'true',
      'limit': '$limit',
      'offset': '$offset',
    }));
    final items =
        r.list.map((e) => Recipe.fromJson(e as Map<String, dynamic>)).toList();
    return PagedResult(items, r.totalCount ?? items.length);
  }

  Future<PagedResult<Recipe>> byUser(int userId, {int offset = 0}) async {
    final r = await _api.get(
        _u('/users/$userId/recipes', {'limit': '20', 'offset': '$offset'}));
    final items =
        r.list.map((e) => Recipe.fromJson(e as Map<String, dynamic>)).toList();
    return PagedResult(items, r.totalCount ?? items.length);
  }

  Future<Recipe> detail(int id) async =>
      Recipe.fromJson((await _api.get(_u('/recipes/$id'))).map);

  Future<List<Recipe>> related(int id) async =>
      (await _api.get(_u('/recipes/$id/related')))
          .list
          .map((e) => Recipe.fromJson(e as Map<String, dynamic>))
          .toList();

  Future<void> registerView(int id) async {
    await _api.post(_u('/recipes/$id/view'));
  }

  Future<Recipe> create(RecipeDraft draft) async => Recipe.fromJson(
      (await _api.post(_u('/recipes'), body: draft.toJson())).map);

  Future<Recipe> update(int id, RecipeDraft draft) async => Recipe.fromJson(
      (await _api.patch(_u('/recipes/$id'), body: draft.toJson())).map);

  Future<void> remove(int id) async {
    await _api.delete(_u('/recipes/$id'));
  }

  Future<Recipe> uploadImage(int id, String path) async => Recipe.fromJson(
      (await _api.uploadFile(_u('/recipes/$id/image'), path)).map);
}

class InteractionApi {
  InteractionApi(this._api, this._config);

  final ApiClient _api;
  final ApiConfig _config;

  Uri _u(String path, [Map<String, String>? q]) =>
      _config.uri(ApiConfig.interactionPort, path, q);

  Future<InteractionSummary> summary(int recipeId) async =>
      InteractionSummary.fromJson(
          (await _api.get(_u('/recipes/$recipeId/interactions'))).map);

  Future<PagedResult<Comment>> comments(int recipeId, {int offset = 0}) async {
    final r = await _api.get(_u(
        '/recipes/$recipeId/comments', {'limit': '20', 'offset': '$offset'}));
    final items =
        r.list.map((e) => Comment.fromJson(e as Map<String, dynamic>)).toList();
    return PagedResult(items, r.totalCount ?? items.length);
  }

  Future<Comment> addComment(int recipeId, String text) async =>
      Comment.fromJson((await _api
              .post(_u('/recipes/$recipeId/comments'), body: {'text': text}))
          .map);

  Future<Comment> editComment(int commentId, String text) async =>
      Comment.fromJson((await _api
              .patch(_u('/comments/$commentId'), body: {'text': text}))
          .map);

  Future<void> deleteComment(int commentId) async {
    await _api.delete(_u('/comments/$commentId'));
  }

  Future<void> like(int recipeId) async {
    await _api.post(_u('/recipes/$recipeId/like'));
  }

  Future<void> unlike(int recipeId) async {
    await _api.delete(_u('/recipes/$recipeId/like'));
  }

  Future<RatingSummary> rate(int recipeId, int score) async =>
      RatingSummary.fromJson((await _api
              .post(_u('/recipes/$recipeId/ratings'), body: {'score': score}))
          .map);

  Future<List<Collection>> collections() async =>
      (await _api.get(_u('/favorite-collections')))
          .list
          .map((e) => Collection.fromJson(e as Map<String, dynamic>))
          .toList();

  Future<Collection> createCollection(String name) async => Collection.fromJson(
      (await _api.post(_u('/favorite-collections'), body: {'name': name})).map);

  Future<void> deleteCollection(int id) async {
    await _api.delete(_u('/favorite-collections/$id'));
  }

  Future<Collection> addToCollection(int collectionId, int recipeId) async =>
      Collection.fromJson((await _api.post(
              _u('/favorite-collections/$collectionId/recipes/$recipeId')))
          .map);

  Future<void> removeFromCollection(int collectionId, int recipeId) async {
    await _api
        .delete(_u('/favorite-collections/$collectionId/recipes/$recipeId'));
  }

  Future<void> share(int recipeId, String username) async {
    await _api.post(_u('/recipes/$recipeId/share'),
        body: {'recipient_username': username});
  }

  Future<List<RecipeShare>> receivedShares() async =>
      (await _api.get(_u('/shares/received', {'limit': '50'})))
          .list
          .map((e) => RecipeShare.fromJson(e as Map<String, dynamic>))
          .toList();

  Future<List<Conversation>> conversations() async =>
      (await _api.get(_u('/messages/conversations')))
          .list
          .map((e) => Conversation.fromJson(e as Map<String, dynamic>))
          .toList();

  Future<List<Message>> messages(int userId, {int afterId = 0}) async =>
      (await _api.get(_u(
              '/messages/$userId', {'after_id': '$afterId', 'limit': '100'})))
          .list
          .map((e) => Message.fromJson(e as Map<String, dynamic>))
          .toList();

  Future<Message> sendMessage(int userId, String text) async =>
      Message.fromJson(
          (await _api.post(_u('/messages/$userId'), body: {'text': text})).map);
}

class NotificationPage {
  const NotificationPage(this.items, this.total, this.unread);

  final List<AppNotification> items;
  final int total;
  final int unread;
}

class ActivityApi {
  ActivityApi(this._api, this._config);

  final ApiClient _api;
  final ApiConfig _config;

  Uri _u(String path, [Map<String, String>? q]) =>
      _config.uri(ApiConfig.activityPort, path, q);

  Future<NotificationPage> notifications({int offset = 0}) async {
    final r = await _api
        .get(_u('/notifications', {'limit': '20', 'offset': '$offset'}));
    final items = r.list
        .map((e) => AppNotification.fromJson(e as Map<String, dynamic>))
        .toList();
    return NotificationPage(
        items, r.totalCount ?? items.length, r.unreadCount ?? 0);
  }

  Future<int> unreadCount() async =>
      ((await _api.get(_u('/notifications/unread-count'))).map['unread']
          as int?) ??
      0;

  Future<void> markRead(int id) async {
    await _api.post(_u('/notifications/$id/read'));
  }

  Future<void> markAllRead() async {
    await _api.post(_u('/notifications/read-all'));
  }

  Future<StatsTotals> stats(int days) async => StatsTotals.fromJson(
      ((await _api.get(_u('/stats/me', {'days': '$days'}))).map['totals']
              as Map<String, dynamic>?) ??
          const {});

  Future<List<DayPoint>> timeline(int days) async =>
      (await _api.get(_u('/stats/me/timeline', {'days': '$days'})))
          .list
          .map((e) => DayPoint.fromJson(e as Map<String, dynamic>))
          .toList();

  Future<List<TopRecipe>> topRecipes(int days, {String sort = 'views'}) async =>
      (await _api.get(_u('/stats/me/top-recipes',
              {'days': '$days', 'sort': sort, 'limit': '5'})))
          .list
          .map((e) => TopRecipe.fromJson(e as Map<String, dynamic>))
          .toList();
}
