import 'package:flutter_test/flutter_test.dart';
import 'package:tastelume/models/activity.dart';
import 'package:tastelume/models/interaction.dart';
import 'package:tastelume/models/recipe.dart';
import 'package:tastelume/models/user.dart';

Map<String, dynamic> recipeJson({String? author = 'ana'}) => {
      'id': 7,
      'title': 'Caldo verde',
      'author_id': 1,
      'author_username': author,
      'category': {'slug': 'sopas', 'name': 'Sopas'},
      'difficulty': 'facil',
      'preparation_time': 40,
      'image_url': '/images/a.png',
      'rating_avg': 4.5,
      'rating_count': 2,
      'view_count': 10,
      'like_count': 3,
      'comment_count': 1,
      'created_at': '2026-11-11T10:00:00',
      'description': 'Sopa',
      'ingredients': [
        {'name': 'batata', 'quantity': 500, 'unit': 'g'}
      ],
      'preparation_steps': [
        {'order': 2, 'text': 'Servir'},
        {'order': 1, 'text': 'Cozer'},
      ],
      'tags': ['tradicional'],
      'servings': 4,
    };

void main() {
  test('Recipe.fromJson ordena os passos e lê os contadores', () {
    final r = Recipe.fromJson(recipeJson());
    expect(r.steps, ['Cozer', 'Servir']);
    expect(r.ingredients.single.label, '500 g de batata');
    expect(r.likeCount, 3);
    expect(r.ratingAvg, 4.5);
    expect(r.category.name, 'Sopas');
  });

  test('autor desconhecido (Users Service em baixo) usa um nome de recurso',
      () {
    expect(Recipe.fromJson(recipeJson(author: null)).authorLabel, 'Autor #1');
  });

  test('resumo de receita sem campos de detalhe', () {
    final json = recipeJson()
      ..remove('ingredients')
      ..remove('preparation_steps')
      ..remove('tags')
      ..remove('description')
      ..remove('servings');
    final r = Recipe.fromJson(json);
    expect(r.ingredients, isEmpty);
    expect(r.steps, isEmpty);
  });

  test('UserProfile aceita resposta privada e pública', () {
    final priv = UserProfile.fromJson({
      'id': 1,
      'username': 'ana',
      'email': 'a@b.pt',
      'created_at': '2026-01-01T00:00:00'
    });
    expect(priv.email, 'a@b.pt');
    expect(priv.followersCount, 0);
    final pub = UserProfile.fromJson({
      'id': 2,
      'username': 'rui',
      'created_at': '2026-01-01T00:00:00',
      'followers_count': 5,
      'following_count': 2,
      'is_following': true,
      'interests': ['Sopas'],
    });
    expect(pub.isFollowing, isTrue);
    expect(
        pub.copyWith(isFollowing: false, followersCount: 4).followersCount, 4);
  });

  test('InteractionSummary e comentários', () {
    final s = InteractionSummary.fromJson({
      'like_count': 2,
      'comment_count': 1,
      'rating': {
        'average': 4.0,
        'count': 1,
        'distribution': {'4': 1},
        'my_score': 4
      },
      'my_like': true,
    });
    expect(s.rating.myScore, 4);
    expect(s.copyWith(likeCount: 3).likeCount, 3);
    final c = Comment.fromJson({
      'id': 1,
      'recipe_id': 7,
      'user_id': 3,
      'username': null,
      'text': 'ótimo',
      'created_at': '2026-11-11T10:00:00',
      'updated_at': '2026-11-11T11:00:00',
    });
    expect(c.authorLabel, 'Utilizador #3');
    expect(c.edited, isTrue);
  });

  test('notificações e estatísticas', () {
    final n = AppNotification.fromJson({
      'id': 1,
      'type': 'like',
      'actor_id': 2,
      'recipe_id': 7,
      'text': 'rui gostou da tua receita',
      'read': false,
      'created_at': '2026-11-11T10:00:00',
    });
    expect(n.asRead().read, isTrue);
    final p = DayPoint.fromJson(
        {'date': '2026-11-11', 'views': 3, 'likes': 1, 'comments': 1});
    expect(p.interactions, 2);
    expect(const TopRecipe(recipeId: 4).label, 'Receita #4');
  });
}
