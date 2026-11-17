import '../core/format.dart';

class Category {
  const Category({required this.slug, required this.name});

  factory Category.fromJson(Map<String, dynamic> json) =>
      Category(slug: json['slug'] as String, name: json['name'] as String);

  final String slug;
  final String name;
}

class Ingredient {
  const Ingredient({required this.name, this.quantity, this.unit});

  factory Ingredient.fromJson(Map<String, dynamic> json) => Ingredient(
        name: json['name'] as String,
        quantity: (json['quantity'] as num?)?.toDouble(),
        unit: json['unit'] as String?,
      );

  final String name;
  final double? quantity;
  final String? unit;

  /// Ex.: «200 g de farinha», «2 ovos», «sal».
  String get label {
    final parts = <String>[
      if (quantity != null) formatQuantity(quantity!),
      if (unit != null && unit!.isNotEmpty) unit!,
    ];
    if (parts.isEmpty) return name;
    final hasUnit = unit != null && unit!.isNotEmpty;
    return '${parts.join(' ')}${hasUnit ? ' de' : ''} $name';
  }

  Map<String, dynamic> toJson() =>
      {'name': name, 'quantity': quantity, 'unit': unit};
}

/// Receita. A listagem devolve só os campos de resumo; o detalhe acrescenta descrição, ingredientes, passos, etc.
class Recipe {
  Recipe({
    required this.id,
    required this.title,
    required this.authorId,
    this.authorUsername,
    required this.category,
    required this.difficulty,
    required this.preparationTime,
    this.imageUrl,
    this.ratingAvg,
    this.ratingCount = 0,
    this.viewCount = 0,
    this.likeCount = 0,
    this.commentCount = 0,
    required this.createdAt,
    this.description = '',
    this.ingredients = const [],
    this.steps = const [],
    this.tags = const [],
    this.servings = 0,
  });

  factory Recipe.fromJson(Map<String, dynamic> json) {
    final steps = ((json['preparation_steps'] as List<dynamic>?) ?? const [])
        .map((e) => e as Map<String, dynamic>)
        .toList()
      ..sort((a, b) => (a['order'] as int).compareTo(b['order'] as int));
    return Recipe(
      id: json['id'] as int,
      title: json['title'] as String,
      authorId: json['author_id'] as int,
      authorUsername: json['author_username'] as String?,
      category: Category.fromJson(json['category'] as Map<String, dynamic>),
      difficulty: json['difficulty'] as String,
      preparationTime: json['preparation_time'] as int,
      imageUrl: json['image_url'] as String?,
      ratingAvg: (json['rating_avg'] as num?)?.toDouble(),
      ratingCount: (json['rating_count'] as int?) ?? 0,
      viewCount: (json['view_count'] as int?) ?? 0,
      likeCount: (json['like_count'] as int?) ?? 0,
      commentCount: (json['comment_count'] as int?) ?? 0,
      createdAt: parseUtc(json['created_at'] as String),
      description: (json['description'] as String?) ?? '',
      ingredients: ((json['ingredients'] as List<dynamic>?) ?? const [])
          .map((e) => Ingredient.fromJson(e as Map<String, dynamic>))
          .toList(),
      steps: steps.map((e) => e['text'] as String).toList(),
      tags: ((json['tags'] as List<dynamic>?) ?? const [])
          .map((e) => e.toString())
          .toList(),
      servings: (json['servings'] as int?) ?? 0,
    );
  }

  final int id;
  final String title;
  final int authorId;
  final String? authorUsername;
  final Category category;
  final String difficulty;
  final int preparationTime;
  final String? imageUrl;
  final double? ratingAvg;
  final int ratingCount;
  final int viewCount;
  final int likeCount;
  final int commentCount;
  final DateTime createdAt;
  final String description;
  final List<Ingredient> ingredients;
  final List<String> steps;
  final List<String> tags;
  final int servings;

  /// Se o Users Service estiver em baixo o nome vem a `null`: mostra-se o número do autor.
  String get authorLabel => authorUsername ?? 'Autor #$authorId';
}

/// Dados do formulário de criação/edição.
class RecipeDraft {
  RecipeDraft({
    required this.title,
    required this.description,
    required this.category,
    required this.ingredients,
    required this.steps,
    required this.preparationTime,
    required this.servings,
    required this.difficulty,
    required this.tags,
  });

  final String title;
  final String description;
  final String category;
  final List<Ingredient> ingredients;
  final List<String> steps;
  final int preparationTime;
  final int servings;
  final String difficulty;
  final List<String> tags;

  Map<String, dynamic> toJson() => {
        'title': title,
        'description': description,
        'category': category,
        'ingredients': ingredients.map((e) => e.toJson()).toList(),
        'preparation_steps': steps,
        'preparation_time': preparationTime,
        'servings': servings,
        'difficulty': difficulty,
        'tags': tags,
      };
}

class PagedResult<T> {
  const PagedResult(this.items, this.total);

  final List<T> items;
  final int total;
}
