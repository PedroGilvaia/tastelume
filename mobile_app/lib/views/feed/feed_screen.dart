import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../services/backend.dart';
import '../../viewmodels/feed_viewmodel.dart';
import '../common/widgets.dart';
import '../navigation.dart';
import 'recipe_card.dart';

const _sortLabels = <String, String>{
  'popular': 'Populares',
  'recent': 'Recentes',
  'rating': 'Melhor avaliadas',
  'views': 'Mais vistas',
};

class FeedScreen extends StatelessWidget {
  const FeedScreen({super.key});

  @override
  Widget build(BuildContext context) => ChangeNotifierProvider(
        create: (c) => FeedViewModel(c.read<RecipeApi>())..start(),
        child: const _FeedView(),
      );
}

class _FeedView extends StatelessWidget {
  const _FeedView();

  Future<void> _create(BuildContext context) async {
    final vm = context.read<FeedViewModel>();
    final created = await openRecipeForm(context);
    if (created == true) vm.refresh();
  }

  @override
  Widget build(BuildContext context) {
    final vm = context.watch<FeedViewModel>();
    return Scaffold(
      appBar: AppBar(
        title: const Text('Tastelume'),
        actions: [
          IconButton(
            tooltip: 'Mensagens',
            icon: const Icon(Icons.mail_outline),
            onPressed: () => openMessages(context),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => _create(context),
        icon: const Icon(Icons.add_a_photo_outlined),
        label: const Text('Nova receita'),
      ),
      body: Column(
        children: [
          _Filters(vm: vm),
          if (vm.error != null && vm.items.isNotEmpty)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12),
              child: InlineNotice(message: vm.error!, onRetry: vm.refresh),
            ),
          Expanded(child: _Content(vm: vm)),
        ],
      ),
    );
  }
}

class _Filters extends StatelessWidget {
  const _Filters({required this.vm});

  final FeedViewModel vm;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          padding: const EdgeInsets.symmetric(horizontal: 12),
          child: Row(
            children: [
              FilterChip(
                avatar: const Icon(Icons.auto_awesome, size: 16),
                label: const Text('Para ti'),
                selected: vm.personalized,
                onSelected: vm.setPersonalized,
              ),
              const SizedBox(width: 8),
              for (final entry in _sortLabels.entries) ...[
                ChoiceChip(
                  label: Text(entry.value),
                  selected: vm.sort == entry.key,
                  onSelected: (_) => vm.setSort(entry.key),
                ),
                const SizedBox(width: 8),
              ],
            ],
          ),
        ),
        if (vm.categories.isNotEmpty)
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            padding: const EdgeInsets.symmetric(horizontal: 12),
            child: Row(
              children: [
                ChoiceChip(
                  label: const Text('Todas'),
                  selected: vm.category == null,
                  onSelected: (_) => vm.setCategory(null),
                ),
                const SizedBox(width: 8),
                for (final c in vm.categories) ...[
                  ChoiceChip(
                    label: Text(c.name),
                    selected: vm.category == c.slug,
                    onSelected: (_) => vm.setCategory(c.slug),
                  ),
                  const SizedBox(width: 8),
                ],
              ],
            ),
          ),
      ],
    );
  }
}

class _Content extends StatelessWidget {
  const _Content({required this.vm});

  final FeedViewModel vm;

  @override
  Widget build(BuildContext context) {
    if (vm.loading && vm.items.isEmpty)
      return const Center(child: CircularProgressIndicator());
    if (vm.error != null && vm.items.isEmpty)
      return ErrorState(message: vm.error!, onRetry: vm.refresh);
    if (vm.items.isEmpty) {
      return RefreshIndicator(
        onRefresh: vm.refresh,
        child: ListView(children: const [
          SizedBox(height: 120),
          EmptyState(
              icon: Icons.restaurant_menu,
              message:
                  'Ainda não há receitas aqui.\nSê o primeiro a partilhar uma!'),
        ]),
      );
    }
    return EndlessScroll(
      onEnd: vm.loadMore,
      child: RefreshIndicator(
        onRefresh: vm.refresh,
        child: ListView.builder(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.only(top: 4, bottom: 88),
          itemCount: vm.items.length + 1,
          itemBuilder: (context, i) {
            if (i < vm.items.length) return RecipeCard(recipe: vm.items[i]);
            if (vm.loadingMore) {
              return const Padding(
                  padding: EdgeInsets.all(16),
                  child: Center(child: CircularProgressIndicator()));
            }
            if (vm.loadMoreError != null) {
              return Padding(
                padding: const EdgeInsets.symmetric(horizontal: 12),
                child: InlineNotice(
                    message: vm.loadMoreError!, onRetry: vm.loadMore),
              );
            }
            return const SizedBox.shrink();
          },
        ),
      ),
    );
  }
}
