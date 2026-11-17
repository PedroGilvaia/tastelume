import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/format.dart';
import '../../models/activity.dart';
import '../../viewmodels/notifications_viewmodel.dart';
import '../common/widgets.dart';
import '../navigation.dart';

class NotificationsScreen extends StatefulWidget {
  const NotificationsScreen({super.key});

  @override
  State<NotificationsScreen> createState() => _NotificationsScreenState();
}

class _NotificationsScreenState extends State<NotificationsScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) context.read<NotificationsViewModel>().refresh();
    });
  }

  IconData _icon(String type) {
    switch (type) {
      case 'like':
        return Icons.favorite;
      case 'comment':
        return Icons.chat_bubble;
      case 'rating':
        return Icons.star;
      case 'follow':
        return Icons.person_add;
      case 'share':
        return Icons.share;
      case 'message':
        return Icons.mail;
      default:
        return Icons.notifications;
    }
  }

  Future<void> _open(BuildContext context, NotificationsViewModel vm,
      AppNotification n) async {
    vm.markRead(n);
    if (n.type == 'message' && n.actorId != null) {
      await openChat(context, n.actorId!, null);
    } else if (n.recipeId != null) {
      await openRecipe(context, n.recipeId!);
    } else if (n.actorId != null) {
      await openProfile(context, n.actorId!);
    }
  }

  @override
  Widget build(BuildContext context) {
    final vm = context.watch<NotificationsViewModel>();
    Widget body;
    if (vm.loading && vm.items.isEmpty) {
      body = const Center(child: CircularProgressIndicator());
    } else if (vm.error != null && vm.items.isEmpty) {
      body = ErrorState(message: vm.error!, onRetry: vm.refresh);
    } else if (vm.items.isEmpty) {
      body = const EmptyState(
          icon: Icons.notifications_none,
          message: 'Sem notificações por agora.');
    } else {
      body = EndlessScroll(
        onEnd: vm.loadMore,
        child: RefreshIndicator(
          onRefresh: vm.refresh,
          child: ListView.separated(
            physics: const AlwaysScrollableScrollPhysics(),
            itemCount: vm.items.length,
            separatorBuilder: (_, __) => const Divider(height: 1),
            itemBuilder: (context, i) {
              final n = vm.items[i];
              return ListTile(
                tileColor: n.read
                    ? null
                    : Theme.of(context)
                        .colorScheme
                        .primaryContainer
                        .withAlpha(70),
                leading: CircleAvatar(child: Icon(_icon(n.type), size: 20)),
                title: Text(n.text,
                    style: TextStyle(
                        fontWeight:
                            n.read ? FontWeight.normal : FontWeight.bold)),
                subtitle: Text(timeAgo(n.createdAt)),
                onTap: () => _open(context, vm, n),
              );
            },
          ),
        ),
      );
    }
    return Scaffold(
      appBar: AppBar(
        title: const Text('Notificações'),
        actions: [
          if (vm.unread > 0)
            TextButton(
              onPressed: () async {
                final error = await vm.markAllRead();
                if (error != null && context.mounted) showSnack(context, error);
              },
              child: const Text('Marcar lidas'),
            ),
        ],
      ),
      body: body,
    );
  }
}
