const versionEl = document.getElementById("app-version");
const migrationEl = document.getElementById("migration-result");
const deckCountEl = document.getElementById("deck-count");
const seasonCountEl = document.getElementById("season-count");
const matchCountEl = document.getElementById("match-count");
const matchesTableBody = document.querySelector("#matches-table tbody");
const refreshButton = document.getElementById("refresh-button");
const toastEl = document.getElementById("toast");
const deckTableBody = document.querySelector("#deck-table tbody");
const opponentTableBody = document.querySelector("#opponent-deck-table tbody");
const matchStartSelect = document.getElementById("match-start-deck");
const matchStartSeasonSelect = document.getElementById("match-start-season");
const matchOpponentInput = document.getElementById("match-opponent");
const matchOpponentList = document.getElementById("match-opponent-list");
const deckForm = document.getElementById("deck-form");
const opponentDeckForm = document.getElementById("opponent-deck-form");
const matchStartForm = document.getElementById("match-start-form");
const matchEntryForm = document.getElementById("match-entry-form");
const matchEntryDeckNameEl = document.getElementById("match-entry-deck-name");
const matchEntryNumberEl = document.getElementById("match-entry-number");
const matchEntryClockEl = document.getElementById("match-entry-clock");
const matchEntrySeasonEl = document.getElementById("match-entry-season");
const matchEntryDateEl = document.getElementById("match-entry-date");
const settingsMigrationEl = document.getElementById("settings-migration");
const settingsMigrationTimestampEl = document.getElementById("settings-migration-timestamp");
const settingsDbPathEl = document.getElementById("settings-db-path");
const settingsLastBackupPathEl = document.getElementById("settings-last-backup-path");
const settingsLastBackupAtEl = document.getElementById("settings-last-backup-at");
const settingsBackupExportButton = document.getElementById("settings-backup-export");
const settingsBackupImportInput = document.getElementById("settings-backup-import");
const settingsImportStatusEl = document.getElementById("settings-import-status");
const settingsResetButton = document.getElementById("settings-reset-db");
const keywordForm = document.getElementById("keyword-form");
const keywordNameInput = document.getElementById("keyword-name");
const keywordDescriptionInput = document.getElementById("keyword-description");
const keywordTableBody = document.querySelector("#keyword-table tbody");
const matchKeywordsContainer = document.getElementById("match-keywords");
const matchKeywordsInput = document.getElementById("match-keywords-input");
const matchEntryMemoInput = document.getElementById("match-entry-memo");
const matchListTableBody = document.querySelector("#match-list-table tbody");
const matchDetailTimestampEl = document.getElementById("match-detail-timestamp");
const matchDetailDeckEl = document.getElementById("match-detail-deck");
const matchDetailSeasonEl = document.getElementById("match-detail-season");
const matchDetailNumberEl = document.getElementById("match-detail-number");
const matchDetailResultEl = document.getElementById("match-detail-result");
const matchDetailTurnEl = document.getElementById("match-detail-turn");
const matchDetailOpponentEl = document.getElementById("match-detail-opponent");
const matchDetailKeywordsEl = document.getElementById("match-detail-keywords");
const matchDetailMemoEl = document.getElementById("match-detail-memo");
const matchDetailYoutubeStatusEl = document.getElementById("match-detail-youtube-status");
const matchDetailYoutubeCheckedAtEl = document.getElementById("match-detail-youtube-checked-at");
const matchDetailYoutubeLinkEl = document.getElementById("match-detail-youtube-link");
const matchDetailYoutubeInputEl = document.getElementById("match-detail-youtube-input");
const matchDetailYoutubeSaveButton = document.getElementById("match-detail-youtube-save");
const matchDetailYoutubeRetryButton = document.getElementById("match-detail-youtube-retry");
const matchDetailRecordingPathInput = document.getElementById("match-detail-recording-path");
const matchDetailFavoriteEl = document.getElementById("match-detail-favorite");
const matchDetailEditButton = document.getElementById("match-detail-edit");
const matchEditForm = document.getElementById("match-edit-form");
const matchEditDeckSelect = document.getElementById("match-edit-deck");
const matchEditNumberInput = document.getElementById("match-edit-number");
const matchEditOpponentSelect = document.getElementById("match-edit-opponent");
const matchEditSeasonSelect = document.getElementById("match-edit-season");
const matchEditKeywordsContainer = document.getElementById("match-edit-keywords");
const matchEditKeywordsInput = document.getElementById("match-edit-keywords-input");
const matchEditMemoInput = document.getElementById("match-edit-memo");
const matchEditYoutubeInput = document.getElementById("match-edit-youtube");
const matchEditFavoriteInput = document.getElementById("match-edit-favorite");
const seasonForm = document.getElementById("season-form");
const seasonTableBody = document.querySelector("#season-table tbody");
const deckAnalysisFilter = document.getElementById("deck-analysis-filter");
const deckAnalysisSummaryEl = document.getElementById("deck-analysis-summary");
const deckAnalysisTableBody = document.querySelector("#deck-analysis-table tbody");
const deckAnalysisChartCanvas = document.getElementById("deck-analysis-chart");
const opponentAnalysisFilter = document.getElementById("opponent-analysis-filter");
const opponentAnalysisSummaryEl = document.getElementById("opponent-analysis-summary");
const opponentAnalysisTableBody = document.querySelector("#opponent-analysis-table tbody");
const opponentAnalysisChartCanvas = document.getElementById("opponent-analysis-chart");

const YOUTUBE_STATUS_MAP = {
  0: { label: "未送信", tone: "idle" },
  1: { label: "再試行待ち", tone: "danger" },
  2: { label: "送信中...", tone: "warning" },
  3: { label: "送信完了", tone: "success" },
  4: { label: "手動登録済", tone: "info" },
};

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
  seasonId: null,
  seasonName: "",
};

let currentMatchDetail = null;

let matchEntryClockTimer = null;

const keywordToggleState = {
  entry: new Set(),
  edit: new Set(),
};

let deckAnalysisData = [];
let opponentAnalysisData = [];

const SEASON_FILTER_ALL = "__ALL__";
const SEASON_FILTER_RANK = "__RANK__";

let deckAnalysisFilterValue = SEASON_FILTER_ALL;
let opponentAnalysisFilterValue = SEASON_FILTER_ALL;

const eelBridge = typeof window !== "undefined" ? window.eel : undefined;
const hasEel = Boolean(eelBridge);

if (!hasEel) {
  console.info("Eel bridge is not available; running in fallback mode.");
}

const callPy = (name, ...args) => {
  if (!hasEel || typeof eelBridge[name] !== "function") {
    return Promise.reject(new Error(`[EEL_UNAVAILABLE] ${name}`));
  }
  try {
    const result = eelBridge[name](...args);
    return typeof result === "function" ? result() : result;
  } catch (error) {
    return Promise.reject(error);
  }
};

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
  if (matchEntryDateEl) {
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, "0");
    const day = String(now.getDate()).padStart(2, "0");
    matchEntryDateEl.textContent = `(${year}/${month}/${day})`;
  }
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

function formatPercentage(value) {
  const numeric = Number(value ?? 0);
  if (!Number.isFinite(numeric) || numeric <= 0) {
    return "0.0%";
  }
  return `${(numeric * 100).toFixed(1)}%`;
}

function formatScore(value) {
  const numeric = Number(value ?? 0);
  if (!Number.isFinite(numeric)) {
    return "0.00";
  }
  const fixed = numeric.toFixed(2);
  return numeric > 0 ? `+${fixed}` : fixed;
}

function parseKeywordInputValue(hiddenInput) {
  if (!hiddenInput) {
    return [];
  }
  try {
    const raw = hiddenInput.value ? JSON.parse(hiddenInput.value) : [];
    if (!Array.isArray(raw)) {
      return [];
    }
    const seen = new Set();
    const values = [];
    raw.forEach((item) => {
      const normalized = String(item ?? "").trim();
      if (normalized && !seen.has(normalized)) {
        seen.add(normalized);
        values.push(normalized);
      }
    });
    return values;
  } catch (error) {
    console.warn("Failed to parse keyword selection", error);
    return [];
  }
}

function formatSeasonPeriod(season) {
  if (!season) {
    return "―";
  }
  const startDate = season.start_date || "";
  const startTime = season.start_time || "";
  const endDate = season.end_date || "";
  const endTime = season.end_time || "";
  const startParts = [];
  if (startDate) {
    startParts.push(startDate);
  }
  if (startTime) {
    startParts.push(startTime);
  }
  const endParts = [];
  if (endDate) {
    endParts.push(endDate);
  }
  if (endTime) {
    endParts.push(endTime);
  }
  if (!startParts.length && !endParts.length) {
    return "―";
  }
  if (!endParts.length) {
    return `${startParts.join(" ")} 〜`;
  }
  if (!startParts.length) {
    return `〜 ${endParts.join(" ")}`;
  }
  return `${startParts.join(" ")} 〜 ${endParts.join(" ")}`;
}

function resolveSeasonLabel(seasonId) {
  if (!seasonId || !latestSnapshot?.seasons) {
    return "";
  }
  const season = latestSnapshot.seasons.find(
    (item) => String(item.id) === String(seasonId)
  );
  if (!season) {
    return "";
  }
  const period = formatSeasonPeriod(season);
  return period && period !== "―" ? `${season.name}（${period}）` : season.name;
}

