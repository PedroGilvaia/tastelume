import 'dart:convert';

import 'package:http/http.dart' as http;

/// Erro de uma chamada à API, já com mensagem pronta a mostrar ao utilizador.
class ApiException implements Exception {
  ApiException(this.message, {this.status, this.network = false});

  factory ApiException.network() => ApiException(
        'Sem ligação ao servidor. Verifica a rede e o endereço do servidor.',
        network: true,
      );

  final String message;
  final int? status;

  /// `true` quando nem sequer houve resposta (sem rede, timeout, servidor desligado).
  final bool network;

  bool get unauthorized => status == 401;
  bool get notFound => status == 404;
  bool get conflict => status == 409;

  /// O serviço não consegue responder agora (a app deve degradar em vez de falhar).
  bool get unavailable =>
      network || status == 502 || status == 503 || status == 504;

  @override
  String toString() => message;
}

class ApiResponse {
  ApiResponse(this.status, this.json, this.headers);

  final int status;
  final dynamic json;
  final Map<String, String> headers;

  int? get totalCount => int.tryParse(headers['x-total-count'] ?? '');
  int? get unreadCount => int.tryParse(headers['x-unread-count'] ?? '');

  List<dynamic> get list => json is List ? json as List<dynamic> : const [];
  Map<String, dynamic> get map =>
      json is Map<String, dynamic> ? json as Map<String, dynamic> : const {};
}

/// Cliente HTTP único: junta o token JWT, aplica timeout e converte erros em [ApiException].
class ApiClient {
  ApiClient({http.Client? client, this.timeout = const Duration(seconds: 8)})
      : _http = client ?? http.Client();

  final http.Client _http;
  final Duration timeout;

  String? token;

  /// Chamado quando um pedido com sessão devolve 401 (token expirado ou inválido).
  void Function()? onUnauthorized;

  Map<String, String> _headers({bool json = false}) => {
        'Accept': 'application/json',
        if (json) 'Content-Type': 'application/json; charset=utf-8',
        if (token != null) 'Authorization': 'Bearer $token',
      };

  Future<ApiResponse> get(Uri uri) => _run('GET', uri);
  Future<ApiResponse> post(Uri uri, {Object? body}) =>
      _run('POST', uri, body: body);
  Future<ApiResponse> patch(Uri uri, {Object? body}) =>
      _run('PATCH', uri, body: body);
  Future<ApiResponse> delete(Uri uri) => _run('DELETE', uri);

  /// Pedido sem enviar o token (login e registo: um 401 aqui é "credenciais inválidas", não sessão expirada).
  Future<ApiResponse> postPublic(Uri uri, {Object? body}) =>
      _run('POST', uri, body: body, sendToken: false);

  Future<ApiResponse> _run(String method, Uri uri,
      {Object? body, bool sendToken = true}) async {
    final hadToken = sendToken && token != null;
    final headers = _headers(json: body != null);
    if (!sendToken) headers.remove('Authorization');
    try {
      final request = http.Request(method, uri)..headers.addAll(headers);
      if (body != null) request.body = jsonEncode(body);
      final streamed = await _http.send(request).timeout(timeout);
      final response =
          await http.Response.fromStream(streamed).timeout(timeout);
      return _handle(response, hadToken);
    } on ApiException {
      rethrow;
    } catch (_) {
      throw ApiException.network();
    }
  }

  /// Envia um ficheiro (campo `file`) por multipart, p. ex. a foto de uma receita.
  Future<ApiResponse> uploadFile(Uri uri, String filePath,
      {String field = 'file'}) async {
    final hadToken = token != null;
    try {
      final request = http.MultipartRequest('POST', uri)
        ..headers.addAll(_headers())
        ..files.add(await http.MultipartFile.fromPath(field, filePath));
      final streamed =
          await _http.send(request).timeout(const Duration(seconds: 30));
      final response = await http.Response.fromStream(streamed);
      return _handle(response, hadToken);
    } on ApiException {
      rethrow;
    } catch (_) {
      throw ApiException.network();
    }
  }

