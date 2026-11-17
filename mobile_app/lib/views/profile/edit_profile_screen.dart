import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../viewmodels/auth_viewmodel.dart';
import '../common/widgets.dart';

class EditProfileScreen extends StatefulWidget {
  const EditProfileScreen({super.key});

  @override
  State<EditProfileScreen> createState() => _EditProfileScreenState();
}

class _EditProfileScreenState extends State<EditProfileScreen> {
  late final TextEditingController _description;
  late final TextEditingController _interests;
  bool _saving = false;

  @override
  void initState() {
    super.initState();
    final me = context.read<AuthViewModel>().me!;
    _description = TextEditingController(text: me.description);
    _interests = TextEditingController(text: me.interests.join(', '));
  }

  @override
  void dispose() {
    _description.dispose();
    _interests.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    setState(() => _saving = true);
    final interests = _interests.text
        .split(',')
        .map((e) => e.trim())
        .where((e) => e.isNotEmpty)
        .toList();
    final error = await context.read<AuthViewModel>().updateProfile(
        description: _description.text.trim(), interests: interests);
    if (!mounted) return;
    setState(() => _saving = false);
    if (error != null) {
      showSnack(context, error);
    } else {
      Navigator.of(context).pop(true);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(
          title: const Text('Editar perfil'),
          actions: [
            TextButton(
                onPressed: _saving ? null : _save, child: const Text('Guardar'))
          ],
        ),
        body: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            TextField(
              controller: _description,
              maxLines: 4,
              maxLength: 500,
              decoration: const InputDecoration(
                  labelText: 'Sobre mim', border: OutlineInputBorder()),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _interests,
              decoration: const InputDecoration(
                labelText: 'Interesses',
                helperText:
                    'Separados por vírgulas. Usa nomes de categorias (Sopas, Sobremesas…) para personalizar o feed «Para ti».',
                helperMaxLines: 3,
                border: OutlineInputBorder(),
              ),
            ),
          ],
        ),
      );
}