function base64ToBlob(base64, mimeType = "application/octet-stream") {
  const binary = atob(base64);
  const length = binary.length;
  const bytes = new Uint8Array(length);
  for (let i = 0; i < length; i += 1) {
    bytes[i] = binary.charCodeAt(i);
  }
  return new Blob([bytes], { type: mimeType });
}

function arrayBufferToBase64(buffer) {
  const bytes = new Uint8Array(buffer);
  let binary = "";
  bytes.forEach((byte) => {
    binary += String.fromCharCode(byte);
  });
  return btoa(binary);
}

function setYoutubeStatus(element, flag) {
  if (!element) {
    return;
  }
  const status = YOUTUBE_STATUS_MAP[flag] ?? YOUTUBE_STATUS_MAP[0];
  element.textContent = status.label;
  element.className = `status-pill status-pill--${status.tone}`;
  element.dataset.tone = status.tone;
}

function formatDateTime(value) {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  const hours = String(date.getHours()).padStart(2, "0");
  const minutes = String(date.getMinutes()).padStart(2, "0");
  const seconds = String(date.getSeconds()).padStart(2, "0");
  return `${year}/${month}/${day} ${hours}:${minutes}:${seconds}`;
}

function renderMatches(matches) {
  matchesTableBody.innerHTML = "";

  if (!matches.length) {
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = 6;
    cell.className = "data-table__empty";
    cell.textContent = "ランク統計対象の対戦がまだ登録されていません。";
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
    cell.colSpan = 4;
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

    const actionsCell = document.createElement("td");
    actionsCell.className = "data-table__actions";
    const deleteButton = document.createElement("button");
    deleteButton.type = "button";
    deleteButton.className = "icon-button";
    deleteButton.dataset.action = "delete-deck";
    deleteButton.dataset.deckName = deck.name;
    deleteButton.setAttribute("aria-label", `${deck.name} を削除`);
    deleteButton.textContent = "🗑️";
    const deckUsage = Number(deck.usage_count ?? 0);
    if (!deck.name || deckUsage > 0) {
      deleteButton.disabled = true;
      deleteButton.title = deckUsage > 0 ? "使用中のデッキは削除できません" : "削除できません";
    }
    actionsCell.appendChild(deleteButton);
    row.appendChild(actionsCell);

    deckTableBody.appendChild(row);
  });
}

function renderOpponentDeckTable(records) {
  opponentTableBody.innerHTML = "";

  if (!records.length) {
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = 3;
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

    const actionsCell = document.createElement("td");
    actionsCell.className = "data-table__actions";
    const deleteButton = document.createElement("button");
    deleteButton.type = "button";
    deleteButton.className = "icon-button";
    deleteButton.dataset.action = "delete-opponent";
    deleteButton.dataset.opponentName = record.name;
    deleteButton.setAttribute("aria-label", `${record.name} を削除`);
    deleteButton.textContent = "🗑️";
    const usageCount = Number(record.usage_count ?? 0);
    if (!record.name || usageCount > 0) {
      deleteButton.disabled = true;
      deleteButton.title = usageCount > 0 ? "使用中のデッキは削除できません" : "削除できません";
    }
    actionsCell.appendChild(deleteButton);
    row.appendChild(actionsCell);

    opponentTableBody.appendChild(row);
  });
}

function renderSeasonTable(records) {
  if (!seasonTableBody) {
    return;
  }

  seasonTableBody.innerHTML = "";

  if (!records.length) {
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = 5;
    cell.className = "data-table__empty";
    cell.textContent = "まだデータがありません。";
    row.appendChild(cell);
    seasonTableBody.appendChild(row);
    return;
  }

  records.forEach((season) => {
    const row = document.createElement("tr");

    const nameCell = document.createElement("td");
    nameCell.textContent = season.name || "(未設定)";
    row.appendChild(nameCell);

    const periodCell = document.createElement("td");
    periodCell.textContent = formatSeasonPeriod(season);
    row.appendChild(periodCell);

    const rankCell = document.createElement("td");
    rankCell.textContent = season.rank_statistics_target ? "対象" : "対象外";
    row.appendChild(rankCell);

    const notesCell = document.createElement("td");
    notesCell.textContent = season.notes ? season.notes : "―";
    row.appendChild(notesCell);

    const actionsCell = document.createElement("td");
    actionsCell.className = "data-table__actions";
    const deleteButton = document.createElement("button");
    deleteButton.type = "button";
    deleteButton.className = "icon-button";
    deleteButton.dataset.action = "delete-season";
    deleteButton.dataset.seasonName = season.name;
    deleteButton.setAttribute("aria-label", `${season.name} を削除`);
    deleteButton.textContent = "🗑️";
    actionsCell.appendChild(deleteButton);
    row.appendChild(actionsCell);

    seasonTableBody.appendChild(row);
  });
}

function renderKeywordTable(keywords) {
  if (!keywordTableBody) {
    return;
  }

  keywordTableBody.innerHTML = "";

  if (!keywords.length) {
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = 6;
    cell.className = "data-table__empty";
    cell.textContent = "まだデータがありません。";
    row.appendChild(cell);
    keywordTableBody.appendChild(row);
    return;
  }

  keywords.forEach((keyword) => {
    const row = document.createElement("tr");

    const nameCell = document.createElement("td");
    nameCell.textContent = keyword.name || "(未設定)";
    row.appendChild(nameCell);

    const idCell = document.createElement("td");
    idCell.textContent = keyword.identifier || "-";
    row.appendChild(idCell);

    const descriptionCell = document.createElement("td");
    descriptionCell.textContent = keyword.description ? keyword.description : "―";
    row.appendChild(descriptionCell);

    const usageCell = document.createElement("td");
    usageCell.textContent = `${formatCount(keyword.usage_count)} 回`;
    row.appendChild(usageCell);

    const statusCell = document.createElement("td");
    const states = [];
    states.push(keyword.is_hidden ? "非表示" : "表示中");
    if (keyword.is_protected) {
      states.push("削除不可");
    }
    statusCell.textContent = states.join(" / ");
    row.appendChild(statusCell);

    const actionsCell = document.createElement("td");
    actionsCell.className = "data-table__actions";
    const toggleButton = document.createElement("button");
    toggleButton.type = "button";
    toggleButton.className = "icon-button";
    toggleButton.dataset.action = "toggle-keyword-visibility";
    toggleButton.dataset.keywordId = keyword.identifier;
    toggleButton.dataset.hidden = keyword.is_hidden ? "1" : "0";
    toggleButton.dataset.keywordName = keyword.name || "";
    toggleButton.setAttribute(
      "aria-label",
      keyword.is_hidden
        ? `${keyword.name} を表示する`
        : `${keyword.name} を非表示にする`
    );
    toggleButton.textContent = keyword.is_hidden ? "👁️‍🗗" : "👁️";
    actionsCell.appendChild(toggleButton);

    const deleteButton = document.createElement("button");
    deleteButton.type = "button";
    deleteButton.className = "icon-button";
    deleteButton.dataset.action = "delete-keyword";
    deleteButton.dataset.keywordId = keyword.identifier;
    deleteButton.setAttribute("aria-label", `${keyword.name} を削除`);
    deleteButton.textContent = "🗑️";
    const usage = Number(keyword.usage_count ?? 0);
    if (!keyword.identifier || usage > 0 || keyword.is_protected) {
      deleteButton.disabled = true;
      if (keyword.is_protected) {
        deleteButton.title = "このキーワードは削除できません";
      } else {
        deleteButton.title =
          usage > 0 ? "使用中のキーワードは削除できません" : "削除できません";
      }
    }
    actionsCell.appendChild(deleteButton);
    row.appendChild(actionsCell);

    keywordTableBody.appendChild(row);
  });
}

function renderMatchList(records) {
  if (!matchListTableBody) {
    return;
  }

  matchListTableBody.innerHTML = "";

  if (!records.length) {
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = 5;
    cell.className = "data-table__empty";
    cell.textContent = "まだデータがありません。";
    row.appendChild(cell);
    matchListTableBody.appendChild(row);
    return;
  }

  records.forEach((record) => {
    const row = document.createElement("tr");

    const timestampCell = document.createElement("td");
    timestampCell.textContent = formatDateTime(record.created_at);
    row.appendChild(timestampCell);

    const deckCell = document.createElement("td");
    deckCell.textContent = record.deck_name || "(未設定)";
    row.appendChild(deckCell);

    const matchNoCell = document.createElement("td");
    matchNoCell.textContent = record.match_no ? `#${record.match_no}` : "-";
    row.appendChild(matchNoCell);

    const resultCell = document.createElement("td");
    resultCell.textContent = formatResult(record.result);
    row.appendChild(resultCell);

    const actionCell = document.createElement("td");
    actionCell.className = "data-table__actions";
    const detailButton = document.createElement("button");
    detailButton.type = "button";
    detailButton.className = "primary-button table-action-button";
    detailButton.dataset.action = "view-match-detail";
    if (record.id != null) {
      detailButton.dataset.matchId = String(record.id);
    } else {
      detailButton.disabled = true;
    }
    detailButton.textContent = "詳細";
    actionCell.appendChild(detailButton);
    row.appendChild(actionCell);

    const deleteCell = document.createElement("td");
    deleteCell.className = "data-table__actions";
    const deleteButton = document.createElement("button");
    deleteButton.type = "button";
    deleteButton.className = "icon-button";
    deleteButton.dataset.action = "delete-match";
    if (record.id != null) {
      deleteButton.dataset.matchId = String(record.id);
      const identifier = record.match_no ? `#${record.match_no}` : record.id;
      deleteButton.setAttribute(
        "aria-label",
        `対戦情報 ${identifier} を削除`
      );
    } else {
      deleteButton.disabled = true;
    }
    deleteButton.textContent = "🗑️";
    deleteCell.appendChild(deleteButton);
    row.appendChild(deleteCell);

    matchListTableBody.appendChild(row);
  });
}