  ApiResponse _handle(http.Response response, bool hadToken) {
    dynamic decoded;
    if (response.bodyBytes.isNotEmpty) {
      try {
        decoded = jsonDecode(utf8.decode(response.bodyBytes));
      } catch (_) {
        decoded = null;
      }
    }
    if (response.statusCode >= 200 && response.statusCode < 300) {
      return ApiResponse(response.statusCode, decoded, response.headers);
    }
    if (response.statusCode == 401 && hadToken) onUnauthorized?.call();
    throw ApiException(_messageFor(response.statusCode, decoded),
        status: response.statusCode);
  }

  static String _messageFor(int status, dynamic body) {
    final detail = body is Map ? body['detail'] : null;
    if (detail is String && detail.isNotEmpty) return detail;
    if (detail is List && detail.isNotEmpty) {
      final parts = <String>{
        for (final e in detail) _validationMessage(e),
      }.where((s) => s.isNotEmpty).toList();
      if (parts.isNotEmpty) return parts.join(' ');
    }
    switch (status) {
      case 401:
        return 'Sessão inválida ou expirada. Entra novamente.';
      case 403:
        return 'Não tens permissão para fazer isto.';
      case 404:
        return 'Não encontrado.';
      case 413:
        return 'O ficheiro é demasiado grande (máximo 5 MB).';
      case 415:
        return 'Formato de imagem inválido. Usa JPEG, PNG ou WebP.';
      case 502:
      case 503:
      case 504:
        return 'Serviço temporariamente indisponível. Tenta novamente daqui a pouco.';
      default:
        return status >= 500
            ? 'Erro no servidor. Tenta novamente.'
            : 'Pedido inválido.';
    }
  }

  static const _fieldNames = <String, String>{
    'title': 'Título',
    'description': 'Descrição',
    'category': 'Categoria',
    'ingredients': 'Ingredientes',
    'preparation_steps': 'Passos',
    'preparation_time': 'Tempo de preparação',
    'servings': 'Doses',
    'difficulty': 'Dificuldade',
    'tags': 'Etiquetas',
    'username': 'Nome de utilizador',
    'email': 'Email',
    'password': 'Password',
    'text': 'Texto',
    'score': 'Avaliação',
    'interests': 'Interesses',
    'name': 'Nome',
  };

  /// Traduz um erro de validação do FastAPI/Pydantic (em inglês) para uma frase curta em português.
  static String _validationMessage(dynamic item) {
    if (item is! Map) return item.toString();
    final raw =
        (item['msg'] ?? '').toString().replaceFirst('Value error, ', '');
    final loc = item['loc'];
    String? field;
    if (loc is List) {
      for (final part in loc) {
        if (part is String && part != 'body' && part != 'query') {
          field = _fieldNames[part] ?? part;
          break;
        }
      }
    }
    final text = _translate(raw);
    return field == null ? '$text.' : '$field: $text.';
  }

  static String _translate(String msg) {
    var m = RegExp(r'at least (\d+) characters?').firstMatch(msg);
    if (m != null) return 'mínimo ${m.group(1)} caracteres';
    m = RegExp(r'at most (\d+) characters?').firstMatch(msg);
    if (m != null) return 'máximo ${m.group(1)} caracteres';
    m = RegExp(r'at least (\d+) items?').firstMatch(msg);
    if (m != null) return 'adiciona pelo menos ${m.group(1)}';
    m = RegExp(r'at most (\d+) items?').firstMatch(msg);
    if (m != null) return 'no máximo ${m.group(1)}';
    if (msg.contains('valid email')) return 'email inválido';
    if (msg.contains('Field required')) return 'campo obrigatório';
    if (msg.contains('greater than or equal')) return 'valor demasiado baixo';
    if (msg.contains('less than or equal')) return 'valor demasiado alto';
    if (msg.contains('valid integer') || msg.contains('valid number'))
      return 'número inválido';
    return msg;
  }
}
