/* Minimal client; no build step, runs on Android + Windows browsers. */

const API = {
  async request(path, opts = {}) {
    const token = localStorage.getItem("todo_token");
    const headers = Object.assign({ "Content-Type": "application/json" }, opts.headers || {});
    if (token) headers.Authorization = `Bearer ${token}`;
    const res = await fetch(path, Object.assign({}, opts, { headers }));
    let data = null;
    try {
      data = await res.json();
    } catch {
      data = null;
    }
    if (!res.ok) throw new Error(data && data.error ? data.error : `HTTP ${res.status}`);
    if (data && data.ok === false) throw new Error(data.error || "error");
    return data;
  },
  register(email, password) {
    return this.request("/api/register", { method: "POST", body: JSON.stringify({ email, password }) });
  },
  login(email, password) {
    return this.request("/api/login", { method: "POST", body: JSON.stringify({ email, password }) });
  },
  me() {
    return this.request("/api/me", { method: "GET" });
  },
  changePassword(currentPassword, newPassword) {
    return this.request("/api/password/change", { method: "POST", body: JSON.stringify({ currentPassword, newPassword }) });
  },
  resetPassword(newPassword) {
    return this.request("/api/password/reset", { method: "POST", body: JSON.stringify({ newPassword }) });
  },
  requestPasswordReset(email) {
    return this.request("/api/password/forgot", { method: "POST", body: JSON.stringify({ email }) });
  },
  confirmPasswordReset(email, token, code, newPassword) {
    return this.request("/api/password/forgot/confirm", {
      method: "POST",
      body: JSON.stringify({ email, token, code, newPassword }),
    });
  },
  version() {
    return this.request("/api/version", { method: "GET", cache: "no-store" });
  },
  organizeTodos(text) {
    return this.request("/api/ai/organize", { method: "POST", body: JSON.stringify({ text }) });
  },
  organizeRecord(text) {
    return this.request("/api/records/organize", { method: "POST", body: JSON.stringify({ text }) });
  },
  listRecords(filters = {}) {
    const params = new URLSearchParams();
    if (filters.q) params.set("q", filters.q);
    if (filters.source) params.set("source", filters.source);
    if (filters.status) params.set("status", filters.status);
    if (filters.type) params.set("type", filters.type);
    if (filters.tag) params.set("tag", filters.tag);
    if (filters.linked !== undefined && filters.linked !== "") params.set("hasTodo", filters.linked);
    const qs = params.toString();
    return this.request(`/api/records${qs ? `?${qs}` : ""}`, { method: "GET" });
  },
  bulkRecords(action, ids) {
    return this.request("/api/records/bulk", { method: "POST", body: JSON.stringify({ action, ids }) });
  },
  patchRecord(id, patch) {
    return this.request(`/api/records/${id}`, { method: "PATCH", body: JSON.stringify(patch) });
  },
  delRecord(id) {
    return this.request(`/api/records/${id}`, { method: "DELETE" });
  },
  retryRecord(id) {
    return this.request(`/api/records/${id}/retry`, { method: "POST", body: JSON.stringify({}) });
  },
  saveRecordTodos(id, items) {
    return this.request(`/api/records/${id}/todos`, { method: "POST", body: JSON.stringify({ items }) });
  },
  syncRecordDates(id) {
    return this.request(`/api/records/${id}/sync-dates`, { method: "POST", body: JSON.stringify({}) });
  },
  dailyPlan() {
    return this.request("/api/ai/daily-plan", { method: "POST", body: JSON.stringify({}) });
  },
  listTodos() {
    return this.request("/api/todos", { method: "GET" });
  },
  listArchive(filters = {}) {
    const params = new URLSearchParams();
    if (filters.q) params.set("q", filters.q);
    if (filters.from) params.set("from", filters.from);
    if (filters.to) params.set("to", filters.to);
    if (filters.urgency !== undefined && filters.urgency !== "") params.set("urgency", filters.urgency);
    const qs = params.toString();
    return this.request(`/api/todos/archive${qs ? `?${qs}` : ""}`, { method: "GET" });
  },
  restoreTodo(id) {
    return this.request(`/api/todos/${id}/restore`, { method: "POST", body: JSON.stringify({}) });
  },
  addTodo(todo) {
    return this.request("/api/todos", { method: "POST", body: JSON.stringify(todo) });
  },
  patchTodo(id, patch) {
    return this.request(`/api/todos/${id}`, { method: "PATCH", body: JSON.stringify(patch) });
  },
  delTodo(id) {
    return this.request(`/api/todos/${id}`, { method: "DELETE" });
  },
  addSub(todoId, title) {
    return this.request(`/api/todos/${todoId}/subtasks`, { method: "POST", body: JSON.stringify({ title }) });
  },
  patchSub(id, patch) {
    return this.request(`/api/subtasks/${id}`, { method: "PATCH", body: JSON.stringify(patch) });
  },
  delSub(id) {
    return this.request(`/api/subtasks/${id}`, { method: "DELETE" });
  },
};