function renderAnalysisSummary(container, data) {
  if (!container) {
    return;
  }

  container.innerHTML = "";

  if (!data.length) {
    container.textContent = "該当するデータがありません。";
    return;
  }

  const totals = data.reduce(
    (acc, item) => {
      acc.matches += item.matchCount;
      acc.wins += item.wins;
      acc.losses += item.losses;
      acc.draws += item.draws;
      acc.scoreSum += item.scoreSum;
      return acc;
    },
    { matches: 0, wins: 0, losses: 0, draws: 0, scoreSum: 0 }
  );

  const winRate = totals.matches ? totals.wins / totals.matches : 0;
  const avgScore = totals.matches ? totals.scoreSum / totals.matches : 0;

  container.innerHTML = `
    <p>対象試合数: <strong>${formatCount(totals.matches)}</strong>（勝ち ${formatCount(
      totals.wins
    )} / 負け ${formatCount(totals.losses)} / 引き分け ${formatCount(
      totals.draws
    )}）</p>
    <p>通算勝率: <strong>${formatPercentage(winRate)}</strong></p>
    <p>平均スコア: <strong>${formatScore(avgScore)}</strong></p>
  `;
}

function renderDeckAnalysisTable(data) {
  if (!deckAnalysisTableBody) {
    return;
  }

  deckAnalysisTableBody.innerHTML = "";

  if (!data.length) {
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = 7;
    cell.className = "data-table__empty";
    cell.textContent = "データがありません。";
    row.appendChild(cell);
    deckAnalysisTableBody.appendChild(row);
    return;
  }

  data.forEach((item) => {
    const row = document.createElement("tr");
    const columns = [
      item.label,
      formatCount(item.matchCount),
      formatCount(item.wins),
      formatCount(item.losses),
      formatCount(item.draws),
      formatPercentage(item.winRate),
      formatScore(item.avgScore),
    ];
    columns.forEach((value) => {
      const cell = document.createElement("td");
      cell.textContent = value;
      row.appendChild(cell);
    });
    deckAnalysisTableBody.appendChild(row);
  });
}

function renderOpponentAnalysisTable(data) {
  if (!opponentAnalysisTableBody) {
    return;
  }

  opponentAnalysisTableBody.innerHTML = "";

  if (!data.length) {
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = 7;
    cell.className = "data-table__empty";
    cell.textContent = "データがありません。";
    row.appendChild(cell);
    opponentAnalysisTableBody.appendChild(row);
    return;
  }

  data.forEach((item) => {
    const row = document.createElement("tr");
    const columns = [
      item.label,
      formatCount(item.matchCount),
      formatCount(item.wins),
      formatCount(item.losses),
      formatCount(item.draws),
      formatPercentage(item.winRate),
      formatScore(item.avgScore),
    ];
    columns.forEach((value) => {
      const cell = document.createElement("td");
      cell.textContent = value;
      row.appendChild(cell);
    });
    opponentAnalysisTableBody.appendChild(row);
  });
}

function renderDeckAnalysisChart(data) {
  renderComboChart(deckAnalysisChartCanvas, data, {
    labelKey: "label",
    countAxisLabel: "試合数",
    rateAxisLabel: "勝率",
  });
}

function renderOpponentAnalysisChart(data) {
  renderComboChart(opponentAnalysisChartCanvas, data, {
    labelKey: "label",
    countAxisLabel: "試合数",
    rateAxisLabel: "勝率",
  });
}

function renderComboChart(canvas, data, options = {}) {
  if (!canvas) {
    return;
  }
  const ctx = canvas.getContext("2d");
  if (!ctx) {
    return;
  }

  const width = canvas.width;
  const height = canvas.height;
  ctx.clearRect(0, 0, width, height);

  if (!data.length) {
    ctx.fillStyle = "rgba(255, 255, 255, 0.6)";
    ctx.font = "16px 'Segoe UI', 'BIZ UDPGothic', sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText("データがありません", width / 2, height / 2);
    return;
  }

  const leftPad = 64;
  const rightPad = 48;
  const topPad = 32;
  const bottomPad = 72;
  const chartWidth = width - leftPad - rightPad;
  const chartHeight = height - topPad - bottomPad;

  const labelKey = options.labelKey ?? "label";
  const maxCount = Math.max(...data.map((item) => item.matchCount || 0), 1);
  const countStep = Math.max(1, Math.ceil(maxCount / 5));
  const scaledMaxCount = countStep * 5;
  const countScale = chartHeight / scaledMaxCount;

  ctx.strokeStyle = "rgba(255, 255, 255, 0.12)";
  ctx.fillStyle = "rgba(255, 255, 255, 0.6)";
  ctx.font = "12px 'Segoe UI', 'BIZ UDPGothic', sans-serif";
  ctx.textAlign = "right";
  ctx.textBaseline = "middle";

  for (let i = 0; i <= 5; i += 1) {
    const value = countStep * i;
    const y = topPad + chartHeight - value * countScale;
    ctx.beginPath();
    ctx.moveTo(leftPad, y);
    ctx.lineTo(width - rightPad, y);
    ctx.stroke();
    ctx.fillText(String(value), leftPad - 8, y);
  }

  ctx.textAlign = "left";
  for (let i = 0; i <= 4; i += 1) {
    const ratio = i / 4;
    const y = topPad + chartHeight - ratio * chartHeight;
    ctx.fillText(`${Math.round(ratio * 100)}%`, width - rightPad + 8, y);
  }

  const barSpace = chartWidth / data.length;
  const barWidth = Math.min(40, Math.max(18, barSpace * 0.5));
  const barOffset = (barSpace - barWidth) / 2;

  const barColor = options.barColor ?? "rgba(79, 141, 209, 0.72)";
  const lineColor = options.lineColor ?? "#f6c945";
  const points = [];

  ctx.textAlign = "center";
  ctx.textBaseline = "alphabetic";
  ctx.fillStyle = "rgba(255, 255, 255, 0.8)";
  ctx.font = "12px 'Segoe UI', 'BIZ UDPGothic', sans-serif";

  data.forEach((item, index) => {
    const x = leftPad + index * barSpace + barOffset;
    const count = item.matchCount || 0;
    const barHeight = count * countScale;
    const y = topPad + chartHeight - barHeight;

    ctx.fillStyle = barColor;
    ctx.fillRect(x, y, barWidth, barHeight);

    ctx.fillStyle = "rgba(255, 255, 255, 0.85)";
    ctx.fillText(String(count), x + barWidth / 2, y - 6);

    const rate = Math.max(0, Math.min(1, Number(item.winRate ?? 0)));
    const rateY = topPad + chartHeight - rate * chartHeight;
    points.push({ x: x + barWidth / 2, y: rateY, rate });

    const label = String(item[labelKey] ?? "-");
    ctx.save();
    ctx.translate(x + barWidth / 2, height - bottomPad + 12);
    ctx.rotate((-45 * Math.PI) / 180);
    ctx.textAlign = "right";
    ctx.textBaseline = "middle";
    ctx.fillStyle = "rgba(255, 255, 255, 0.85)";
    ctx.fillText(label, 0, 0);
    ctx.restore();
  });

  ctx.strokeStyle = lineColor;
  ctx.lineWidth = 2;
  ctx.beginPath();
  points.forEach((point, index) => {
    if (index === 0) {
      ctx.moveTo(point.x, point.y);
    } else {
      ctx.lineTo(point.x, point.y);
    }
  });
  ctx.stroke();

  ctx.fillStyle = lineColor;
  points.forEach((point) => {
    ctx.beginPath();
    ctx.arc(point.x, point.y, 3, 0, Math.PI * 2);
    ctx.fill();
    ctx.font = "11px 'Segoe UI', 'BIZ UDPGothic', sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "bottom";
    ctx.fillText(formatPercentage(point.rate), point.x, point.y - 6);
  });

  ctx.font = "12px 'Segoe UI', 'BIZ UDPGothic', sans-serif";
  ctx.fillStyle = "rgba(255, 255, 255, 0.78)";
  ctx.textAlign = "left";
  ctx.textBaseline = "bottom";
  ctx.fillText(options.countAxisLabel ?? "試合数", leftPad, topPad - 8);
  ctx.textAlign = "right";
  ctx.fillText(options.rateAxisLabel ?? "勝率", width - rightPad, topPad - 8);
}

function ensureValidSeasonFilter(value, seasons) {
  const allowed = new Set([SEASON_FILTER_ALL, SEASON_FILTER_RANK]);
  seasons.forEach((season) => {
    if (season && season.id != null) {
      allowed.add(String(season.id));
    }
  });
  return allowed.has(value) ? value : SEASON_FILTER_ALL;
}

