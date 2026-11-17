import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../viewmodels/auth_viewmodel.dart';
import '../viewmodels/notifications_viewmodel.dart';
import 'feed/feed_screen.dart';
import 'notifications/notifications_screen.dart';
import 'profile/profile_screen.dart';
import 'feed/search_screen.dart';

class HomeShell extends StatefulWidget {
  const HomeShell({super.key});

  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  int _index = 0;
  int _profileTick = 0;

  void _select(int i) {
    setState(() {
      _index = i;
      if (i == 3) _profileTick++;
    });
    if (i == 2) context.read<NotificationsViewModel>().refresh();
  }

  @override
  Widget build(BuildContext context) {
    final unread = context.watch<NotificationsViewModel>().unread;
    final myId = context.read<AuthViewModel>().me!.id;
    return Scaffold(
      body: IndexedStack(
        index: _index,
        children: [
          const FeedScreen(),
          const SearchScreen(),
          const NotificationsScreen(),
          ProfileScreen(userId: myId, isTab: true, refreshTick: _profileTick),
        ],
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: _select,
        destinations: [
          const NavigationDestination(
              icon: Icon(Icons.home_outlined),
              selectedIcon: Icon(Icons.home),
              label: 'Início'),
          const NavigationDestination(
              icon: Icon(Icons.search), label: 'Procurar'),
          NavigationDestination(
            icon: Badge(
              label: Text(unread > 99 ? '99+' : '$unread'),
              isLabelVisible: unread > 0,
              child: const Icon(Icons.notifications_outlined),
            ),
            selectedIcon: const Icon(Icons.notifications),
            label: 'Avisos',
          ),
          const NavigationDestination(
              icon: Icon(Icons.person_outline),
              selectedIcon: Icon(Icons.person),
              label: 'Perfil'),
        ],
      ),
    );
  }
}