const els = {
  authCard: document.getElementById("authCard"),
  appCard: document.getElementById("appCard"),
  authEmail: document.getElementById("authEmail"),
  authPassword: document.getElementById("authPassword"),
  btnLogin: document.getElementById("btnLogin"),
  btnRegister: document.getElementById("btnRegister"),
  btnForgotPasswordOpen: document.getElementById("btnForgotPasswordOpen"),
  authMsg: document.getElementById("authMsg"),
  btnLogout: document.getElementById("btnLogout"),
  btnRefresh: document.getElementById("btnRefresh"),
  btnSecurity: document.getElementById("btnSecurity"),
  versionNotice: document.getElementById("versionNotice"),
  versionNoticeTitle: document.getElementById("versionNoticeTitle"),
  versionNoticeText: document.getElementById("versionNoticeText"),
  btnApplyUpdate: document.getElementById("btnApplyUpdate"),
  whoami: document.getElementById("whoami"),
  taskStats: document.getElementById("taskStats"),
  versionInfo: document.getElementById("versionInfo"),
  calendarMonth: document.getElementById("calendarMonth"),
  calendarGrid: document.getElementById("calendarGrid"),
  btnToggleCalendar: document.getElementById("btnToggleCalendar"),
  securityDialog: document.getElementById("securityDialog"),
  btnCloseSecurity: document.getElementById("btnCloseSecurity"),
  btnToggleChangePassword: document.getElementById("btnToggleChangePassword"),
  btnToggleResetPassword: document.getElementById("btnToggleResetPassword"),
  changePasswordPanel: document.getElementById("changePasswordPanel"),
  resetPasswordPanel: document.getElementById("resetPasswordPanel"),
  changeCurrentPassword: document.getElementById("changeCurrentPassword"),
  changeNewPassword: document.getElementById("changeNewPassword"),
  changeConfirmPassword: document.getElementById("changeConfirmPassword"),
  btnChangePassword: document.getElementById("btnChangePassword"),
  resetNewPassword: document.getElementById("resetNewPassword"),
  resetConfirmPassword: document.getElementById("resetConfirmPassword"),
  btnResetPassword: document.getElementById("btnResetPassword"),
  securityMsg: document.getElementById("securityMsg"),
  forgotDialog: document.getElementById("forgotDialog"),
  btnCloseForgot: document.getElementById("btnCloseForgot"),
  forgotEmail: document.getElementById("forgotEmail"),
  forgotCode: document.getElementById("forgotCode"),
  forgotToken: document.getElementById("forgotToken"),
  forgotNewPassword: document.getElementById("forgotNewPassword"),
  forgotConfirmPassword: document.getElementById("forgotConfirmPassword"),
  btnRequestReset: document.getElementById("btnRequestReset"),
  btnConfirmForgotReset: document.getElementById("btnConfirmForgotReset"),
  forgotMsg: document.getElementById("forgotMsg"),
  newTitle: document.getElementById("newTitle"),
  newNote: document.getElementById("newNote"),
  newUrgency: document.getElementById("newUrgency"),
  newRepeatRule: document.getElementById("newRepeatRule"),
  newReminder: document.getElementById("newReminder"),
  newDueDate: document.getElementById("newDueDate"),
  newDueTime: document.getElementById("newDueTime"),
  dueSummary: document.getElementById("dueSummary"),
  btnAddTodo: document.getElementById("btnAddTodo"),
  appMsg: document.getElementById("appMsg"),
  btnToggleArchive: document.getElementById("btnToggleArchive"),
  btnCloseArchive: document.getElementById("btnCloseArchive"),
  archivePanel: document.getElementById("archivePanel"),
  archiveQuery: document.getElementById("archiveQuery"),
  archiveFrom: document.getElementById("archiveFrom"),
  archiveTo: document.getElementById("archiveTo"),
  archiveUrgency: document.getElementById("archiveUrgency"),
  btnArchiveSearch: document.getElementById("btnArchiveSearch"),
  archiveMsg: document.getElementById("archiveMsg"),
  archiveList: document.getElementById("archiveList"),
  aiInput: document.getElementById("aiInput"),
  btnAiGenerate: document.getElementById("btnAiGenerate"),
  btnAiClear: document.getElementById("btnAiClear"),
  aiMsg: document.getElementById("aiMsg"),
  aiDraftList: document.getElementById("aiDraftList"),
  aiSaveRow: document.getElementById("aiSaveRow"),
  btnAiSave: document.getElementById("btnAiSave"),
  aiSaveMsg: document.getElementById("aiSaveMsg"),
  recordActive: document.getElementById("recordActive"),
  recordList: document.getElementById("recordList"),
  recordQueryFilter: document.getElementById("recordQueryFilter"),
  recordSourceFilter: document.getElementById("recordSourceFilter"),
  recordStatusFilter: document.getElementById("recordStatusFilter"),
  recordTypeFilter: document.getElementById("recordTypeFilter"),
  recordTagFilter: document.getElementById("recordTagFilter"),
  recordLinkedFilter: document.getElementById("recordLinkedFilter"),
  recordSelectAll: document.getElementById("recordSelectAll"),
  btnRecordBulkDelete: document.getElementById("btnRecordBulkDelete"),
  recordBulkMsg: document.getElementById("recordBulkMsg"),
  btnDailyPlan: document.getElementById("btnDailyPlan"),
  dailyPlanMsg: document.getElementById("dailyPlanMsg"),
  dailyPlanResult: document.getElementById("dailyPlanResult"),
  todoList: document.getElementById("todoList"),
  todoTpl: document.getElementById("todoTpl"),
  subTpl: document.getElementById("subTpl"),
  btnEnableNotifications: document.getElementById("btnEnableNotifications"),
  notificationStatus: document.getElementById("notificationStatus"),
};

let currentTodos = [];
let todoStats = { active: 0, archived: 0, total: 0 };
let archivedTodos = [];
let aiDrafts = [];
let currentRecords = [];
let activeRecord = null;
const openTodoIds = new Set();
const selectedRecordIds = new Set();
const notifiedTodoIds = new Set();
let reminderTimer = null;
let calendarExpanded = false;
let resetCooldownTimer = null;

function setMsg(el, s, kind = "info") {
  el.textContent = s || "";
  el.style.color = kind === "error" ? "rgba(255,84,112,.95)" : "rgba(170,180,214,.95)";
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (ch) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "\"": "&quot;",
    "'": "&#39;",
  }[ch]));
}

const recordTypeLabels = {
  task: "任务",
  note: "笔记",
  idea: "灵感",
  reminder: "提醒",
  event: "事件",
  question: "问题",
  other: "其他",
};

const sentimentLabels = {
  positive: "积极",
  neutral: "中性",
  negative: "消极",
};

const recordSourceLabels = {
  web: "Web",
  feishu: "飞书",
};

const recordStatusLabels = {
  pending: "待整理",
  processing: "整理中",
  ready: "已整理",
  failed: "整理失败",
};

function recordStatusClass(status) {
  if (status === "failed") return "record-failed";
  if (status === "processing" || status === "pending") return "record-processing";
  return "";
}

function startResetCooldown(seconds = 60) {
  clearInterval(resetCooldownTimer);
  let remaining = Number(seconds) || 60;
  els.btnRequestReset.disabled = true;
  els.btnRequestReset.textContent = `${remaining}s 后重试`;
  resetCooldownTimer = setInterval(() => {
    remaining -= 1;
    if (remaining <= 0) {
      clearInterval(resetCooldownTimer);
      resetCooldownTimer = null;
      els.btnRequestReset.disabled = false;
      els.btnRequestReset.textContent = "发送验证码/链接";
      return;
    }
    els.btnRequestReset.textContent = `${remaining}s 后重试`;
  }, 1000);
}

function urgencyLabel(u) {
  if (u === 0) return "不急";
  if (u === 2) return "紧急";
  if (u === 3) return "非常紧急";
  return "普通";
}

function repeatLabel(rule) {
  if (rule === "daily") return "每天";
  if (rule === "weekly") return "每周";
  if (rule === "monthly") return "每月";
  return "";
}

function reminderLabel(minutes) {
  if (minutes === 0) return "到点提醒";
  if (minutes === 10) return "提前 10 分钟";
  if (minutes === 30) return "提前 30 分钟";
  if (minutes === 60) return "提前 1 小时";
  return "";
}

function fmtDue(dueAt) {
  if (!dueAt) return "";
  const d = new Date(dueAt);
  if (Number.isNaN(d.getTime())) return String(dueAt);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  const hh = String(d.getHours()).padStart(2, "0");
  const mm = String(d.getMinutes()).padStart(2, "0");
  return `${y}-${m}-${day} ${hh}:${mm}`;
}

function dateToInputValue(d) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function defaultDueLocal() {
  const d = new Date();
  d.setDate(d.getDate() + 1);
  d.setHours(18, 30, 0, 0);
  return d;
}

function applyDuePreset(offsetDays) {
  const d = new Date();
  d.setDate(d.getDate() + offsetDays);
  const parts = (els.newDueTime.value || "18:30").split(":");
  d.setHours(Number(parts[0]), Number(parts[1]), 0, 0);
  els.newDueDate.value = dateToInputValue(d);
  updateDueSummary();
}

