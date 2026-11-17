import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/format.dart';
import '../../models/interaction.dart';
import '../../models/recipe.dart';
import '../../services/backend.dart';
import '../../viewmodels/auth_viewmodel.dart';
import '../../viewmodels/recipe_detail_viewmodel.dart';
import '../common/widgets.dart';
import '../feed/recipe_card.dart';
import '../navigation.dart';

class RecipeDetailScreen extends StatelessWidget {
  const RecipeDetailScreen({super.key, required this.recipeId});

  final int recipeId;

  @override
  Widget build(BuildContext context) => ChangeNotifierProvider(
        create: (c) => RecipeDetailViewModel(
          recipeId,
          c.read<RecipeApi>(),
          c.read<InteractionApi>(),
          c.read<AuthViewModel>().me!.id,
        )..load(),
        child: const _DetailView(),
      );
}

class _DetailView extends StatelessWidget {
  const _DetailView();

  Future<void> _edit(BuildContext context, RecipeDetailViewModel vm) async {
    final updated = await openRecipeForm(context, existing: vm.recipe);
    if (updated == true) vm.load();
  }

  Future<void> _delete(BuildContext context, RecipeDetailViewModel vm) async {
    final ok = await confirm(
        context, 'Apagar receita', 'Esta ação não pode ser desfeita.',
        action: 'Apagar');
    if (!ok) return;
    final error = await vm.deleteRecipe();
    if (!context.mounted) return;
    if (error != null) {
      showSnack(context, error);
    } else {
      Navigator.of(context).pop();
    }
  }

  @override
  Widget build(BuildContext context) {
    final vm = context.watch<RecipeDetailViewModel>();
    return Scaffold(
      appBar: AppBar(
        title: Text(vm.recipe?.title ?? 'Receita',
            maxLines: 1, overflow: TextOverflow.ellipsis),
        actions: [
          if (vm.isOwner)
            PopupMenuButton<String>(
              onSelected: (v) =>
                  v == 'edit' ? _edit(context, vm) : _delete(context, vm),
              itemBuilder: (_) => const [
                PopupMenuItem(value: 'edit', child: Text('Editar')),
                PopupMenuItem(value: 'delete', child: Text('Apagar')),
              ],
            ),
        ],
      ),
      body: _body(context, vm),
    );
  }

  Widget _body(BuildContext context, RecipeDetailViewModel vm) {
    if (vm.loadingRecipe)
      return const Center(child: CircularProgressIndicator());
    final recipe = vm.recipe;
    if (recipe == null)
      return ErrorState(
          message: vm.recipeError ?? 'Receita indisponível.', onRetry: vm.load);
    final theme = Theme.of(context);
    return RefreshIndicator(
      onRefresh: vm.load,
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.only(bottom: 32),
        children: [
          RecipeImage(imageUrl: recipe.imageUrl, height: 240),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const SizedBox(height: 16),
                Text(recipe.title,
                    style: theme.textTheme.headlineSmall
                        ?.copyWith(fontWeight: FontWeight.bold)),
                const SizedBox(height: 4),
                InkWell(
                  onTap: () => openProfile(context, recipe.authorId),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(vertical: 4),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Avatar(name: recipe.authorLabel, radius: 12),
                        const SizedBox(width: 8),
                        Text(recipe.authorLabel,
                            style: TextStyle(color: theme.colorScheme.primary)),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8,
                  runSpacing: 4,
                  children: [
                    Chip(
                        avatar: const Icon(Icons.category_outlined, size: 16),
                        label: Text(recipe.category.name)),
                    Chip(
                        avatar: const Icon(Icons.timer_outlined, size: 16),
                        label: Text(formatMinutes(recipe.preparationTime))),
                    Chip(
                        avatar: const Icon(Icons.local_fire_department_outlined,
                            size: 16),
                        label: Text(difficultyLabel(recipe.difficulty))),
                    Chip(
                        avatar: const Icon(Icons.people_outline, size: 16),
                        label: Text('${recipe.servings} doses')),
                  ],
                ),
                if (recipe.description.isNotEmpty) ...[
                  const SizedBox(height: 8),
                  Text(recipe.description),
                ],
                const SizedBox(height: 8),
                _Interactions(vm: vm),
                const SectionTitle('Ingredientes'),
                for (final i in recipe.ingredients)
                  Padding(
                    padding: const EdgeInsets.symmetric(vertical: 2),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text('•  '),
                        Expanded(child: Text(i.label))
                      ],
                    ),
                  ),
                const SectionTitle('Preparação'),
                for (var n = 0; n < recipe.steps.length; n++)
                  Padding(
                    padding: const EdgeInsets.symmetric(vertical: 6),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        CircleAvatar(
                            radius: 12,
                            child: Text('${n + 1}',
                                style: const TextStyle(fontSize: 12))),
                        const SizedBox(width: 10),
                        Expanded(child: Text(recipe.steps[n])),
                      ],
                    ),
                  ),
                if (recipe.tags.isNotEmpty) ...[
                  const SizedBox(height: 12),
                  Wrap(spacing: 6, children: [
                    for (final t in recipe.tags) Chip(label: Text('#$t'))
                  ]),
                ],
              ],
            ),
          ),
          if (vm.related.isNotEmpty) ...[
            const Padding(
                padding: EdgeInsets.symmetric(horizontal: 16),
                child: SectionTitle('Receitas relacionadas')),
            for (final r in vm.related.take(3)) RecipeCard(recipe: r),
          ],
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: _Comments(vm: vm),
          ),
        ],
      ),
    );
  }
}