function populateAnalysisFilters(seasons = []) {
  const records = Array.isArray(seasons) ? seasons : [];
  deckAnalysisFilterValue = ensureValidSeasonFilter(deckAnalysisFilterValue, records);
  opponentAnalysisFilterValue = ensureValidSeasonFilter(
    opponentAnalysisFilterValue,
    records
  );

  const baseOptions = [
    { value: SEASON_FILTER_ALL, label: "試合記録全体" },
    { value: SEASON_FILTER_RANK, label: "ランク通算" },
  ];

  const seasonOptions = records.map((season) => {
    const labelParts = [season.name || "未設定"];
    const period = formatSeasonPeriod(season);
    if (period && period !== "―") {
      labelParts.push(`（${period}）`);
    }
    return {
      value: String(season.id),
      label: labelParts.join(""),
    };
  });

  const options = [...baseOptions, ...seasonOptions];

  const fill = (select, selected) => {
    if (!select) {
      return;
    }
    const current = ensureValidSeasonFilter(selected ?? SEASON_FILTER_ALL, records);
    select.innerHTML = "";
    options.forEach((option) => {
      const optionEl = document.createElement("option");
      optionEl.value = option.value;
      optionEl.textContent = option.label;
      if (option.value === current) {
        optionEl.selected = true;
      }
      select.appendChild(optionEl);
    });
    return current;
  };

  const deckValue = fill(deckAnalysisFilter, deckAnalysisFilterValue);
  if (typeof deckValue === "string") {
    deckAnalysisFilterValue = deckValue;
  }
  const opponentValue = fill(opponentAnalysisFilter, opponentAnalysisFilterValue);
  if (typeof opponentValue === "string") {
    opponentAnalysisFilterValue = opponentValue;
  }
}

function filterMatchesForAnalysis(matches, filterValue) {
  const records = Array.isArray(matches) ? matches : [];
  if (!filterValue || filterValue === SEASON_FILTER_ALL) {
    return records;
  }
  if (filterValue === SEASON_FILTER_RANK) {
    return records.filter((match) => Boolean(match?.rank_statistics_target));
  }
  const seasonId = Number.parseInt(filterValue, 10);
  if (Number.isNaN(seasonId)) {
    return records;
  }
  return records.filter((match) => {
    if (match?.season_id == null) {
      return false;
    }
    const candidate = Number.parseInt(String(match.season_id), 10);
    return !Number.isNaN(candidate) && candidate === seasonId;
  });
}

function buildDeckAnalysisData(matches) {
  const buckets = new Map();
  (matches || []).forEach((match) => {
    const label = match?.deck_name ? String(match.deck_name) : "(未設定)";
    if (!buckets.has(label)) {
      buckets.set(label, {
        label,
        matchCount: 0,
        wins: 0,
        losses: 0,
        draws: 0,
        scoreSum: 0,
      });
    }
    const bucket = buckets.get(label);
    bucket.matchCount += 1;
    const result = Number(match?.result ?? 0);
    if (result > 0) {
      bucket.wins += 1;
    } else if (result < 0) {
      bucket.losses += 1;
    } else {
      bucket.draws += 1;
    }
    if (Number.isFinite(result)) {
      bucket.scoreSum += result;
    }
  });

  return Array.from(buckets.values())
    .map((bucket) => ({
      ...bucket,
      winRate: bucket.matchCount ? bucket.wins / bucket.matchCount : 0,
      avgScore: bucket.matchCount ? bucket.scoreSum / bucket.matchCount : 0,
    }))
    .sort((a, b) => {
      if (b.matchCount !== a.matchCount) {
        return b.matchCount - a.matchCount;
      }
      return a.label.localeCompare(b.label, "ja");
    });
}

function buildOpponentAnalysisData(matches) {
  const buckets = new Map();
  (matches || []).forEach((match) => {
    const label = match?.opponent_deck
      ? String(match.opponent_deck)
      : "(未設定)";
    if (!buckets.has(label)) {
      buckets.set(label, {
        label,
        matchCount: 0,
        wins: 0,
        losses: 0,
        draws: 0,
        scoreSum: 0,
      });
    }
    const bucket = buckets.get(label);
    bucket.matchCount += 1;
    const result = Number(match?.result ?? 0);
    if (result > 0) {
      bucket.wins += 1;
    } else if (result < 0) {
      bucket.losses += 1;
    } else {
      bucket.draws += 1;
    }
    if (Number.isFinite(result)) {
      bucket.scoreSum += result;
    }
  });

  return Array.from(buckets.values())
    .map((bucket) => ({
      ...bucket,
      winRate: bucket.matchCount ? bucket.wins / bucket.matchCount : 0,
      avgScore: bucket.matchCount ? bucket.scoreSum / bucket.matchCount : 0,
    }))
    .sort((a, b) => {
      if (b.matchCount !== a.matchCount) {
        return b.matchCount - a.matchCount;
      }
      return a.label.localeCompare(b.label, "ja");
    });
}

function updateDeckAnalysisView() {
  const matches = latestSnapshot?.matches ?? [];
  const filtered = filterMatchesForAnalysis(matches, deckAnalysisFilterValue);
  deckAnalysisData = buildDeckAnalysisData(filtered);
  renderAnalysisSummary(deckAnalysisSummaryEl, deckAnalysisData);
  renderDeckAnalysisTable(deckAnalysisData);
  renderDeckAnalysisChart(deckAnalysisData);
}

function updateOpponentAnalysisView() {
  const matches = latestSnapshot?.matches ?? [];
  const filtered = filterMatchesForAnalysis(matches, opponentAnalysisFilterValue);
  opponentAnalysisData = buildOpponentAnalysisData(filtered);
  renderAnalysisSummary(opponentAnalysisSummaryEl, opponentAnalysisData);
  renderOpponentAnalysisTable(opponentAnalysisData);
  renderOpponentAnalysisChart(opponentAnalysisData);
}

function renderMatchDetail(detail) {
  if (!matchDetailTimestampEl) {
    return;
  }

  if (!detail) {
    matchDetailTimestampEl.textContent = "-";
    matchDetailDeckEl.textContent = "-";
    if (matchDetailSeasonEl) {
      matchDetailSeasonEl.textContent = "-";
    }
    matchDetailNumberEl.textContent = "-";
    matchDetailResultEl.textContent = "-";
    matchDetailTurnEl.textContent = "-";
    matchDetailOpponentEl.textContent = "-";
    if (matchDetailKeywordsEl) {
      matchDetailKeywordsEl.innerHTML = "";
      matchDetailKeywordsEl.textContent = "-";
    }
    if (matchDetailMemoEl) {
      matchDetailMemoEl.innerHTML = "";
      matchDetailMemoEl.textContent = "-";
    }
    if (matchDetailYoutubeStatusEl) {
      setYoutubeStatus(matchDetailYoutubeStatusEl, 0);
    }
    if (matchDetailYoutubeCheckedAtEl) {
      matchDetailYoutubeCheckedAtEl.textContent = "―";
    }
    if (matchDetailYoutubeLinkEl) {
      matchDetailYoutubeLinkEl.textContent = "―";
    }
    if (matchDetailYoutubeInputEl) {
      matchDetailYoutubeInputEl.value = "";
    }
    if (matchDetailYoutubeSaveButton) {
      matchDetailYoutubeSaveButton.disabled = true;
    }
    if (matchDetailYoutubeRetryButton) {
      matchDetailYoutubeRetryButton.disabled = true;
    }
    if (matchDetailRecordingPathInput) {
      matchDetailRecordingPathInput.value = "";
    }
    matchDetailFavoriteEl.textContent = "-";
    if (matchDetailEditButton) {
      matchDetailEditButton.disabled = true;
      matchDetailEditButton.removeAttribute("data-match-id");
    }
    return;
  }

  matchDetailTimestampEl.textContent = formatDateTime(detail.created_at);
  matchDetailDeckEl.textContent = detail.deck_name || "(未設定)";
  if (matchDetailSeasonEl) {
    matchDetailSeasonEl.textContent =
      detail.season_name || resolveSeasonLabel(detail.season_id) || "―";
  }
  matchDetailNumberEl.textContent = detail.match_no
    ? `#${detail.match_no}`
    : "-";
  matchDetailResultEl.textContent = formatResult(detail.result);
  matchDetailTurnEl.textContent = formatTurn(detail.turn);
  matchDetailOpponentEl.textContent = detail.opponent_deck || "-";

  if (matchDetailKeywordsEl) {
    matchDetailKeywordsEl.innerHTML = "";
    if (detail.keyword_details && detail.keyword_details.length) {
      detail.keyword_details.forEach((keyword) => {
        const chip = document.createElement("span");
        chip.className = "keyword-chip";
        chip.textContent = keyword.name;
        matchDetailKeywordsEl.appendChild(chip);
      });
    } else {
      const placeholder = document.createElement("span");
      placeholder.className = "keyword-chip";
      placeholder.dataset.empty = "true";
      placeholder.textContent = "未設定";
      matchDetailKeywordsEl.appendChild(placeholder);
    }
  }

  if (matchDetailMemoEl) {
    matchDetailMemoEl.innerHTML = "";
    if (detail.memo) {
      const lines = String(detail.memo).split(/\r?\n/);
      lines.forEach((line, index) => {
        if (index > 0) {
          matchDetailMemoEl.appendChild(document.createElement("br"));
        }
        matchDetailMemoEl.appendChild(document.createTextNode(line));
      });
    } else {
      matchDetailMemoEl.textContent = "―";
    }
  }

  if (matchDetailYoutubeStatusEl) {
    setYoutubeStatus(matchDetailYoutubeStatusEl, detail.youtube_flag ?? 0);
  }
  const youtubeFlagValue = Number(detail.youtube_flag ?? 0);
  if (matchDetailYoutubeCheckedAtEl) {
    matchDetailYoutubeCheckedAtEl.textContent = detail.youtube_checked_at
      ? formatDateTime(detail.youtube_checked_at)
      : "―";
  }
  if (matchDetailYoutubeLinkEl) {
    matchDetailYoutubeLinkEl.innerHTML = "";
    if (detail.youtube_url) {
      const link = document.createElement("a");
      link.href = detail.youtube_url;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      link.textContent = detail.youtube_url;
      matchDetailYoutubeLinkEl.appendChild(link);
    } else {
      matchDetailYoutubeLinkEl.textContent = "―";
    }
  }
  if (matchDetailYoutubeInputEl) {
    matchDetailYoutubeInputEl.value = detail.youtube_url || "";
  }
  if (matchDetailYoutubeSaveButton) {
    matchDetailYoutubeSaveButton.disabled = !hasEel;
  }
  if (matchDetailYoutubeRetryButton) {
    const disableRetry =
      !hasEel || youtubeFlagValue === 2 || youtubeFlagValue === 3 || youtubeFlagValue === 4;
    matchDetailYoutubeRetryButton.disabled = disableRetry;
  }
  if (matchDetailRecordingPathInput) {
    matchDetailRecordingPathInput.value = "";
  }

  matchDetailFavoriteEl.textContent = detail.favorite ? "はい" : "いいえ";

  if (matchDetailEditButton) {
    matchDetailEditButton.disabled = false;
    matchDetailEditButton.dataset.matchId = detail.id;
  }
}

