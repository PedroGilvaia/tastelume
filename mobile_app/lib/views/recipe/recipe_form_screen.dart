import 'dart:io';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';

import '../../core/format.dart';
import '../../models/recipe.dart';
import '../../services/backend.dart';
import '../../viewmodels/create_recipe_viewmodel.dart';
import '../common/widgets.dart';

class RecipeFormScreen extends StatelessWidget {
  const RecipeFormScreen({super.key, this.existingRecipe});

  final Recipe? existingRecipe;

  @override
  Widget build(BuildContext context) => ChangeNotifierProvider(
        create: (c) =>
            RecipeFormViewModel(c.read<RecipeApi>(), existing: existingRecipe)
              ..loadCategories(),
        child: _FormView(existing: existingRecipe),
      );
}

class _IngredientRow {
  _IngredientRow({String name = '', String quantity = '', String unit = ''})
      : name = TextEditingController(text: name),
        quantity = TextEditingController(text: quantity),
        unit = TextEditingController(text: unit);

  final TextEditingController name;
  final TextEditingController quantity;
  final TextEditingController unit;

  void dispose() {
    name.dispose();
    quantity.dispose();
    unit.dispose();
  }
}

class _FormView extends StatefulWidget {
  const _FormView({this.existing});

  final Recipe? existing;

  @override
  State<_FormView> createState() => _FormViewState();
}

class _FormViewState extends State<_FormView> {
  final _formKey = GlobalKey<FormState>();
  final _title = TextEditingController();
  final _description = TextEditingController();
  final _time = TextEditingController(text: '30');
  final _servings = TextEditingController(text: '4');
  final _tags = TextEditingController();
  final List<_IngredientRow> _ingredients = [];
  final List<TextEditingController> _steps = [];
  String? _category;
  String _difficulty = 'facil';
  String? _imagePath;
  final _picker = ImagePicker();

  @override
  void initState() {
    super.initState();
    final r = widget.existing;
    if (r != null) {
      _title.text = r.title;
      _description.text = r.description;
      _time.text = '${r.preparationTime}';
      _servings.text = '${r.servings}';
      _tags.text = r.tags.join(', ');
      _category = r.category.slug;
      _difficulty = r.difficulty;
      for (final i in r.ingredients) {
        _ingredients.add(_IngredientRow(
          name: i.name,
          quantity: i.quantity == null ? '' : formatQuantity(i.quantity!),
          unit: i.unit ?? '',
        ));
      }
      for (final s in r.steps) {
        _steps.add(TextEditingController(text: s));
      }
    }
    if (_ingredients.isEmpty) _ingredients.add(_IngredientRow());
    if (_steps.isEmpty) _steps.add(TextEditingController());
  }

  @override
  void dispose() {
    _title.dispose();
    _description.dispose();
    _time.dispose();
    _servings.dispose();
    _tags.dispose();
    for (final i in _ingredients) {
      i.dispose();
    }
    for (final s in _steps) {
      s.dispose();
    }
    super.dispose();
  }

  Future<void> _pick(ImageSource source) async {
    try {
      final file = await _picker.pickImage(
          source: source, maxWidth: 1600, imageQuality: 85);
      if (file != null) setState(() => _imagePath = file.path);
    } catch (_) {
      if (mounted) {
        showSnack(
            context,
            source == ImageSource.camera
                ? 'Não foi possível abrir a câmara. Verifica a permissão da app ou escolhe da galeria.'
                : 'Não foi possível abrir a galeria.');
      }
    }
  }