function clearDue() {
  els.newDueDate.value = "";
  updateDueSummary();
}

function updateDueSummary() {
  if (!els.newDueDate.value) {
    els.dueSummary.textContent = "未设置完成时间";
    return;
  }
  els.dueSummary.textContent = `计划完成：${els.newDueDate.value} ${els.newDueTime.value}`;
}

function toUtcIsoFromInputs() {
  if (!els.newDueDate.value) return null;
  const value = `${els.newDueDate.value}T${els.newDueTime.value || "18:30"}`;
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return null;
  return d.toISOString().replace(".000Z", "+00:00");
}

function isoToDatetimeLocal(value) {
  if (!value) return "";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "";
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  const hh = String(d.getHours()).padStart(2, "0");
  const mm = String(d.getMinutes()).padStart(2, "0");
  return `${y}-${m}-${day}T${hh}:${mm}`;
}

function datetimeLocalToUtcIso(value) {
  if (!value) return null;
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return null;
  return d.toISOString().replace(".000Z", "+00:00");
}

function initDueDefaults() {
  const d = defaultDueLocal();
  els.newDueDate.value = dateToInputValue(d);
  els.newDueTime.value = "18:30";
  updateDueSummary();
}

async function loadVersionInfo() {
  try {
    const data = await API.version();
    const short = data.version && data.version.short ? data.version.short : "unknown";
    const source = data.version && data.version.source ? data.version.source : "unknown";
    els.versionInfo.textContent = `版本：${short}`;
    els.versionInfo.title = `后端版本来源：${source}`;
    const last = localStorage.getItem("todo_app_version");
    if (last && last !== short) {
      showVersionNotice("发现新版本", `当前浏览器记录的是 ${last}，服务器已是 ${short}。`);
    } else {
      hideVersionNotice();
    }
    localStorage.setItem("todo_app_version", short);
  } catch {
    els.versionInfo.textContent = "版本：未知";
    showVersionNotice("版本检测失败", "后端版本暂时不可确认，待办和收件箱仍可继续加载。", false);
  }
}

function showVersionNotice(title, text, canUpdate = true) {
  els.versionNoticeTitle.textContent = title;
  els.versionNoticeText.textContent = text;
  els.btnApplyUpdate.classList.toggle("hidden", !canUpdate);
  els.versionNotice.classList.remove("hidden");
}

function hideVersionNotice() {
  els.versionNotice.classList.add("hidden");
}

async function applyPageUpdate() {
  els.btnApplyUpdate.disabled = true;
  els.versionNoticeText.textContent = "正在清理旧缓存并刷新...";
  try {
    if ("caches" in window) {
      await caches.keys().then((keys) => Promise.all(keys.map((key) => caches.delete(key))));
    }
    if ("serviceWorker" in navigator) {
      const registrations = await navigator.serviceWorker.getRegistrations();
      await Promise.all(registrations.map((registration) => registration.update().catch(() => {})));
    }
  } finally {
    location.reload();
  }
}

function renderCalendar() {
  els.calendarGrid.innerHTML = "";
  const today = new Date();
  const start = new Date(today);
  start.setHours(0, 0, 0, 0);
  start.setDate(today.getDate() - today.getDay());
  const days = calendarExpanded ? 31 : 7;
  const end = new Date(start);
  end.setDate(start.getDate() + days - 1);
  els.calendarMonth.textContent = calendarExpanded
    ? `${start.getMonth() + 1}/${start.getDate()} - ${end.getMonth() + 1}/${end.getDate()}`
    : `本周 ${start.getMonth() + 1}/${start.getDate()} - ${end.getMonth() + 1}/${end.getDate()}`;
  els.btnToggleCalendar.textContent = calendarExpanded ? "收起" : "展开";
  const byDay = new Map();
  for (const todo of currentTodos) {
    if (!todo.dueAt || todo.done) continue;
    const d = new Date(todo.dueAt);
    d.setHours(0, 0, 0, 0);
    if (d < start || d > end) continue;
    const key = dateToInputValue(d);
    byDay.set(key, (byDay.get(key) || 0) + 1);
  }
  ["日", "一", "二", "三", "四", "五", "六"].forEach((label) => {
    const el = document.createElement("div");
    el.className = "calendar-week";
    el.textContent = label;
    els.calendarGrid.appendChild(el);
  });
  for (let i = 0; i < days; i += 1) {
    const d = new Date(start);
    d.setDate(start.getDate() + i);
    const key = dateToInputValue(d);
    const el = document.createElement("div");
    el.className = "calendar-day";
    if (key === dateToInputValue(today)) el.classList.add("today");
    const count = byDay.get(key) || 0;
    el.innerHTML = `<span>${d.getDate()}</span>${count ? `<strong>${count}</strong>` : ""}`;
    els.calendarGrid.appendChild(el);
  }
}

function editTodo(todo) {
  const title = prompt("修改主任务标题", todo.title);
  if (title === null) return;
  const nextTitle = title.trim();
  if (!nextTitle) {
    setMsg(els.appMsg, "标题不能为空", "error");
    return;
  }
  const note = prompt("修改备注", todo.note || "");
  if (note === null) return;
  API.patchTodo(todo.id, { title: nextTitle, note: note.trim() })
    .then(refresh)
    .catch((e) => setMsg(els.appMsg, e.message, "error"));
}

function editSubtask(todo, subtask) {
  const title = prompt("修改子任务标题", subtask.title);
  if (title === null) return;
  const nextTitle = title.trim();
  if (!nextTitle) {
    setMsg(els.appMsg, "子任务标题不能为空", "error");
    return;
  }
  API.patchSub(subtask.id, { title: nextTitle })
    .then(() => {
      subtask.title = nextTitle;
      openTodoIds.add(todo.id);
      renderTodos();
    })
    .catch((e) => setMsg(els.appMsg, e.message, "error"));
}

function updateNotificationStatus() {
  if (!("Notification" in window)) {
    els.notificationStatus.textContent = "当前浏览器不支持";
    return;
  }
  els.notificationStatus.textContent = Notification.permission === "granted" ? "已开启" : "未开启";
}

function reminderTime(todo) {
  if (!todo.dueAt || todo.reminderMinutes == null) return null;
  const due = new Date(todo.dueAt);
  if (Number.isNaN(due.getTime())) return null;
  return due.getTime() - Number(todo.reminderMinutes) * 60 * 1000;
}

function scheduleReminderCheck() {
  clearInterval(reminderTimer);
  reminderTimer = setInterval(() => {
    if (!("Notification" in window) || Notification.permission !== "granted") return;
    const now = Date.now();
    for (const todo of currentTodos) {
      if (todo.done || notifiedTodoIds.has(todo.id)) continue;
      const at = reminderTime(todo);
      if (at && now >= at && now - at < 60 * 1000) {
        notifiedTodoIds.add(todo.id);
        new Notification("随记代办提醒", {
          body: `${todo.title}${todo.dueAt ? `\n截止：${fmtDue(todo.dueAt)}` : ""}`,
          tag: `todo-${todo.id}`,
        });
      }
    }
  }, 15000);
}

