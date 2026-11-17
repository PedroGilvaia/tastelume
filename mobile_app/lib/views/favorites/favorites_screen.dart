import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../models/interaction.dart';
import '../../services/backend.dart';
import '../../viewmodels/favorites_viewmodel.dart';
import '../common/widgets.dart';
import '../feed/recipe_card.dart';
import '../navigation.dart';

class FavoritesScreen extends StatelessWidget {
  const FavoritesScreen({super.key});

  @override
  Widget build(BuildContext context) => ChangeNotifierProvider(
        create: (c) => FavoritesViewModel(c.read<InteractionApi>())..load(),
        child: const _FavoritesView(),
      );
}

class _FavoritesView extends StatelessWidget {
  const _FavoritesView();

  Future<void> _create(BuildContext context, FavoritesViewModel vm) async {
    final name = await promptText(context,
        title: 'Nova lista', label: 'Nome', maxLength: 60, action: 'Criar');
    if (name == null) return;
    final error = await vm.create(name);
    if (error != null && context.mounted) showSnack(context, error);
  }

  Future<void> _remove(
      BuildContext context, FavoritesViewModel vm, Collection c) async {
    if (!await confirm(context, 'Apagar lista',
        'Apagar «${c.name}»? As receitas não são apagadas.', action: 'Apagar'))
      return;
    final error = await vm.remove(c);
    if (error != null && context.mounted) showSnack(context, error);
  }

  @override
  Widget build(BuildContext context) {
    final vm = context.watch<FavoritesViewModel>();
    Widget body;
    if (vm.loading) {
      body = const Center(child: CircularProgressIndicator());
    } else if (vm.error != null) {
      body = ErrorState(message: vm.error!, onRetry: vm.load);
    } else if (vm.collections.isEmpty) {
      body = const EmptyState(
          icon: Icons.bookmark_border,
          message:
              'Ainda não tens listas.\nCria uma e guarda as tuas receitas favoritas.');
    } else {
      body = RefreshIndicator(
        onRefresh: vm.load,
        child: ListView(
          children: [
            for (final c in vm.collections)
              ListTile(
                leading: const Icon(Icons.bookmark),
                title: Text(c.name),
                subtitle: Text('${c.recipeIds.length} receitas'),
                trailing: IconButton(
                    icon: const Icon(Icons.delete_outline),
                    onPressed: () => _remove(context, vm, c)),
                onTap: () async {
                  await openCollection(context, c);
                  vm.load();
                },
              ),
          ],
        ),
      );
    }
    return Scaffold(
      appBar: AppBar(title: const Text('Favoritos')),
      floatingActionButton: FloatingActionButton(
          onPressed: () => _create(context, vm), child: const Icon(Icons.add)),
      body: body,
    );
  }
}

class CollectionScreen extends StatelessWidget {
  const CollectionScreen({super.key, required this.collection});

  final Collection collection;

  @override
  Widget build(BuildContext context) => ChangeNotifierProvider(
        create: (c) => CollectionViewModel(
            collection, c.read<RecipeApi>(), c.read<InteractionApi>())
          ..load(),
        child: const _CollectionView(),
      );
}

class _CollectionView extends StatelessWidget {
  const _CollectionView();

  @override
  Widget build(BuildContext context) {
    final vm = context.watch<CollectionViewModel>();
    Widget body;
    if (vm.loading) {
      body = const Center(child: CircularProgressIndicator());
    } else if (vm.error != null) {
      body = ErrorState(message: vm.error!, onRetry: vm.load);
    } else if (vm.recipes.isEmpty) {
      body = const EmptyState(
          icon: Icons.restaurant_menu, message: 'Esta lista está vazia.');
    } else {
      body = ListView(
        padding: const EdgeInsets.only(bottom: 24),
        children: [
          for (final r in vm.recipes)
            Dismissible(
              key: ValueKey(r.id),
              direction: DismissDirection.endToStart,
              background: Container(
                color: Colors.red.shade400,
                alignment: Alignment.centerRight,
                padding: const EdgeInsets.only(right: 20),
                child: const Icon(Icons.bookmark_remove, color: Colors.white),
              ),
              confirmDismiss: (_) async {
                final error = await vm.removeRecipe(r);
                if (error != null && context.mounted) showSnack(context, error);
                return false; // a lista já foi atualizada pelo ViewModel
              },
              child: RecipeCard(recipe: r),
            ),
        ],
      );
    }
    return Scaffold(
        appBar: AppBar(title: Text(vm.collection.name)), body: body);
  }
}