  void _photoSheet() {
    showModalBottomSheet<void>(
      context: context,
      builder: (ctx) => SafeArea(
        child: Wrap(
          children: [
            ListTile(
              leading: const Icon(Icons.photo_camera),
              title: const Text('Tirar fotografia'),
              onTap: () {
                Navigator.pop(ctx);
                _pick(ImageSource.camera);
              },
            ),
            ListTile(
              leading: const Icon(Icons.photo_library),
              title: const Text('Escolher da galeria'),
              onTap: () {
                Navigator.pop(ctx);
                _pick(ImageSource.gallery);
              },
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    if (_category == null) {
      showSnack(context, 'Escolhe uma categoria.');
      return;
    }
    final ingredients = <Ingredient>[];
    for (final row in _ingredients) {
      final name = row.name.text.trim();
      if (name.isEmpty) continue;
      final qText = row.quantity.text.trim().replaceAll(',', '.');
      final unit = row.unit.text.trim();
      ingredients.add(Ingredient(
          name: name,
          quantity: qText.isEmpty ? null : double.tryParse(qText),
          unit: unit.isEmpty ? null : unit));
    }
    final steps =
        _steps.map((c) => c.text.trim()).where((s) => s.isNotEmpty).toList();
    if (ingredients.isEmpty) {
      showSnack(context, 'Adiciona pelo menos um ingrediente.');
      return;
    }
    if (steps.isEmpty) {
      showSnack(context, 'Adiciona pelo menos um passo de preparação.');
      return;
    }
    final draft = RecipeDraft(
      title: _title.text.trim(),
      description: _description.text.trim(),
      category: _category!,
      ingredients: ingredients,
      steps: steps,
      preparationTime: int.parse(_time.text.trim()),
      servings: int.parse(_servings.text.trim()),
      difficulty: _difficulty,
      tags: _tags.text
          .split(',')
          .map((t) => t.trim().toLowerCase())
          .where((t) => t.isNotEmpty)
          .toList(),
    );
    final result = await context
        .read<RecipeFormViewModel>()
        .save(draft, imagePath: _imagePath);
    if (!mounted) return;
    if (result.error != null) {
      showSnack(context, result.error!);
      return;
    }
    if (result.warning != null) showSnack(context, result.warning!);
    Navigator.of(context).pop(true);
  }

  String? _positiveInt(String? v) {
    final n = int.tryParse((v ?? '').trim());
    return (n == null || n < 1) ? 'Número inválido' : null;
  }

  @override
  Widget build(BuildContext context) {
    final vm = context.watch<RecipeFormViewModel>();
    return Scaffold(
      appBar: AppBar(
        title: Text(vm.isEdit ? 'Editar receita' : 'Nova receita'),
        actions: [
          TextButton(
            onPressed: vm.saving ? null : _submit,
            child: vm.saving
                ? const SizedBox(
                    height: 18,
                    width: 18,
                    child: CircularProgressIndicator(strokeWidth: 2))
                : const Text('Publicar'),
          ),
        ],
      ),
      body: Form(
        key: _formKey,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            _PhotoPicker(
              path: _imagePath,
              existingUrl: widget.existing?.imageUrl,
              onTap: _photoSheet,
            ),
            const SizedBox(height: 16),
            TextFormField(
              controller: _title,
              maxLength: 120,
              decoration: const InputDecoration(
                  labelText: 'Título', border: OutlineInputBorder()),
              validator: (v) =>
                  (v ?? '').trim().length < 3 ? 'Mínimo 3 caracteres' : null,
            ),
            const SizedBox(height: 8),
            TextFormField(
              controller: _description,
              maxLines: 3,
              maxLength: 1000,
              decoration: const InputDecoration(
                  labelText: 'Descrição (opcional)',
                  border: OutlineInputBorder()),
            ),
            const SectionTitle('Categoria'),
            if (vm.categoriesError != null)
              InlineNotice(
                  message: 'Não foi possível carregar as categorias.',
                  onRetry: vm.loadCategories)
            else
              Wrap(
                spacing: 8,
                children: [
                  for (final c in vm.categories)
                    ChoiceChip(
                      label: Text(c.name),
                      selected: _category == c.slug,
                      onSelected: (_) => setState(() => _category = c.slug),
                    ),
                ],
              ),
            const SectionTitle('Dificuldade'),
            Wrap(
              spacing: 8,
              children: [
                for (final e in difficulties.entries)
                  ChoiceChip(
                    label: Text(e.value),
                    selected: _difficulty == e.key,
                    onSelected: (_) => setState(() => _difficulty = e.key),
                  ),
              ],
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  child: TextFormField(
                    controller: _time,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(
                        labelText: 'Tempo (min)', border: OutlineInputBorder()),
                    validator: _positiveInt,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: TextFormField(
                    controller: _servings,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(
                        labelText: 'Doses', border: OutlineInputBorder()),
                    validator: _positiveInt,
                  ),
                ),
              ],
            ),
            const SectionTitle('Ingredientes'),
            for (var i = 0; i < _ingredients.length; i++)
              Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Row(
                  children: [
                    SizedBox(
                      width: 64,
                      child: TextField(
                        controller: _ingredients[i].quantity,
                        keyboardType: const TextInputType.numberWithOptions(
                            decimal: true),
                        decoration: const InputDecoration(
                            hintText: 'Qtd',
                            border: OutlineInputBorder(),
                            isDense: true),
                      ),
                    ),
                    const SizedBox(width: 6),
                    SizedBox(
                      width: 72,
                      child: TextField(
                        controller: _ingredients[i].unit,
                        decoration: const InputDecoration(
                            hintText: 'Unid.',
                            border: OutlineInputBorder(),
                            isDense: true),
                      ),
                    ),
                    const SizedBox(width: 6),
                    Expanded(
                      child: TextField(
                        controller: _ingredients[i].name,
                        decoration: const InputDecoration(
                            hintText: 'Ingrediente',
                            border: OutlineInputBorder(),
                            isDense: true),
                      ),
                    ),
                    IconButton(
                      icon: const Icon(Icons.remove_circle_outline),
                      onPressed: _ingredients.length == 1
                          ? null
                          : () => setState(() => _ingredients.removeAt(i)),
                    ),
                  ],
                ),
              ),
            TextButton.icon(
              onPressed: () =>
                  setState(() => _ingredients.add(_IngredientRow())),
              icon: const Icon(Icons.add),
              label: const Text('Adicionar ingrediente'),
            ),
            const SectionTitle('Passos de preparação'),
            for (var i = 0; i < _steps.length; i++)
              Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Padding(
                      padding: const EdgeInsets.only(top: 12, right: 8),
                      child: CircleAvatar(
                          radius: 12,
                          child: Text('${i + 1}',
                              style: const TextStyle(fontSize: 12))),
                    ),
                    Expanded(
                      child: TextField(
                        controller: _steps[i],
                        minLines: 1,
                        maxLines: 4,
                        decoration: const InputDecoration(
                            hintText: 'Descreve este passo',
                            border: OutlineInputBorder(),
                            isDense: true),
                      ),
                    ),
                    IconButton(
                      icon: const Icon(Icons.remove_circle_outline),
                      onPressed: _steps.length == 1
                          ? null
                          : () => setState(() => _steps.removeAt(i)),
                    ),
                  ],
                ),
              ),
            TextButton.icon(
              onPressed: () =>
                  setState(() => _steps.add(TextEditingController())),
              icon: const Icon(Icons.add),
              label: const Text('Adicionar passo'),
            ),
            const SectionTitle('Etiquetas'),
            TextFormField(
              controller: _tags,
              decoration: const InputDecoration(
                hintText: 'tradicional, verão, rápido',
                helperText: 'Separadas por vírgulas',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 24),
            FilledButton.icon(
              onPressed: vm.saving ? null : _submit,
              icon: const Icon(Icons.check),
              label:
                  Text(vm.isEdit ? 'Guardar alterações' : 'Publicar receita'),
            ),
          ],
        ),
      ),
    );
  }
}

class _PhotoPicker extends StatelessWidget {
  const _PhotoPicker(
      {required this.path, required this.existingUrl, required this.onTap});

  final String? path;
  final String? existingUrl;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    Widget content;
    if (path != null) {
      content = Image.file(File(path!),
          height: 200, width: double.infinity, fit: BoxFit.cover);
    } else if (existingUrl != null) {
      content = RecipeImage(imageUrl: existingUrl, height: 200);
    } else {
      content = Container(
        height: 200,
        color: Colors.orange.shade50,
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.add_a_photo, size: 40, color: Colors.orange.shade300),
            const SizedBox(height: 8),
            const Text('Tirar ou escolher uma fotografia'),
          ],
        ),
      );
    }
    return GestureDetector(
      onTap: onTap,
      child: ClipRRect(borderRadius: BorderRadius.circular(12), child: content),
    );
  }
}