async function showMatchDetail(matchId, { pushHistory = true, navigate = true } = {}) {
  if (!Number.isInteger(matchId) || matchId <= 0) {
    showNotification("対戦情報が見つかりません", 3600);
    return false;
  }

  try {
    const response = await callPy("get_match_detail", { id: matchId });
    if (!response || response.ok !== true) {
      const message = response?.error || "対戦情報を取得できませんでした";
      showNotification(message, 4200);
      return false;
    }
    currentMatchDetail = response.data;
    renderMatchDetail(currentMatchDetail);

    if (navigate) {
      if (pushHistory) {
        navigateTo("match-detail", { pushCurrent: true });
      } else {
        setActiveView("match-detail");
      }
    }
    return true;
  } catch (error) {
    return handleError(error, "対戦情報の取得に失敗しました", {
      context: "get_match_detail",
    });
  }
}

function openMatchEditView() {
  if (!currentMatchDetail) {
    showNotification("対戦情報が選択されていません", 3600);
    return;
  }
  fillMatchEditForm(currentMatchDetail);
  navigateTo("match-edit", { pushCurrent: true });
}

function fillMatchEditForm(detail) {
  if (!matchEditForm) {
    return;
  }

  matchEditForm.reset();
  matchEditForm.dataset.matchId = detail.id;

  populateDeckOptions(latestSnapshot?.decks ?? [], {
    select: matchEditDeckSelect,
    selectedValue: detail.deck_name || "",
  });

  populateSeasonOptions(latestSnapshot?.seasons ?? [], {
    editSelect: matchEditSeasonSelect,
    editValue: detail.season_id ? String(detail.season_id) : "",
  });

  if (matchEditNumberInput) {
    matchEditNumberInput.value = detail.match_no ?? "";
  }

  populateOpponentOptions(latestSnapshot?.opponent_decks ?? [], {
    select: matchEditOpponentSelect,
    selectedValue: detail.opponent_deck || "",
  });

  refreshKeywordToggleList("edit", latestSnapshot?.keywords ?? [], {
    selected: Array.isArray(detail.keyword_ids)
      ? detail.keyword_ids.map((value) => String(value))
      : [],
  });

  const turnInputs = matchEditForm.querySelectorAll('input[name="turn"]');
  turnInputs.forEach((input) => {
    input.checked = input.value === (detail.turn ? "first" : "second");
  });

  const resultInputs = matchEditForm.querySelectorAll('input[name="result"]');
  resultInputs.forEach((input) => {
    input.checked = input.value === String(detail.result ?? "");
  });

  if (matchEditYoutubeInput) {
    matchEditYoutubeInput.value = detail.youtube_url || "";
  }

  if (matchEditFavoriteInput) {
    matchEditFavoriteInput.checked = Boolean(detail.favorite);
  }

  if (matchEditMemoInput) {
    matchEditMemoInput.value = detail.memo || "";
  }
}

function populateDeckOptions(decks, options = {}) {
  const { select = matchStartSelect, selectedValue } = options;
  if (!select) {
    return;
  }

  const current = selectedValue ?? select.value ?? "";
  select.innerHTML = "";

  const placeholder = document.createElement("option");
  placeholder.value = "";
  placeholder.textContent = "デッキを選択...";
  placeholder.selected = !current;
  select.appendChild(placeholder);

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
    select.appendChild(option);
  });

  if (current && !decks.some((deck) => deck.name === current)) {
    placeholder.selected = true;
  }
}

function populateOpponentOptions(records, options = {}) {
  const selectElement = options.select ?? matchEditOpponentSelect;
  const inputElement = options.input ?? matchOpponentInput;
  const listElement = options.list ?? matchOpponentList;
  const selectedValue = options.selectedValue ?? (
    selectElement ? selectElement.value ?? "" : inputElement?.value ?? ""
  );

  if (selectElement) {
    const current = selectedValue ?? selectElement.value ?? "";
    selectElement.innerHTML = "";

    const placeholder = document.createElement("option");
    placeholder.value = "";
    placeholder.textContent = "対戦相手デッキを選択...";
    let matched = false;
    selectElement.appendChild(placeholder);

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
      selectElement.appendChild(option);
    });

    if (!current || !matched) {
      placeholder.selected = true;
    }
  }

  if (inputElement && listElement) {
    const existingValue = options.selectedValue ?? inputElement.value ?? "";
    listElement.innerHTML = "";
    records.forEach((record) => {
      const option = document.createElement("option");
      option.value = record.name;
      const usage = Number(record.usage_count ?? 0);
      option.label = usage
        ? `${record.name}（${formatCount(record.usage_count)}回）`
        : record.name;
      listElement.appendChild(option);
    });
    if (existingValue) {
      inputElement.value = existingValue;
    }
  }
}

function populateSeasonOptions(seasons, options = {}) {
  const startSelect = options.startSelect ?? matchStartSeasonSelect;
  const editSelect = options.editSelect ?? matchEditSeasonSelect;
  const startValue =
    options.startValue ?? (startSelect ? startSelect.value ?? "" : "");
  const editValue = options.editValue ?? (editSelect ? editSelect.value ?? "" : "");

  const fill = (select, selected) => {
    if (!select) {
      return;
    }
    const current = selected ?? "";
    select.innerHTML = "";
    const placeholder = document.createElement("option");
    placeholder.value = "";
    placeholder.textContent = "シーズンを選択...";
    placeholder.selected = !current;
    select.appendChild(placeholder);

    seasons.forEach((season) => {
      const option = document.createElement("option");
      option.value = String(season.id);
      const period = formatSeasonPeriod(season);
      option.textContent = period && period !== "―"
        ? `${season.name}（${period}）`
        : season.name;
      if (String(season.id) === String(current)) {
        option.selected = true;
      }
      select.appendChild(option);
    });

    if (current && !Array.from(select.options).some((opt) => opt.value === String(current))) {
      placeholder.selected = true;
    }
  };

  fill(startSelect, startValue);
  fill(editSelect, editValue);
}

function refreshKeywordToggleList(target, keywords, { selected } = {}) {
  const container =
    target === "entry" ? matchKeywordsContainer : matchEditKeywordsContainer;
  const hiddenInput =
    target === "entry" ? matchKeywordsInput : matchEditKeywordsInput;
  const state = keywordToggleState[target];
  if (!container || !hiddenInput || !state) {
    return;
  }

  state.clear();
  const initialValues = Array.isArray(selected)
    ? selected
    : (() => {
        try {
          const value = hiddenInput.value ? JSON.parse(hiddenInput.value) : [];
          return Array.isArray(value) ? value : [];
        } catch (error) {
          return [];
        }
      })();
  initialValues.forEach((value) => {
    if (value) {
      state.add(String(value));
    }
  });

  const keywordList = Array.isArray(keywords) ? keywords : [];
  const items = keywordList.filter((keyword) => {
    if (!keyword) {
      return false;
    }
    if (!keyword.is_hidden) {
      return true;
    }
    return state.has(String(keyword.identifier));
  });

  const uniqueItems = [];
  const seen = new Set();
  items.forEach((keyword) => {
    const id = String(keyword.identifier);
    if (!seen.has(id)) {
      uniqueItems.push(keyword);
      seen.add(id);
    }
  });

  container.innerHTML = "";
  uniqueItems.forEach((keyword) => {
    const id = String(keyword.identifier);
    const button = document.createElement("button");
    button.type = "button";
    button.className = "keyword-toggle";
    if (keyword.is_hidden) {
      button.classList.add("keyword-toggle--hidden");
      button.title = "非表示のキーワードです";
    }
    button.dataset.keywordId = id;
    const selectedNow = state.has(id);
    button.setAttribute("aria-pressed", selectedNow ? "true" : "false");
    button.textContent = keyword.name;
    button.addEventListener("click", () => {
      const pressed = button.getAttribute("aria-pressed") === "true";
      if (pressed) {
        state.delete(id);
        button.setAttribute("aria-pressed", "false");
        if (keyword.is_hidden && target === "entry") {
          button.remove();
        }
      } else {
        state.add(id);
        button.setAttribute("aria-pressed", "true");
      }
      hiddenInput.value = JSON.stringify(Array.from(state));
    });
    container.appendChild(button);
  });

  hiddenInput.value = JSON.stringify(Array.from(state));
}

