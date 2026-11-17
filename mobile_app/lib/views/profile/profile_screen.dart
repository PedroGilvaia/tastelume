import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../models/user.dart';
import '../../services/backend.dart';
import '../../viewmodels/auth_viewmodel.dart';
import '../../viewmodels/profile_viewmodel.dart';
import '../common/widgets.dart';
import '../feed/recipe_card.dart';
import '../navigation.dart';
import 'edit_profile_screen.dart';

/// Perfil próprio (separador) ou de outro utilizador (ecrã empurrado).
class ProfileScreen extends StatefulWidget {
  const ProfileScreen(
      {super.key,
      required this.userId,
      this.isTab = false,
      this.refreshTick = 0});

  final int userId;
  final bool isTab;

  /// Quando muda, o separador recarrega (p. ex. depois de publicar uma receita).
  final int refreshTick;

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  late final ProfileViewModel _vm;

  @override
  void initState() {
    super.initState();
    _vm = ProfileViewModel(
      widget.userId,
      context.read<UsersApi>(),
      context.read<RecipeApi>(),
      context.read<AuthViewModel>().me!.id,
    )..load();
  }

  @override
  void didUpdateWidget(covariant ProfileScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.refreshTick != widget.refreshTick) _vm.load();
  }

  @override
  void dispose() {
    _vm.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) =>
      ChangeNotifierProvider<ProfileViewModel>.value(
        value: _vm,
        child: _ProfileView(isTab: widget.isTab),
      );
}

class _ProfileView extends StatelessWidget {
  const _ProfileView({required this.isTab});

  final bool isTab;

  Future<void> _edit(BuildContext context, ProfileViewModel vm) async {
    final changed = await Navigator.of(context).push<bool>(
        MaterialPageRoute(builder: (_) => const EditProfileScreen()));
    if (changed == true) vm.load();
  }

  Future<void> _logout(BuildContext context) async {
    final auth = context.read<AuthViewModel>();
    if (await confirm(context, 'Terminar sessão', 'Queres sair da tua conta?',
        action: 'Sair')) auth.logout();
  }

  @override
  Widget build(BuildContext context) {
    final vm = context.watch<ProfileViewModel>();
    final user = vm.user;
    return Scaffold(
      appBar: AppBar(
        title: Text(user?.username ?? 'Perfil'),
        actions: [
          if (vm.isMe) ...[
            IconButton(
                tooltip: 'Editar perfil',
                icon: const Icon(Icons.edit_outlined),
                onPressed: () => _edit(context, vm)),
            IconButton(
                tooltip: 'Terminar sessão',
                icon: const Icon(Icons.logout),
                onPressed: () => _logout(context)),
          ],
        ],
      ),
      body: _body(context, vm, user),
    );
  }

