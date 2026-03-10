const API_PREFIX = window.__VIDSCRIBE_CONFIG__?.apiPrefix ?? "/v1";
const STORAGE_KEYS = {
  history: "vidscribe.history.v1",
  drafts: "vidscribe.drafts.v1",
};

const state = {
  currentResult: null,
  currentJobDetail: null,
  pollTimer: null,
  toastTimer: null,
};

const statusText = document.getElementById("status-text");
const toast = document.getElementById("toast");
const probeCard = document.getElementById("probe-result");
const probeContent = document.getElementById("probe-result-content");
const resultMeta = document.getElementById("result-meta");
const resultSummary = document.getElementById("result-summary");
const resultCover = document.getElementById("result-cover");
const resultSource = document.getElementById("result-source");
const resultArticle = document.getElementById("result-article");
const resultTitles = document.getElementById("result-titles");
const resultOutline = document.getElementById("result-outline");
const resultHighlights = document.getElementById("result-highlights");
const resultTags = document.getElementById("result-tags");
const jobSteps = document.getElementById("job-steps");
const jobType = document.getElementById("job-type");
const jobIdInput = document.getElementById("job-id-input");
const historyList = document.getElementById("history-list");
const draftList = document.getElementById("draft-list");
const resultStatusBadge = document.getElementById("result-status-badge");
const overviewInputType = document.getElementById("overview-input-type");
const overviewStatus = document.getElementById("overview-status");
const overviewLanguage = document.getElementById("overview-language");
const overviewDuration = document.getElementById("overview-duration");

function getLocalArray(key) {
  try {
    return JSON.parse(window.localStorage.getItem(key) || "[]");
  } catch {
    return [];
  }
}

function setLocalArray(key, value) {
  window.localStorage.setItem(key, JSON.stringify(value));
}

function setStatus(message, tone = "") {
  statusText.textContent = message;
  statusText.className = tone ? `status-text ${tone}` : "status-text";
}

function showToast(message) {
  toast.textContent = message;
  toast.classList.remove("hidden");
  window.clearTimeout(state.toastTimer);
  state.toastTimer = window.setTimeout(() => {
    toast.classList.add("hidden");
  }, 2200);
}