function updateMatchEntryView() {
  matchEntryDeckNameEl.textContent = matchEntryState.deckName || "-";
  matchEntryNumberEl.textContent =
    matchEntryState.matchNumber !== null ? matchEntryState.matchNumber : "-";
  matchEntryForm.reset();
  if (matchEntryMemoInput) {
    matchEntryMemoInput.value = "";
  }
  if (matchKeywordsInput) {
    matchKeywordsInput.value = "[]";
  }
  keywordToggleState.entry.clear();
  const seasonLabel =
    resolveSeasonLabel(matchEntryState.seasonId) || matchEntryState.seasonName || "―";
  if (matchEntrySeasonEl) {
    matchEntrySeasonEl.textContent = seasonLabel;
  }
  populateOpponentOptions(latestSnapshot?.opponent_decks ?? [], {
    input: matchOpponentInput,
    list: matchOpponentList,
    selectedValue: "",
  });
  refreshKeywordToggleList("entry", latestSnapshot?.keywords ?? [], { selected: [] });
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

  const records = snapshot.matches ? [...snapshot.matches] : [];
  records.sort((a, b) => {
    if (a.created_at === b.created_at) {
      return (a.match_no ?? 0) - (b.match_no ?? 0);
    }
    return a.created_at > b.created_at ? 1 : -1;
  });
  const rankMatches = records.filter((record) =>
    Boolean(record.rank_statistics_target)
  );
  renderMatches(rankMatches.slice(-10).reverse());

  const deckRecords = snapshot.decks ? [...snapshot.decks] : [];
  renderDeckTable(deckRecords);
  populateDeckOptions(deckRecords);

  const opponentRecords = snapshot.opponent_decks
    ? [...snapshot.opponent_decks]
    : [];
  renderOpponentDeckTable(opponentRecords);
  populateOpponentOptions(opponentRecords, {
    input: matchOpponentInput,
    list: matchOpponentList,
    selectedValue: matchOpponentInput?.value ?? "",
  });
  populateOpponentOptions(opponentRecords, {
    select: matchEditOpponentSelect,
    selectedValue:
      matchEditOpponentSelect?.value || currentMatchDetail?.opponent_deck || "",
  });

  const keywordRecords = snapshot.keywords ? [...snapshot.keywords] : [];
  renderKeywordTable(keywordRecords);
  refreshKeywordToggleList("entry", keywordRecords, {
    selected: Array.from(keywordToggleState.entry),
  });
  const editSelection =
    currentView === "match-edit"
      ? Array.from(keywordToggleState.edit)
      : [];
  refreshKeywordToggleList("edit", keywordRecords, { selected: editSelection });

  const seasonRecords = snapshot.seasons ? [...snapshot.seasons] : [];
  renderSeasonTable(seasonRecords);
  populateSeasonOptions(seasonRecords, {
    startSelect: matchStartSeasonSelect,
    startValue:
      matchStartSeasonSelect?.value || (matchEntryState.seasonId ? String(matchEntryState.seasonId) : ""),
    editSelect: matchEditSeasonSelect,
    editValue:
      matchEditSeasonSelect?.value || (currentMatchDetail?.season_id ? String(currentMatchDetail.season_id) : ""),
  });

  populateDeckOptions(deckRecords, {
    select: matchEditDeckSelect,
    selectedValue: matchEditDeckSelect?.value || currentMatchDetail?.deck_name || "",
  });

  populateAnalysisFilters(seasonRecords);
  updateDeckAnalysisView();
  updateOpponentAnalysisView();

  const matchRecords = snapshot.matches ? [...snapshot.matches] : [];
  matchRecords.sort((a, b) => {
    const timeA = Date.parse(a.created_at ?? "");
    const timeB = Date.parse(b.created_at ?? "");
    if (Number.isNaN(timeA) || Number.isNaN(timeB)) {
      return (b.id ?? 0) - (a.id ?? 0);
    }
    if (timeA === timeB) {
      return (b.match_no ?? 0) - (a.match_no ?? 0);
    }
    return timeB - timeA;
  });
  renderMatchList(matchRecords);

  if (currentMatchDetail?.id && currentView === "match-detail") {
    showMatchDetail(currentMatchDetail.id, { pushHistory: false, navigate: false });
  }

  settingsMigrationEl.textContent = migrationEl.textContent;
  if (settingsMigrationTimestampEl) {
    const migrationLabel = snapshot.migration_timestamp
      ? `最終実行：${formatDateTime(snapshot.migration_timestamp)}`
      : "最終実行：未実行";
    settingsMigrationTimestampEl.textContent = migrationLabel;
  }
  if (settingsDbPathEl) {
    settingsDbPathEl.textContent = snapshot.database_path || "―";
  }
  if (settingsLastBackupPathEl) {
    settingsLastBackupPathEl.textContent = snapshot.last_backup_path || "―";
  }
  if (settingsLastBackupAtEl) {
    settingsLastBackupAtEl.textContent = snapshot.last_backup_at
      ? `最終出力：${formatDateTime(snapshot.last_backup_at)}`
      : "最終出力：未実行";
  }
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

if (hasEel && typeof eelBridge.expose === "function") {
  eelBridge.expose(showNotification, "show_notification");
}

function handleError(error, friendlyMessage, options = {}) {
  const { durationMs = 4200, context } = options;
  const message = friendlyMessage ?? "予期しないエラーが発生しました";
  const prefix = context ? `${context}: ${message}` : message;
  console.error(prefix, error);
  showNotification(message, durationMs);
  return false;
}

function validateRequired(value, label, { message, durationMs = 3600 } = {}) {
  const normalized = typeof value === "string" ? value.trim() : value;
  if (normalized) {
    return normalized;
  }
  const text = message ?? `${label ?? "値"}を入力してください`;
  showNotification(text, durationMs);
  return null;
}

function handleOperationResponse(response, successMessage) {
  if (!response || response.ok !== true) {
    const errorMessage = response?.error || "操作に失敗しました";
    console.error("Operation failed", response);
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
    const snapshot = await callPy("fetch_snapshot");
    applySnapshot(snapshot);
    if (!silent) {
      showNotification("最新のデータを読み込みました");
    }
  } catch (error) {
    handleError(error, "データの取得に失敗しました", {
      context: "fetch_snapshot",
    });
  }
}

async function beginMatchEntry(
  deckName,
  { pushHistory = true, seasonId = null, seasonName = "" } = {}
) {
  try {
    const payload = { deck_name: deckName };
    if (seasonId !== null && seasonId !== "" && seasonId !== false) {
      payload.season_id = seasonId;
    }
    const response = await callPy("prepare_match", payload);
    if (!response || response.ok !== true) {
      const message = response?.error || "対戦情報の準備に失敗しました";
      showNotification(message, 4200);
      return false;
    }

    matchEntryState.deckName = response.data.deck_name;
    matchEntryState.matchNumber = response.data.next_match_no;
    if (response.data.season_id !== undefined && response.data.season_id !== null) {
      matchEntryState.seasonId = String(response.data.season_id);
    } else if (seasonId !== null && seasonId !== "") {
      matchEntryState.seasonId = String(seasonId);
    } else {
      matchEntryState.seasonId = null;
    }
    matchEntryState.seasonName =
      seasonName || resolveSeasonLabel(matchEntryState.seasonId) || "";
    updateMatchEntryView();

    if (pushHistory) {
      navigateTo("match-entry", { pushCurrent: true });
    }
    return true;
  } catch (error) {
    return handleError(error, "対戦情報の準備に失敗しました", {
      context: "prepare_match",
    });
  }
}

deckForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const formData = new FormData(deckForm);
  const rawName = formData.get("name")?.toString() ?? "";
  const name = validateRequired(rawName, "デッキ名");
  if (name === null) {
    return;
  }
  const description = formData.get("description")?.toString().trim() ?? "";

  try {
    const response = await callPy("register_deck", { name, description });
    if (handleOperationResponse(response, "デッキを登録しました")) {
      deckForm.reset();
    }
  } catch (error) {
    handleError(error, "デッキの登録に失敗しました", { context: "register_deck" });
  }
});

opponentDeckForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const formData = new FormData(opponentDeckForm);
  const rawName = formData.get("name")?.toString() ?? "";
  const name = validateRequired(rawName, "対戦相手デッキ名");
  if (name === null) {
    return;
  }

  try {
    const response = await callPy("register_opponent_deck", { name });
    if (handleOperationResponse(response, "対戦相手デッキを登録しました")) {
      opponentDeckForm.reset();
    }
  } catch (error) {
    handleError(error, "対戦相手デッキの登録に失敗しました", {
      context: "register_opponent_deck",
    });
  }
});