function clearSecurityForms() {
  els.changeCurrentPassword.value = "";
  els.changeNewPassword.value = "";
  els.changeConfirmPassword.value = "";
  els.resetNewPassword.value = "";
  els.resetConfirmPassword.value = "";
}

function showSecurityPanel(kind) {
  const change = kind === "change";
  els.changePasswordPanel.classList.toggle("hidden", !change);
  els.resetPasswordPanel.classList.toggle("hidden", change);
  els.btnToggleChangePassword.classList.toggle("btn-secondary", change);
  els.btnToggleChangePassword.classList.toggle("btn-ghost", !change);
  els.btnToggleResetPassword.classList.toggle("btn-secondary", !change);
  els.btnToggleResetPassword.classList.toggle("btn-ghost", change);
  setMsg(els.securityMsg, "");
}

async function bootstrap() {
  initDueDefaults();
  updateNotificationStatus();
  await loadVersionInfo();
  const token = localStorage.getItem("todo_token");
  if (!token) {
    showAuth();
    return;
  }
  try {
    const me = await API.me();
    showApp(me.user);
    await refresh();
  } catch {
    localStorage.removeItem("todo_token");
    showAuth();
  }
}

function showAuth() {
  els.authCard.classList.remove("hidden");
  els.appCard.classList.add("hidden");
  els.btnLogout.classList.add("hidden");
  els.btnSecurity.classList.add("hidden");
  els.whoami.textContent = "账号：未登录";
  todoStats = { active: 0, archived: 0, total: 0 };
  updateTaskStats();
  setMsg(els.authMsg, "");
}

function showApp(user) {
  els.authCard.classList.add("hidden");
  els.appCard.classList.remove("hidden");
  els.btnLogout.classList.remove("hidden");
  els.btnSecurity.classList.remove("hidden");
  els.whoami.textContent = `账号：${user.email}`;
  setMsg(els.appMsg, "");
}

async function refresh() {
  setMsg(els.appMsg, "同步中...");
  const data = await API.listTodos();
  currentTodos = data.todos || [];
  todoStats = data.stats || { active: currentTodos.length, archived: 0, total: currentTodos.length };
  renderTodos();
  if (!els.archivePanel.classList.contains("hidden")) await refreshArchive();
  renderCalendar();
  await refreshRecords();
  scheduleReminderCheck();
  setMsg(els.appMsg, `已同步：${new Date().toLocaleTimeString()}`);
}

function updateTaskStats() {
  els.taskStats.textContent = `活跃 ${todoStats.active || 0} · 已完成 ${todoStats.archived || 0} · 总计 ${todoStats.total || 0}`;
}

function renderTodos() {
  els.todoList.innerHTML = "";
  updateTaskStats();

  if (!currentTodos.length) {
    const empty = document.createElement("div");
    empty.className = "msg empty-state";
    empty.textContent = "还没有代办，先添加一个。";
    els.todoList.appendChild(empty);
    return;
  }

  for (const t of currentTodos) {
    const node = els.todoTpl.content.firstElementChild.cloneNode(true);
    node.dataset.todoId = String(t.id);

    const doneBox = node.querySelector(".todo-done");
    const titleBtn = node.querySelector(".todo-title");
    const noteEl = node.querySelector(".todo-note");
    const metaEl = node.querySelector(".todo-meta");
    const urg = node.querySelector(".badge.urgency");
    const repeat = node.querySelector(".badge.repeat");
    const due = node.querySelector(".badge.due");
    const editBtn = node.querySelector(".todo-edit");
    const delBtn = node.querySelector(".todo-del");
    const subtasksWrap = node.querySelector(".subtasks");
    const subList = node.querySelector(".sub-list");
    const subNew = node.querySelector(".sub-new");
    const subAdd = node.querySelector(".sub-add");

    doneBox.checked = !!t.done;
    if (t.done) node.classList.add("done");

    titleBtn.textContent = t.title;
    noteEl.textContent = t.note || "";

    urg.textContent = urgencyLabel(t.urgency);
    urg.classList.add(`u${t.urgency}`);

    const repeatText = repeatLabel(t.repeatRule);
    if (repeatText) {
      repeat.textContent = repeatText;
      repeat.classList.remove("hidden");
    }

    if (t.dueAt) {
      due.textContent = `截止：${fmtDue(t.dueAt)}`;
      due.classList.remove("hidden");
    }

    const subs = Array.isArray(t.subtasks) ? t.subtasks : [];
    const openSubs = subs.filter((s) => !s.done).length;
    const reminderText = reminderLabel(t.reminderMinutes);
    const sourceText = t.sourceRecord
      ? ` · 来源：${t.sourceRecord.deleted ? "随记已删除" : (t.sourceRecord.summary || `#${t.sourceRecord.id}`)}`
      : "";
    metaEl.textContent = `${subs.length} 个子任务，未完成 ${openSubs} 个${reminderText ? ` · ${reminderText}` : ""}${sourceText}`;

    if (openTodoIds.has(t.id)) subtasksWrap.classList.remove("hidden");
    titleBtn.addEventListener("click", () => {
      if (openTodoIds.has(t.id)) openTodoIds.delete(t.id);
      else openTodoIds.add(t.id);
      subtasksWrap.classList.toggle("hidden");
    });

    doneBox.addEventListener("change", async () => {
      try {
        await API.patchTodo(t.id, { done: doneBox.checked });
        await refresh();
      } catch (e) {
        doneBox.checked = !doneBox.checked;
        setMsg(els.appMsg, e.message, "error");
      }
    });

    editBtn.addEventListener("click", () => editTodo(t));

    delBtn.addEventListener("click", async () => {
      if (!confirm("删除这个代办以及所有子任务？")) return;
      try {
        await API.delTodo(t.id);
        openTodoIds.delete(t.id);
        await refresh();
      } catch (e) {
        setMsg(els.appMsg, e.message, "error");
      }
    });

    subAdd.addEventListener("click", async () => {
      const title = (subNew.value || "").trim();
      if (!title) return;
      subNew.value = "";
      try {
        await API.addSub(t.id, title);
        openTodoIds.add(t.id);
        await refresh();
      } catch (e) {
        setMsg(els.appMsg, e.message, "error");
      }
    });
    subNew.addEventListener("keydown", (ev) => {
      if (ev.key === "Enter") subAdd.click();
    });

    subList.innerHTML = "";
    for (const s of subs) {
      const sn = els.subTpl.content.firstElementChild.cloneNode(true);
      if (s.done) sn.classList.add("done");
      const sDone = sn.querySelector(".sub-done");
      const sTitle = sn.querySelector(".sub-title");
      const sEdit = sn.querySelector(".sub-edit");
      const sDel = sn.querySelector(".sub-del");
      sDone.checked = !!s.done;
      sTitle.textContent = s.title;
      sDone.addEventListener("change", async () => {
        try {
          await API.patchSub(s.id, { done: sDone.checked });
          s.done = sDone.checked;
          openTodoIds.add(t.id);
          renderTodos();
        } catch (e) {
          sDone.checked = !sDone.checked;
          setMsg(els.appMsg, e.message, "error");
        }
      });
      sEdit.addEventListener("click", () => editSubtask(t, s));
      sDel.addEventListener("click", async () => {
        if (!confirm("删除这个子任务？")) return;
        try {
          await API.delSub(s.id);
          t.subtasks = subs.filter((x) => x.id !== s.id);
          openTodoIds.add(t.id);
          renderTodos();
        } catch (e) {
          setMsg(els.appMsg, e.message, "error");
        }
      });
      subList.appendChild(sn);
    }

    els.todoList.appendChild(node);
  }
}

