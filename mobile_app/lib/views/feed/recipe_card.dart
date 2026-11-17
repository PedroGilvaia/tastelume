import 'package:flutter/material.dart';

import '../../core/format.dart';
import '../../models/recipe.dart';
import '../common/widgets.dart';
import '../navigation.dart';

class RecipeCard extends StatelessWidget {
  const RecipeCard({super.key, required this.recipe});

  final Recipe recipe;

  @override
  Widget build(BuildContext context) {
    final muted = Theme.of(context)
        .textTheme
        .bodySmall
        ?.copyWith(color: Colors.grey.shade700);
    return Card(
      clipBehavior: Clip.antiAlias,
      margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      child: InkWell(
        onTap: () => openRecipe(context, recipe.id),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            RecipeImage(imageUrl: recipe.imageUrl, height: 170),
            Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(recipe.title,
                      style: Theme.of(context)
                          .textTheme
                          .titleMedium
                          ?.copyWith(fontWeight: FontWeight.bold)),
                  const SizedBox(height: 4),
                  Text(
                    '${recipe.category.name} · ${formatMinutes(recipe.preparationTime)} · ${difficultyLabel(recipe.difficulty)}',
                    style: muted,
                  ),
                  Text('por ${recipe.authorLabel}', style: muted),
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      Icon(Icons.star, size: 16, color: Colors.amber.shade700),
                      Text(' ${formatRating(recipe.ratingAvg)}', style: muted),
                      const SizedBox(width: 14),
                      const Icon(Icons.favorite,
                          size: 16, color: Colors.redAccent),
                      Text(' ${recipe.likeCount}', style: muted),
                      const SizedBox(width: 14),
                      const Icon(Icons.chat_bubble_outline,
                          size: 16, color: Colors.grey),
                      Text(' ${recipe.commentCount}', style: muted),
                      const SizedBox(width: 14),
                      const Icon(Icons.visibility_outlined,
                          size: 16, color: Colors.grey),
                      Text(' ${recipe.viewCount}', style: muted),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
