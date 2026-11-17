import '../core/format.dart';

class RatingSummary {
  const RatingSummary(
      {this.average,
      this.count = 0,
      this.distribution = const {},
      this.myScore});

  factory RatingSummary.fromJson(Map<String, dynamic> json) => RatingSummary(
        average: (json['average'] as num?)?.toDouble(),
        count: (json['count'] as int?) ?? 0,
        distribution:
            ((json['distribution'] as Map<String, dynamic>?) ?? const {})
                .map((k, v) => MapEntry(k, (v as num).toInt())),
        myScore: json['my_score'] as int?,
      );

  final double? average;
  final int count;
  final Map<String, int> distribution;
  final int? myScore;
}

class InteractionSummary {
  const InteractionSummary({
    required this.likeCount,
    required this.commentCount,
    required this.rating,
    this.myLike,
  });

  factory InteractionSummary.fromJson(Map<String, dynamic> json) =>
      InteractionSummary(
        likeCount: (json['like_count'] as int?) ?? 0,
        commentCount: (json['comment_count'] as int?) ?? 0,
        rating: RatingSummary.fromJson(
            (json['rating'] as Map<String, dynamic>?) ?? const {}),
        myLike: json['my_like'] as bool?,
      );

  final int likeCount;
  final int commentCount;
  final RatingSummary rating;
  final bool? myLike;

  InteractionSummary copyWith(
          {int? likeCount,
          int? commentCount,
          RatingSummary? rating,
          bool? myLike}) =>
      InteractionSummary(
        likeCount: likeCount ?? this.likeCount,
        commentCount: commentCount ?? this.commentCount,
        rating: rating ?? this.rating,
        myLike: myLike ?? this.myLike,
      );
}

class Comment {
  const Comment({
    required this.id,
    required this.recipeId,
    required this.userId,
    this.username,
    required this.text,
    required this.createdAt,
    this.edited = false,
  });

  factory Comment.fromJson(Map<String, dynamic> json) => Comment(
        id: json['id'] as int,
        recipeId: json['recipe_id'] as int,
        userId: json['user_id'] as int,
        username: json['username'] as String?,
        text: json['text'] as String,
        createdAt: parseUtc(json['created_at'] as String),
        edited: json['updated_at'] != null,
      );

  final int id;
  final int recipeId;
  final int userId;
  final String? username;
  final String text;
  final DateTime createdAt;
  final bool edited;

  String get authorLabel => username ?? 'Utilizador #$userId';
}

class Collection {
  const Collection(
      {required this.id, required this.name, required this.recipeIds});

  factory Collection.fromJson(Map<String, dynamic> json) => Collection(
        id: json['id'] as int,
        name: json['name'] as String,
        recipeIds: ((json['recipe_ids'] as List<dynamic>?) ?? const [])
            .map((e) => e as int)
            .toList(),
      );

  final int id;
  final String name;
  final List<int> recipeIds;
}

class RecipeShare {
  const RecipeShare({
    required this.id,
    required this.senderId,
    this.senderUsername,
    required this.recipeId,
    this.recipeTitle,
    required this.createdAt,
  });

  factory RecipeShare.fromJson(Map<String, dynamic> json) => RecipeShare(
        id: json['id'] as int,
        senderId: json['sender_id'] as int,
        senderUsername: json['sender_username'] as String?,
        recipeId: json['recipe_id'] as int,
        recipeTitle: json['recipe_title'] as String?,
        createdAt: parseUtc(json['created_at'] as String),
      );

  final int id;
  final int senderId;
  final String? senderUsername;
  final int recipeId;
  final String? recipeTitle;
  final DateTime createdAt;
}

class Message {
  const Message({
    required this.id,
    required this.senderId,
    required this.recipientId,
    required this.text,
    required this.createdAt,
    this.read = false,
  });

  factory Message.fromJson(Map<String, dynamic> json) => Message(
        id: json['id'] as int,
        senderId: json['sender_id'] as int,
        recipientId: json['recipient_id'] as int,
        text: json['text'] as String,
        createdAt: parseUtc(json['created_at'] as String),
        read: json['read_at'] != null,
      );

  final int id;
  final int senderId;
  final int recipientId;
  final String text;
  final DateTime createdAt;
  final bool read;
}

class Conversation {
  const Conversation(
      {required this.userId,
      this.username,
      required this.last,
      required this.unread});

  factory Conversation.fromJson(Map<String, dynamic> json) => Conversation(
        userId: json['user_id'] as int,
        username: json['username'] as String?,
        last: Message.fromJson(json['last_message'] as Map<String, dynamic>),
        unread: (json['unread_count'] as int?) ?? 0,
      );

  final int userId;
  final String? username;
  final Message last;
  final int unread;

  String get label => username ?? 'Utilizador #$userId';
}