function archiveFilters() {
  return {
    q: (els.archiveQuery.value || "").trim(),
    from: els.archiveFrom.value || "",
    to: els.archiveTo.value || "",
    urgency: els.archiveUrgency.value,
  };
}

async function refreshArchive() {
  setMsg(els.archiveMsg, "加载归档...");
  const data = await API.listArchive(archiveFilters());
  archivedTodos = data.todos || [];
  todoStats = data.stats || todoStats;
  updateTaskStats();
  renderArchive();
  setMsg(els.archiveMsg, archivedTodos.length ? `已加载 ${archivedTodos.length} 条归档` : "暂无匹配归档");
}

function renderArchive() {
  els.archiveList.innerHTML = "";
  if (!archivedTodos.length) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.textContent = "暂无归档任务";
    els.archiveList.appendChild(empty);
    return;
  }
  for (const todo of archivedTodos) {
    const subtasks = todo.subtaskSummary || {};
    const source = todo.sourceRecord ? (todo.sourceRecord.deleted ? "随记已删除" : (todo.sourceRecord.summary || `#${todo.sourceRecord.id}`)) : "无来源";
    const card = document.createElement("article");
    card.className = "archive-item";
    card.innerHTML = `
      <div>
        <strong>${escapeHtml(todo.title)}</strong>
        <p>${escapeHtml(todo.note || "无备注")}</p>
        <span>${urgencyLabel(todo.urgency)} · 完成 ${fmtDue(todo.doneAt || todo.archivedAt)} · 子任务 ${subtasks.done || 0}/${subtasks.total || 0} · 来源：${escapeHtml(source)}</span>
      </div>
      <button class="btn btn-secondary btn-mini archive-restore" type="button">恢复</button>
    `;
    card.querySelector(".archive-restore").addEventListener("click", async () => {
      try {
        await API.restoreTodo(todo.id);
        setMsg(els.archiveMsg, "已恢复到活跃待办");
        await refresh();
      } catch (e) {
        setMsg(els.archiveMsg, e.message, "error");
      }
    });
    els.archiveList.appendChild(card);
  }
}

function renderAiDrafts() {
  els.aiDraftList.innerHTML = "";
  els.aiSaveRow.classList.toggle("hidden", aiDrafts.length === 0);
  if (!aiDrafts.length) return;
  aiDrafts.forEach((draft, index) => {
    const card = document.createElement("article");
    card.className = "ai-draft";
    card.innerHTML = `
      <label class="ai-draft-check">
        <input type="checkbox" class="ai-draft-selected" ${draft.selected ? "checked" : ""} />
        <span>保存</span>
      </label>
      <label class="field">
        <span>任务</span>
        <input class="ai-draft-title" type="text" value="" />
      </label>
      <label class="field">
        <span>备注</span>
        <textarea class="ai-draft-note" rows="2"></textarea>
      </label>
      <div class="grid2">
        <label class="field">
          <span>优先级</span>
          <select class="ai-draft-urgency">
            <option value="0">不急</option>
            <option value="1">普通</option>
            <option value="2">紧急</option>
            <option value="3">非常紧急</option>
          </select>
        </label>
        <label class="field">
          <span>完成时间</span>
          <input class="ai-draft-due" type="datetime-local" />
        </label>
      </div>
      <label class="field">
        <span>子任务（一行一个）</span>
        <textarea class="ai-draft-subtasks" rows="3"></textarea>
      </label>
    `;
    const selected = card.querySelector(".ai-draft-selected");
    const title = card.querySelector(".ai-draft-title");
    const note = card.querySelector(".ai-draft-note");
    const urgency = card.querySelector(".ai-draft-urgency");
    const due = card.querySelector(".ai-draft-due");
    const subtasks = card.querySelector(".ai-draft-subtasks");
    title.value = draft.title || "";
    note.value = draft.note || "";
    urgency.value = String(draft.urgency ?? 1);
    due.value = isoToDatetimeLocal(draft.dueAt);
    subtasks.value = (draft.subtasks || []).join("\n");
    selected.addEventListener("change", () => {
      aiDrafts[index].selected = selected.checked;
    });
    title.addEventListener("input", () => {
      aiDrafts[index].title = title.value;
    });
    note.addEventListener("input", () => {
      aiDrafts[index].note = note.value;
    });
    urgency.addEventListener("change", () => {
      aiDrafts[index].urgency = Number(urgency.value || "1");
    });
    due.addEventListener("change", () => {
      aiDrafts[index].dueAt = datetimeLocalToUtcIso(due.value);
    });
    subtasks.addEventListener("input", () => {
      aiDrafts[index].subtasks = subtasks.value.split("\n").map((x) => x.trim()).filter(Boolean);
    });
    els.aiDraftList.appendChild(card);
  });
}

function renderActiveRecord() {
  if (!activeRecord) {
    els.recordActive.classList.add("hidden");
    els.recordActive.innerHTML = "";
    return;
  }
  els.recordActive.classList.remove("hidden");
  const tags = (activeRecord.tags || []).map((x) => `<span class="badge">${escapeHtml(x)}</span>`).join("");
  const dates = (activeRecord.dates || []).map((x) => `<span class="badge due">${fmtDue(x)}</span>`).join("");
  const linked = activeRecord.linkedTodos || [];
  const sourceLabel = recordSourceLabels[activeRecord.source] || activeRecord.source || "Web";
  const statusLabel = recordStatusLabels[activeRecord.aiStatus] || activeRecord.aiStatus || "待整理";
  els.recordActive.innerHTML = `
    <div class="record-head">
      <strong>${escapeHtml(activeRecord.summary || "未整理摘要")}</strong>
      <span class="badge">${recordTypeLabels[activeRecord.type] || "其他"}</span>
      <span class="badge">${sentimentLabels[activeRecord.sentiment] || "中性"}</span>
      <span class="badge">${escapeHtml(sourceLabel)}</span>
      <span class="badge ${recordStatusClass(activeRecord.aiStatus)}">${escapeHtml(statusLabel)}</span>
    </div>
    <div class="record-raw">${escapeHtml(activeRecord.originalInput || "")}</div>
    <div class="record-tags">${tags || '<span class="hint">无标签</span>'}${dates}</div>
    ${activeRecord.aiError ? `<div class="msg record-error">${escapeHtml(activeRecord.aiError)}</div>` : ""}
    <div class="record-links">${linked.length ? `关联任务：${linked.map((x) => escapeHtml(x.title)).join("、")}` : "暂无关联任务"}</div>
    <div class="row">
      <button class="btn btn-ghost btn-mini record-edit" type="button">编辑</button>
      <button class="btn btn-ghost btn-mini record-retry" type="button">重试整理</button>
      <button class="btn btn-ghost btn-mini record-sync" type="button">同步日期到任务</button>
      <button class="btn btn-ghost btn-mini record-delete" type="button">删除记录</button>
    </div>
  `;
  els.recordActive.querySelector(".record-edit").addEventListener("click", () => editActiveRecord());
  els.recordActive.querySelector(".record-retry").addEventListener("click", () => retryActiveRecord());
  els.recordActive.querySelector(".record-sync").addEventListener("click", () => syncActiveRecordDates());
  els.recordActive.querySelector(".record-delete").addEventListener("click", () => deleteActiveRecord());
}