class _Interactions extends StatelessWidget {
  const _Interactions({required this.vm});

  final RecipeDetailViewModel vm;

  Future<void> _run(
      BuildContext context, Future<String?> Function() action) async {
    final error = await action();
    if (error != null && context.mounted) showSnack(context, error);
  }

  Future<void> _favorite(BuildContext context) async {
    List<Collection> collections;
    try {
      collections = await vm.fetchCollections();
    } catch (_) {
      if (context.mounted)
        showSnack(context, 'Os favoritos estão indisponíveis neste momento.');
      return;
    }
    if (!context.mounted) return;
    await showModalBottomSheet<void>(
      context: context,
      builder: (ctx) => SafeArea(
        child: ListView(
          shrinkWrap: true,
          children: [
            const ListTile(
                title: Text('Guardar em…',
                    style: TextStyle(fontWeight: FontWeight.bold))),
            for (final c in collections)
              ListTile(
                leading: const Icon(Icons.bookmark_border),
                title: Text(c.name),
                trailing: c.recipeIds.contains(vm.recipeId)
                    ? const Icon(Icons.check, color: Colors.green)
                    : null,
                onTap: () async {
                  Navigator.pop(ctx);
                  final error = await vm.addToCollection(c.id);
                  if (context.mounted)
                    showSnack(context, error ?? 'Guardada em «${c.name}».');
                },
              ),
            ListTile(
              leading: const Icon(Icons.add),
              title: const Text('Nova lista…'),
              onTap: () async {
                Navigator.pop(ctx);
                final name = await promptText(context,
                    title: 'Nova lista de favoritos',
                    label: 'Nome',
                    maxLength: 60,
                    action: 'Criar');
                if (name == null) return;
                final error = await vm.createCollectionAndAdd(name);
                if (context.mounted)
                  showSnack(context, error ?? 'Guardada em «$name».');
              },
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _share(BuildContext context) async {
    final username = await promptText(context,
        title: 'Partilhar com…',
        label: 'Nome de utilizador',
        maxLength: 30,
        action: 'Enviar');
    if (username == null) return;
    final error = await vm.share(username);
    if (context.mounted)
      showSnack(context, error ?? 'Receita partilhada com $username.');
  }

  @override
  Widget build(BuildContext context) {
    final summary = vm.summary;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (summary == null && vm.summaryError != null)
          InlineNotice(
            message:
                'Gostos, avaliações e comentários estão indisponíveis de momento. A receita continua disponível.',
            onRetry: vm.loadInteractions,
          ),
        Row(
          children: [
            StarRating(value: vm.ratingAverage, size: 22),
            Text('  ${formatRating(vm.ratingAverage)} (${vm.ratingCount})'),
            const Spacer(),
            Icon(Icons.visibility_outlined,
                size: 18, color: Colors.grey.shade600),
            Text(' ${vm.recipe?.viewCount ?? 0}'),
          ],
        ),
        const SizedBox(height: 8),
        Wrap(
          spacing: 8,
          children: [
            FilledButton.tonalIcon(
              onPressed:
                  summary == null ? null : () => _run(context, vm.toggleLike),
              icon: Icon(vm.liked ? Icons.favorite : Icons.favorite_border,
                  color: Colors.redAccent),
              label: Text('${vm.likeCount}'),
            ),
            OutlinedButton.icon(
              onPressed: () => _favorite(context),
              icon: const Icon(Icons.bookmark_add_outlined),
              label: const Text('Guardar'),
            ),
            OutlinedButton.icon(
              onPressed: () => _share(context),
              icon: const Icon(Icons.share_outlined),
              label: const Text('Partilhar'),
            ),
          ],
        ),
        if (summary != null) ...[
          const SizedBox(height: 12),
          Row(
            children: [
              Text(vm.myScore == null
                  ? 'Avalia esta receita: '
                  : 'A tua avaliação: '),
              StarRating(
                value: vm.myScore?.toDouble(),
                size: 30,
                onChanged: (score) => _run(context, () => vm.rate(score)),
              ),
            ],
          ),
        ],
      ],
    );
  }
}

class _Comments extends StatefulWidget {
  const _Comments({required this.vm});

  final RecipeDetailViewModel vm;

  @override
  State<_Comments> createState() => _CommentsState();
}

class _CommentsState extends State<_Comments> {
  final _controller = TextEditingController();
  bool _sending = false;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _send() async {
    final text = _controller.text.trim();
    if (text.isEmpty || _sending) return;
    setState(() => _sending = true);
    final error = await widget.vm.addComment(text);
    if (!mounted) return;
    setState(() => _sending = false);
    if (error != null) {
      showSnack(context, error);
    } else {
      _controller.clear();
    }
  }

  Future<void> _edit(Comment c) async {
    final text = await promptText(context,
        title: 'Editar comentário',
        initial: c.text,
        maxLength: 1000,
        maxLines: 3);
    if (text == null || text == c.text) return;
    final error = await widget.vm.editComment(c, text);
    if (error != null && mounted) showSnack(context, error);
  }

  Future<void> _delete(Comment c) async {
    if (!await confirm(
        context, 'Apagar comentário', 'Queres mesmo apagar este comentário?',
        action: 'Apagar')) return;
    final error = await widget.vm.deleteComment(c);
    if (error != null && mounted) showSnack(context, error);
  }

  @override
  Widget build(BuildContext context) {
    final vm = widget.vm;
    final myId = vm.myId;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SectionTitle('Comentários (${vm.commentCount})'),
        Row(
          children: [
            Expanded(
              child: TextField(
                controller: _controller,
                maxLength: 1000,
                minLines: 1,
                maxLines: 4,
                decoration: const InputDecoration(
                    hintText: 'Escreve um comentário…',
                    border: OutlineInputBorder(),
                    counterText: ''),
              ),
            ),
            const SizedBox(width: 8),
            IconButton.filled(
              onPressed: _sending ? null : _send,
              icon: _sending
                  ? const SizedBox(
                      height: 18,
                      width: 18,
                      child: CircularProgressIndicator(strokeWidth: 2))
                  : const Icon(Icons.send),
            ),
          ],
        ),
        if (vm.commentsError != null && vm.comments.isEmpty)
          InlineNotice(
              message: 'Não foi possível carregar os comentários.',
              onRetry: vm.loadComments),
        for (final c in vm.comments)
          ListTile(
            contentPadding: EdgeInsets.zero,
            leading: GestureDetector(
                onTap: () => openProfile(context, c.userId),
                child: Avatar(name: c.authorLabel)),
            title: Text(
                '${c.authorLabel} · ${timeAgo(c.createdAt)}${c.edited ? ' (editado)' : ''}',
                style: const TextStyle(fontSize: 13)),
            subtitle: Text(c.text),
            trailing: c.userId == myId
                ? PopupMenuButton<String>(
                    onSelected: (v) => v == 'edit' ? _edit(c) : _delete(c),
                    itemBuilder: (_) => const [
                      PopupMenuItem(value: 'edit', child: Text('Editar')),
                      PopupMenuItem(value: 'delete', child: Text('Apagar')),
                    ],
                  )
                : null,
          ),
        if (vm.hasMoreComments)
          TextButton(
            onPressed: vm.loadingMoreComments ? null : vm.loadMoreComments,
            child: Text(vm.loadingMoreComments
                ? 'A carregar…'
                : 'Ver mais comentários'),
          ),
      ],
    );
  }
}
