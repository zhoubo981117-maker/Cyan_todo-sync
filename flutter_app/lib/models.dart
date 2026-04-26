class Todo {
  Todo({
    required this.clientId,
    required this.title,
    required this.note,
    required this.urgency,
    required this.dueAtUtcIso,
    required this.done,
    required this.deletedAtUtcIso,
    required this.updatedAtUtcIso,
  });

  final String clientId;
  final String title;
  final String note;
  final int urgency; // 0..3
  final String? dueAtUtcIso; // ISO in UTC, nullable
  final bool done;
  final String? deletedAtUtcIso;
  final String updatedAtUtcIso;

  Map<String, Object?> toJsonForSync() {
    return <String, Object?>{
      "clientId": clientId,
      "title": title,
      "note": note,
      "urgency": urgency,
      "dueAt": dueAtUtcIso,
      "done": done,
      "deletedAt": deletedAtUtcIso,
    };
  }
}

class Subtask {
  Subtask({
    required this.clientId,
    required this.todoClientId,
    required this.title,
    required this.done,
    required this.deletedAtUtcIso,
    required this.updatedAtUtcIso,
  });

  final String clientId;
  final String todoClientId;
  final String title;
  final bool done;
  final String? deletedAtUtcIso;
  final String updatedAtUtcIso;

  Map<String, Object?> toJsonForSync() {
    return <String, Object?>{
      "clientId": clientId,
      "todoClientId": todoClientId,
      "title": title,
      "done": done,
      "deletedAt": deletedAtUtcIso,
    };
  }
}

