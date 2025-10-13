const versionEl = document.getElementById("app-version");
const migrationEl = document.getElementById("migration-result");
const deckCountEl = document.getElementById("deck-count");
const seasonCountEl = document.getElementById("season-count");
const matchCountEl = document.getElementById("match-count");
const uiModeEl = document.getElementById("ui-mode");
const matchesTableBody = document.querySelector("#matches-table tbody");
const refreshButton = document.getElementById("refresh-button");
const toastEl = document.getElementById("toast");
const deckTableBody = document.querySelector("#deck-table tbody");
const opponentTableBody = document.querySelector("#opponent-deck-table tbody");
const matchStartSelect = document.getElementById("match-start-deck");
const matchOpponentSelect = document.getElementById("match-opponent");
const deckForm = document.getElementById("deck-form");
const opponentDeckForm = document.getElementById("opponent-deck-form");
const matchStartForm = document.getElementById("match-start-form");
const matchEntryForm = document.getElementById("match-entry-form");
const matchEntryDeckNameEl = document.getElementById("match-entry-deck-name");
const matchEntryNumberEl = document.getElementById("match-entry-number");
const matchEntryClockEl = document.getElementById("match-entry-clock");
const settingsUiModeEl = document.getElementById("settings-ui-mode");
const settingsMigrationEl = document.getElementById("settings-migration");

const viewElements = new Map();
let currentView = "dashboard";

for (const view of document.querySelectorAll(".view")) {
  const id = view.dataset.view;
  if (!id) {
    continue;
  }
  viewElements.set(id, view);
  if (view.classList.contains("view--active")) {
    currentView = id;
  } else {
    view.setAttribute("hidden", "");
  }
}

const viewStack = [];
let toastTimer = null;
let latestSnapshot = null;
const matchEntryState = {
  deckName: "",
  matchNumber: null,
};

let matchEntryClockTimer = null;

function updateMatchEntryClock() {
  if (!matchEntryClockEl) {
    return;
  }
  const now = new Date();
  const hours = String(now.getHours()).padStart(2, "0");
  const minutes = String(now.getMinutes()).padStart(2, "0");
  const seconds = String(now.getSeconds()).padStart(2, "0");
  matchEntryClockEl.textContent = `${hours}:${minutes}:${seconds}`;
  matchEntryClockEl.setAttribute("datetime", now.toISOString());
}

function initialiseMatchEntryClock() {
  if (!matchEntryClockEl) {
    return;
  }
  updateMatchEntryClock();
  if (matchEntryClockTimer !== null) {
    return;
  }
  matchEntryClockTimer = window.setInterval(updateMatchEntryClock, 1000);
}

function setActiveView(id) {
  if (!id || currentView === id) {
    return;
  }
  const currentEl = viewElements.get(currentView);
  const nextEl = viewElements.get(id);
  if (!nextEl) {
    return;
  }
  if (currentEl) {
    currentEl.classList.remove("view--active");
    currentEl.setAttribute("hidden", "");
  }
  nextEl.classList.add("view--active");
  nextEl.removeAttribute("hidden");
  currentView = id;
}

function navigateTo(id, { pushCurrent = false } = {}) {
  if (pushCurrent && currentView) {
    viewStack.push(currentView);
  }
  setActiveView(id);
}

function goHome() {
  viewStack.length = 0;
  setActiveView("dashboard");
}

function goBack() {
  const previous = viewStack.pop();
  if (previous) {
    setActiveView(previous);
  } else {
    goHome();
  }
}

function registerNavigationHandlers() {
  document.querySelectorAll("[data-nav-target]").forEach((button) => {
    button.addEventListener("click", (event) => {
      const target = event.currentTarget?.dataset.navTarget;
      if (!target) {
        return;
      }
      viewStack.length = 0;
      setActiveView(target);
    });
  });

  document.querySelectorAll("[data-nav]").forEach((button) => {
    button.addEventListener("click", (event) => {
      const action = event.currentTarget?.dataset.nav;
      if (action === "home") {
        goHome();
      } else if (action === "back") {
        goBack();
      }
    });
  });
}

