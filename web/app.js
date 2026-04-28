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
  listTodos() {
    return this.request("/api/todos", { method: "GET" });
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
  authMsg: document.getElementById("authMsg"),
  btnLogout: document.getElementById("btnLogout"),
  btnRefresh: document.getElementById("btnRefresh"),
  btnSecurity: document.getElementById("btnSecurity"),
  whoami: document.getElementById("whoami"),
  taskStats: document.getElementById("taskStats"),
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
  newTitle: document.getElementById("newTitle"),
  newNote: document.getElementById("newNote"),
  newUrgency: document.getElementById("newUrgency"),
  newRepeatRule: document.getElementById("newRepeatRule"),
  newDueDate: document.getElementById("newDueDate"),
  newDueTime: document.getElementById("newDueTime"),
  dueSummary: document.getElementById("dueSummary"),
  btnAddTodo: document.getElementById("btnAddTodo"),
  appMsg: document.getElementById("appMsg"),
  todoList: document.getElementById("todoList"),
  todoTpl: document.getElementById("todoTpl"),
  subTpl: document.getElementById("subTpl"),
  pomodoroMode: document.getElementById("pomodoroMode"),
  pomodoroTime: document.getElementById("pomodoroTime"),
  btnPomodoroStart: document.getElementById("btnPomodoroStart"),
  btnPomodoroPause: document.getElementById("btnPomodoroPause"),
  btnPomodoroReset: document.getElementById("btnPomodoroReset"),
  focusMinutes: document.getElementById("focusMinutes"),
  breakMinutes: document.getElementById("breakMinutes"),
};

let currentTodos = [];
const openTodoIds = new Set();

const pomodoro = {
  mode: "focus",
  running: false,
  remaining: 25 * 60,
  timer: null,
};

function setMsg(el, s, kind = "info") {
  el.textContent = s || "";
  el.style.color = kind === "error" ? "rgba(255,84,112,.95)" : "rgba(170,180,214,.95)";
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

function initDueDefaults() {
  const d = defaultDueLocal();
  els.newDueDate.value = dateToInputValue(d);
  els.newDueTime.value = "18:30";
  updateDueSummary();
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
  updatePomodoroDisplay();
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
  setMsg(els.authMsg, "");
}

function showApp(user) {
  els.authCard.classList.add("hidden");
  els.appCard.classList.remove("hidden");
  els.btnLogout.classList.remove("hidden");
  els.btnSecurity.classList.remove("hidden");
  els.whoami.textContent = `已登录：${user.email}`;
  setMsg(els.appMsg, "");
}

async function refresh() {
  setMsg(els.appMsg, "同步中...");
  const data = await API.listTodos();
  currentTodos = data.todos || [];
  renderTodos();
  setMsg(els.appMsg, `已同步：${new Date().toLocaleTimeString()}`);
}

function renderTodos() {
  els.todoList.innerHTML = "";
  const total = currentTodos.length;
  const doneCount = currentTodos.filter((t) => t.done).length;
  els.taskStats.textContent = `${doneCount} / ${total}`;

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
    metaEl.textContent = `${subs.length} 个子任务，未完成 ${openSubs} 个`;

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

function setPomodoroMode(mode) {
  pomodoro.mode = mode;
  pomodoro.running = false;
  clearInterval(pomodoro.timer);
  pomodoro.timer = null;
  const minutes = mode === "focus" ? Number(els.focusMinutes.value) : Number(els.breakMinutes.value);
  pomodoro.remaining = minutes * 60;
  updatePomodoroDisplay();
}

function updatePomodoroDisplay() {
  const minutes = Math.floor(pomodoro.remaining / 60);
  const seconds = pomodoro.remaining % 60;
  els.pomodoroTime.textContent = `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
  els.pomodoroMode.textContent = pomodoro.mode === "focus" ? "专注" : "休息";
}

function startPomodoro() {
  if (pomodoro.running) return;
  pomodoro.running = true;
  pomodoro.timer = setInterval(() => {
    pomodoro.remaining -= 1;
    if (pomodoro.remaining <= 0) {
      setPomodoroMode(pomodoro.mode === "focus" ? "break" : "focus");
      return;
    }
    updatePomodoroDisplay();
  }, 1000);
}

function pausePomodoro() {
  pomodoro.running = false;
  clearInterval(pomodoro.timer);
  pomodoro.timer = null;
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

els.btnAddTodo.addEventListener("click", async () => {
  setMsg(els.appMsg, "");
  const title = (els.newTitle.value || "").trim();
  const note = (els.newNote.value || "").trim();
  const urgency = Number(els.newUrgency.value || "1");
  const repeatRule = els.newRepeatRule.value || "none";
  const dueAt = toUtcIsoFromInputs();
  if (!title) {
    setMsg(els.appMsg, "标题不能为空", "error");
    return;
  }
  try {
    await API.addTodo({ title, note, urgency, repeatRule, dueAt });
    els.newTitle.value = "";
    els.newNote.value = "";
    els.newUrgency.value = "1";
    els.newRepeatRule.value = "none";
    initDueDefaults();
    await refresh();
  } catch (e) {
    setMsg(els.appMsg, e.message, "error");
  }
});

els.btnPomodoroStart.addEventListener("click", startPomodoro);
els.btnPomodoroPause.addEventListener("click", pausePomodoro);
els.btnPomodoroReset.addEventListener("click", () => setPomodoroMode(pomodoro.mode));
els.focusMinutes.addEventListener("change", () => {
  if (pomodoro.mode === "focus") setPomodoroMode("focus");
});
els.breakMinutes.addEventListener("change", () => {
  if (pomodoro.mode === "break") setPomodoroMode("break");
});

bootstrap();

if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("/sw.js").catch(() => {});
}
