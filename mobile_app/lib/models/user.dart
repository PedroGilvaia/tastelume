import '../core/format.dart';

/// Perfil de utilizador. Serve para a resposta privada (`/users/me`, com email) e para a pública
/// (com contagens de seguidores e `isFollowing`).
class UserProfile {
  UserProfile({
    required this.id,
    required this.username,
    this.email,
    this.description = '',
    this.interests = const [],
    required this.createdAt,
    this.followersCount = 0,
    this.followingCount = 0,
    this.isFollowing,
  });

  factory UserProfile.fromJson(Map<String, dynamic> json) => UserProfile(
        id: json['id'] as int,
        username: json['username'] as String,
        email: json['email'] as String?,
        description: (json['description'] as String?) ?? '',
        interests: ((json['interests'] as List<dynamic>?) ?? const [])
            .map((e) => e.toString())
            .toList(),
        createdAt: parseUtc(json['created_at'] as String),
        followersCount: (json['followers_count'] as int?) ?? 0,
        followingCount: (json['following_count'] as int?) ?? 0,
        isFollowing: json['is_following'] as bool?,
      );

  final int id;
  final String username;
  final String? email;
  final String description;
  final List<String> interests;
  final DateTime createdAt;
  final int followersCount;
  final int followingCount;
  final bool? isFollowing;

  UserProfile copyWith({int? followersCount, bool? isFollowing}) => UserProfile(
        id: id,
        username: username,
        email: email,
        description: description,
        interests: interests,
        createdAt: createdAt,
        followersCount: followersCount ?? this.followersCount,
        followingCount: followingCount,
        isFollowing: isFollowing ?? this.isFollowing,
      );
}
