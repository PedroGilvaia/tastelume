import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/format.dart';
import '../../services/backend.dart';
import '../../viewmodels/auth_viewmodel.dart';
import '../../viewmodels/messages_viewmodel.dart';
import '../common/widgets.dart';

class ChatScreen extends StatelessWidget {
  const ChatScreen({super.key, required this.userId, this.username});

  final int userId;
  final String? username;

  @override
  Widget build(BuildContext context) => ChangeNotifierProvider(
        create: (c) => ChatViewModel(
            userId, c.read<InteractionApi>(), c.read<AuthViewModel>().me!.id)
          ..load(),
        child: _ChatView(title: username ?? 'Utilizador #$userId'),
      );
}

class _ChatView extends StatefulWidget {
  const _ChatView({required this.title});

  final String title;

  @override
  State<_ChatView> createState() => _ChatViewState();
}

class _ChatViewState extends State<_ChatView> {
  final _controller = TextEditingController();
  final _scroll = ScrollController();
  int _lastCount = 0;

  @override
  void dispose() {
    _controller.dispose();
    _scroll.dispose();
    super.dispose();
  }

  void _scrollToEnd() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scroll.hasClients)
        _scroll.animateTo(_scroll.position.maxScrollExtent,
            duration: const Duration(milliseconds: 200), curve: Curves.easeOut);
    });
  }

  Future<void> _send(ChatViewModel vm) async {
    final text = _controller.text.trim();
    if (text.isEmpty || vm.sending) return;
    final error = await vm.send(text);
    if (!mounted) return;
    if (error != null) {
      showSnack(context, error);
    } else {
      _controller.clear();
    }
  }

  @override
  Widget build(BuildContext context) {
    final vm = context.watch<ChatViewModel>();
    if (vm.messages.length != _lastCount) {
      _lastCount = vm.messages.length;
      _scrollToEnd();
    }
    Widget body;
    if (vm.loading) {
      body = const Center(child: CircularProgressIndicator());
    } else if (vm.error != null && vm.messages.isEmpty) {
      body = ErrorState(message: vm.error!, onRetry: vm.load);
    } else if (vm.messages.isEmpty) {
      body = const EmptyState(
          icon: Icons.chat_bubble_outline, message: 'Diz olá 👋');
    } else {
      body = ListView.builder(
        controller: _scroll,
        padding: const EdgeInsets.all(12),
        itemCount: vm.messages.length,
        itemBuilder: (context, i) {
          final m = vm.messages[i];
          final mine = m.senderId == vm.myId;
          final scheme = Theme.of(context).colorScheme;
          return Align(
            alignment: mine ? Alignment.centerRight : Alignment.centerLeft,
            child: Container(
              margin: const EdgeInsets.symmetric(vertical: 3),
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              constraints: BoxConstraints(
                  maxWidth: MediaQuery.of(context).size.width * 0.75),
              decoration: BoxDecoration(
                color: mine
                    ? scheme.primaryContainer
                    : scheme.surfaceContainerHighest,
                borderRadius: BorderRadius.circular(14),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Text(m.text),
                  Text(timeAgo(m.createdAt),
                      style: Theme.of(context)
                          .textTheme
                          .labelSmall
                          ?.copyWith(color: Colors.grey.shade700)),
                ],
              ),
            ),
          );
        },
      );
    }
    return Scaffold(
      appBar: AppBar(title: Text(widget.title)),
      body: Column(
        children: [
          if (vm.pollError != null)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12),
              child: const InlineNotice(
                  message:
                      'Sem ligação: as novas mensagens vão aparecer quando o serviço voltar.'),
            ),
          Expanded(child: body),
          SafeArea(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(12, 4, 12, 8),
              child: Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _controller,
                      minLines: 1,
                      maxLines: 4,
                      maxLength: 2000,
                      textInputAction: TextInputAction.send,
                      onSubmitted: (_) => _send(vm),
                      decoration: const InputDecoration(
                          hintText: 'Mensagem…',
                          border: OutlineInputBorder(),
                          isDense: true,
                          counterText: ''),
                    ),
                  ),
                  const SizedBox(width: 8),
                  IconButton.filled(
                    onPressed: vm.sending ? null : () => _send(vm),
                    icon: const Icon(Icons.send),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