function formatTurn(value) {
  return value ? "先攻" : "後攻";
}

function formatResult(value) {
  switch (value) {
    case 1:
      return "勝ち";
    case -1:
      return "負け";
    default:
      return "引き分け";
  }
}

function formatCount(value) {
  const numeric = Number(value ?? 0);
  if (Number.isNaN(numeric)) {
    return "0";
  }
  return numeric.toLocaleString("ja-JP");
}

function renderMatches(matches) {
  matchesTableBody.innerHTML = "";

  if (!matches.length) {
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = 6;
    cell.className = "data-table__empty";
    cell.textContent = "まだデータがありません。";
    row.appendChild(cell);
    matchesTableBody.appendChild(row);
    return;
  }

  matches.forEach((record, index) => {
    const row = document.createElement("tr");

    const noCell = document.createElement("td");
    noCell.textContent = record.match_no ?? index + 1;
    row.appendChild(noCell);

    const deckCell = document.createElement("td");
    deckCell.textContent = record.deck_name || "(未設定)";
    row.appendChild(deckCell);

    const opponentCell = document.createElement("td");
    opponentCell.textContent = record.opponent_deck || "-";
    row.appendChild(opponentCell);

    const turnCell = document.createElement("td");
    turnCell.textContent = formatTurn(record.turn);
    row.appendChild(turnCell);

    const resultCell = document.createElement("td");
    resultCell.textContent = formatResult(record.result);
    row.appendChild(resultCell);

    const createdAtCell = document.createElement("td");
    createdAtCell.textContent = record.created_at || "-";
    row.appendChild(createdAtCell);

    matchesTableBody.appendChild(row);
  });
}

function renderDeckTable(decks) {
  deckTableBody.innerHTML = "";

  if (!decks.length) {
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = 3;
    cell.className = "data-table__empty";
    cell.textContent = "まだデータがありません。";
    row.appendChild(cell);
    deckTableBody.appendChild(row);
    return;
  }

  decks.forEach((deck) => {
    const row = document.createElement("tr");

    const nameCell = document.createElement("td");
    nameCell.textContent = deck.name || "(未設定)";
    row.appendChild(nameCell);

    const descriptionCell = document.createElement("td");
    descriptionCell.textContent = deck.description ? deck.description : "―";
    row.appendChild(descriptionCell);

    const usageCell = document.createElement("td");
    usageCell.textContent = `${formatCount(deck.usage_count)} 回`;
    row.appendChild(usageCell);

    deckTableBody.appendChild(row);
  });
}

function renderOpponentDeckTable(records) {
  opponentTableBody.innerHTML = "";

  if (!records.length) {
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = 2;
    cell.className = "data-table__empty";
    cell.textContent = "まだデータがありません。";
    row.appendChild(cell);
    opponentTableBody.appendChild(row);
    return;
  }

  records.forEach((record) => {
    const row = document.createElement("tr");

    const nameCell = document.createElement("td");
    nameCell.textContent = record.name || "(未設定)";
    row.appendChild(nameCell);

    const usageCell = document.createElement("td");
    usageCell.textContent = `${formatCount(record.usage_count)} 回`;
    row.appendChild(usageCell);

    opponentTableBody.appendChild(row);
  });
}

function populateDeckOptions(decks) {
  const current = matchStartSelect.value;
  matchStartSelect.innerHTML = "";

  const placeholder = document.createElement("option");
  placeholder.value = "";
  placeholder.textContent = "デッキを選択...";
  placeholder.selected = !current;
  matchStartSelect.appendChild(placeholder);

  decks.forEach((deck) => {
    const option = document.createElement("option");
    option.value = deck.name;
    const usage = Number(deck.usage_count ?? 0);
    option.textContent = usage
      ? `${deck.name}（${formatCount(deck.usage_count)}回）`
      : deck.name;
    if (deck.name === current) {
      option.selected = true;
    }
    matchStartSelect.appendChild(option);
  });

  if (current && !decks.some((deck) => deck.name === current)) {
    placeholder.selected = true;
  }
}

