import '../models/activity.dart';
import '../services/backend.dart';
import 'base.dart';

/// Estatísticas do utilizador. Cada bloco carrega e falha de forma independente.
class StatsViewModel extends BaseViewModel {
  StatsViewModel(this._activity);

  final ActivityApi _activity;

  int days = 30;
  bool loading = false;

  StatsTotals? totals;
  String? totalsError;
  List<DayPoint> timeline = [];
  String? timelineError;
  List<TopRecipe> top = [];
  String? topError;

  int get timelineDays => days > 90 ? 90 : days;

  Future<void> load() async {
    loading = true;
    totalsError = timelineError = topError = null;
    notifyListeners();
    await Future.wait([_loadTotals(), _loadTimeline(), _loadTop()]);
    loading = false;
    notifyListeners();
  }

  Future<void> _loadTotals() async {
    try {
      totals = await _activity.stats(days);
    } catch (e) {
      totalsError = errorText(e);
    }
  }

  Future<void> _loadTimeline() async {
    try {
      timeline = await _activity.timeline(timelineDays);
    } catch (e) {
      timelineError = errorText(e);
    }
  }

  Future<void> _loadTop() async {
    try {
      top = await _activity.topRecipes(days);
    } catch (e) {
      topError = errorText(e);
    }
  }

  void setDays(int value) {
    if (value == days) return;
    days = value;
    load();
  }
}