function renderRecords() {
  els.recordList.innerHTML = "";
  els.recordSelectAll.checked = currentRecords.length > 0 && currentRecords.every((record) => selectedRecordIds.has(record.id));
  if (!currentRecords.length) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.textContent = "暂无随记";
    els.recordList.appendChild(empty);
    return;
  }
  for (const record of currentRecords) {
    const card = document.createElement("article");
    card.className = "record-item";
    const sourceLabel = recordSourceLabels[record.source] || record.source || "Web";
    const statusLabel = recordStatusLabels[record.aiStatus] || record.aiStatus || "待整理";
    card.innerHTML = `
      <label class="record-select">
        <input type="checkbox" ${selectedRecordIds.has(record.id) ? "checked" : ""} />
      </label>
      <button class="record-open" type="button">
        <strong>${escapeHtml(record.summary || record.originalInput || "未命名随记")}</strong>
        <span>${escapeHtml(sourceLabel)} · ${escapeHtml(statusLabel)} · ${recordTypeLabels[record.type] || "其他"} · ${sentimentLabels[record.sentiment] || "中性"} · ${(record.tags || []).join(" / ") || "无标签"}</span>
      </button>
    `;
    card.querySelector(".record-select input").addEventListener("change", (ev) => {
      if (ev.target.checked) selectedRecordIds.add(record.id);
      else selectedRecordIds.delete(record.id);
      els.recordSelectAll.checked = currentRecords.length > 0 && currentRecords.every((item) => selectedRecordIds.has(item.id));
    });
    card.querySelector(".record-open").addEventListener("click", () => {
      activeRecord = record;
      aiDrafts = normalizeDrafts(record.aiItems || []);
      renderAiDrafts();
      renderActiveRecord();
    });
    els.recordList.appendChild(card);
  }
}

async function refreshRecords() {
  if (!els.recordList) return;
  const data = await API.listRecords({
    q: (els.recordQueryFilter.value || "").trim(),
    source: els.recordSourceFilter.value,
    status: els.recordStatusFilter.value,
    type: els.recordTypeFilter.value,
    tag: (els.recordTagFilter.value || "").trim(),
    linked: els.recordLinkedFilter.value,
  });
  currentRecords = data.records || [];
  for (const id of Array.from(selectedRecordIds)) {
    if (!currentRecords.some((record) => record.id === id)) selectedRecordIds.delete(id);
  }
  if (activeRecord) {
    activeRecord = currentRecords.find((x) => x.id === activeRecord.id) || activeRecord;
  }
  renderRecords();
  renderActiveRecord();
}

async function bulkDeleteRecords() {
  const ids = Array.from(selectedRecordIds);
  if (!ids.length) {
    setMsg(els.recordBulkMsg, "先选择要清理的随记", "error");
    return;
  }
  if (!confirm(`清理选中的 ${ids.length} 条随记？关联任务会保留。`)) return;
  try {
    const data = await API.bulkRecords("delete", ids);
    selectedRecordIds.clear();
    activeRecord = null;
    aiDrafts = [];
    renderAiDrafts();
    await refreshRecords();
    const result = data.result || {};
    setMsg(els.recordBulkMsg, `成功 ${result.succeeded || 0}，跳过 ${result.skipped || 0}，失败 ${result.failed || 0}`);
  } catch (e) {
    setMsg(els.recordBulkMsg, e.message, "error");
  }
}

function editActiveRecord() {
  if (!activeRecord) return;
  const summary = prompt("摘要", activeRecord.summary || "");
  if (summary === null) return;
  const tags = prompt("标签，用逗号分隔", (activeRecord.tags || []).join(","));
  if (tags === null) return;
  API.patchRecord(activeRecord.id, {
    summary,
    tags: tags.split(",").map((x) => x.trim()).filter(Boolean),
    type: activeRecord.type,
    dates: activeRecord.dates || [],
    sentiment: activeRecord.sentiment,
  }).then((data) => {
    activeRecord = data.record;
    return refreshRecords();
  }).catch((e) => setMsg(els.aiMsg, e.message, "error"));
}

async function retryActiveRecord() {
  if (!activeRecord) return;
  setMsg(els.aiMsg, "AI 正在重新整理...");
  try {
    const data = await API.retryRecord(activeRecord.id);
    activeRecord = data.record;
    aiDrafts = normalizeDrafts(data.items || []);
    renderAiDrafts();
    await refreshRecords();
    setMsg(els.aiMsg, activeRecord.aiStatus === "failed" ? "整理失败，已保留原文" : "已重新整理");
  } catch (e) {
    setMsg(els.aiMsg, e.message, "error");
  }
}

async function syncActiveRecordDates() {
  if (!activeRecord) return;
  try {
    const data = await API.syncRecordDates(activeRecord.id);
    const created = Number(data.created || 0);
    const updated = Number(data.updated || 0);
    setMsg(els.aiMsg, created ? `已创建 ${created} 个任务，同步 ${updated} 个截止时间` : `已同步 ${updated} 个任务`);
    await refresh();
    await refreshRecords();
  } catch (e) {
    setMsg(els.aiMsg, e.message, "error");
  }
}

async function deleteActiveRecord() {
  if (!activeRecord || !confirm("删除这条随记？关联任务会保留。")) return;
  try {
    await API.delRecord(activeRecord.id);
    activeRecord = null;
    await refreshRecords();
    await refresh();
  } catch (e) {
    setMsg(els.aiMsg, e.message, "error");
  }
}

function normalizeDrafts(items) {
  return (items || []).map((item) => ({
    selected: true,
    title: item.title || "",
    note: item.note || "",
    urgency: Number(item.urgency ?? 1),
    dueAt: item.dueAt || null,
    subtasks: Array.isArray(item.subtasks) ? item.subtasks : [],
  })).filter((item) => item.title.trim());
}

async function generateAiDrafts() {
  const text = (els.aiInput.value || "").trim();
  setMsg(els.aiMsg, "");
  setMsg(els.aiSaveMsg, "");
  if (!text) {
    setMsg(els.aiMsg, "请先粘贴要整理的内容", "error");
    return;
  }
  els.btnAiGenerate.disabled = true;
  setMsg(els.aiMsg, "正在保存并整理...");
  try {
    const data = await API.organizeRecord(text);
    activeRecord = data.record || null;
    aiDrafts = normalizeDrafts(data.items || []);
    renderAiDrafts();
    renderActiveRecord();
    await refreshRecords();
    setMsg(els.aiMsg, aiDrafts.length ? `已保存随记，并生成 ${aiDrafts.length} 个草稿` : "已保存随记，暂无明确代办草稿");
  } catch (e) {
    setMsg(els.aiMsg, e.message, "error");
  } finally {
    els.btnAiGenerate.disabled = false;
  }
}

