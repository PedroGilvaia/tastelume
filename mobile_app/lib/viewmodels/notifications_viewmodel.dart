import 'dart:async';

import '../models/activity.dart';
import '../services/backend.dart';
import 'base.dart';

class NotificationsViewModel extends BaseViewModel {
  NotificationsViewModel(this._activity);

  final ActivityApi _activity;

  int unread = 0;
  List<AppNotification> items = [];
  int total = 0;
  bool loading = false;
  bool loadingMore = false;
  String? error;
  Timer? _timer;

  bool get hasMore => items.length < total;

  /// Consulta periódica do emblema (sem tempo real: o backend não envia push).
  void startPolling() {
    _timer?.cancel();
    refreshUnread();
    _timer =
        Timer.periodic(const Duration(seconds: 30), (_) => refreshUnread());
  }

  Future<void> refreshUnread() async {
    try {
      final n = await _activity.unreadCount();
      if (n != unread) {
        unread = n;
        notifyListeners();
      }
    } catch (_) {
      // O emblema é secundário: sem Activity Service simplesmente não atualiza.
    }
  }

  Future<void> refresh() async {
    loading = true;
    error = null;
    notifyListeners();
    try {
      final page = await _activity.notifications();
      items = page.items;
      total = page.total;
      unread = page.unread;
    } catch (e) {
      error = errorText(e);
    }
    loading = false;
    notifyListeners();
  }

  Future<void> loadMore() async {
    if (loading || loadingMore || !hasMore) return;
    loadingMore = true;
    notifyListeners();
    try {
      final page = await _activity.notifications(offset: items.length);
      items = [...items, ...page.items];
      total = page.total;
      unread = page.unread;
    } catch (_) {}
    loadingMore = false;
    notifyListeners();
  }

  Future<void> markRead(AppNotification n) async {
    if (n.read) return;
    items = [for (final i in items) i.id == n.id ? i.asRead() : i];
    if (unread > 0) unread -= 1;
    notifyListeners();
    try {
      await _activity.markRead(n.id);
    } catch (_) {
      refreshUnread();
    }
  }

  Future<String?> markAllRead() async {
    try {
      await _activity.markAllRead();
      items = [for (final i in items) i.asRead()];
      unread = 0;
      notifyListeners();
      return null;
    } catch (e) {
      return errorText(e);
    }
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }
}
