import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'core/api_client.dart';
import 'core/config.dart';
import 'core/token_storage.dart';
import 'services/backend.dart';
import 'viewmodels/auth_viewmodel.dart';
import 'viewmodels/notifications_viewmodel.dart';
import 'views/auth/login_screen.dart';
import 'views/home_shell.dart';

/// Objetos partilhados por toda a app (um cliente HTTP, quatro APIs, estado de sessão).
class AppDependencies {
  AppDependencies(this.config)
      : client = ApiClient(),
        storage = TokenStorage() {
    users = UsersApi(client, config);
    recipes = RecipeApi(client, config);
    interactions = InteractionApi(client, config);
    activity = ActivityApi(client, config);
    auth = AuthViewModel(client, users, storage)..init();
  }

  final ApiConfig config;
  final ApiClient client;
  final TokenStorage storage;
  late final UsersApi users;
  late final RecipeApi recipes;
  late final InteractionApi interactions;
  late final ActivityApi activity;
  late final AuthViewModel auth;
}

class TastelumeApp extends StatelessWidget {
  const TastelumeApp({super.key, required this.deps});

  final AppDependencies deps;

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider<ApiConfig>.value(value: deps.config),
        Provider<UsersApi>.value(value: deps.users),
        Provider<RecipeApi>.value(value: deps.recipes),
        Provider<InteractionApi>.value(value: deps.interactions),
        Provider<ActivityApi>.value(value: deps.activity),
        ChangeNotifierProvider<AuthViewModel>.value(value: deps.auth),
      ],
      child: MaterialApp(
        title: 'Tastelume',
        debugShowCheckedModeBanner: false,
        theme: ThemeData(
          useMaterial3: true,
          colorScheme: ColorScheme.fromSeed(seedColor: Colors.deepOrange),
          appBarTheme: const AppBarTheme(centerTitle: false),
        ),
        home: const AuthGate(),
      ),
    );
  }
}

/// Decide o ecrã inicial consoante a sessão.
class AuthGate extends StatelessWidget {
  const AuthGate({super.key});

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthViewModel>();
    switch (auth.status) {
      case AuthStatus.unknown:
        return const Scaffold(body: Center(child: CircularProgressIndicator()));
      case AuthStatus.offline:
        return const OfflineScreen();
      case AuthStatus.loggedOut:
        // Se a sessão terminou com ecrãs abertos por cima (token expirado), fecha-os.
        WidgetsBinding.instance.addPostFrameCallback((_) {
          if (context.mounted)
            Navigator.of(context).popUntil((route) => route.isFirst);
        });
        return const LoginScreen();
      case AuthStatus.loggedIn:
        return ChangeNotifierProvider<NotificationsViewModel>(
          key: ValueKey(auth.me!.id),
          create: (c) =>
              NotificationsViewModel(c.read<ActivityApi>())..startPolling(),
          child: const HomeShell(),
        );
    }
  }
}
