import '../core/format.dart';

class AppNotification {
  const AppNotification({
    required this.id,
    required this.type,
    this.actorId,
    this.recipeId,
    required this.text,
    required this.read,
    required this.createdAt,
  });

  factory AppNotification.fromJson(Map<String, dynamic> json) =>
      AppNotification(
        id: json['id'] as int,
        type: json['type'] as String,
        actorId: json['actor_id'] as int?,
        recipeId: json['recipe_id'] as int?,
        text: json['text'] as String,
        read: json['read'] as bool,
        createdAt: parseUtc(json['created_at'] as String),
      );

  final int id;
  final String type;
  final int? actorId;
  final int? recipeId;
  final String text;
  final bool read;
  final DateTime createdAt;

  AppNotification asRead() => AppNotification(
        id: id,
        type: type,
        actorId: actorId,
        recipeId: recipeId,
        text: text,
        read: true,
        createdAt: createdAt,
      );
}

class StatsTotals {
  const StatsTotals({
    this.views = 0,
    this.likes = 0,
    this.comments = 0,
    this.ratings = 0,
    this.shares = 0,
    this.newFollowers = 0,
    this.recipesPublished = 0,
  });

  factory StatsTotals.fromJson(Map<String, dynamic> json) => StatsTotals(
        views: (json['views'] as int?) ?? 0,
        likes: (json['likes'] as int?) ?? 0,
        comments: (json['comments'] as int?) ?? 0,
        ratings: (json['ratings'] as int?) ?? 0,
        shares: (json['shares'] as int?) ?? 0,
        newFollowers: (json['new_followers'] as int?) ?? 0,
        recipesPublished: (json['recipes_published'] as int?) ?? 0,
      );

  final int views;
  final int likes;
  final int comments;
  final int ratings;
  final int shares;
  final int newFollowers;
  final int recipesPublished;
}

class DayPoint {
  const DayPoint({
    required this.date,
    this.views = 0,
    this.likes = 0,
    this.comments = 0,
    this.ratings = 0,
    this.shares = 0,
  });

  factory DayPoint.fromJson(Map<String, dynamic> json) => DayPoint(
        date: DateTime.parse(json['date'] as String),
        views: (json['views'] as int?) ?? 0,
        likes: (json['likes'] as int?) ?? 0,
        comments: (json['comments'] as int?) ?? 0,
        ratings: (json['ratings'] as int?) ?? 0,
        shares: (json['shares'] as int?) ?? 0,
      );

  final DateTime date;
  final int views;
  final int likes;
  final int comments;
  final int ratings;
  final int shares;

  int get interactions => likes + comments + ratings + shares;
}

class TopRecipe {
  const TopRecipe({
    required this.recipeId,
    this.title,
    this.views = 0,
    this.likes = 0,
    this.comments = 0,
    this.ratings = 0,
    this.shares = 0,
  });

  factory TopRecipe.fromJson(Map<String, dynamic> json) => TopRecipe(
        recipeId: json['recipe_id'] as int,
        title: json['title'] as String?,
        views: (json['views'] as int?) ?? 0,
        likes: (json['likes'] as int?) ?? 0,
        comments: (json['comments'] as int?) ?? 0,
        ratings: (json['ratings'] as int?) ?? 0,
        shares: (json['shares'] as int?) ?? 0,
      );

  final int recipeId;
  final String? title;
  final int views;
  final int likes;
  final int comments;
  final int ratings;
  final int shares;

  String get label => title ?? 'Receita #$recipeId';
}
