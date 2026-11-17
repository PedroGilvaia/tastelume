/// Datas do backend vêm em UTC, por vezes sem sufixo de fuso: trata-as sempre como UTC.
DateTime parseUtc(String value) {
  final hasZone =
      value.endsWith('Z') || RegExp(r'[+-]\d\d:?\d\d$').hasMatch(value);
  return DateTime.parse(hasZone ? value : '${value}Z').toLocal();
}

String _two(int n) => n.toString().padLeft(2, '0');

String formatDate(DateTime d) => '${_two(d.day)}/${_two(d.month)}/${d.year}';

String timeAgo(DateTime date) {
  final diff = DateTime.now().difference(date);
  if (diff.inSeconds < 60) return 'agora mesmo';
  if (diff.inMinutes < 60) return 'há ${diff.inMinutes} min';
  if (diff.inHours < 24) return 'há ${diff.inHours} h';
  if (diff.inDays < 7) return 'há ${diff.inDays} d';
  return formatDate(date);
}

String difficultyLabel(String value) => difficulties[value] ?? value;

const difficulties = <String, String>{
  'facil': 'Fácil',
  'media': 'Média',
  'dificil': 'Difícil'
};

String formatMinutes(int minutes) {
  if (minutes < 60) return '$minutes min';
  final h = minutes ~/ 60;
  final m = minutes % 60;
  return m == 0 ? '$h h' : '$h h $m min';
}

String formatQuantity(double value) {
  final text = value == value.roundToDouble()
      ? value.toInt().toString()
      : value.toString();
  return text.replaceAll('.', ',');
}

String formatRating(double? value) =>
    value == null ? '—' : value.toStringAsFixed(1).replaceAll('.', ',');
