import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../models/activity.dart';
import '../../services/backend.dart';
import '../../viewmodels/stats_viewmodel.dart';
import '../common/widgets.dart';
import '../navigation.dart';

class StatsScreen extends StatelessWidget {
  const StatsScreen({super.key});

  @override
  Widget build(BuildContext context) => ChangeNotifierProvider(
        create: (c) => StatsViewModel(c.read<ActivityApi>())..load(),
        child: const _StatsView(),
      );
}

class _StatsView extends StatefulWidget {
  const _StatsView();

  @override
  State<_StatsView> createState() => _StatsViewState();
}

class _StatsViewState extends State<_StatsView> {
  bool _interactions = false;

  @override
  Widget build(BuildContext context) {
    final vm = context.watch<StatsViewModel>();
    return Scaffold(
      appBar: AppBar(title: const Text('Estatísticas')),
      body: RefreshIndicator(
        onRefresh: vm.load,
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(16),
          children: [
            Wrap(
              spacing: 8,
              children: [
                for (final d in const [7, 30, 90])
                  ChoiceChip(
                      label: Text('$d dias'),
                      selected: vm.days == d,
                      onSelected: (_) => vm.setDays(d)),
              ],
            ),
            const SizedBox(height: 12),
            if (vm.loading && vm.totals == null)
              const Padding(
                  padding: EdgeInsets.all(32),
                  child: Center(child: CircularProgressIndicator())),
            if (vm.totalsError != null)
              InlineNotice(
                  message: 'Totais indisponíveis: ${vm.totalsError}',
                  onRetry: vm.load),
            if (vm.totals != null) _Totals(totals: vm.totals!),
            const SectionTitle('Evolução diária'),
            Wrap(
              spacing: 8,
              children: [
                ChoiceChip(
                    label: const Text('Visualizações'),
                    selected: !_interactions,
                    onSelected: (_) => setState(() => _interactions = false)),
                ChoiceChip(
                    label: const Text('Interações'),
                    selected: _interactions,
                    onSelected: (_) => setState(() => _interactions = true)),
              ],
            ),
            const SizedBox(height: 8),
            if (vm.timelineError != null)
              InlineNotice(
                  message: 'Gráfico indisponível: ${vm.timelineError}',
                  onRetry: vm.load)
            else
              _BarChart(points: vm.timeline, useInteractions: _interactions),
            const SectionTitle('Receitas com mais visualizações'),
            if (vm.topError != null)
              InlineNotice(
                  message: 'Lista indisponível: ${vm.topError}',
                  onRetry: vm.load)
            else if (vm.top.isEmpty && !vm.loading)
              const Text('Ainda sem dados neste período.',
                  style: TextStyle(color: Colors.grey))
            else
              for (final t in vm.top)
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  title: Text(t.label),
                  subtitle: Text(
                      '${t.views} visualizações · ${t.likes} gostos · ${t.comments} comentários'),
                  onTap: () => openRecipe(context, t.recipeId),
                ),
          ],
        ),
      ),
    );
  }
}

class _Totals extends StatelessWidget {
  const _Totals({required this.totals});

  final StatsTotals totals;

  @override
  Widget build(BuildContext context) {
    final items = <(IconData, String, int)>[
      (Icons.visibility_outlined, 'Visualizações', totals.views),
      (Icons.favorite_border, 'Gostos', totals.likes),
      (Icons.chat_bubble_outline, 'Comentários', totals.comments),
      (Icons.star_border, 'Avaliações', totals.ratings),
      (Icons.share_outlined, 'Partilhas', totals.shares),
      (Icons.person_add_alt, 'Novos seguidores', totals.newFollowers),
    ];
    return Wrap(
      spacing: 10,
      runSpacing: 10,
      children: [
        for (final item in items)
          SizedBox(
            width: 150,
            child: Card(
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(item.$1, color: Theme.of(context).colorScheme.primary),
                    const SizedBox(height: 6),
                    Text('${item.$3}',
                        style: Theme.of(context)
                            .textTheme
                            .headlineSmall
                            ?.copyWith(fontWeight: FontWeight.bold)),
                    Text(item.$2, style: Theme.of(context).textTheme.bodySmall),
                  ],
                ),
              ),
            ),
          ),
      ],
    );
  }
}

/// Gráfico de barras simples (sem dependências externas).
class _BarChart extends StatelessWidget {
  const _BarChart({required this.points, required this.useInteractions});

  final List<DayPoint> points;
  final bool useInteractions;

  @override
  Widget build(BuildContext context) {
    if (points.isEmpty)
      return const SizedBox(
          height: 120,
          child: Center(
              child: Text('Sem dados.', style: TextStyle(color: Colors.grey))));
    final values = [
      for (final p in points) useInteractions ? p.interactions : p.views
    ];
    final maxValue = values.fold<int>(0, (a, b) => b > a ? b : a);
    final color = Theme.of(context).colorScheme.primary;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          height: 120,
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              for (final v in values)
                Expanded(
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 0.5),
                    child: Align(
                      alignment: Alignment.bottomCenter,
                      child: FractionallySizedBox(
                        heightFactor: maxValue == 0
                            ? 0.02
                            : (v / maxValue).clamp(0.02, 1.0),
                        child: Container(
                            decoration: BoxDecoration(
                                color: color,
                                borderRadius: BorderRadius.circular(2))),
                      ),
                    ),
                  ),
                ),
            ],
          ),
        ),
        const SizedBox(height: 4),
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(_label(points.first.date),
                style: Theme.of(context).textTheme.bodySmall),
            Text('máx. $maxValue/dia',
                style: Theme.of(context).textTheme.bodySmall),
            Text(_label(points.last.date),
                style: Theme.of(context).textTheme.bodySmall),
          ],
        ),
      ],
    );
  }

  String _label(DateTime d) =>
      '${d.day.toString().padLeft(2, '0')}/${d.month.toString().padLeft(2, '0')}';
}
