import 'package:flutter_test/flutter_test.dart';
import 'package:tastelume/core/api_client.dart';
import 'package:tastelume/core/config.dart';
import 'package:tastelume/core/token_storage.dart';
import 'package:tastelume/models/user.dart';
import 'package:tastelume/services/backend.dart';
import 'package:tastelume/viewmodels/auth_viewmodel.dart';

class MemoryStorage extends TokenStorage {
  String? value;

  @override
  Future<String?> read() async => value;

  @override
  Future<void> write(String token) async => value = token;

  @override
  Future<void> clear() async => value = null;
}

class FakeUsersApi extends UsersApi {
  FakeUsersApi() : super(ApiClient(), ApiConfig());

  Object? meError;
  Object? loginError;

  @override
  Future<UserProfile> me() async {
    if (meError != null) throw meError!;
    return UserProfile(id: 1, username: 'ana', createdAt: DateTime(2026));
  }

  @override
  Future<String> login(String identifier, String password) async {
    if (loginError != null) throw loginError!;
    return 'token-novo';
  }
}

void main() {
  late MemoryStorage storage;
  late FakeUsersApi users;
  late ApiClient client;
  late AuthViewModel auth;

  setUp(() {
    storage = MemoryStorage();
    users = FakeUsersApi();
    client = ApiClient();
    auth = AuthViewModel(client, users, storage);
  });

  test('sem token guardado → loggedOut', () async {
    await auth.init();
    expect(auth.status, AuthStatus.loggedOut);
  });

  test('token válido recupera a sessão', () async {
    storage.value = 't';
    await auth.init();
    expect(auth.status, AuthStatus.loggedIn);
    expect(auth.me!.username, 'ana');
    expect(client.token, 't');
  });

  test('servidor em baixo → offline e o token é mantido', () async {
    storage.value = 't';
    users.meError = ApiException.network();
    await auth.init();
    expect(auth.status, AuthStatus.offline);
    expect(storage.value, 't');
  });

  test('token expirado → loggedOut com aviso e token apagado', () async {
    storage.value = 't';
    users.meError = ApiException('expirado', status: 401);
    await auth.init();
    expect(auth.status, AuthStatus.loggedOut);
    expect(auth.notice, isNotNull);
    expect(storage.value, isNull);
  });

  test('login falhado mostra erro e não guarda token', () async {
    users.loginError = ApiException('Credenciais inválidas', status: 401);
    expect(await auth.login('ana', 'x'), isFalse);
    expect(auth.error, 'Credenciais inválidas');
    expect(storage.value, isNull);
  });

  test('login e logout', () async {
    expect(await auth.login('ana', 'Tastelume123'), isTrue);
    expect(auth.status, AuthStatus.loggedIn);
    expect(storage.value, 'token-novo');
    await auth.logout();
    expect(auth.status, AuthStatus.loggedOut);
    expect(client.token, isNull);
  });
}
