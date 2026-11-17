import 'package:flutter/foundation.dart';

import '../core/api_client.dart';

/// Evita `notifyListeners()` depois de o ecrã ter sido fechado (pedidos assíncronos que terminam tarde).
class BaseViewModel extends ChangeNotifier {
  bool _disposed = false;

  bool get disposed => _disposed;

  @override
  void dispose() {
    _disposed = true;
    super.dispose();
  }

  @override
  void notifyListeners() {
    if (!_disposed) super.notifyListeners();
  }
}

String errorText(Object error) =>
    error is ApiException ? error.message : 'Ocorreu um erro inesperado.';

/// `true` quando o erro significa "serviço indisponível" (e não, p. ex., "não encontrado").
bool isUnavailable(Object error) => error is ApiException && error.unavailable;