async function saveAiDrafts() {
  const selected = aiDrafts.filter((draft) => draft.selected && draft.title.trim());
  if (!selected.length) {
    setMsg(els.aiSaveMsg, "没有选中的草稿", "error");
    return;
  }
  els.btnAiSave.disabled = true;
  setMsg(els.aiSaveMsg, "保存中...");
  try {
    if (activeRecord) {
      await API.saveRecordTodos(activeRecord.id, selected);
    } else {
      for (const draft of selected) {
        const todo = await API.addTodo({
          title: draft.title.trim(),
          note: (draft.note || "").trim(),
          urgency: Number(draft.urgency || 1),
          repeatRule: "none",
          reminderMinutes: null,
          dueAt: draft.dueAt || null,
        });
        for (const subtask of draft.subtasks || []) {
          const title = String(subtask || "").trim();
          if (title) await API.addSub(todo.id, title);
        }
      }
    }
    aiDrafts = [];
    renderAiDrafts();
    els.aiInput.value = "";
    setMsg(els.aiMsg, "");
    setMsg(els.aiSaveMsg, `已保存 ${selected.length} 个代办`);
    await refresh();
  } catch (e) {
    setMsg(els.aiSaveMsg, e.message, "error");
  } finally {
    els.btnAiSave.disabled = false;
  }
}

function renderDailyPlan(plan, todoCount) {
  const items = Array.isArray(plan.items) ? plan.items : [];
  els.dailyPlanResult.classList.remove("hidden");
  els.dailyPlanResult.innerHTML = "";
  const head = document.createElement("div");
  head.className = "daily-plan-head";
  head.innerHTML = `<strong>${plan.date || "今日计划"}</strong><span>${todoCount || 0} 个未完成任务参与整理</span>`;
  els.dailyPlanResult.appendChild(head);
  if (plan.summary) {
    const summary = document.createElement("div");
    summary.className = "daily-plan-summary";
    summary.textContent = plan.summary;
    els.dailyPlanResult.appendChild(summary);
  }
  if (!items.length) {
    const empty = document.createElement("div");
    empty.className = "msg empty-state";
    empty.textContent = "AI 暂时没有生成明确建议。";
    els.dailyPlanResult.appendChild(empty);
    return;
  }
  const list = document.createElement("div");
  list.className = "daily-plan-list";
  items.forEach((item) => {
    const row = document.createElement("div");
    row.className = "daily-plan-item";
    const time = item.time ? `<span class="badge due">${item.time}</span>` : "";
    const ids = Array.isArray(item.todoIds) && item.todoIds.length ? `<small>关联任务：${item.todoIds.join(", ")}</small>` : "";
    row.innerHTML = `${time}<div>${item.text || ""}</div>${ids}`;
    list.appendChild(row);
  });
  els.dailyPlanResult.appendChild(list);
}

async function generateDailyPlan() {
  els.btnDailyPlan.disabled = true;
  setMsg(els.dailyPlanMsg, "AI 正在整理今日计划...");
  try {
    const data = await API.dailyPlan();
    renderDailyPlan(data.plan || {}, data.todoCount || 0);
    setMsg(els.dailyPlanMsg, "已生成");
  } catch (e) {
    setMsg(els.dailyPlanMsg, e.message, "error");
  } finally {
    els.btnDailyPlan.disabled = false;
  }
}

els.btnLogin.addEventListener("click", async () => {
  setMsg(els.authMsg, "");
  const email = (els.authEmail.value || "").trim();
  const password = (els.authPassword.value || "").trim();
  try {
    const data = await API.login(email, password);
    localStorage.setItem("todo_token", data.token);
    showApp(data.user);
    await refresh();
  } catch (e) {
    setMsg(els.authMsg, e.message, "error");
  }
});

els.btnRegister.addEventListener("click", async () => {
  setMsg(els.authMsg, "");
  const email = (els.authEmail.value || "").trim();
  const password = (els.authPassword.value || "").trim();
  try {
    const data = await API.register(email, password);
    localStorage.setItem("todo_token", data.token);
    showApp(data.user);
    await refresh();
  } catch (e) {
    setMsg(els.authMsg, e.message, "error");
  }
});

els.btnForgotPasswordOpen.addEventListener("click", () => {
  els.forgotEmail.value = els.authEmail.value || "";
  setMsg(els.forgotMsg, "");
  els.forgotDialog.showModal();
});
els.btnCloseForgot.addEventListener("click", () => els.forgotDialog.close());
els.btnRequestReset.addEventListener("click", async () => {
  const email = (els.forgotEmail.value || "").trim();
  if (!email) {
    setMsg(els.forgotMsg, "请先输入邮箱。", "error");
    return;
  }
  els.btnRequestReset.disabled = true;
  els.btnRequestReset.textContent = "发送中...";
  try {
    const data = await API.requestPasswordReset(email);
    startResetCooldown(60);
    setMsg(els.forgotMsg, data.message || "如果邮箱存在，重置邮件会在几分钟内发送。");
  } catch (e) {
    const seconds = Number(String(e.message || "").match(/(\d+)s/)?.[1] || 60);
    startResetCooldown(seconds);
    setMsg(els.forgotMsg, e.message, "error");
  }
});
els.btnConfirmForgotReset.addEventListener("click", async () => {
  const email = (els.forgotEmail.value || "").trim();
  const token = (els.forgotToken.value || "").trim();
  const code = (els.forgotCode.value || "").trim();
  const newPassword = els.forgotNewPassword.value.trim();
  const confirmPassword = els.forgotConfirmPassword.value.trim();
  if (!email || (!token && !code) || !newPassword) {
    setMsg(els.forgotMsg, "邮箱、验证码/Token、新密码都需要填写。", "error");
    return;
  }
  if (newPassword !== confirmPassword) {
    setMsg(els.forgotMsg, "两次输入的新密码不一致。", "error");
    return;
  }
  try {
    await API.confirmPasswordReset(email, token, code, newPassword);
    setMsg(els.forgotMsg, "密码已重置，现在可以登录。");
  } catch (e) {
    setMsg(els.forgotMsg, e.message, "error");
  }
});

els.btnLogout.addEventListener("click", () => {
  localStorage.removeItem("todo_token");
  clearSecurityForms();
  currentTodos = [];
  openTodoIds.clear();
  showAuth();
});

els.btnRefresh.addEventListener("click", () => refresh().catch((e) => setMsg(els.appMsg, e.message, "error")));
els.btnSecurity.addEventListener("click", () => {
  showSecurityPanel("change");
  els.securityDialog.showModal();
});
els.btnCloseSecurity.addEventListener("click", () => els.securityDialog.close());
els.btnToggleChangePassword.addEventListener("click", () => showSecurityPanel("change"));
els.btnToggleResetPassword.addEventListener("click", () => showSecurityPanel("reset"));

