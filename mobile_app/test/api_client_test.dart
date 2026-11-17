import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:tastelume/core/api_client.dart';

http.Response jsonResponse(Object body, int status,
        {Map<String, String> headers = const {}}) =>
    http.Response.bytes(
      utf8.encode(jsonEncode(body)),
      status,
      headers: {'content-type': 'application/json; charset=utf-8', ...headers},
    );

void main() {
  final uri = Uri.parse('http://localhost:8001/x');

  test('envia o token e lê cabeçalhos de contagem', () async {
    String? auth;
    final client = ApiClient(
      client: MockClient((req) async {
        auth = req.headers['Authorization'];
        return jsonResponse([1, 2], 200, headers: {'x-total-count': '42'});
      }),
    )..token = 'abc';
    final r = await client.get(uri);
    expect(auth, 'Bearer abc');
    expect(r.totalCount, 42);
    expect(r.list, hasLength(2));
  });

  test('lê acentos em UTF-8', () async {
    final client = ApiClient(
        client:
            MockClient((_) async => jsonResponse({'nome': 'Pão de Ló'}, 200)));
    expect((await client.get(uri)).map['nome'], 'Pão de Ló');
  });

  test('401 com sessão chama onUnauthorized', () async {
    var called = false;
    final client = ApiClient(
        client: MockClient(
            (_) async => jsonResponse({'detail': 'Token inválido'}, 401)))
      ..token = 'abc'
      ..onUnauthorized = () => called = true;
    await expectLater(
        client.get(uri),
        throwsA(isA<ApiException>()
            .having((e) => e.unauthorized, 'unauthorized', isTrue)));
    expect(called, isTrue);
  });

  test('401 no login (sem token) não conta como sessão expirada', () async {
    var called = false;
    final client = ApiClient(
        client: MockClient((_) async =>
            jsonResponse({'detail': 'Credenciais inválidas'}, 401)))
      ..onUnauthorized = () => called = true;
    await expectLater(
        client.postPublic(uri, body: {}),
        throwsA(isA<ApiException>()
            .having((e) => e.message, 'message', 'Credenciais inválidas')));
    expect(called, isFalse);
  });

  test('erros de validação 422 ficam em português', () async {
    final client = ApiClient(
      client: MockClient((_) async => jsonResponse({
            'detail': [
              {
                'loc': ['body', 'title'],
                'msg': 'String should have at least 3 characters'
              },
              {
                'loc': ['body', 'ingredients'],
                'msg':
                    'List should have at least 1 item after validation, not 0'
              },
            ]
          }, 422)),
    );
    await expectLater(
      client.post(uri, body: {}),
      throwsA(isA<ApiException>().having((e) => e.message, 'message',
          'Título: mínimo 3 caracteres. Ingredientes: adiciona pelo menos 1.')),
    );
  });

  test('503 e falhas de rede contam como serviço indisponível', () async {
    final unavailable = ApiClient(
        client: MockClient((_) async =>
            jsonResponse({'detail': 'users service indisponível'}, 503)));
    await expectLater(
        unavailable.get(uri),
        throwsA(isA<ApiException>()
            .having((e) => e.unavailable, 'unavailable', isTrue)));

    final offline = ApiClient(
        client:
            MockClient((_) async => throw http.ClientException('sem rede')));
    await expectLater(
        offline.get(uri),
        throwsA(
            isA<ApiException>().having((e) => e.network, 'network', isTrue)));
  });
}
