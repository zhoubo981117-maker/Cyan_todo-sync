import "package:flutter/material.dart";

import "../app_state.dart";
import "../models.dart";
import "login_page.dart";

class HomePage extends StatefulWidget {
  const HomePage({super.key, required this.state});
  final AppState state;

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  @override
  void initState() {
    super.initState();
    widget.state.addListener(_onState);
  }

  @override
  void dispose() {
    widget.state.removeListener(_onState);
    super.dispose();
  }

  void _onState() {
    if (mounted) setState(() {});
  }

  @override
  Widget build(BuildContext context) {
    if (!widget.state.ready) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }
    if (!widget.state.loggedIn) {
      return LoginPage(state: widget.state);
    }

    return Scaffold(
      appBar: AppBar(
        title: const Text("Todo Sync"),
        actions: [
          IconButton(
            onPressed: widget.state.syncing ? null : () => widget.state.runSync(),
            icon: const Icon(Icons.sync),
            tooltip: "同步",
          ),
          IconButton(
            onPressed: () async => widget.state.logout(),
            icon: const Icon(Icons.logout),
            tooltip: "退出",
          ),
        ],
      ),
      body: Column(
        children: [
          if (widget.state.msg != null)
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 10, 16, 0),
              child: Text(widget.state.msg!, style: TextStyle(color: Theme.of(context).colorScheme.onSurfaceVariant)),
            ),
          Expanded(
            child: RefreshIndicator(
              onRefresh: () => widget.state.runSync(),
              child: ListView.builder(
                itemCount: widget.state.todos.length,
                itemBuilder: (context, i) => _TodoTile(state: widget.state, todo: widget.state.todos[i]),
              ),
            ),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () => _showAddTodo(context),
        child: const Icon(Icons.add),
      ),
    );
  }

  Future<void> _showAddTodo(BuildContext context) async {
    final title = TextEditingController();
    final note = TextEditingController();
    int urgency = 1;
    DateTime? due;

    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) {
        return AlertDialog(
          title: const Text("新代办"),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextField(controller: title, decoration: const InputDecoration(labelText: "标题")),
                TextField(controller: note, decoration: const InputDecoration(labelText: "备注（可选）")),
                const SizedBox(height: 10),
                DropdownButtonFormField<int>(
                  value: urgency,
                  items: const [
                    DropdownMenuItem(value: 0, child: Text("不急")),
                    DropdownMenuItem(value: 1, child: Text("普通")),
                    DropdownMenuItem(value: 2, child: Text("紧急")),
                    DropdownMenuItem(value: 3, child: Text("非常紧急")),
                  ],
                  onChanged: (v) => urgency = v ?? 1,
                  decoration: const InputDecoration(labelText: "紧急程度"),
                ),
                const SizedBox(height: 10),
                OutlinedButton.icon(
                  onPressed: () async {
                    final now = DateTime.now();
                    final d = await showDatePicker(context: ctx, firstDate: now, lastDate: now.add(const Duration(days: 3650)));
                    if (d == null) return;
                    final t = await showTimePicker(context: ctx, initialTime: TimeOfDay.fromDateTime(now));
                    if (t == null) return;
                    due = DateTime(d.year, d.month, d.day, t.hour, t.minute);
                    if (ctx.mounted) (ctx as Element).markNeedsBuild();
                  },
                  icon: const Icon(Icons.schedule),
                  label: Text(due == null ? "选择截止时间（可选）" : "截止: ${due!.toString().substring(0, 16)}"),
                ),
              ],
            ),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text("取消")),
            FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text("添加")),
          ],
        );
      },
    );

    if (ok != true) return;
    final v = title.text.trim();
    if (v.isEmpty) return;
    await widget.state.addTodo(title: v, note: note.text, urgency: urgency, dueAtLocal: due);
    await widget.state.runSync();
  }
}

class _TodoTile extends StatefulWidget {
  const _TodoTile({required this.state, required this.todo});
  final AppState state;
  final Todo todo;

  @override
  State<_TodoTile> createState() => _TodoTileState();
}

class _TodoTileState extends State<_TodoTile> {
  bool _open = false;
  final _sub = TextEditingController();