function escapeHtml(value) {
  return String(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
}

function renderList(target, values) {
  if (!values?.length) {
    target.innerHTML = '<li class="empty">暂无</li>';
    return;
  }
  target.innerHTML = values.map((item) => `<li>${escapeHtml(item)}</li>`).join("");
}

function renderPre(target, payload) {
  target.textContent = payload || "暂无";
}

function updateOverview(payload) {
  overviewInputType.textContent = payload?.input_type || "暂无";
  overviewStatus.textContent = payload?.status || "等待中";
  overviewLanguage.textContent = payload?.source?.language || "zh";
  overviewDuration.textContent = String(payload?.source?.duration_sec ?? 0);
  resultStatusBadge.textContent = payload?.status || "等待结果";
}

function renderResult(payload) {
  state.currentResult = payload;
  updateOverview(payload);
  resultMeta.textContent = JSON.stringify(
    {
      job_id: payload.job_id,
      input_type: payload.input_type,
      status: payload.status,
      source_language: payload.source?.language ?? "zh",
      duration_sec: payload.source?.duration_sec ?? 0,
    },
    null,
    2,
  );
  renderList(resultTitles, payload.title_candidates);
  renderPre(resultSummary, payload.summary);
  renderList(resultOutline, payload.outline);
  renderList(resultHighlights, payload.highlights);
  renderList(resultTags, payload.tags);
  renderPre(resultArticle, payload.article_markdown);
  renderPre(resultCover, JSON.stringify(payload.cover ?? {}, null, 2));
  renderPre(resultSource, JSON.stringify(payload.source ?? {}, null, 2));
}

function clearResultView() {
  state.currentResult = null;
  state.currentJobDetail = null;
  updateOverview(null);
  renderPre(resultMeta, "尚未返回结果。");
  renderPre(resultSummary, "暂无");
  renderPre(resultCover, "暂无");
  renderPre(resultSource, "暂无");
  renderPre(resultArticle, "暂无");
  renderList(resultTitles, []);
  renderList(resultOutline, []);
  renderList(resultHighlights, []);
  renderList(resultTags, []);
  renderSteps(null);
}

function renderSteps(payload) {
  state.currentJobDetail = payload;
  if (!payload?.steps?.length) {
    jobSteps.innerHTML = '<div class="step"><strong>暂无任务</strong><small>提交异步任务后，这里会显示 step_name、状态和错误信息。</small></div>';
    return;
  }
  jobSteps.innerHTML = payload.steps
    .map((step) => {
      const extra = [
        `状态: ${step.status}`,
        step.retry_count ? `重试: ${step.retry_count}` : "",
        step.start_time ? `开始: ${step.start_time}` : "",
        step.end_time ? `结束: ${step.end_time}` : "",
        step.error_message ? `错误: ${step.error_message}` : "",
      ]
        .filter(Boolean)
        .join(" | ");
      return `
        <div class="step">
          <strong>${escapeHtml(step.step_name)}</strong>
          <small>${escapeHtml(extra || "无附加信息")}</small>
        </div>
      `;
    })
    .join("");
}

async function requestJson(url, options = {}) {
  const response = await fetch(url, options);
  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json") ? await response.json() : await response.text();
  if (!response.ok) {
    const detail = typeof payload === "string" ? payload : payload.detail || JSON.stringify(payload);
    throw new Error(detail);
  }
  return payload;
}

function getNumberValue(id) {
  return Number(document.getElementById(id).value || 1200);
}

function getTextValue(id) {
  return document.getElementById(id).value.trim();
}

function setTextValue(id, value) {
  document.getElementById(id).value = value ?? "";
}

function getCurrentFormSnapshot() {
  return {
    activeView: document.querySelector(".tab.active")?.dataset.viewTarget ?? "text-view",
    rawText: getTextValue("raw-text"),
    textLength: getNumberValue("text-length"),
    textLanguage: getTextValue("text-language"),
    remoteUrl: getTextValue("remote-url"),
    remoteFallback: getTextValue("remote-fallback"),
    remoteLength: getNumberValue("remote-length"),
    remoteLanguage: getTextValue("remote-language"),
    jobType: jobType.value,
    jobLength: getNumberValue("job-length"),
    jobLanguage: getTextValue("job-language"),
    jobRawText: getTextValue("job-raw-text"),
    jobBilibiliUrl: getTextValue("job-bilibili-url"),
    jobDouyinUrl: getTextValue("job-douyin-url"),
    jobUploadedVideoPath: getTextValue("job-uploaded-video-path"),
    jobFallback: getTextValue("job-fallback"),
    jobId: getTextValue("job-id-input"),
  };
}

function applyDraft(snapshot) {
  setTextValue("raw-text", snapshot.rawText);
  setTextValue("text-length", snapshot.textLength);
  setTextValue("text-language", snapshot.textLanguage);
  setTextValue("remote-url", snapshot.remoteUrl);
  setTextValue("remote-fallback", snapshot.remoteFallback);
  setTextValue("remote-length", snapshot.remoteLength);
  setTextValue("remote-language", snapshot.remoteLanguage);
  jobType.value = snapshot.jobType || "raw_text";
  setTextValue("job-length", snapshot.jobLength);
  setTextValue("job-language", snapshot.jobLanguage);
  setTextValue("job-raw-text", snapshot.jobRawText);
  setTextValue("job-bilibili-url", snapshot.jobBilibiliUrl);
  setTextValue("job-douyin-url", snapshot.jobDouyinUrl);
  setTextValue("job-uploaded-video-path", snapshot.jobUploadedVideoPath);
  setTextValue("job-fallback", snapshot.jobFallback);
  setTextValue("job-id-input", snapshot.jobId);
  syncJobFields();
  if (snapshot.activeView) {
    activateView(snapshot.activeView);
  }
}

function buildHistoryEntry(label, result, meta = {}) {
  return {
    id: `${Date.now()}`,
    label,
    createdAt: new Date().toISOString(),
    result,
    meta,
  };
}

function saveHistoryEntry(entry) {
  const history = getLocalArray(STORAGE_KEYS.history);
  history.unshift(entry);
  setLocalArray(STORAGE_KEYS.history, history.slice(0, 8));
  renderHistory();
}

function renderHistory() {
  const history = getLocalArray(STORAGE_KEYS.history);
  if (!history.length) {
    historyList.innerHTML = '<p class="empty-card">还没有最近记录。</p>';
    return;
  }
  historyList.innerHTML = history
    .map(
      (item) => `
        <article class="history-item" data-history-id="${escapeHtml(item.id)}">
          <div class="history-item-head">
            <strong>${escapeHtml(item.label)}</strong>
            <span>${escapeHtml(new Date(item.createdAt).toLocaleString("zh-CN"))}</span>
          </div>
          <p>${escapeHtml(item.result?.summary || item.meta?.status || "无摘要")}</p>
          <div class="history-item-actions">
            <button class="secondary" type="button" data-history-load="${escapeHtml(item.id)}">载入结果</button>
            <button class="ghost" type="button" data-history-delete="${escapeHtml(item.id)}">删除</button>
          </div>
        </article>
      `,
    )
    .join("");
}

function renderDrafts() {
  const drafts = getLocalArray(STORAGE_KEYS.drafts);
  if (!drafts.length) {
    draftList.innerHTML = '<p class="empty-card">还没有保存草稿。</p>';
    return;
  }
  draftList.innerHTML = drafts
    .map(
      (item) => `
        <article class="history-item">
          <div class="history-item-head">
            <strong>${escapeHtml(item.label)}</strong>
            <span>${escapeHtml(new Date(item.createdAt).toLocaleString("zh-CN"))}</span>
          </div>
          <p>${escapeHtml(item.summary)}</p>
          <div class="history-item-actions">
            <button class="secondary" type="button" data-draft-load="${escapeHtml(item.id)}">载入草稿</button>
            <button class="ghost" type="button" data-draft-delete="${escapeHtml(item.id)}">删除</button>
          </div>
        </article>
      `,
    )
    .join("");
}

function saveDraft() {
  const snapshot = getCurrentFormSnapshot();
  const label = snapshot.rawText
    ? `文本草稿 ${new Date().toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" })}`
    : snapshot.remoteUrl || snapshot.jobBilibiliUrl || snapshot.jobDouyinUrl || "未命名草稿";
  const drafts = getLocalArray(STORAGE_KEYS.drafts);
  drafts.unshift({
    id: `${Date.now()}`,
    label,
    createdAt: new Date().toISOString(),
    summary: snapshot.rawText.slice(0, 42) || snapshot.remoteUrl || snapshot.jobType,
    snapshot,
  });
  setLocalArray(STORAGE_KEYS.drafts, drafts.slice(0, 8));
  renderDrafts();
  showToast("草稿已保存到本地浏览器。");
}

function loadHistoryEntry(id) {
  const item = getLocalArray(STORAGE_KEYS.history).find((entry) => entry.id === id);
  if (!item?.result) {
    return;
  }
  renderResult(item.result);
  setStatus(`已载入最近记录：${item.label}`, "success");
  showToast("已载入最近结果。");
}

function loadDraft(id) {
  const item = getLocalArray(STORAGE_KEYS.drafts).find((entry) => entry.id === id);
  if (!item?.snapshot) {
    return;
  }
  applyDraft(item.snapshot);
  setStatus(`已载入草稿：${item.label}`, "success");
  showToast("草稿已恢复到输入区。");
}

function deleteFromStorage(key, id) {
  setLocalArray(
    key,
    getLocalArray(key).filter((entry) => entry.id !== id),
  );
  renderHistory();
  renderDrafts();
}

function downloadText(filename, content, contentType) {
  const blob = new Blob([content], { type: contentType });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

async function copyMarkdown() {
  if (!state.currentResult?.article_markdown) {
    throw new Error("当前没有可复制的 Markdown。");
  }
  await navigator.clipboard.writeText(state.currentResult.article_markdown);
  showToast("Markdown 已复制到剪贴板。");
}

function saveCurrentResult() {
  if (!state.currentResult) {
    throw new Error("当前没有可保存的结果。");
  }
  saveHistoryEntry(
    buildHistoryEntry(
      state.currentResult.title_candidates?.[0] || state.currentResult.input_type || "分析结果",
      state.currentResult,
      { status: state.currentResult.status },
    ),
  );
  showToast("结果已保存到最近记录。");
}

function stopPolling() {
  if (state.pollTimer) {
    clearInterval(state.pollTimer);
    state.pollTimer = null;
  }
}

function syncJobFields() {
  const current = jobType.value;
  document.querySelectorAll(".job-field").forEach((node) => {
    node.classList.toggle("hidden", node.dataset.jobField !== current);
  });
}

function activateView(viewId) {
  document.querySelectorAll("[data-view-target]").forEach((tab) => {
    tab.classList.toggle("active", tab.dataset.viewTarget === viewId);
  });
  document.querySelectorAll(".view").forEach((view) => {
    view.classList.toggle("active", view.id === viewId);
  });
}

function buildJobPayload() {
  const inputType = jobType.value;
  const payload = {
    input_type: inputType,
    desired_length: getNumberValue("job-length"),
    language: getTextValue("job-language") || "zh",
  };
  const fallback = getTextValue("job-fallback");
  if (fallback) {
    payload.raw_text = fallback;
  }
  if (inputType === "raw_text") {
    payload.raw_text = getTextValue("job-raw-text");
  }
  if (inputType === "bilibili_url") {
    payload.bilibili_url = getTextValue("job-bilibili-url");
  }
  if (inputType === "douyin_url") {
    payload.douyin_url = getTextValue("job-douyin-url");
  }
  if (inputType === "uploaded_video") {
    payload.uploaded_video_path = getTextValue("job-uploaded-video-path");
  }
  return payload;
}

async function runTextAnalysis() {
  setStatus("正在分析文本…");
  const payload = {
    raw_text: getTextValue("raw-text"),
    desired_length: getNumberValue("text-length"),
    language: getTextValue("text-language") || "zh",
  };
  const data = await requestJson(`${API_PREFIX}/analyze-text`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  renderResult(data);
  saveHistoryEntry(buildHistoryEntry(data.title_candidates?.[0] || "文本分析结果", data));
  setStatus("文本分析完成。", "success");
  showToast("文本分析完成。");
}

async function probeRemoteUrl() {
  setStatus("正在探测远程链接…");
  const data = await requestJson(`${API_PREFIX}/probe-video-url`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ video_url: getTextValue("remote-url") }),
  });
  probeCard.classList.remove("hidden");
  probeContent.textContent = JSON.stringify(data, null, 2);
  setStatus("链接探测完成。", data.downloadable ? "success" : "error");
  showToast(data.detail || "链接探测完成。");
}

