import '../core/api_client.dart';
import '../core/token_storage.dart';
import '../models/user.dart';
import '../services/backend.dart';
import 'base.dart';

enum AuthStatus { unknown, loggedOut, loggedIn, offline }

class AuthViewModel extends BaseViewModel {
  AuthViewModel(this._api, this._users, this._storage) {
    _api.onUnauthorized = _handleUnauthorized;
  }

  final ApiClient _api;
  final UsersApi _users;
  final TokenStorage _storage;

  AuthStatus status = AuthStatus.unknown;
  UserProfile? me;
  bool busy = false;
  String? error;
  String? notice;

  /// Arranque da app: recupera a sessão guardada, se existir.
  Future<void> init() async {
    final token = await _storage.read();
    if (token == null) {
      status = AuthStatus.loggedOut;
      notifyListeners();
      return;
    }
    _api.token = token;
    await _loadMe();
  }

  Future<void> retry() async {
    status = AuthStatus.unknown;
    error = null;
    notifyListeners();
    final token = await _storage.read();
    if (token == null) {
      status = AuthStatus.loggedOut;
      notifyListeners();
      return;
    }
    _api.token = token;
    await _loadMe();
  }

  Future<void> _loadMe() async {
    try {
      me = await _users.me();
      status = AuthStatus.loggedIn;
      error = null;
    } on ApiException catch (e) {
      if (e.unavailable) {
        // Mantém o token: quando o servidor voltar, "Tentar novamente" recupera a sessão.
        status = AuthStatus.offline;
        error = e.message;
      } else {
        _dropSession();
        status = AuthStatus.loggedOut;
        notice = e.unauthorized ? 'A sessão expirou. Entra novamente.' : null;
      }
    }
    notifyListeners();
  }

  void _dropSession() {
    _api.token = null;
    me = null;
    _storage.clear();
  }

  void _handleUnauthorized() {
    if (status != AuthStatus.loggedIn) return;
    _dropSession();
    notice = 'A sessão expirou. Entra novamente.';
    status = AuthStatus.loggedOut;
    notifyListeners();
  }

  Future<bool> login(String identifier, String password) async {
    busy = true;
    error = null;
    notice = null;
    notifyListeners();
    try {
      final token = await _users.login(identifier.trim(), password);
      _api.token = token;
      await _storage.write(token);
      me = await _users.me();
      status = AuthStatus.loggedIn;
      busy = false;
      notifyListeners();
      return true;
    } on ApiException catch (e) {
      _dropSession();
      error = e.message;
    }
    busy = false;
    notifyListeners();
    return false;
  }

  Future<bool> register(String username, String email, String password) async {
    busy = true;
    error = null;
    notice = null;
    notifyListeners();
    try {
      await _users.register(username.trim(), email.trim(), password);
    } on ApiException catch (e) {
      error = e.message;
      busy = false;
      notifyListeners();
      return false;
    }
    busy = false;
    return login(username, password);
  }

  Future<void> logout() async {
    _dropSession();
    status = AuthStatus.loggedOut;
    error = null;
    notice = null;
    notifyListeners();
  }

  /// Devolve uma mensagem de erro, ou `null` se correu bem.
  Future<String?> updateProfile(
      {required String description, required List<String> interests}) async {
    try {
      me =
          await _users.updateMe(description: description, interests: interests);
      notifyListeners();
      return null;
    } catch (e) {
      return errorText(e);
    }
  }
}