  @override
  void dispose() {
    _sub.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final t = widget.todo;
    final due = t.dueAtUtcIso == null ? null : DateTime.tryParse(t.dueAtUtcIso!)?.toLocal();
    final urg = _urgencyLabel(t.urgency);

    return Card(
      margin: const EdgeInsets.fromLTRB(12, 8, 12, 0),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(12, 10, 12, 10),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Checkbox(value: t.done, onChanged: (v) => widget.state.toggleTodoDone(t, v ?? false)),
                Expanded(
                  child: InkWell(
                    onTap: () => setState(() => _open = !_open),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(t.title, style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700, decoration: t.done ? TextDecoration.lineThrough : null)),
                        const SizedBox(height: 4),
                        Wrap(
                          spacing: 8,
                          runSpacing: 6,
                          children: [
                            _chip(context, urg, _urgencyColor(context, t.urgency)),
                            if (due != null) _chip(context, "截止 ${due.toString().substring(0, 16)}", Theme.of(context).colorScheme.primary),
                          ],
                        ),
                      ],
                    ),
                  ),
                ),
                IconButton(
                  onPressed: () async {
                    final ok = await showDialog<bool>(
                      context: context,
                      builder: (ctx) => AlertDialog(
                        title: const Text("删除代办"),
                        content: const Text("删除后会在所有设备消失（同步后生效）。"),
                        actions: [
                          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text("取消")),
                          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text("删除")),
                        ],
                      ),
                    );
                    if (ok == true) await widget.state.deleteTodo(t);
                    await widget.state.runSync();
                  },
                  icon: const Icon(Icons.delete_outline),
                  tooltip: "删除",
                ),
              ],
            ),
            if (t.note.isNotEmpty)
              Padding(
                padding: const EdgeInsets.only(left: 48, top: 2, right: 8),
                child: Text(t.note, style: TextStyle(color: Theme.of(context).colorScheme.onSurfaceVariant)),
              ),
            if (_open) ...[
              const SizedBox(height: 10),
              FutureBuilder(
                future: widget.state.subtasks(t.clientId),
                builder: (context, snap) {
                  final subs = snap.data ?? const <Subtask>[];
                  return Column(
                    children: [
                      for (final s in subs)
                        ListTile(
                          dense: true,
                          contentPadding: const EdgeInsets.only(left: 40, right: 0),
                          leading: Checkbox(value: s.done, onChanged: (v) => widget.state.toggleSubtask(s, v ?? false)),
                          title: Text(s.title, style: TextStyle(decoration: s.done ? TextDecoration.lineThrough : null)),
                          trailing: IconButton(
                            onPressed: () async {
                              await widget.state.deleteSubtask(s);
                              await widget.state.runSync();
                              if (mounted) setState(() {});
                            },
                            icon: const Icon(Icons.close),
                          ),
                        ),
                      Padding(
                        padding: const EdgeInsets.fromLTRB(40, 6, 10, 0),
                        child: Row(
                          children: [
                            Expanded(
                              child: TextField(
                                controller: _sub,
                                decoration: const InputDecoration(hintText: "添加子任务..."),
                                onSubmitted: (_) => _addSub(t.clientId),
                              ),
                            ),
                            const SizedBox(width: 8),
                            FilledButton(onPressed: () => _addSub(t.clientId), child: const Text("添加")),
                          ],
                        ),
                      ),
                    ],
                  );
                },
              ),
            ],
          ],
        ),
      ),
    );
  }

  Future<void> _addSub(String todoClientId) async {
    final title = _sub.text.trim();
    if (title.isEmpty) return;
    _sub.clear();
    await widget.state.addSubtask(todoClientId, title);
    await widget.state.runSync();
    if (mounted) setState(() {});
  }

  Widget _chip(BuildContext context, String text, Color c) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: c.withOpacity(.45)),
      ),
      child: Text(text, style: TextStyle(fontSize: 12, color: c)),
    );
  }

  String _urgencyLabel(int u) {
    if (u == 0) return "不急";
    if (u == 2) return "紧急";
    if (u == 3) return "非常紧急";
    return "普通";
  }

  Color _urgencyColor(BuildContext context, int u) {
    if (u == 0) return Colors.greenAccent;
    if (u == 2) return Colors.amber;
    if (u == 3) return Colors.redAccent;
    return Theme.of(context).colorScheme.onSurfaceVariant;
  }
}