function populateOpponentOptions(records, selectedValue = "") {
  const current = selectedValue || matchOpponentSelect.value;
  matchOpponentSelect.innerHTML = "";

  const placeholder = document.createElement("option");
  placeholder.value = "";
  placeholder.textContent = "対戦相手デッキを選択...";
  let matched = false;
  matchOpponentSelect.appendChild(placeholder);

  records.forEach((record) => {
    const option = document.createElement("option");
    option.value = record.name;
    const usage = Number(record.usage_count ?? 0);
    option.textContent = usage
      ? `${record.name}（${formatCount(record.usage_count)}回）`
      : record.name;
    if (record.name === current) {
      option.selected = true;
      matched = true;
    }
    matchOpponentSelect.appendChild(option);
  });

  if (!current || !matched) {
    placeholder.selected = true;
  }
}

function updateMatchEntryView() {
  matchEntryDeckNameEl.textContent = matchEntryState.deckName || "-";
  matchEntryNumberEl.textContent =
    matchEntryState.matchNumber !== null ? matchEntryState.matchNumber : "-";
  matchEntryForm.reset();
  populateOpponentOptions(latestSnapshot?.opponent_decks ?? [], "");
}

function applySnapshot(snapshot) {
  latestSnapshot = snapshot;
  versionEl.textContent = snapshot.version ?? "DPL";
  migrationEl.textContent = snapshot.migration_result?.trim()
    ? snapshot.migration_result
    : "特記事項なし";

  deckCountEl.textContent = snapshot.decks?.length ?? 0;
  seasonCountEl.textContent = snapshot.seasons?.length ?? 0;
  matchCountEl.textContent = snapshot.matches?.length ?? 0;
  uiModeEl.textContent = snapshot.ui_mode ?? "normal";

  const records = snapshot.matches ? [...snapshot.matches] : [];
  records.sort((a, b) => {
    if (a.created_at === b.created_at) {
      return (a.match_no ?? 0) - (b.match_no ?? 0);
    }
    return a.created_at > b.created_at ? 1 : -1;
  });
  renderMatches(records.slice(-10).reverse());

  const deckRecords = snapshot.decks ? [...snapshot.decks] : [];
  renderDeckTable(deckRecords);
  populateDeckOptions(deckRecords);

  const opponentRecords = snapshot.opponent_decks ? [...snapshot.opponent_decks] : [];
  renderOpponentDeckTable(opponentRecords);
  populateOpponentOptions(opponentRecords, matchOpponentSelect.value);

  settingsUiModeEl.textContent = snapshot.ui_mode ?? "normal";
  settingsMigrationEl.textContent = migrationEl.textContent;
}

function showNotification(message, durationMs = 2400) {
  toastEl.textContent = message;
  toastEl.hidden = false;
  toastEl.setAttribute("data-visible", "true");

  if (toastTimer !== null) {
    window.clearTimeout(toastTimer);
  }

  toastTimer = window.setTimeout(() => {
    toastEl.removeAttribute("data-visible");
    toastTimer = window.setTimeout(() => {
      toastEl.hidden = true;
      toastTimer = null;
    }, 320);
  }, durationMs);
}

eel.expose(showNotification, "show_notification");

function handleOperationResponse(response, successMessage) {
  if (!response || response.ok !== true) {
    const errorMessage = response?.error || "操作に失敗しました";
    showNotification(errorMessage, 4200);
    return false;
  }

  if (response.snapshot) {
    applySnapshot(response.snapshot);
  }

  if (successMessage) {
    showNotification(successMessage);
  }
  return true;
}

