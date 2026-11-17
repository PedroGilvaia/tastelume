import 'package:flutter_test/flutter_test.dart';
import 'package:tastelume/core/format.dart';
import 'package:tastelume/models/recipe.dart';

void main() {
  group('datas', () {
    test('datas sem fuso horário são tratadas como UTC', () {
      expect(parseUtc('2026-11-11T10:00:00').toUtc().hour, 10);
      expect(parseUtc('2026-11-11T10:00:00Z').toUtc().hour, 10);
      expect(parseUtc('2026-11-11T10:00:00+01:00').toUtc().hour, 9);
    });

    test('timeAgo', () {
      final now = DateTime.now();
      expect(timeAgo(now), 'agora mesmo');
      expect(timeAgo(now.subtract(const Duration(minutes: 5))), 'há 5 min');
      expect(timeAgo(now.subtract(const Duration(hours: 3))), 'há 3 h');
      expect(timeAgo(now.subtract(const Duration(days: 2))), 'há 2 d');
    });
  });

  group('formatação', () {
    test('minutos', () {
      expect(formatMinutes(45), '45 min');
      expect(formatMinutes(60), '1 h');
      expect(formatMinutes(95), '1 h 35 min');
    });

    test('quantidades e avaliações', () {
      expect(formatQuantity(200), '200');
      expect(formatQuantity(1.5), '1,5');
      expect(formatRating(null), '—');
      expect(formatRating(4.5), '4,5');
    });

    test('dificuldade', () {
      expect(difficultyLabel('facil'), 'Fácil');
      expect(difficultyLabel('dificil'), 'Difícil');
    });
  });

  group('Ingredient.label', () {
    test('com quantidade e unidade', () {
      expect(const Ingredient(name: 'farinha', quantity: 200, unit: 'g').label,
          '200 g de farinha');
    });
    test('só quantidade', () {
      expect(const Ingredient(name: 'ovos', quantity: 2).label, '2 ovos');
    });
    test('sem quantidade', () {
      expect(const Ingredient(name: 'sal').label, 'sal');
    });
  });
}