  Widget _body(BuildContext context, ProfileViewModel vm, UserProfile? user) {
    if (vm.loading && user == null)
      return const Center(child: CircularProgressIndicator());
    if (user == null)
      return ErrorState(
          message: vm.error ?? 'Perfil indisponível.', onRetry: vm.load);
    return EndlessScroll(
      onEnd: vm.loadMore,
      child: RefreshIndicator(
        onRefresh: vm.load,
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.only(bottom: 24),
          children: [
            Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Avatar(name: user.username, radius: 34),
                      const SizedBox(width: 16),
                      Expanded(
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.spaceAround,
                          children: [
                            _Count(label: 'Receitas', value: vm.recipeTotal),
                            _Count(
                              label: 'Seguidores',
                              value: user.followersCount,
                              onTap: () => _openList(
                                  context,
                                  'Seguidores de ${user.username}',
                                  () => context
                                      .read<UsersApi>()
                                      .followers(user.id)),
                            ),
                            _Count(
                              label: 'A seguir',
                              value: user.followingCount,
                              onTap: () => _openList(
                                  context,
                                  'A seguir',
                                  () => context
                                      .read<UsersApi>()
                                      .following(user.id)),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  if (user.description.isNotEmpty) Text(user.description),
                  if (user.interests.isNotEmpty) ...[
                    const SizedBox(height: 8),
                    Wrap(spacing: 6, children: [
                      for (final i in user.interests) Chip(label: Text(i))
                    ]),
                  ],
                  const SizedBox(height: 12),
                  if (vm.isMe)
                    Wrap(
                      spacing: 8,
                      children: [
                        OutlinedButton.icon(
                            onPressed: () => openFavorites(context),
                            icon: const Icon(Icons.bookmark_border),
                            label: const Text('Favoritos')),
                        OutlinedButton.icon(
                            onPressed: () => openStats(context),
                            icon: const Icon(Icons.insights),
                            label: const Text('Estatísticas')),
                        OutlinedButton.icon(
                            onPressed: () => openMessages(context),
                            icon: const Icon(Icons.mail_outline),
                            label: const Text('Mensagens')),
                      ],
                    )
                  else
                    Row(
                      children: [
                        Expanded(
                          child: FilledButton(
                            onPressed: vm.followBusy
                                ? null
                                : () async {
                                    final error = await vm.toggleFollow();
                                    if (error != null && context.mounted)
                                      showSnack(context, error);
                                  },
                            child: Text((user.isFollowing ?? false)
                                ? 'A seguir ✓'
                                : 'Seguir'),
                          ),
                        ),
                        const SizedBox(width: 8),
                        OutlinedButton.icon(
                          onPressed: () =>
                              openChat(context, user.id, user.username),
                          icon: const Icon(Icons.chat_bubble_outline),
                          label: const Text('Mensagem'),
                        ),
                      ],
                    ),
                ],
              ),
            ),
            const Divider(height: 1),
            if (vm.recipesError != null && vm.recipes.isEmpty)
              Padding(
                padding: const EdgeInsets.all(12),
                child: InlineNotice(
                    message: 'As receitas estão indisponíveis de momento.',
                    onRetry: vm.loadRecipes),
              )
            else if (vm.recipes.isEmpty)
              const Padding(
                padding: EdgeInsets.all(32),
                child: EmptyState(
                    icon: Icons.restaurant_menu,
                    message: 'Ainda não publicou receitas.'),
              )
            else
              for (final r in vm.recipes) RecipeCard(recipe: r),
            if (vm.loadingMore)
              const Padding(
                  padding: EdgeInsets.all(16),
                  child: Center(child: CircularProgressIndicator())),
          ],
        ),
      ),
    );
  }

  void _openList(BuildContext context, String title,
      Future<List<UserProfile>> Function() loader) {
    Navigator.of(context).push(MaterialPageRoute<void>(
        builder: (_) => UserListScreen(title: title, loader: loader)));
  }
}

class _Count extends StatelessWidget {
  const _Count({required this.label, required this.value, this.onTap});

  final String label;
  final int value;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) => InkWell(
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(4),
          child: Column(
            children: [
              Text('$value',
                  style: Theme.of(context)
                      .textTheme
                      .titleLarge
                      ?.copyWith(fontWeight: FontWeight.bold)),
              Text(label, style: Theme.of(context).textTheme.bodySmall),
            ],
          ),
        ),
      );
}

class UserListScreen extends StatelessWidget {
  const UserListScreen({super.key, required this.title, required this.loader});

  final String title;
  final Future<List<UserProfile>> Function() loader;

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: Text(title)),
        body: FutureBuilder<List<UserProfile>>(
          future: loader(),
          builder: (context, snapshot) {
            if (snapshot.connectionState != ConnectionState.done)
              return const Center(child: CircularProgressIndicator());
            if (snapshot.hasError) {
              final error = snapshot.error;
              return ErrorState(
                  message: error is Exception
                      ? error.toString()
                      : 'Não foi possível carregar a lista.');
            }
            final users = snapshot.data ?? const [];
            if (users.isEmpty)
              return const EmptyState(
                  icon: Icons.people_outline,
                  message: 'Ainda não há ninguém aqui.');
            return ListView(
              children: [
                for (final u in users)
                  ListTile(
                    leading: Avatar(name: u.username),
                    title: Text(u.username),
                    subtitle: u.description.isEmpty
                        ? null
                        : Text(u.description,
                            maxLines: 1, overflow: TextOverflow.ellipsis),
                    onTap: () => openProfile(context, u.id),
                  ),
              ],
            );
          },
        ),
      );
}