if (keywordForm) {
  keywordForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const name = keywordNameInput?.value?.trim() ?? "";
    const description = keywordDescriptionInput?.value?.trim() ?? "";

    if (!name) {
      showNotification("キーワード名を入力してください", 3600);
      return;
    }

    try {
      const response = await callPy("register_keyword", { name, description });
      if (handleOperationResponse(response, "キーワードを登録しました")) {
        keywordForm.reset();
      }
    } catch (error) {
      handleError(error, "キーワードの登録に失敗しました", {
        context: "register_keyword",
      });
    }
  });
}

if (deckTableBody) {
  deckTableBody.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-action='delete-deck']");
    if (!button) {
      return;
    }

    const deckName = button.dataset.deckName;
    if (!deckName) {
      return;
    }

    const confirmed = window.confirm(
      `デッキ「${deckName}」を削除しますか？この操作は取り消せません。`
    );
    if (!confirmed) {
      return;
    }

    try {
      const response = await callPy("delete_deck", { name: deckName });
      handleOperationResponse(response, "デッキを削除しました");
    } catch (error) {
      handleError(error, "デッキの削除に失敗しました", { context: "delete_deck" });
    }
  });
}

if (opponentTableBody) {
  opponentTableBody.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-action='delete-opponent']");
    if (!button) {
      return;
    }

    const opponentName = button.dataset.opponentName;
    if (!opponentName) {
      return;
    }

    const confirmed = window.confirm(
      `対戦相手デッキ「${opponentName}」を削除しますか？`
    );
    if (!confirmed) {
      return;
    }

    try {
      const response = await callPy("delete_opponent_deck", { name: opponentName });
      handleOperationResponse(response, "対戦相手デッキを削除しました");
    } catch (error) {
      handleError(error, "対戦相手デッキの削除に失敗しました", {
        context: "delete_opponent_deck",
      });
    }
  });
}

if (keywordTableBody) {
  keywordTableBody.addEventListener("click", async (event) => {
    const toggleButton = event.target.closest(
      "[data-action='toggle-keyword-visibility']"
    );
    if (toggleButton) {
      const keywordId = toggleButton.dataset.keywordId;
      if (!keywordId) {
        return;
      }
      const hiddenFlag = toggleButton.dataset.hidden === "1";
      try {
        const response = await callPy("set_keyword_visibility", {
          identifier: keywordId,
          hidden: hiddenFlag ? 0 : 1,
        });
        const success = handleOperationResponse(
          response,
          hiddenFlag ? "キーワードを表示しました" : "キーワードを非表示にしました"
        );
        if (success) {
          const nextHidden = hiddenFlag ? 0 : 1;
          toggleButton.dataset.hidden = nextHidden ? "1" : "0";
          const keywordName = toggleButton.dataset.keywordName || "";
          toggleButton.textContent = nextHidden ? "👁️‍🗗" : "👁️";
          toggleButton.setAttribute(
            "aria-label",
            nextHidden
              ? `${keywordName || "キーワード"} を表示する`
              : `${keywordName || "キーワード"} を非表示にする`
          );
        }
      } catch (error) {
        handleError(error, "キーワードの表示設定に失敗しました", {
          context: "set_keyword_visibility",
        });
      }
      return;
    }

    const button = event.target.closest("[data-action='delete-keyword']");
    if (!button) {
      return;
    }

    const keywordId = button.dataset.keywordId;
    if (!keywordId) {
      return;
    }

    const confirmed = window.confirm("選択したキーワードを削除しますか？");
    if (!confirmed) {
      return;
    }

    try {
      const response = await callPy("delete_keyword", { identifier: keywordId });
      handleOperationResponse(response, "キーワードを削除しました");
    } catch (error) {
      handleError(error, "キーワードの削除に失敗しました", {
        context: "delete_keyword",
      });
    }
  });
}

if (seasonForm) {
  seasonForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(seasonForm);
    const name = formData.get("name")?.toString().trim() ?? "";
    if (!name) {
      showNotification("シーズン名を入力してください", 3600);
      return;
    }

    const payload = {
      name,
      notes: formData.get("notes")?.toString().trim() ?? "",
      start_date: formData.get("start_date")?.toString() ?? "",
      start_time: formData.get("start_time")?.toString() ?? "",
      end_date: formData.get("end_date")?.toString() ?? "",
      end_time: formData.get("end_time")?.toString() ?? "",
      rank_statistics_target: formData.has("rank_statistics_target"),
    };

    try {
      const response = await callPy("register_season", payload);
      if (handleOperationResponse(response, "シーズンを登録しました")) {
        seasonForm.reset();
      }
    } catch (error) {
      handleError(error, "シーズンの登録に失敗しました", {
        context: "register_season",
      });
    }
  });
}

if (seasonTableBody) {
  seasonTableBody.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-action='delete-season']");
    if (!button) {
      return;
    }

    const seasonName = button.dataset.seasonName;
    if (!seasonName) {
      return;
    }

    const confirmed = window.confirm(
      `シーズン「${seasonName}」を削除しますか？`
    );
    if (!confirmed) {
      return;
    }

    try {
      const response = await callPy("delete_season", { name: seasonName });
      handleOperationResponse(response, "シーズンを削除しました");
    } catch (error) {
      handleError(error, "シーズンの削除に失敗しました", {
        context: "delete_season",
      });
    }
  });
}

matchStartForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const deckName = matchStartSelect.value.trim();
  if (!deckName) {
    showNotification("使用するデッキを選択してください", 3600);
    return;
  }
  const seasonId = matchStartSeasonSelect?.value?.trim() ?? "";
  const seasonName = seasonId
    ? matchStartSeasonSelect?.selectedOptions?.[0]?.textContent?.trim() ?? ""
    : "";
  await beginMatchEntry(deckName, {
    pushHistory: true,
    seasonId,
    seasonName,
  });
});

if (deckAnalysisFilter) {
  deckAnalysisFilter.addEventListener("change", (event) => {
    const value = event.target?.value ?? SEASON_FILTER_ALL;
    deckAnalysisFilterValue = ensureValidSeasonFilter(
      value,
      latestSnapshot?.seasons ?? []
    );
    updateDeckAnalysisView();
  });
}

if (opponentAnalysisFilter) {
  opponentAnalysisFilter.addEventListener("change", (event) => {
    const value = event.target?.value ?? SEASON_FILTER_ALL;
    opponentAnalysisFilterValue = ensureValidSeasonFilter(
      value,
      latestSnapshot?.seasons ?? []
    );
    updateOpponentAnalysisView();
  });
}

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
  const selectedKeywords = parseKeywordInputValue(matchKeywordsInput);
  const memo = formData.get("memo")?.toString() ?? "";

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
    keywords: selectedKeywords,
    result: Number.parseInt(resultValue.toString(), 10),
    memo,
  };
  if (matchEntryState.seasonId) {
    payload.season_id = matchEntryState.seasonId;
  }
  if (matchEntryState.seasonName) {
    payload.season_name = matchEntryState.seasonName;
  }

  try {
    const response = await callPy("register_match", payload);
    if (handleOperationResponse(response, "対戦情報を登録しました")) {
      await beginMatchEntry(matchEntryState.deckName, {
        pushHistory: false,
        seasonId: matchEntryState.seasonId,
        seasonName: matchEntryState.seasonName,
      });
    }
  } catch (error) {
    handleError(error, "対戦情報の登録に失敗しました", { context: "register_match" });
  }
});

refreshButton.addEventListener("click", () => fetchSnapshot({ silent: false }));

if (matchListTableBody) {
  matchListTableBody.addEventListener("click", async (event) => {
    const detailButton = event.target.closest(
      "[data-action='view-match-detail']"
    );
    if (detailButton) {
      const matchId = Number.parseInt(detailButton.dataset.matchId ?? "", 10);
      if (!Number.isInteger(matchId) || matchId <= 0) {
        showNotification("対戦情報が見つかりません", 3600);
        return;
      }
      await showMatchDetail(matchId, { pushHistory: true, navigate: true });
      return;
    }

    const deleteButton = event.target.closest("[data-action='delete-match']");
    if (deleteButton) {
      const matchId = Number.parseInt(deleteButton.dataset.matchId ?? "", 10);
      if (!Number.isInteger(matchId) || matchId <= 0) {
        showNotification("対戦情報が見つかりません", 3600);
        return;
      }
      const confirmed = window.confirm(
        "選択した対戦情報を削除しますか？この操作は取り消せません。"
      );
      if (!confirmed) {
        return;
      }
      try {
        const response = await callPy("delete_match", { id: matchId });
        handleOperationResponse(response, "対戦情報を削除しました");
      } catch (error) {
        handleError(error, "対戦情報の削除に失敗しました", {
          context: "delete_match",
        });
      }
    }
  });
}

if (matchDetailEditButton) {
  matchDetailEditButton.addEventListener("click", () => {
    openMatchEditView();
  });
}

