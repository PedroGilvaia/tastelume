import 'dart:async';

import '../models/interaction.dart';
import '../services/backend.dart';
import 'base.dart';

/// Lista de conversas e de receitas partilhadas comigo (dois blocos independentes).
class MessagesViewModel extends BaseViewModel {
  MessagesViewModel(this._interactions);

  final InteractionApi _interactions;

  List<Conversation> conversations = [];
  String? conversationsError;
  List<RecipeShare> shares = [];
  String? sharesError;
  bool loading = true;

  Future<void> load() async {
    loading = true;
    notifyListeners();
    await Future.wait([_loadConversations(), _loadShares()]);
    loading = false;
    notifyListeners();
  }

  Future<void> _loadConversations() async {
    try {
      conversations = await _interactions.conversations();
      conversationsError = null;
    } catch (e) {
      conversationsError = errorText(e);
    }
  }

  Future<void> _loadShares() async {
    try {
      shares = await _interactions.receivedShares();
      sharesError = null;
    } catch (e) {
      sharesError = errorText(e);
    }
  }
}

class ChatViewModel extends BaseViewModel {
  ChatViewModel(this.otherUserId, this._interactions, this.myId);

  final int otherUserId;
  final InteractionApi _interactions;
  final int myId;

  List<Message> messages = [];
  bool loading = true;
  bool sending = false;
  String? error;
  String? pollError;
  Timer? _timer;
  bool _polling = false;

  int get _lastId => messages.isEmpty ? 0 : messages.last.id;

  Future<void> load() async {
    loading = true;
    error = null;
    notifyListeners();
    try {
      List<Message> batch;
      do {
        batch = await _interactions.messages(otherUserId, afterId: _lastId);
        messages = [...messages, ...batch];
      } while (batch.length >= 100);
      _timer?.cancel();
      _timer = Timer.periodic(const Duration(seconds: 5), (_) => poll());
    } catch (e) {
      error = errorText(e);
    }
    loading = false;
    notifyListeners();
  }

  /// Sem tempo real: pede só as mensagens novas (`after_id`). Falhas de rede não interrompem a conversa.
  Future<void> poll() async {
    if (_polling || loading) return;
    _polling = true;
    try {
      final batch = await _interactions.messages(otherUserId, afterId: _lastId);
      final hadError = pollError != null;
      pollError = null;
      if (batch.isNotEmpty) messages = [...messages, ...batch];
      if (batch.isNotEmpty || hadError) notifyListeners();
    } catch (e) {
      final had = pollError != null;
      pollError = errorText(e);
      if (!had) notifyListeners();
    } finally {
      _polling = false;
    }
  }

  Future<String?> send(String text) async {
    sending = true;
    notifyListeners();
    try {
      final m = await _interactions.sendMessage(otherUserId, text);
      if (!messages.any((x) => x.id == m.id)) messages = [...messages, m];
      return null;
    } catch (e) {
      return errorText(e);
    } finally {
      sending = false;
      notifyListeners();
    }
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }
}
