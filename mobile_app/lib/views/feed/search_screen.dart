import 'dart:async';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../services/backend.dart';
import '../../viewmodels/search_viewmodel.dart';
import '../common/widgets.dart';
import '../navigation.dart';
import 'recipe_card.dart';

class SearchScreen extends StatelessWidget {
  const SearchScreen({super.key});

  @override
  Widget build(BuildContext context) => ChangeNotifierProvider(
        create: (c) => SearchViewModel(c.read<RecipeApi>(), c.read<UsersApi>()),
        child: const _SearchView(),
      );
}

class _SearchView extends StatefulWidget {
  const _SearchView();

  @override
  State<_SearchView> createState() => _SearchViewState();
}

class _SearchViewState extends State<_SearchView> {
  final _controller = TextEditingController();
  Timer? _debounce;

  @override
  void dispose() {
    _debounce?.cancel();
    _controller.dispose();
    super.dispose();
  }

  void _onChanged(String text) {
    _debounce?.cancel();
    final vm = context.read<SearchViewModel>();
    _debounce = Timer(const Duration(milliseconds: 400), () => vm.search(text));
  }

  @override
  Widget build(BuildContext context) {
    final vm = context.watch<SearchViewModel>();
    return Scaffold(
      appBar: AppBar(title: const Text('Procurar')),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(12, 8, 12, 0),
            child: TextField(
              controller: _controller,
              onChanged: _onChanged,
              textInputAction: TextInputAction.search,
              onSubmitted: vm.search,
              decoration: InputDecoration(
                hintText: vm.mode == SearchMode.users
                    ? 'Nome de utilizador'
                    : (vm.byIngredient
                        ? 'Ingrediente (ex.: bacalhau)'
                        : 'Título, descrição ou ingrediente'),
                prefixIcon: const Icon(Icons.search),
                suffixIcon: _controller.text.isEmpty
                    ? null
                    : IconButton(
                        icon: const Icon(Icons.clear),
                        onPressed: () {
                          _controller.clear();
                          vm.search('');
                        },
                      ),
                border: const OutlineInputBorder(),
                isDense: true,
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12),
            child: Wrap(
              spacing: 8,
              children: [
                ChoiceChip(
                  label: const Text('Receitas'),
                  selected: vm.mode == SearchMode.recipes,
                  onSelected: (_) => vm.setMode(SearchMode.recipes),
                ),
                ChoiceChip(
                  label: const Text('Utilizadores'),
                  selected: vm.mode == SearchMode.users,
                  onSelected: (_) => vm.setMode(SearchMode.users),
                ),
                if (vm.mode == SearchMode.recipes)
                  FilterChip(
                    label: const Text('Só ingredientes'),
                    selected: vm.byIngredient,
                    onSelected: vm.setByIngredient,
                  ),
              ],
            ),
          ),
          Expanded(child: _Results(vm: vm)),
        ],
      ),
    );
  }
}

class _Results extends StatelessWidget {
  const _Results({required this.vm});

  final SearchViewModel vm;

  @override
  Widget build(BuildContext context) {
    if (vm.loading) return const Center(child: CircularProgressIndicator());
    if (vm.error != null)
      return ErrorState(message: vm.error!, onRetry: () => vm.search());
    if (!vm.searched) {
      return const EmptyState(
          icon: Icons.search,
          message: 'Escreve para procurar receitas ou pessoas.');
    }
    if (vm.mode == SearchMode.users) {
      if (vm.userResults.isEmpty)
        return const EmptyState(
            icon: Icons.person_search,
            message: 'Nenhum utilizador encontrado.');
      return ListView(
        children: [
          for (final u in vm.userResults)
            ListTile(
              leading: Avatar(name: u.username),
              title: Text(u.username),
              subtitle: Text(
                  u.description.isEmpty
                      ? '${u.followersCount} seguidores'
                      : u.description,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis),
              onTap: () => openProfile(context, u.id),
            ),
        ],
      );
    }
    if (vm.recipeResults.isEmpty)
      return const EmptyState(
          icon: Icons.no_food, message: 'Nenhuma receita encontrada.');
    return EndlessScroll(
      onEnd: vm.loadMore,
      child: ListView.builder(
        padding: const EdgeInsets.only(top: 4, bottom: 24),
        itemCount: vm.recipeResults.length + (vm.loadingMore ? 1 : 0),
        itemBuilder: (context, i) {
          if (i >= vm.recipeResults.length) {
            return const Padding(
                padding: EdgeInsets.all(16),
                child: Center(child: CircularProgressIndicator()));
          }
          return RecipeCard(recipe: vm.recipeResults[i]);
        },
      ),
    );
  }
}
