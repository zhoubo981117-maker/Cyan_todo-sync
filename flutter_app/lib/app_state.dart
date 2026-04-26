import "dart:async";
import "dart:convert";

import "package:flutter/foundation.dart";

import "data/api_client.dart";
import "data/auth_store.dart";
import "data/local_db.dart";
import "data/sync_service.dart";
import "models.dart";

class AppState extends ChangeNotifier {
  AppState({required this.auth, required this.db, required this.sync});

  final AuthStore auth;
  final LocalDb db;
  final SyncService sync;

  bool _ready = false;
  bool get ready => _ready;

  String? _email;
  String? get email => _email;

  String _baseUrl = "";
  String get baseUrl => _baseUrl;

  bool _syncing = false;
  bool get syncing => _syncing;

  String? _msg;
  String? get msg => _msg;

  List<Todo> _todos = const [];
  List<Todo> get todos => _todos;

  Timer? _timer;

  Future<void> init() async {
    _baseUrl = (await auth.getBaseUrl()) ?? "";
    _email = await auth.getEmail();
    await _reloadLocal();
    _ready = true;
    notifyListeners();

    // Background sync every ~20s when logged in.
    _timer?.cancel();
    _timer = Timer.periodic(const Duration(seconds: 20), (_) {
      if (!loggedIn) return;
      unawaited(runSync());
    });

    if (loggedIn) {
      unawaited(runSync());
    }
  }

  bool get loggedIn => (_baseUrl.isNotEmpty) && (_email != null) && ((_tokenCache ?? "").isNotEmpty);

  String? _tokenCache;

  Future<String?> _token() async {
    _tokenCache ??= await auth.getToken();
    return _tokenCache;
  }

  ApiClient? _api;
  Future<ApiClient> _apiClient() async {
    final token = await _token();
    final api = ApiClient(baseUrl: _baseUrl, token: token);
    _api = api;
    return api;
  }

  Future<void> setBaseUrl(String v) async {
    _baseUrl = v.trim();
    await auth.setBaseUrl(_baseUrl);
    notifyListeners();
  }

  Future<void> register(String email, String password) async {
    final api = ApiClient(baseUrl: _baseUrl, token: null);
    final res = await api.postJson("/api/register", {"email": email, "password": password});
    final token = res["token"]?.toString() ?? "";
    if (token.isEmpty) throw Exception("No token");
    await auth.setToken(token);
    await auth.setEmail(email);
    _tokenCache = token;
    _email = email;
    notifyListeners();
    await runSync();
  }

  Future<void> login(String email, String password) async {
    final api = ApiClient(baseUrl: _baseUrl, token: null);
    final res = await api.postJson("/api/login", {"email": email, "password": password});
    final token = res["token"]?.toString() ?? "";
    if (token.isEmpty) throw Exception("No token");
    await auth.setToken(token);
    await auth.setEmail(email);
    _tokenCache = token;
    _email = email;
    notifyListeners();
    await runSync();
  }

  Future<void> logout() async {
    await auth.clearToken();
    _tokenCache = null;
    _email = null;
    _api = null;
    _msg = null;
    notifyListeners();
  }

  Future<void> _reloadLocal() async {
    _todos = await db.listTodos();
    notifyListeners();
  }

  Future<void> runSync() async {
    if (_syncing) return;
    _syncing = true;
    _msg = "同步中...";
    notifyListeners();
    try {
      final api = await _apiClient();
      await sync.pushAndPull(api);
      await _reloadLocal();
      _msg = "已同步 ${DateTime.now().toLocal().toString().substring(11, 19)}";
    } catch (e) {
      _msg = "同步失败: $e";
    } finally {
      _syncing = false;
      notifyListeners();
    }
  }

  Future<void> addTodo({
    required String title,
    required String note,
    required int urgency,
    required DateTime? dueAtLocal,
  }) async {
    final cid = sync.newClientId();
    final dueUtcIso = dueAtLocal == null ? null : dueAtLocal.toUtc().toIso8601String().replaceFirst(RegExp(r"\\.\\d+Z\$"), "+00:00");
    final now = utcNowIso();
    final t = Todo(
      clientId: cid,
      title: title.trim(),
      note: note.trim(),
      urgency: urgency,
      dueAtUtcIso: dueUtcIso,
      done: false,
      deletedAtUtcIso: null,
      updatedAtUtcIso: now,
    );
    await db.upsertTodo(t);
    await db.enqueueOutbox("todo", jsonEncode(t.toJsonForSync()), now);
    await _reloadLocal();
  }

  Future<void> toggleTodoDone(Todo t, bool done) async {
    final now = utcNowIso();
    final next = Todo(
      clientId: t.clientId,
      title: t.title,
      note: t.note,
      urgency: t.urgency,
      dueAtUtcIso: t.dueAtUtcIso,
      done: done,
      deletedAtUtcIso: t.deletedAtUtcIso,
      updatedAtUtcIso: now,
    );
    await db.upsertTodo(next);
    await db.enqueueOutbox("todo", jsonEncode(next.toJsonForSync()), now);
    await _reloadLocal();
  }

  Future<void> deleteTodo(Todo t) async {
    final now = utcNowIso();
    final next = Todo(
      clientId: t.clientId,
      title: t.title,
      note: t.note,
      urgency: t.urgency,
      dueAtUtcIso: t.dueAtUtcIso,
      done: t.done,
      deletedAtUtcIso: now,
      updatedAtUtcIso: now,
    );
    await db.upsertTodo(next);
    await db.enqueueOutbox("todo", jsonEncode(<String, Object?>{"clientId": t.clientId, "deleted": true}), now);
    await _reloadLocal();
  }

  Future<List<Subtask>> subtasks(String todoClientId) => db.listSubtasks(todoClientId);

  Future<void> addSubtask(String todoClientId, String title) async {
    final now = utcNowIso();
    final s = Subtask(
      clientId: sync.newClientId(),
      todoClientId: todoClientId,
      title: title.trim(),
      done: false,
      deletedAtUtcIso: null,
      updatedAtUtcIso: now,
    );
    await db.upsertSubtask(s);
    await db.enqueueOutbox("subtask", jsonEncode(s.toJsonForSync()), now);
    await _reloadLocal();
  }

  Future<void> toggleSubtask(Subtask s, bool done) async {
    final now = utcNowIso();
    final next = Subtask(
      clientId: s.clientId,
      todoClientId: s.todoClientId,
      title: s.title,
      done: done,
      deletedAtUtcIso: s.deletedAtUtcIso,
      updatedAtUtcIso: now,
    );
    await db.upsertSubtask(next);
    await db.enqueueOutbox("subtask", jsonEncode(next.toJsonForSync()), now);
    await _reloadLocal();
  }

  Future<void> deleteSubtask(Subtask s) async {
    final now = utcNowIso();
    final next = Subtask(
      clientId: s.clientId,
      todoClientId: s.todoClientId,
      title: s.title,
      done: s.done,
      deletedAtUtcIso: now,
      updatedAtUtcIso: now,
    );
    await db.upsertSubtask(next);
    await db.enqueueOutbox("subtask", jsonEncode(<String, Object?>{"clientId": s.clientId, "todoClientId": s.todoClientId, "deleted": true}), now);
    await _reloadLocal();
  }
}