async function runRemoteAnalysis() {
  setStatus("正在同步分析远程视频…");
  const fallback = getTextValue("remote-fallback");
  const payload = {
    video_url: getTextValue("remote-url"),
    raw_text: fallback || null,
    desired_length: getNumberValue("remote-length"),
    language: getTextValue("remote-language") || "zh",
  };
  const data = await requestJson(`${API_PREFIX}/analyze-remote-video`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  renderResult(data);
  saveHistoryEntry(buildHistoryEntry(data.title_candidates?.[0] || "远程视频分析结果", data));
  setStatus("远程视频分析完成。", "success");
  showToast("远程视频分析完成。");
}

async function runUploadAnalysis() {
  const file = document.getElementById("video-file").files[0];
  if (!file) {
    throw new Error("请先选择一个视频文件。");
  }
  setStatus("正在上传并分析视频…");
  const formData = new FormData();
  formData.append("file", file);
  const data = await requestJson(`${API_PREFIX}/analyze-video`, {
    method: "POST",
    body: formData,
  });
  renderResult(data);
  saveHistoryEntry(buildHistoryEntry(data.title_candidates?.[0] || file.name || "视频分析结果", data));
  setStatus("视频上传分析完成。", "success");
  showToast("视频上传分析完成。");
}

async function createJob() {
  setStatus("正在提交异步任务…");
  const data = await requestJson(`${API_PREFIX}/jobs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(buildJobPayload()),
  });
  jobIdInput.value = data.job_id;
  renderPre(resultMeta, JSON.stringify(data, null, 2));
  updateOverview({ status: data.status, input_type: buildJobPayload().input_type, source: { language: "zh", duration_sec: 0 } });
  setStatus(`任务已提交: ${data.job_id}`, "success");
  showToast("异步任务已提交。");
  await refreshJob();
}

async function refreshJob() {
  const jobId = jobIdInput.value.trim();
  if (!jobId) {
    throw new Error("请先提供 job_id。");
  }
  setStatus("正在刷新任务状态…");
  const detail = await requestJson(`${API_PREFIX}/jobs/${jobId}`);
  renderPre(resultMeta, JSON.stringify(detail, null, 2));
  renderSteps(detail);
  updateOverview({ status: detail.status, input_type: detail.input_type, source: { language: "zh", duration_sec: 0 } });
  if (detail.status === "SUCCESS") {
    const result = await requestJson(`${API_PREFIX}/jobs/${jobId}/result`);
    renderResult(result);
    saveHistoryEntry(buildHistoryEntry(result.title_candidates?.[0] || `任务 ${jobId}`, result, { jobId }));
    stopPolling();
    setStatus("任务已完成，结果已加载。", "success");
    showToast("异步任务已完成。");
    return;
  }
  if (detail.status === "FAILED") {
    stopPolling();
    setStatus(detail.error_message || "任务失败。", "error");
    showToast(detail.error_message || "任务失败。");
    return;
  }
  setStatus(`任务状态: ${detail.status}`);
}

async function togglePolling() {
  if (state.pollTimer) {
    stopPolling();
    setStatus("已停止轮询。");
    return;
  }
  await refreshJob();
  state.pollTimer = window.setInterval(() => {
    refreshJob().catch((error) => {
      stopPolling();
      setStatus(error.message, "error");
      showToast(error.message);
    });
  }, 3000);
  setStatus("已开始每 3 秒轮询一次任务状态。");
}

function fillTextDemo() {
  activateView("text-view");
  setTextValue(
    "raw-text",
    "这是一段关于如何把短视频整理成公众号文章的示例文本。核心思路是先提炼观点，再重构结构，最后补足适合阅读的起承转合，让原本零散的视频信息变成可直接发布的文章内容。",
  );
  setTextValue("text-length", 1200);
  setTextValue("text-language", "zh");
  showToast("已填充文本示例。");
}

function fillBilibiliDemo() {
  activateView("remote-view");
  setTextValue("remote-url", "https://www.bilibili.com/video/BV1S5PrzZEzQ");
  setTextValue("remote-fallback", "如果远程视频下载失败，可以使用这段回退文本继续生成内容。");
  setTextValue("remote-length", 1200);
  setTextValue("remote-language", "zh");
  showToast("已填充 B 站示例。");
}

function fillJobDemo() {
  activateView("job-view");
  jobType.value = "raw_text";
  syncJobFields();
  setTextValue(
    "job-raw-text",
    "这是一段用于异步任务测试的文本示例，适合验证 job 提交、状态追踪和结果回填链路是否完整。",
  );
  setTextValue("job-length", 1200);
  setTextValue("job-language", "zh");
  showToast("已填充异步任务示例。");
}

async function runAction(action, buttonId) {
  const button = buttonId ? document.getElementById(buttonId) : null;
  try {
    if (button) {
      button.disabled = true;
    }
    await action();
  } catch (error) {
    stopPolling();
    setStatus(error.message || "请求失败。", "error");
    showToast(error.message || "请求失败。");
  } finally {
    if (button) {
      button.disabled = false;
    }
  }
}

function registerShortcuts() {
  document.addEventListener("keydown", (event) => {
    if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
      const activeView = document.querySelector(".view.active")?.id;
      if (activeView === "text-view") {
        runAction(runTextAnalysis, "run-text");
      }
      if (activeView === "remote-view") {
        runAction(runRemoteAnalysis, "run-remote");
      }
    }
  });
}

function bindHistoryActions() {
  historyList.addEventListener("click", (event) => {
    const loadId = event.target.dataset.historyLoad;
    const deleteId = event.target.dataset.historyDelete;
    if (loadId) {
      loadHistoryEntry(loadId);
    }
    if (deleteId) {
      deleteFromStorage(STORAGE_KEYS.history, deleteId);
    }
  });

  draftList.addEventListener("click", (event) => {
    const loadId = event.target.dataset.draftLoad;
    const deleteId = event.target.dataset.draftDelete;
    if (loadId) {
      loadDraft(loadId);
    }
    if (deleteId) {
      deleteFromStorage(STORAGE_KEYS.drafts, deleteId);
    }
  });
}

document.querySelectorAll("[data-view-target]").forEach((button) => {
  button.addEventListener("click", () => activateView(button.dataset.viewTarget));
});

jobType.addEventListener("change", syncJobFields);
document.getElementById("run-text").addEventListener("click", () => runAction(runTextAnalysis, "run-text"));
document.getElementById("probe-remote").addEventListener("click", () => runAction(probeRemoteUrl, "probe-remote"));
document.getElementById("run-remote").addEventListener("click", () => runAction(runRemoteAnalysis, "run-remote"));
document.getElementById("run-upload").addEventListener("click", () => runAction(runUploadAnalysis, "run-upload"));
document.getElementById("create-job").addEventListener("click", () => runAction(createJob, "create-job"));
document.getElementById("refresh-job").addEventListener("click", () => runAction(refreshJob, "refresh-job"));
document.getElementById("poll-job").addEventListener("click", () => runAction(togglePolling, "poll-job"));
document.getElementById("fill-text-demo").addEventListener("click", fillTextDemo);
document.getElementById("fill-bilibili-demo").addEventListener("click", fillBilibiliDemo);
document.getElementById("fill-job-demo").addEventListener("click", fillJobDemo);
document.getElementById("save-draft").addEventListener("click", saveDraft);
document.getElementById("copy-markdown").addEventListener("click", () => runAction(copyMarkdown));
document.getElementById("download-markdown").addEventListener("click", () => {
  if (!state.currentResult?.article_markdown) {
    showToast("当前没有可下载的 Markdown。");
    return;
  }
  downloadText("vidscribe-article.md", state.currentResult.article_markdown, "text/markdown;charset=utf-8");
});
document.getElementById("download-json").addEventListener("click", () => {
  if (!state.currentResult) {
    showToast("当前没有可下载的 JSON。");
    return;
  }
  downloadText("vidscribe-result.json", JSON.stringify(state.currentResult, null, 2), "application/json;charset=utf-8");
});
document.getElementById("save-result").addEventListener("click", () => runAction(async () => saveCurrentResult()));
document.getElementById("clear-result").addEventListener("click", () => {
  clearResultView();
  setStatus("结果已清空。");
});
document.getElementById("clear-history").addEventListener("click", () => {
  setLocalArray(STORAGE_KEYS.history, []);
  renderHistory();
});
document.getElementById("clear-drafts").addEventListener("click", () => {
  setLocalArray(STORAGE_KEYS.drafts, []);
  renderDrafts();
});

syncJobFields();
clearResultView();
renderHistory();
renderDrafts();
bindHistoryActions();
registerShortcuts();
