import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Endereço do backend. Os quatro serviços partilham o mesmo anfitrião e têm portas diferentes.
///
/// Valor por omissão: `10.0.2.2` no emulador Android (é o computador onde corre o Docker),
/// `localhost` no simulador iOS. Pode mudar-se na app (ícone de servidor no ecrã de entrada)
/// ou ao compilar: `flutter run --dart-define=API_HOST=192.168.1.20`.
class ApiConfig extends ChangeNotifier {
  static const String _prefKey = 'api_host';
  static const String _fromEnv = String.fromEnvironment('API_HOST');

  static const int usersPort = 8001;
  static const int recipePort = 8002;
  static const int interactionPort = 8003;
  static const int activityPort = 8004;

  String _host = _fromEnv.isNotEmpty ? _fromEnv : _platformDefault();

  String get host => _host;

  static String _platformDefault() =>
      defaultTargetPlatform == TargetPlatform.android
          ? '10.0.2.2'
          : 'localhost';

  Future<void> load() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final saved = prefs.getString(_prefKey);
      if (saved != null && saved.trim().isNotEmpty) _host = saved.trim();
    } catch (_) {
      // Sem preferências guardadas: usa o valor por omissão.
    }
    notifyListeners();
  }

  Future<void> setHost(String value) async {
    final cleaned = value
        .trim()
        .replaceAll(RegExp(r'^https?://'), '')
        .replaceAll(RegExp(r'[/:].*$'), '');
    _host = cleaned.isEmpty ? _platformDefault() : cleaned;
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(_prefKey, _host);
    } catch (_) {}
    notifyListeners();
  }

  Uri uri(int port, String path, [Map<String, String>? query]) => Uri(
        scheme: 'http',
        host: _host,
        port: port,
        path: path,
        queryParameters: (query == null || query.isEmpty) ? null : query,
      );

  /// `image_url` vem do Recipe Service como caminho relativo (`/images/<nome>`).
  String? imageUrl(String? relative) {
    if (relative == null || relative.isEmpty) return null;
    if (relative.startsWith('http')) return relative;
    return 'http://$_host:$recipePort$relative';
  }
}