els.btnChangePassword.addEventListener("click", async () => {
  const currentPassword = els.changeCurrentPassword.value.trim();
  const newPassword = els.changeNewPassword.value.trim();
  const confirmPassword = els.changeConfirmPassword.value.trim();
  if (!currentPassword || !newPassword) {
    setMsg(els.securityMsg, "请先填写完整密码信息。", "error");
    return;
  }
  if (newPassword !== confirmPassword) {
    setMsg(els.securityMsg, "两次输入的新密码不一致。", "error");
    return;
  }
  try {
    await API.changePassword(currentPassword, newPassword);
    clearSecurityForms();
    setMsg(els.securityMsg, "密码已更新。");
  } catch (e) {
    setMsg(els.securityMsg, e.message, "error");
  }
});

els.btnResetPassword.addEventListener("click", async () => {
  const newPassword = els.resetNewPassword.value.trim();
  const confirmPassword = els.resetConfirmPassword.value.trim();
  if (!newPassword) {
    setMsg(els.securityMsg, "请先输入新密码。", "error");
    return;
  }
  if (newPassword !== confirmPassword) {
    setMsg(els.securityMsg, "两次输入的新密码不一致。", "error");
    return;
  }
  try {
    await API.resetPassword(newPassword);
    clearSecurityForms();
    setMsg(els.securityMsg, "密码已重置。");
  } catch (e) {
    setMsg(els.securityMsg, e.message, "error");
  }
});

els.newDueDate.addEventListener("change", updateDueSummary);
els.newDueTime.addEventListener("change", updateDueSummary);
document.querySelectorAll(".due-preset").forEach((button) => {
  button.addEventListener("click", () => applyDuePreset(Number(button.dataset.offset || "1")));
});
document.querySelector(".due-clear").addEventListener("click", clearDue);
els.btnApplyUpdate.addEventListener("click", () => applyPageUpdate());
els.btnToggleArchive.addEventListener("click", async () => {
  els.archivePanel.classList.toggle("hidden");
  if (!els.archivePanel.classList.contains("hidden")) {
    await refreshArchive().catch((e) => setMsg(els.archiveMsg, e.message, "error"));
  }
});
els.btnCloseArchive.addEventListener("click", () => els.archivePanel.classList.add("hidden"));
els.btnArchiveSearch.addEventListener("click", () => refreshArchive().catch((e) => setMsg(els.archiveMsg, e.message, "error")));
els.archiveQuery.addEventListener("keydown", (ev) => {
  if (ev.key !== "Enter" || ev.isComposing) return;
  ev.preventDefault();
  els.btnArchiveSearch.click();
});
els.btnToggleCalendar.addEventListener("click", () => {
  calendarExpanded = !calendarExpanded;
  renderCalendar();
});
els.btnAiGenerate.addEventListener("click", () => generateAiDrafts());
els.btnAiClear.addEventListener("click", () => {
  els.aiInput.value = "";
  aiDrafts = [];
  activeRecord = null;
  renderAiDrafts();
  renderActiveRecord();
  setMsg(els.aiMsg, "");
  setMsg(els.aiSaveMsg, "");
});
els.btnAiSave.addEventListener("click", () => saveAiDrafts());
els.recordQueryFilter.addEventListener("keydown", (ev) => {
  if (ev.key !== "Enter" || ev.isComposing) return;
  ev.preventDefault();
  refreshRecords().catch((e) => setMsg(els.aiMsg, e.message, "error"));
});
els.recordQueryFilter.addEventListener("change", () => refreshRecords().catch((e) => setMsg(els.aiMsg, e.message, "error")));
els.recordSourceFilter.addEventListener("change", () => refreshRecords().catch((e) => setMsg(els.aiMsg, e.message, "error")));
els.recordStatusFilter.addEventListener("change", () => refreshRecords().catch((e) => setMsg(els.aiMsg, e.message, "error")));
els.recordTypeFilter.addEventListener("change", () => refreshRecords().catch((e) => setMsg(els.aiMsg, e.message, "error")));
els.recordLinkedFilter.addEventListener("change", () => refreshRecords().catch((e) => setMsg(els.aiMsg, e.message, "error")));
els.recordTagFilter.addEventListener("change", () => refreshRecords().catch((e) => setMsg(els.aiMsg, e.message, "error")));
els.recordSelectAll.addEventListener("change", () => {
  if (els.recordSelectAll.checked) currentRecords.forEach((record) => selectedRecordIds.add(record.id));
  else currentRecords.forEach((record) => selectedRecordIds.delete(record.id));
  renderRecords();
});
els.btnRecordBulkDelete.addEventListener("click", () => bulkDeleteRecords());
els.btnDailyPlan.addEventListener("click", () => generateDailyPlan());

els.btnAddTodo.addEventListener("click", async () => {
  setMsg(els.appMsg, "");
  const title = (els.newTitle.value || "").trim();
  const note = (els.newNote.value || "").trim();
  const urgency = Number(els.newUrgency.value || "1");
  const repeatRule = els.newRepeatRule.value || "none";
  const reminderMinutes = els.newReminder.value === "none" ? null : (els.newReminder.value === "at_due" ? 0 : Number(els.newReminder.value));
  const dueAt = toUtcIsoFromInputs();
  if (!title) {
    setMsg(els.appMsg, "标题不能为空", "error");
    return;
  }
  try {
    await API.addTodo({ title, note, urgency, repeatRule, reminderMinutes, dueAt });
    els.newTitle.value = "";
    els.newNote.value = "";
    els.newUrgency.value = "1";
    els.newRepeatRule.value = "none";
    els.newReminder.value = "none";
    initDueDefaults();
    await refresh();
  } catch (e) {
    setMsg(els.appMsg, e.message, "error");
  }
});
els.newTitle.addEventListener("keydown", (ev) => {
  if (ev.key !== "Enter" || ev.isComposing) return;
  ev.preventDefault();
  els.btnAddTodo.click();
});

els.btnEnableNotifications.addEventListener("click", async () => {
  if (!("Notification" in window)) {
    updateNotificationStatus();
    return;
  }
  await Notification.requestPermission();
  updateNotificationStatus();
});

const resetParams = new URLSearchParams(location.search);
if (resetParams.has("resetToken")) {
  els.forgotEmail.value = resetParams.get("email") || "";
  els.forgotToken.value = resetParams.get("resetToken") || "";
  els.forgotDialog.showModal();
  history.replaceState({}, "", location.pathname);
}

bootstrap();

if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("/sw.js").then((registration) => {
    registration.update().catch(() => {});
    registration.addEventListener("updatefound", () => {
      const worker = registration.installing;
      if (!worker) return;
      worker.addEventListener("statechange", () => {
        if (worker.state === "installed" && navigator.serviceWorker.controller) {
          showVersionNotice("页面资源已更新", "刷新后使用最新界面。");
        }
      });
    });
  }).catch(() => {});
}