if (matchDetailYoutubeSaveButton) {
  matchDetailYoutubeSaveButton.addEventListener("click", async () => {
    if (!currentMatchDetail) {
      showNotification("対戦情報が選択されていません", 3600);
      return;
    }
    if (!hasEel) {
      showNotification("YouTube URL の更新は現在利用できません", 4200);
      return;
    }
    const url = matchDetailYoutubeInputEl?.value.trim() ?? "";
    const originalLabel = matchDetailYoutubeSaveButton.textContent;
    matchDetailYoutubeSaveButton.disabled = true;
    matchDetailYoutubeSaveButton.textContent = "保存中...";
    try {
      const response = await callPy("set_youtube_url", {
        id: currentMatchDetail.id,
        url,
      });
      if (handleOperationResponse(response, "YouTube URL を更新しました")) {
        await showMatchDetail(currentMatchDetail.id, { pushHistory: false, navigate: false });
      }
    } catch (error) {
      handleError(error, "YouTube URL の更新に失敗しました", {
        context: "set_youtube_url",
      });
    } finally {
      matchDetailYoutubeSaveButton.disabled = false;
      matchDetailYoutubeSaveButton.textContent = originalLabel;
    }
  });
}

if (matchDetailYoutubeRetryButton) {
  matchDetailYoutubeRetryButton.addEventListener("click", async () => {
    if (!currentMatchDetail) {
      showNotification("対戦情報が選択されていません", 3600);
      return;
    }
    if (!hasEel) {
      showNotification("YouTube 再試行は現在利用できません", 4200);
      return;
    }
    const recordingPath = matchDetailRecordingPathInput?.value.trim() ?? "";
    const originalLabel = matchDetailYoutubeRetryButton.textContent;
    matchDetailYoutubeRetryButton.disabled = true;
    matchDetailYoutubeRetryButton.textContent = "再試行中...";
    try {
      const response = await callPy("retry_youtube_upload", {
        id: currentMatchDetail.id,
        recording_path: recordingPath,
      });
      if (handleOperationResponse(response, "YouTube アップロードを再試行しました")) {
        if (matchDetailRecordingPathInput) {
          matchDetailRecordingPathInput.value = "";
        }
        await showMatchDetail(currentMatchDetail.id, { pushHistory: false, navigate: false });
      }
    } catch (error) {
      handleError(error, "YouTube アップロードの再試行に失敗しました", {
        context: "retry_youtube_upload",
      });
    } finally {
      matchDetailYoutubeRetryButton.disabled = false;
      matchDetailYoutubeRetryButton.textContent = originalLabel;
    }
  });
}

if (settingsBackupExportButton) {
  settingsBackupExportButton.addEventListener("click", async () => {
    if (!hasEel) {
      showNotification("バックアップ機能は現在利用できません", 4200);
      return;
    }

    const originalLabel = settingsBackupExportButton.textContent;
    settingsBackupExportButton.disabled = true;
    settingsBackupExportButton.textContent = "出力中...";

    try {
      const response = await callPy("export_backup_archive");
      if (!response || response.ok !== true) {
        const message = response?.error || "バックアップの出力に失敗しました";
        showNotification(message, 4200);
        if (settingsImportStatusEl) {
          settingsImportStatusEl.textContent = `バックアップ出力失敗：${message}`;
        }
        return;
      }

      if (response.snapshot) {
        applySnapshot(response.snapshot);
      }

      const archive = response.data || {};
      if (!archive.content) {
        showNotification("バックアップデータの生成に失敗しました", 4200);
        if (settingsImportStatusEl) {
          settingsImportStatusEl.textContent = "バックアップ出力失敗：生成エラー";
        }
        return;
      }

      const blob = base64ToBlob(archive.content, "application/zip");
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = archive.filename || `dpl-backup-${Date.now()}.zip`;
      document.body.appendChild(anchor);
      anchor.click();
      document.body.removeChild(anchor);
      window.setTimeout(() => URL.revokeObjectURL(url), 0);

      if (settingsImportStatusEl) {
        const generatedAt = archive.generated_at
          ? `（${formatDateTime(archive.generated_at)}）`
          : "";
        settingsImportStatusEl.textContent = `バックアップを出力しました${generatedAt}`;
      }

      showNotification("バックアップファイルをダウンロードしました");
    } catch (error) {
      handleError(error, "バックアップの出力に失敗しました", {
        context: "export_backup_archive",
      });
      if (settingsImportStatusEl) {
        settingsImportStatusEl.textContent = "バックアップ出力失敗：予期しないエラー";
      }
    } finally {
      settingsBackupExportButton.disabled = false;
      settingsBackupExportButton.textContent = originalLabel;
    }
  });
}

if (settingsBackupImportInput) {
  settingsBackupImportInput.addEventListener("change", async (event) => {
    if (!hasEel) {
      showNotification("バックアップ機能は現在利用できません", 4200);
      return;
    }

    const input = event.currentTarget;
    const file = input?.files?.[0];
    if (!file) {
      return;
    }

    if (settingsImportStatusEl) {
      settingsImportStatusEl.textContent = `インポート準備中：${file.name}`;
    }

    try {
      const buffer = await file.arrayBuffer();
      const content = arrayBufferToBase64(buffer);
      const response = await callPy("import_backup_archive", {
        content,
        filename: file.name,
      });

      if (!response || response.ok !== true) {
        const message = response?.error || "バックアップの取り込みに失敗しました";
        showNotification(message, 4200);
        if (settingsImportStatusEl) {
          settingsImportStatusEl.textContent = `インポート失敗：${message}`;
        }
        return;
      }

      if (response.snapshot) {
        applySnapshot(response.snapshot);
      }

      if (settingsImportStatusEl) {
        settingsImportStatusEl.textContent = `バックアップを取り込みました：${file.name}`;
      }

      showNotification("バックアップデータを取り込みました");
    } catch (error) {
      handleError(error, "バックアップの取り込みに失敗しました", {
        context: "import_backup_archive",
      });
      if (settingsImportStatusEl) {
        settingsImportStatusEl.textContent = "インポート失敗：予期しないエラー";
      }
    } finally {
      if (input) {
        input.value = "";
      } else if (event.target && typeof event.target.value === "string") {
        event.target.value = "";
      }
    }
  });
}

if (settingsResetButton) {
  settingsResetButton.addEventListener("click", async () => {
    if (!hasEel) {
      showNotification("初期化機能は現在利用できません", 4200);
      return;
    }

    const confirmed = window.confirm(
      "データベースを初期化しますか？事前にバックアップを取得することを強く推奨します。"
    );
    if (!confirmed) {
      return;
    }

    try {
      const response = await callPy("reset_database");
      const success = handleOperationResponse(
        response,
        "データベースを初期化しました"
      );
      if (success && settingsImportStatusEl) {
        settingsImportStatusEl.textContent = "インポート待機中";
      }
    } catch (error) {
      handleError(error, "データベースの初期化に失敗しました", {
        context: "reset_database",
      });
      if (settingsImportStatusEl) {
        settingsImportStatusEl.textContent = "初期化失敗";
      }
    }
  });
}

if (matchEditForm) {
  matchEditForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const matchId = Number.parseInt(matchEditForm.dataset.matchId ?? "", 10);
    if (!Number.isInteger(matchId) || matchId <= 0) {
      showNotification("更新対象の対戦情報が見つかりません", 4200);
      return;
    }

    const formData = new FormData(matchEditForm);
    const deckNameRaw = formData.get("deck_name")?.toString() ?? "";
    const deckName = validateRequired(deckNameRaw, "使用デッキ");
    if (deckName === null) {
      return;
    }
    const matchNoValue = formData.get("match_no")?.toString().trim() ?? "";
    const turnValue = formData.get("turn")?.toString() ?? "";
    const opponentDeck = formData.get("opponent_deck")?.toString().trim() ?? "";
    const resultValue = formData.get("result")?.toString() ?? "";
    const youtubeUrl = formData.get("youtube_url")?.toString().trim() ?? "";
    const favorite = formData.get("favorite") === "on";
    const seasonIdValue = formData.get("season_id")?.toString().trim() ?? "";
    const keywords = parseKeywordInputValue(matchEditKeywordsInput);
    const memo = formData.get("memo")?.toString() ?? "";

    const matchNo = Number.parseInt(matchNoValue, 10);
    if (!Number.isInteger(matchNo) || matchNo <= 0) {
      showNotification("対戦番号には 1 以上の数値を入力してください", 4200);
      return;
    }

    if (!turnValue) {
      showNotification("先攻/後攻を選択してください", 3600);
      return;
    }

    const opponentName = validateRequired(opponentDeck, "対戦相手デッキ");
    if (opponentName === null) {
      return;
    }

    if (!resultValue) {
      showNotification("勝敗を選択してください", 3600);
      return;
    }

    const payload = {
      id: matchId,
      deck_name: deckName,
      match_no: matchNo,
      turn: turnValue === "first",
      opponent_deck: opponentName,
      keywords,
      result: Number.parseInt(resultValue, 10),
      youtube_url: youtubeUrl,
      favorite,
      season_id: seasonIdValue,
      memo,
    };

    try {
      const response = await callPy("update_match", payload);
      if (handleOperationResponse(response, "対戦情報を更新しました")) {
        await showMatchDetail(matchId, { pushHistory: false, navigate: false });
        goBack();
      }
    } catch (error) {
      handleError(error, "対戦情報の更新に失敗しました", {
        context: "update_match",
      });
    }
  });
}

registerNavigationHandlers();

window.addEventListener("DOMContentLoaded", () => {
  initialiseMatchEntryClock();
  fetchSnapshot({ silent: true });
});