async function fetchSnapshot({ silent = false } = {}) {
  try {
    const snapshot = await eel.fetch_snapshot()();
    applySnapshot(snapshot);
    if (!silent) {
      showNotification("最新のデータを読み込みました");
    }
  } catch (error) {
    console.error("Failed to fetch snapshot", error);
    showNotification("データの取得に失敗しました", 4200);
  }
}

async function beginMatchEntry(deckName, { pushHistory = true } = {}) {
  try {
    const response = await eel.prepare_match({ deck_name: deckName })();
    if (!response || response.ok !== true) {
      const message = response?.error || "対戦情報の準備に失敗しました";
      showNotification(message, 4200);
      return false;
    }

    matchEntryState.deckName = response.data.deck_name;
    matchEntryState.matchNumber = response.data.next_match_no;
    updateMatchEntryView();

    if (pushHistory) {
      navigateTo("match-entry", { pushCurrent: true });
    }
    return true;
  } catch (error) {
    console.error("Failed to prepare match", error);
    showNotification("対戦情報の準備に失敗しました", 4200);
    return false;
  }
}

deckForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const formData = new FormData(deckForm);
  const name = formData.get("name")?.toString().trim() ?? "";
  const description = formData.get("description")?.toString().trim() ?? "";

  if (!name) {
    showNotification("デッキ名を入力してください", 3600);
    return;
  }

  try {
    const response = await eel.register_deck({ name, description })();
    if (handleOperationResponse(response, "デッキを登録しました")) {
      deckForm.reset();
    }
  } catch (error) {
    console.error("Failed to register deck", error);
    showNotification("デッキの登録に失敗しました", 4200);
  }
});

opponentDeckForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const formData = new FormData(opponentDeckForm);
  const name = formData.get("name")?.toString().trim() ?? "";

  if (!name) {
    showNotification("対戦相手デッキ名を入力してください", 3600);
    return;
  }

  try {
    const response = await eel.register_opponent_deck({ name })();
    if (handleOperationResponse(response, "対戦相手デッキを登録しました")) {
      opponentDeckForm.reset();
    }
  } catch (error) {
    console.error("Failed to register opponent deck", error);
    showNotification("対戦相手デッキの登録に失敗しました", 4200);
  }
});

matchStartForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const deckName = matchStartSelect.value.trim();
  if (!deckName) {
    showNotification("使用するデッキを選択してください", 3600);
    return;
  }
  await beginMatchEntry(deckName, { pushHistory: true });
});

matchEntryForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!matchEntryState.deckName) {
    showNotification("デッキが選択されていません", 3600);
    return;
  }

  const formData = new FormData(matchEntryForm);
  const turnValue = formData.get("turn");
  const opponentDeck = formData.get("opponent_deck")?.toString().trim() ?? "";
  const resultValue = formData.get("result");

  if (!turnValue) {
    showNotification("先攻/後攻を選択してください", 3600);
    return;
  }
  if (!opponentDeck) {
    showNotification("対戦相手デッキを選択してください", 3600);
    return;
  }
  if (!resultValue) {
    showNotification("勝敗を選択してください", 3600);
    return;
  }

  const payload = {
    deck_name: matchEntryState.deckName,
    turn: turnValue === "first",
    opponent_deck: opponentDeck,
    result: Number.parseInt(resultValue.toString(), 10),
  };

  try {
    const response = await eel.register_match(payload)();
    if (handleOperationResponse(response, "対戦情報を登録しました")) {
      await beginMatchEntry(matchEntryState.deckName, { pushHistory: false });
    }
  } catch (error) {
    console.error("Failed to register match", error);
    showNotification("対戦情報の登録に失敗しました", 4200);
  }
});

refreshButton.addEventListener("click", () => fetchSnapshot({ silent: false }));

registerNavigationHandlers();

window.addEventListener("DOMContentLoaded", () => {
  initialiseMatchEntryClock();
  fetchSnapshot({ silent: true });
});
