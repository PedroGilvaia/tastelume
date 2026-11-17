import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/format.dart';
import '../../services/backend.dart';
import '../../viewmodels/auth_viewmodel.dart';
import '../../viewmodels/messages_viewmodel.dart';
import '../common/widgets.dart';
import '../navigation.dart';

class MessagesScreen extends StatelessWidget {
  const MessagesScreen({super.key});

  @override
  Widget build(BuildContext context) => ChangeNotifierProvider(
        create: (c) => MessagesViewModel(c.read<InteractionApi>())..load(),
        child: const _MessagesView(),
      );
}

class _MessagesView extends StatelessWidget {
  const _MessagesView();

  Future<void> _newChat(BuildContext context, MessagesViewModel vm) async {
    final users = context.read<UsersApi>();
    final myId = context.read<AuthViewModel>().me!.id;
    final username = await promptText(context,
        title: 'Nova conversa',
        label: 'Nome de utilizador',
        maxLength: 30,
        action: 'Abrir');
    if (username == null) return;
    try {
      final found = await users.search(username.replaceFirst('@', ''));
      final match = found
          .where((u) =>
              u.username.toLowerCase() ==
              username.replaceFirst('@', '').toLowerCase())
          .toList();
      if (!context.mounted) return;
      if (match.isEmpty) {
        showSnack(context, 'Utilizador «$username» não encontrado.');
      } else if (match.first.id == myId) {
        showSnack(context, 'Não podes enviar mensagens a ti próprio.');
      } else {
        await openChat(context, match.first.id, match.first.username);
        vm.load();
      }
    } catch (e) {
      if (context.mounted)
        showSnack(
            context,
            e is Exception
                ? e.toString()
                : 'Não foi possível procurar o utilizador.');
    }
  }

  @override
  Widget build(BuildContext context) {
    final vm = context.watch<MessagesViewModel>();
    return DefaultTabController(
      length: 2,
      child: Scaffold(
        appBar: AppBar(
          title: const Text('Mensagens'),
          bottom: const TabBar(
              tabs: [Tab(text: 'Conversas'), Tab(text: 'Partilhadas comigo')]),
        ),
        floatingActionButton: FloatingActionButton(
          onPressed: () => _newChat(context, vm),
          child: const Icon(Icons.edit_outlined),
        ),
        body: vm.loading && vm.conversations.isEmpty && vm.shares.isEmpty
            ? const Center(child: CircularProgressIndicator())
            : TabBarView(children: [_Conversations(vm: vm), _Shares(vm: vm)]),
      ),
    );
  }
}

class _Conversations extends StatelessWidget {
  const _Conversations({required this.vm});

  final MessagesViewModel vm;

  @override
  Widget build(BuildContext context) {
    if (vm.conversationsError != null && vm.conversations.isEmpty) {
      return ErrorState(message: vm.conversationsError!, onRetry: vm.load);
    }
    if (vm.conversations.isEmpty) {
      return const EmptyState(
          icon: Icons.mail_outline,
          message:
              'Ainda não tens conversas.\nToca no lápis para começar uma.');
    }
    return RefreshIndicator(
      onRefresh: vm.load,
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        children: [
          for (final c in vm.conversations)
            ListTile(
              leading: Avatar(name: c.label),
              title: Text(c.label,
                  style: TextStyle(
                      fontWeight:
                          c.unread > 0 ? FontWeight.bold : FontWeight.normal)),
              subtitle: Text(c.last.text,
                  maxLines: 1, overflow: TextOverflow.ellipsis),
              trailing: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Text(timeAgo(c.last.createdAt),
                      style: Theme.of(context).textTheme.bodySmall),
                  if (c.unread > 0) Badge(label: Text('${c.unread}')),
                ],
              ),
              onTap: () async {
                await openChat(context, c.userId, c.username);
                vm.load();
              },
            ),
        ],
      ),
    );
  }
}

class _Shares extends StatelessWidget {
  const _Shares({required this.vm});

  final MessagesViewModel vm;

  @override
  Widget build(BuildContext context) {
    if (vm.sharesError != null && vm.shares.isEmpty)
      return ErrorState(message: vm.sharesError!, onRetry: vm.load);
    if (vm.shares.isEmpty)
      return const EmptyState(
          icon: Icons.share_outlined,
          message: 'Ninguém partilhou receitas contigo ainda.');
    return RefreshIndicator(
      onRefresh: vm.load,
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        children: [
          for (final s in vm.shares)
            ListTile(
              leading: const CircleAvatar(child: Icon(Icons.restaurant_menu)),
              title: Text(s.recipeTitle ?? 'Receita #${s.recipeId}'),
              subtitle: Text(
                  'de ${s.senderUsername ?? 'Utilizador #${s.senderId}'} · ${timeAgo(s.createdAt)}'),
              onTap: () => openRecipe(context, s.recipeId),
            ),
        ],
      ),
    );
  }
}
