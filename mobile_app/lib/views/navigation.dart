import 'package:flutter/material.dart';

import '../models/interaction.dart';
import '../models/recipe.dart';
import 'favorites/favorites_screen.dart';
import 'messages/chat_screen.dart';
import 'messages/messages_screen.dart';
import 'profile/profile_screen.dart';
import 'recipe/recipe_detail_screen.dart';
import 'recipe/recipe_form_screen.dart';
import 'stats/stats_screen.dart';

Future<T?> _push<T>(BuildContext context, Widget screen) =>
    Navigator.of(context).push<T>(MaterialPageRoute<T>(builder: (_) => screen));

Future<void> openRecipe(BuildContext context, int id) =>
    _push(context, RecipeDetailScreen(recipeId: id));

Future<void> openProfile(BuildContext context, int userId) =>
    _push(context, ProfileScreen(userId: userId));

Future<void> openChat(BuildContext context, int userId, String? username) =>
    _push(context, ChatScreen(userId: userId, username: username));

Future<void> openMessages(BuildContext context) =>
    _push(context, const MessagesScreen());

Future<void> openFavorites(BuildContext context) =>
    _push(context, const FavoritesScreen());

Future<void> openStats(BuildContext context) =>
    _push(context, const StatsScreen());

Future<void> openCollection(BuildContext context, Collection collection) =>
    _push(context, CollectionScreen(collection: collection));

/// Devolve a receita criada/atualizada (ou `null` se o utilizador cancelou).
Future<bool?> openRecipeForm(BuildContext context, {Recipe? existing}) =>
    _push<bool>(context, RecipeFormScreen(existingRecipe: existing));
