import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/config.dart';
import '../../viewmodels/auth_viewmodel.dart';
import '../common/widgets.dart';

Future<void> showServerDialog(BuildContext context) async {
  final config = context.read<ApiConfig>();
  final controller = TextEditingController(text: config.host);
  await showDialog<void>(
    context: context,
    builder: (ctx) => AlertDialog(
      title: const Text('Endereço do servidor'),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          TextField(
            controller: controller,
            keyboardType: TextInputType.url,
            decoration: const InputDecoration(
                labelText: 'Anfitrião (IP ou nome)', hintText: '192.168.1.20'),
          ),
          const SizedBox(height: 12),
          const Text(
            'Emulador Android: 10.0.2.2\nSimulador iOS: localhost\nTelemóvel físico: IP do computador na rede local.\n'
            'Os serviços usam as portas 8001 a 8004.',
            style: TextStyle(fontSize: 12, color: Colors.grey),
          ),
        ],
      ),
      actions: [
        TextButton(
            onPressed: () => Navigator.pop(ctx), child: const Text('Cancelar')),
        FilledButton(
          onPressed: () async {
            await config.setHost(controller.text);
            if (ctx.mounted) Navigator.pop(ctx);
          },
          child: const Text('Guardar'),
        ),
      ],
    ),
  );
}

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  final _identifier = TextEditingController();
  final _username = TextEditingController();
  final _email = TextEditingController();
  final _password = TextEditingController();
  bool _register = false;
  bool _obscure = true;

  @override
  void dispose() {
    _identifier.dispose();
    _username.dispose();
    _email.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    final auth = context.read<AuthViewModel>();
    if (_register) {
      await auth.register(_username.text, _email.text, _password.text);
    } else {
      await auth.login(_identifier.text, _password.text);
    }
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthViewModel>();
    return Scaffold(
      appBar: AppBar(
        actions: [
          IconButton(
            tooltip: 'Servidor',
            icon: const Icon(Icons.dns_outlined),
            onPressed: () => showServerDialog(context),
          ),
        ],
      ),
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 420),
              child: Form(
                key: _formKey,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Icon(Icons.restaurant_menu,
                        size: 64, color: Theme.of(context).colorScheme.primary),
                    const SizedBox(height: 8),
                    Text('Tastelume',
                        textAlign: TextAlign.center,
                        style: Theme.of(context).textTheme.headlineLarge),
                    const Text('Partilha as tuas receitas',
                        textAlign: TextAlign.center),
                    const SizedBox(height: 24),
                    if (auth.notice != null)
                      InlineNotice(message: auth.notice!),
                    if (_register) ...[
                      TextFormField(
                        controller: _username,
                        decoration: const InputDecoration(
                            labelText: 'Nome de utilizador',
                            border: OutlineInputBorder()),
                        validator: (v) => RegExp(r'^[A-Za-z0-9_]{3,30}$')
                                .hasMatch((v ?? '').trim())
                            ? null
                            : '3 a 30 caracteres: letras, números ou _',
                      ),
                      const SizedBox(height: 12),
                      TextFormField(
                        controller: _email,
                        keyboardType: TextInputType.emailAddress,
                        decoration: const InputDecoration(
                            labelText: 'Email', border: OutlineInputBorder()),
                        validator: (v) => RegExp(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
                                .hasMatch((v ?? '').trim())
                            ? null
                            : 'Email inválido',
                      ),
                    ] else
                      TextFormField(
                        controller: _identifier,
                        decoration: const InputDecoration(
                            labelText: 'Utilizador ou email',
                            border: OutlineInputBorder()),
                        validator: (v) =>
                            (v ?? '').trim().isEmpty ? 'Obrigatório' : null,
                      ),
                    const SizedBox(height: 12),
                    TextFormField(
                      controller: _password,
                      obscureText: _obscure,
                      decoration: InputDecoration(
                        labelText: 'Password',
                        border: const OutlineInputBorder(),
                        suffixIcon: IconButton(
                          icon: Icon(_obscure
                              ? Icons.visibility
                              : Icons.visibility_off),
                          onPressed: () => setState(() => _obscure = !_obscure),
                        ),
                      ),
                      validator: (v) {
                        final value = v ?? '';
                        if (value.isEmpty) return 'Obrigatória';
                        if (_register && value.length < 8)
                          return 'Mínimo 8 caracteres';
                        return null;
                      },
                      onFieldSubmitted: (_) => _submit(),
                    ),
                    if (auth.error != null) ...[
                      const SizedBox(height: 12),
                      Text(auth.error!,
                          style: TextStyle(
                              color: Theme.of(context).colorScheme.error)),
                    ],
                    const SizedBox(height: 20),
                    FilledButton(
                      onPressed: auth.busy ? null : _submit,
                      child: auth.busy
                          ? const SizedBox(
                              height: 20,
                              width: 20,
                              child: CircularProgressIndicator(strokeWidth: 2))
                          : Text(_register ? 'Criar conta' : 'Entrar'),
                    ),
                    TextButton(
                      onPressed: () => setState(() => _register = !_register),
                      child: Text(
                          _register ? 'Já tenho conta' : 'Criar conta nova'),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// Mostrado quando há sessão guardada mas o servidor não responde.
class OfflineScreen extends StatelessWidget {
  const OfflineScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthViewModel>();
    return Scaffold(
      appBar: AppBar(title: const Text('Tastelume')),
      body: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          ErrorState(
              message: auth.error ?? 'Não foi possível contactar o servidor.',
              onRetry: auth.retry),
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              TextButton(
                  onPressed: () => showServerDialog(context),
                  child: const Text('Alterar servidor')),
              TextButton(
                  onPressed: auth.logout, child: const Text('Terminar sessão')),
            ],
          ),
        ],
      ),
    );
  }
}
