const versionEl = document.getElementById("app-version");
const migrationEl = document.getElementById("migration-result");
const deckCountEl = document.getElementById("deck-count");
const seasonCountEl = document.getElementById("season-count");
const matchCountEl = document.getElementById("match-count");
const uiModeEl = document.getElementById("ui-mode");
const matchesTableBody = document.querySelector("#matches-table tbody");
const refreshButton = document.getElementById("refresh-button");
const toastEl = document.getElementById("toast");

let toastTimer = null;

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

function applySnapshot(snapshot) {
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

refreshButton.addEventListener("click", () => fetchSnapshot({ silent: false }));

window.addEventListener("DOMContentLoaded", () => {
  fetchSnapshot({ silent: true });
});
