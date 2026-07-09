const state = {
  data: null,
  history: [],
  signals: null,
  activeList: "hot_popularity",
  search: "",
  watchList: JSON.parse(localStorage.getItem("marketRadar.watchList") || "[]"),
  traces: [],
  selectedTraceId: null,
  traceFilters: {
    query: "",
    task: "",
    execution: "",
    review: "",
    repair: "",
  },
  compareTraceIds: [],
  debugTraces: new URLSearchParams(window.location.search).get("debug") === "1",
};

const THEME_RULES = [
  {
    name: "AI硬件/光通信",
    words: ["中际旭创", "新易盛", "天孚通信", "亨通光电", "中天科技", "长飞光纤", "光通信", "光模块", "CPO", "NPO", "算力", "Token", "AI"],
  },
  {
    name: "PCB/电子材料",
    words: ["胜宏科技", "沪电股份", "东山精密", "生益科技", "宏和科", "沃格光电", "国瓷材料", "风华高科", "MLCC", "电容", "电子材料", "玻纤"],
  },
  {
    name: "锂矿/新能源",
    words: ["赣锋锂业", "盛新锂能", "天齐锂业", "比亚迪", "宁德时代", "锂", "锂电池", "新能源"],
  },
  {
    name: "半导体/存储",
    words: ["兆易创新", "美光科技", "TCL中环", "半导体", "存储", "硅片", "芯片"],
  },
  {
    name: "消费白马",
    words: ["五粮液", "贵州茅台", "伊利", "白酒", "消费", "蓝筹", "分红"],
  },
  {
    name: "资源/周期",
    words: ["中国石油", "紫金矿业", "黄金", "铜", "油气", "原油", "集运", "煤炭"],
  },
];

const els = {
  dataStatus: document.querySelector("#dataStatus"),
  refreshBtn: document.querySelector("#refreshBtn"),
  marketTone: document.querySelector("#marketTone"),
  marketSummary: document.querySelector("#marketSummary"),
  sentimentScore: document.querySelector("#sentimentScore"),
  themeCount: document.querySelector("#themeCount"),
  crowdingLevel: document.querySelector("#crowdingLevel"),
  generatedAt: document.querySelector("#generatedAt"),
  historyCount: document.querySelector("#historyCount"),
  indexGrid: document.querySelector("#indexGrid"),
  trendList: document.querySelector("#trendList"),
  recapBox: document.querySelector("#recapBox"),
  runAgentBtn: document.querySelector("#runAgentBtn"),
  agentOutput: document.querySelector("#agentOutput"),
  themeList: document.querySelector("#themeList"),
  explainList: document.querySelector("#explainList"),
  stockTableBody: document.querySelector("#stockTableBody"),
  stockSearch: document.querySelector("#stockSearch"),
  postList: document.querySelector("#postList"),
  watchForm: document.querySelector("#watchForm"),
  watchInput: document.querySelector("#watchInput"),
  watchResults: document.querySelector("#watchResults"),
  copySummaryBtn: document.querySelector("#copySummaryBtn"),
  copyRecapBtn: document.querySelector("#copyRecapBtn"),
  agentChatForm: document.querySelector("#agentChatForm"),
  agentChatInput: document.querySelector("#agentChatInput"),
  agentChatSend: document.querySelector("#agentChatSend"),
  chatMessages: document.querySelector("#chatMessages"),
  agentEvidence: document.querySelector("#agentEvidence"),
  agentNextWatch: document.querySelector("#agentNextWatch"),
  agentTrace: document.querySelector("#agentTrace"),
  refreshTracesBtn: document.querySelector("#refreshTracesBtn"),
  tracePanel: document.querySelector("#tracePanel"),
  traceSearch: document.querySelector("#traceSearch"),
  traceTaskFilter: document.querySelector("#traceTaskFilter"),
  traceExecutionFilter: document.querySelector("#traceExecutionFilter"),
  traceReviewFilter: document.querySelector("#traceReviewFilter"),
  traceRepairFilter: document.querySelector("#traceRepairFilter"),
  clearTraceCompareBtn: document.querySelector("#clearTraceCompareBtn"),
  traceList: document.querySelector("#traceList"),
  traceDetail: document.querySelector("#traceDetail"),
  traceCompare: document.querySelector("#traceCompare"),
};

function formatPct(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "--";
  const n = Number(value);
  return `${n > 0 ? "+" : ""}${n.toFixed(2)}%`;
}

function formatNumber(value, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "--";
  return Number(value).toLocaleString("zh-CN", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

function formatMoney(value) {
  if (!value) return "--";
  const yi = Number(value) / 100000000;
  if (yi >= 10000) return `${(yi / 10000).toFixed(2)}万亿`;
  return `${yi.toFixed(0)}亿`;
}

function pctClass(value) {
  const n = Number(value || 0);
  if (n > 0) return "up";
  if (n < 0) return "down";
  return "flat";
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function classifyText(text) {
  const source = String(text || "").toLowerCase();
  const found = THEME_RULES.find((rule) =>
    rule.words.some((word) => source.includes(word.toLowerCase())),
  );
  return found ? found.name : "其他";
}

function allHotStocks(data) {
  return [...(data.hot_popularity || []), ...(data.hot_watchlist || [])];
}

function uniqueBySymbol(stocks) {
  const seen = new Map();
  for (const stock of stocks) {
    if (!seen.has(stock.symbol)) seen.set(stock.symbol, stock);
  }
  return [...seen.values()];
}

function getThemeStats(data) {
  const stats = new Map();
  const bump = (name, stock, post) => {
    if (!stats.has(name)) stats.set(name, { name, score: 0, stocks: new Set(), posts: 0 });
    const item = stats.get(name);
    item.score += 1;
    if (stock) item.stocks.add(stock);
    if (post) item.posts += 1;
  };

  for (const stock of allHotStocks(data)) {
    const theme = classifyText(`${stock.name} ${stock.symbol}`);
    bump(theme, stock.name, false);
  }
  for (const post of data.hot_posts || []) {
    const theme = classifyText(`${post.title} ${post.text}`);
    bump(theme, null, true);
  }

  return [...stats.values()]
    .filter((item) => item.name !== "其他")
    .map((item) => ({ ...item, stocks: [...item.stocks] }))
    .sort((a, b) => b.score - a.score);
}

function deriveMarket(data) {
  const indices = data.indices || [];
  const byLabel = Object.fromEntries(indices.map((item) => [item.label || item.name, item]));
  const avg = (labels) => {
    const values = labels.map((label) => Number(byLabel[label]?.percent)).filter(Number.isFinite);
    return values.length ? values.reduce((a, b) => a + b, 0) / values.length : 0;
  };
  const growthAvg = avg(["深证成指", "创业板指", "科创50"]);
  const broadAvg = avg(["上证指数", "沪深300", "中证500"]);
  const positiveCount = indices.filter((item) => Number(item.percent) > 0).length;
  const avgPct = indices.reduce((sum, item) => sum + Number(item.percent || 0), 0) / Math.max(indices.length, 1);
  const popularitySymbols = new Set((data.hot_popularity || []).map((item) => item.symbol));
  const duplicateCount = (data.hot_watchlist || []).filter((item) => popularitySymbols.has(item.symbol)).length;
  const limitLikeCount = uniqueBySymbol(allHotStocks(data)).filter((item) => Number(item.percent) >= 9.8).length;
  const themes = getThemeStats(data);

  let tone = "结构分化";
  if (positiveCount === indices.length && growthAvg > broadAvg + 1) tone = "成长进攻";
  else if (positiveCount === indices.length && broadAvg >= growthAvg) tone = "权重修复";
  else if (positiveCount >= 4 && avgPct > 0) tone = "震荡偏强";
  else if (positiveCount <= 2) tone = "风险降温";

  const score = clamp(
    Math.round(positiveCount * 9 + avgPct * 10 + limitLikeCount * 3 + duplicateCount * 1.5),
    0,
    100,
  );
  const crowding = duplicateCount >= 16 ? "高" : duplicateCount >= 10 ? "中" : "低";
  return { tone, growthAvg, broadAvg, positiveCount, avgPct, duplicateCount, limitLikeCount, score, crowding, themes };
}

function normalizeSignals(signals) {
  if (!signals) return null;
  return {
    tone: signals.tone,
    growthAvg: signals.growth_avg,
    broadAvg: signals.broad_avg,
    positiveCount: signals.positive_count,
    avgPct: signals.avg_pct,
    duplicateCount: signals.duplicate_count,
    limitLikeCount: signals.limit_like_count,
    score: signals.sentiment_score,
    crowding: signals.crowding,
    themes: signals.themes || [],
  };
}

function currentMarket(data) {
  return normalizeSignals(state.signals) || deriveMarket(data);
}

function renderBrief(data) {
  const m = currentMarket(data);
  const topThemes = m.themes.slice(0, 3).map((item) => item.name).join("、") || "暂无明确主线";
  els.marketTone.textContent = m.tone;
  els.marketSummary.textContent =
    `${data.indices.length} 个核心指数中 ${m.positiveCount} 个上涨。` +
    `成长侧均值 ${formatPct(m.growthAvg)}，宽基侧均值 ${formatPct(m.broadAvg)}。` +
    `当前讨论集中在 ${topThemes}。`;
  els.sentimentScore.textContent = m.score;
  els.themeCount.textContent = m.themes.length;
  els.crowdingLevel.textContent = m.crowding;
  els.generatedAt.textContent = `更新：${data.generated_at || "--"}`;
}

function renderIndices(data) {
  const maxAbs = Math.max(...(data.indices || []).map((item) => Math.abs(Number(item.percent || 0))), 1);
  els.indexGrid.innerHTML = (data.indices || [])
    .map((item) => {
      const pct = Number(item.percent || 0);
      const width = clamp((Math.abs(pct) / maxAbs) * 100, 4, 100);
      return `
        <article class="index-card">
          <header>
            <h3>${item.label || item.name}</h3>
            <span class="symbol">${item.symbol}</span>
          </header>
          <div class="price">${formatNumber(item.current)}</div>
          <span class="change ${pctClass(pct)}">${formatPct(pct)}</span>
          <div class="bar-track"><div class="bar-fill ${pct >= 0 ? "hot" : "cool"}" style="width:${width}%"></div></div>
          <div class="card-foot">
            <span>成交额 ${formatMoney(item.amount)}</span>
            <span>换手 ${formatPct(item.turnover_rate)}</span>
          </div>
        </article>
      `;
    })
    .join("");
}

function renderThemes(data) {
  const themes = currentMarket(data).themes.slice(0, 6);
  if (!themes.length) {
    els.themeList.innerHTML = `<div class="theme-row"><p>暂未识别出足够集中的主题。</p></div>`;
    return;
  }
  const maxScore = Math.max(...themes.map((item) => item.score), 1);
  els.themeList.innerHTML = themes
    .map((item) => `
      <div class="theme-row">
        <div class="theme-top">
          <strong>${item.name}</strong>
          <span>${item.score} 个信号 · ${item.posts} 篇热帖</span>
        </div>
        <div class="bar-track"><div class="bar-fill" style="width:${(item.score / maxScore) * 100}%"></div></div>
        <p>${item.stocks.slice(0, 6).join("、") || "主要来自热帖讨论"}</p>
      </div>
    `)
    .join("");
}

function renderExplain(data) {
  const m = currentMarket(data);
  const topTheme = m.themes[0]?.name || "暂无明确主线";
  const strongestIndex = [...(data.indices || [])].sort((a, b) => Number(b.percent || 0) - Number(a.percent || 0))[0];
  const weakestIndex = [...(data.indices || [])].sort((a, b) => Number(a.percent || 0) - Number(b.percent || 0))[0];
  const rows = [
    ["市场风格", `${strongestIndex?.label || "--"} 领涨，${weakestIndex?.label || "--"} 相对较弱，说明今天更偏 ${m.tone}。`],
    ["主线", `${topTheme} 是最密集的热度来源，先观察它是否扩散到更多股票。`],
    ["情绪", `热榜中接近涨停的股票有 ${m.limitLikeCount} 只，情绪分 ${m.score}/100。`],
    ["风险", `人气榜和关注榜重合 ${m.duplicateCount} 只，拥挤度为 ${m.crowding}，重合度越高越要留意分化。`],
  ];
  els.explainList.innerHTML = rows
    .map(([label, text]) => `
      <div class="explain-row">
        <strong>${label}</strong>
        <p>${text}</p>
      </div>
    `)
    .join("");
}

function getHistorySeries(label) {
  return state.history
    .map((snapshot) => {
      const item = (snapshot.indices || []).find((index) => index.label === label);
      return item ? Number(item.percent) : null;
    })
    .filter(Number.isFinite);
}

function makeSparkline(values) {
  const width = 320;
  const height = 38;
  if (!values.length) {
    return `<svg class="trend-chart" viewBox="0 0 ${width} ${height}" aria-hidden="true"></svg>`;
  }
  const min = Math.min(...values, 0);
  const max = Math.max(...values, 0);
  const span = max - min || 1;
  const x = (index) => (values.length === 1 ? width : (index / (values.length - 1)) * width);
  const y = (value) => height - ((value - min) / span) * height;
  const points = values.map((value, index) => `${x(index).toFixed(1)},${y(value).toFixed(1)}`);
  const zeroY = y(0).toFixed(1);
  const area = `0,${height} ${points.join(" ")} ${width},${height}`;
  return `
    <svg class="trend-chart" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" aria-hidden="true">
      <polyline class="trend-area" points="${area}"></polyline>
      <line class="trend-zero" x1="0" y1="${zeroY}" x2="${width}" y2="${zeroY}"></line>
      <polyline class="trend-line" points="${points.join(" ")}"></polyline>
    </svg>
  `;
}

function renderTrends(data) {
  const history = state.history.length ? state.history : [{ indices: data.indices, generated_at: data.generated_at }];
  els.historyCount.textContent = `${history.length} 次快照`;
  const rows = (data.indices || []).map((index) => {
    const series = getHistorySeries(index.label || index.name);
    const values = series.length ? series : [Number(index.percent || 0)];
    const first = values[0] || 0;
    const last = values[values.length - 1] || 0;
    const delta = last - first;
    return `
      <div class="trend-row">
        <div class="trend-name">
          <strong>${index.label || index.name}</strong>
          <span>${index.symbol}</span>
        </div>
        ${makeSparkline(values)}
        <div class="trend-change">
          <span class="change ${pctClass(last)}">${formatPct(last)}</span>
          <span>${values.length > 1 ? `较首条 ${formatPct(delta)}` : "等待更多快照"}</span>
        </div>
      </div>
    `;
  });
  els.trendList.innerHTML = rows.join("");
}

function buildRecapText(data) {
  const m = currentMarket(data);
  const sortedIndices = [...(data.indices || [])].sort((a, b) => Number(b.percent || 0) - Number(a.percent || 0));
  const strongest = sortedIndices[0];
  const weakest = sortedIndices[sortedIndices.length - 1];
  const themes = m.themes.slice(0, 4).map((item) => item.name).join("、") || "暂无明确主线";
  const topStocks = uniqueBySymbol(allHotStocks(data))
    .slice(0, 8)
    .map((item) => `${item.name}${formatPct(item.percent)}`)
    .join("、");
  const historyNote = state.history.length > 1
    ? `历史快照已记录 ${state.history.length} 次，可继续观察主线是否延续。`
    : "历史快照刚开始记录，后续多刷新几次会出现更可靠的趋势。";

  return [
    `【市场观察】${data.generated_at || ""}`,
    `今天市场模式偏向「${m.tone}」。${strongest?.label || "--"} 相对最强，涨幅 ${formatPct(strongest?.percent)}；${weakest?.label || "--"} 相对较弱，涨幅 ${formatPct(weakest?.percent)}。`,
    `主线集中在：${themes}。热度股票包括：${topStocks}。`,
    `情绪强度：${m.score}/100；人气榜和关注榜重合 ${m.duplicateCount} 只，拥挤度为「${m.crowding}」。`,
    `风险提示：如果高热度方向不能继续扩散，后续更容易从普涨转向分化；如果宽基指数跟不上成长指数，说明行情仍偏结构性。`,
    `继续跟踪：科创50/创业板相对上证是否继续占优，热榜核心是否从少数股票扩散到同主题更多标的。`,
    historyNote,
    "仅作市场观察，不构成买卖建议。",
  ].join("\n\n");
}

function renderRecap(data) {
  els.recapBox.textContent = buildRecapText(data);
}

function renderStocks() {
  if (!state.data) return;
  const list = state.data[state.activeList] || [];
  const query = state.search.trim().toLowerCase();
  const rows = list
    .map((stock) => ({ ...stock, theme: classifyText(`${stock.name} ${stock.symbol}`) }))
    .filter((stock) => {
      if (!query) return true;
      return `${stock.name} ${stock.symbol} ${stock.theme}`.toLowerCase().includes(query);
    });

  els.stockTableBody.innerHTML = rows
    .map((stock) => `
      <tr>
        <td>#${stock.rank}</td>
        <td>
          <span class="stock-name">
            <strong>${stock.name}</strong>
            <span class="symbol">${stock.symbol}</span>
          </span>
        </td>
        <td><span class="theme-chip">${stock.theme}</span></td>
        <td>${formatNumber(stock.current)}</td>
        <td><span class="change ${pctClass(stock.percent)}">${formatPct(stock.percent)}</span></td>
      </tr>
    `)
    .join("");
}

function renderPosts(data) {
  els.postList.innerHTML = (data.hot_posts || [])
    .slice(0, 8)
    .map((post) => `
      <article class="post-row">
        <strong><a href="${post.url}" target="_blank" rel="noreferrer">${post.title || "无标题"}</a></strong>
        <p>${post.author || "匿名"} · ${post.likes || 0} 赞 · ${classifyText(`${post.title} ${post.text}`)}</p>
      </article>
    `)
    .join("");
}

function renderWatchList() {
  if (!state.data) return;
  els.watchInput.value = state.watchList.join("，");
  if (!state.watchList.length) {
    els.watchResults.innerHTML = `<div class="watch-row"><p>添加自选股后，会显示它是否进入热榜、属于哪条主线、是否被热帖提到。</p></div>`;
    return;
  }
  const stocks = uniqueBySymbol(allHotStocks(state.data));
  const posts = state.data.hot_posts || [];
  els.watchResults.innerHTML = state.watchList
    .map((term) => {
      const q = term.toLowerCase();
      const stock = stocks.find((item) => `${item.name} ${item.symbol}`.toLowerCase().includes(q));
      const mentionedPosts = posts.filter((post) => `${post.title} ${post.text}`.toLowerCase().includes(q));
      if (!stock && !mentionedPosts.length) {
        return `<div class="watch-row"><strong>${term}</strong><p>未进入当前热榜，也未在前 20 篇热帖中明显出现。</p></div>`;
      }
      const theme = stock ? classifyText(`${stock.name} ${stock.symbol}`) : classifyText(`${mentionedPosts[0].title} ${mentionedPosts[0].text}`);
      const desc = stock
        ? `热榜排名 #${stock.rank}，涨跌幅 ${formatPct(stock.percent)}，主题 ${theme}。`
        : `未进热榜，但被 ${mentionedPosts.length} 篇热帖提到，主题 ${theme}。`;
      return `<div class="watch-row"><strong>${stock?.name || term}</strong><p>${desc}</p></div>`;
    })
    .join("");
}

function buildSummaryText() {
  if (!state.data) return "";
  const m = currentMarket(state.data);
  const topThemes = m.themes.slice(0, 4).map((item) => item.name).join("、") || "暂无明确主线";
  const indices = (state.data.indices || [])
    .map((item) => `${item.label}: ${formatNumber(item.current)} (${formatPct(item.percent)})`)
    .join("\n");
  return [
    `A股市场雷达 ${state.data.generated_at || ""}`,
    "",
    indices,
    "",
    `市场模式：${m.tone}`,
    `情绪分：${m.score}/100`,
    `主线：${topThemes}`,
    `风险：热榜重合 ${m.duplicateCount} 只，拥挤度 ${m.crowding}。`,
    "",
    "仅作市场观察，不构成买卖建议。",
  ].join("\n");
}

function renderAll(data) {
  renderBrief(data);
  renderIndices(data);
  renderTrends(data);
  renderRecap(data);
  renderThemes(data);
  renderExplain(data);
  renderStocks();
  renderPosts(data);
  renderWatchList();
}

function escapeHtml(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function prettyJson(value) {
  return escapeHtml(JSON.stringify(value ?? null, null, 2));
}

function appendChatMessage(role, title, content) {
  const item = document.createElement("div");
  item.className = `chat-message ${role}`;
  item.innerHTML = `<strong>${escapeHtml(title)}</strong><p>${escapeHtml(content)}</p>`;
  els.chatMessages.appendChild(item);
  els.chatMessages.scrollTop = els.chatMessages.scrollHeight;
  return item;
}

function renderAgentEvidence(payload) {
  const evidence = payload.evidence || [];
  if (!evidence.length) {
    els.agentEvidence.innerHTML = `<p>暂无证据。</p>`;
  } else {
    els.agentEvidence.innerHTML = evidence
      .map((item) => `
        <div class="evidence-item">
          <strong>${escapeHtml(item.title || item.type)}</strong>
          <p>${escapeHtml(item.summary || "")}</p>
        </div>
      `)
      .join("");
  }
  const nextWatch = payload.next_watch || [];
  els.agentNextWatch.innerHTML = nextWatch.length
    ? `<ul>${nextWatch.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`
    : `<p>暂无观察清单。</p>`;
  els.agentTrace.textContent = payload.trace_id ? `Trace ${payload.trace_id}` : "未生成 trace";
}

async function sendAgentChat(message) {
  appendChatMessage("user", "你", message);
  const pending = appendChatMessage("assistant", "市场观察助手", "分析中...");
  els.agentChatSend.disabled = true;
  try {
    const res = await fetch("/api/agent/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: "local",
        message,
        context: {
          watchlist: state.watchList,
          source: "dashboard",
        },
      }),
    });
    const payload = await res.json();
    if (!res.ok) throw new Error(payload.detail || payload.error || "Agent 回复失败");
    pending.querySelector("p").textContent = payload.content;
    renderAgentEvidence(payload);
    if (state.debugTraces) await loadAgentTraces(payload.trace_id);
    showToast("Agent 已回复");
  } catch (error) {
    pending.querySelector("p").textContent = error.message;
    showToast("Agent 回复失败");
  } finally {
    els.agentChatSend.disabled = false;
  }
}

async function loadAgentMemory() {
  try {
    const res = await fetch("/api/agent/memory");
    if (!res.ok) throw new Error(`Memory 读取失败：${res.status}`);
    const memory = await res.json();
    if ((memory.watchlist || []).length) {
      state.watchList = memory.watchlist;
      localStorage.setItem("marketRadar.watchList", JSON.stringify(state.watchList));
    } else if (state.watchList.length) {
      await saveAgentMemory();
    }
  } catch {
    // LocalStorage remains the offline fallback.
  }
}

async function saveAgentMemory() {
  const res = await fetch("/api/agent/memory", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      user_id: "local",
      watchlist: state.watchList,
    }),
  });
  if (!res.ok) {
    const payload = await res.json().catch(() => ({}));
    throw new Error(payload.detail || payload.error || "Memory 同步失败");
  }
  return res.json();
}

async function loadAgentStatus() {
  try {
    const res = await fetch("/api/agent/status");
    const status = await res.json();
    const runtime = status.runtime || {};
    els.agentOutput.textContent =
      `Agent Runtime 已就绪。Memory: ${runtime.memory ? "on" : "off"}，` +
      `Trace: ${runtime.trace ? "on" : "off"}，Reflection: ${runtime.reflection ? "on" : "off"}。`;
    els.runAgentBtn.disabled = false;
  } catch {
    els.agentOutput.textContent = "无法读取 Agent 状态。";
  }
}

async function runAgentRecap() {
  els.runAgentBtn.disabled = true;
  els.agentOutput.textContent = "Agent 正在生成复盘...";
  try {
    const res = await fetch("/api/agent/briefing", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: "local",
        briefing_type: "close",
        style: "plain_beginner",
        context: {
          watchlist: state.watchList,
          source: "dashboard",
        },
      }),
    });
    const payload = await res.json();
    if (!res.ok) throw new Error(payload.detail || payload.error || "Agent 复盘失败");
    const evidenceText = (payload.evidence || [])
      .slice(0, 3)
      .map((item) => `- ${item.title || item.type}: ${item.summary || ""}`)
      .join("\n");
    els.agentOutput.textContent =
      `${payload.title}\n\n${payload.script}\n\nTrace: ${payload.trace_id}` +
      `${evidenceText ? `\n\n证据链：\n${evidenceText}` : ""}`;
    renderAgentEvidence({
      trace_id: payload.trace_id,
      evidence: payload.evidence,
      next_watch: payload.next_watch,
    });
    if (state.debugTraces) await loadAgentTraces(payload.trace_id);
    showToast("Agent 复盘已生成");
  } catch (error) {
    els.agentOutput.textContent = error.message;
    showToast("Agent 复盘未生成");
  } finally {
    els.runAgentBtn.disabled = false;
  }
}

async function loadAgentTraces(selectTraceId = state.selectedTraceId) {
  if (!state.debugTraces) return;
  if (!els.traceList || !els.traceDetail) return;
  try {
    const params = new URLSearchParams({ limit: "30" });
    if (state.traceFilters.query.trim()) params.set("query", state.traceFilters.query.trim());
    if (state.traceFilters.task) params.set("task_type", state.traceFilters.task);
    if (state.traceFilters.execution) params.set("execution_mode", state.traceFilters.execution);
    if (state.traceFilters.review === "passed") params.set("review_passed", "true");
    if (state.traceFilters.review === "failed") params.set("review_passed", "false");
    if (state.traceFilters.repair === "changed") params.set("repair_changed", "true");
    if (state.traceFilters.repair === "unchanged") params.set("repair_changed", "false");
    const res = await fetch(`/api/agent/traces?${params.toString()}`);
    const payload = await res.json();
    if (!res.ok) throw new Error(payload.detail || payload.error || "Trace 读取失败");
    state.traces = payload.traces || [];
    state.compareTraceIds = state.compareTraceIds.filter((id) => state.traces.some((trace) => trace.trace_id === id));
    syncTraceTaskFilter();
    renderTraceList();
    const targetId = state.traces.some((trace) => trace.trace_id === selectTraceId)
      ? selectTraceId
      : state.traces[0]?.trace_id;
    if (targetId) {
      await selectAgentTrace(targetId);
    } else {
      const hasFilters = Boolean(
        state.traceFilters.query.trim() ||
        state.traceFilters.task ||
        state.traceFilters.execution ||
        state.traceFilters.review ||
        state.traceFilters.repair,
      );
      els.traceDetail.innerHTML = hasFilters
        ? `<div class="trace-empty">当前过滤条件下没有匹配的 trace。</div>`
        : `<div class="trace-empty">还没有 trace。运行一次 Agent 后这里会显示详情。</div>`;
    }
    await renderTraceCompare();
  } catch (error) {
    els.traceList.innerHTML = `<div class="trace-empty">${escapeHtml(error.message)}</div>`;
  }
}

function renderTraceList() {
  if (!state.traces.length) {
    const hasFilters = Boolean(
      state.traceFilters.query.trim() ||
      state.traceFilters.task ||
      state.traceFilters.execution ||
      state.traceFilters.review ||
      state.traceFilters.repair,
    );
    els.traceList.innerHTML = hasFilters
      ? `<div class="trace-empty">没有匹配当前过滤条件的 trace。</div>`
      : `<div class="trace-empty">暂无 trace。</div>`;
    return;
  }
  els.traceList.innerHTML = state.traces
    .map((trace) => {
      const active = trace.trace_id === state.selectedTraceId ? " active" : "";
      const repair = trace.repair_changed ? "已修复" : "未修复";
      const factuality = trace.factuality_status || "--";
      const checked = state.compareTraceIds.includes(trace.trace_id) ? " checked" : "";
      const claimStats = `claims ${trace.claim_binding_count ?? 0}/${trace.unsupported_claim_count ?? 0}/${trace.conflicting_claim_count ?? 0}`;
      const memoryStats = `memory ops ${trace.memory_operation_count ?? 0}`;
      const wikiStats = (trace.wiki_statuses || []).join(", ") || "--";
      return `
        <div class="trace-row${active}">
          <button class="trace-main" data-trace-id="${escapeHtml(trace.trace_id)}" type="button">
            <span class="trace-row-top">
              <strong>${escapeHtml(trace.task_type || "--")}</strong>
              <em>${escapeHtml(trace.execution_mode || "--")}</em>
            </span>
            <span>${escapeHtml(trace.message || "")}</span>
            <span class="trace-row-meta">
              ${escapeHtml(trace.created_at || "--")} · ${escapeHtml(repair)}
            </span>
            <span class="trace-row-meta">
              factuality: ${escapeHtml(factuality)}
            </span>
            <span class="trace-row-meta">
              ${escapeHtml(claimStats)} · ${escapeHtml(memoryStats)} · wiki ${escapeHtml(wikiStats)}
            </span>
          </button>
          <label class="trace-compare-pick">
            <input data-compare-trace-id="${escapeHtml(trace.trace_id)}" type="checkbox"${checked} />
            <span>对比</span>
          </label>
        </div>
      `;
    })
    .join("");
  els.traceList.querySelectorAll("[data-trace-id]").forEach((button) => {
    button.addEventListener("click", () => selectAgentTrace(button.dataset.traceId));
  });
  els.traceList.querySelectorAll("[data-compare-trace-id]").forEach((input) => {
    input.addEventListener("click", (event) => event.stopPropagation());
    input.addEventListener("change", () => toggleTraceCompare(input.dataset.compareTraceId, input.checked));
  });
}

function syncTraceTaskFilter() {
  if (!els.traceTaskFilter) return;
  const tasks = [...new Set(state.traces.map((trace) => trace.task_type).filter(Boolean))].sort();
  const current = state.traceFilters.task;
  const options = current && !tasks.includes(current) ? [...tasks, current].sort() : tasks;
  els.traceTaskFilter.innerHTML =
    `<option value="">全部任务</option>` +
    options.map((task) => `<option value="${escapeHtml(task)}">${escapeHtml(task)}</option>`).join("");
  els.traceTaskFilter.value = current || "";
}

async function toggleTraceCompare(traceId, checked) {
  if (!traceId) return;
  if (checked) {
    state.compareTraceIds = [...state.compareTraceIds.filter((id) => id !== traceId), traceId].slice(-2);
  } else {
    state.compareTraceIds = state.compareTraceIds.filter((id) => id !== traceId);
  }
  renderTraceList();
  await renderTraceCompare();
}

async function renderTraceCompare() {
  if (!els.traceCompare) return;
  if (state.compareTraceIds.length < 2) {
    els.traceCompare.hidden = true;
    els.traceCompare.innerHTML = "";
    return;
  }
  els.traceCompare.hidden = false;
  els.traceCompare.innerHTML = `<div class="trace-empty">读取对比 trace...</div>`;
  try {
    const traces = await Promise.all(state.compareTraceIds.map(fetchTraceDetail));
    els.traceCompare.innerHTML = buildTraceCompareHtml(traces[0], traces[1]);
  } catch (error) {
    els.traceCompare.innerHTML = `<div class="trace-empty">${escapeHtml(error.message)}</div>`;
  }
}

async function fetchTraceDetail(traceId) {
  const res = await fetch(`/api/agent/traces?id=${encodeURIComponent(traceId)}`);
  const trace = await res.json();
  if (!res.ok) throw new Error(trace.detail || trace.error || "Trace 详情读取失败");
  return trace;
}

function buildTraceCompareHtml(left, right) {
  const leftPlan = left.plan || {};
  const rightPlan = right.plan || {};
  const leftExecution = left.execution || {};
  const rightExecution = right.execution || {};
  const leftReview = left.review || {};
  const rightReview = right.review || {};
  const leftRepair = left.repair || {};
  const rightRepair = right.repair || {};
  const leftFactuality = leftReview.factuality || {};
  const rightFactuality = rightReview.factuality || {};
  const rows = [
    ["trace_id", left.trace_id, right.trace_id],
    ["message", left.request?.message, right.request?.message],
    ["task_type", leftPlan.task_type, rightPlan.task_type],
    ["intent", leftPlan.intent, rightPlan.intent],
    ["tools", (leftPlan.required_tools || []).join(", "), (rightPlan.required_tools || []).join(", ")],
    ["knowledge_queries", (leftPlan.knowledge_queries || []).join(" / "), (rightPlan.knowledge_queries || []).join(" / ")],
    ["execution", leftExecution.mode, rightExecution.mode],
    ["llm", [leftExecution.provider, leftExecution.model].filter(Boolean).join(" / "), [rightExecution.provider, rightExecution.model].filter(Boolean).join(" / ")],
    ["review_passed", leftReview.passed, rightReview.passed],
    ["factuality_status", leftFactuality.status, rightFactuality.status],
    ["factuality_coverage", leftFactuality.coverage, rightFactuality.coverage],
    ["factuality_summary", leftFactuality.summary, rightFactuality.summary],
    ["review_issues", (leftReview.issues || []).join(" / "), (rightReview.issues || []).join(" / ")],
    ["repair_changed", leftRepair.changed, rightRepair.changed],
    ["repair_replacements", (leftRepair.replacements || []).map((item) => `${item.source}->${item.target}`).join(" / "), (rightRepair.replacements || []).map((item) => `${item.source}->${item.target}`).join(" / ")],
    ["memory_patch", JSON.stringify(left.memory_patch || {}), JSON.stringify(right.memory_patch || {})],
  ];
  return `
    <div class="trace-compare-head">
      <h3>Trace 对比</h3>
      <span>${escapeHtml(left.trace_id)} ⇄ ${escapeHtml(right.trace_id)}</span>
    </div>
    <div class="trace-compare-table">
      ${rows
        .map(([label, a, b]) => `
          <div class="trace-compare-row${String(a) === String(b) ? "" : " changed"}">
            <strong>${escapeHtml(label)}</strong>
            <span>${escapeHtml(a ?? "--")}</span>
            <span>${escapeHtml(b ?? "--")}</span>
          </div>
        `)
        .join("")}
    </div>
  `;
}

async function selectAgentTrace(traceId) {
  if (!traceId) return;
  state.selectedTraceId = traceId;
  renderTraceList();
  els.traceDetail.innerHTML = `<div class="trace-empty">读取 trace 详情...</div>`;
  try {
    const res = await fetch(`/api/agent/traces?id=${encodeURIComponent(traceId)}`);
    const trace = await res.json();
    if (!res.ok) throw new Error(trace.detail || trace.error || "Trace 详情读取失败");
    renderTraceDetail(trace);
  } catch (error) {
    els.traceDetail.innerHTML = `<div class="trace-empty">${escapeHtml(error.message)}</div>`;
  }
}

function renderTraceDetail(trace) {
  const request = trace.request || {};
  const plan = trace.plan || {};
  const execution = trace.execution || {};
  const review = trace.review || {};
  const repair = trace.repair || {};
  const finalResponse = trace.final_response || {};
  const factuality = review.factuality || {};
  const memoryPatch = trace.memory_patch || {};
  const wikiHits = trace.wiki_hits || [];
  const claimBindingCount = Array.isArray(factuality.claim_bindings) ? factuality.claim_bindings.length : 0;
  const unsupportedClaimCount = Array.isArray(factuality.unsupported_claims) ? factuality.unsupported_claims.length : 0;
  const conflictingClaimCount = Array.isArray(factuality.conflicting_claims) ? factuality.conflicting_claims.length : 0;
  const memoryOperationCount = Array.isArray(memoryPatch.operations) ? memoryPatch.operations.length : 0;
  const wikiStatuses = [...new Set(wikiHits.map((hit) => hit.status).filter(Boolean))];
  const wikiQualities = [...new Set(wikiHits.map((hit) => hit.evidence_quality).filter(Boolean))];
  els.traceDetail.innerHTML = `
    <div class="trace-summary">
      <div><span>Trace</span><strong>${escapeHtml(trace.trace_id)}</strong></div>
      <div><span>任务</span><strong>${escapeHtml(plan.task_type || finalResponse.task_type || "--")}</strong></div>
      <div><span>执行</span><strong>${escapeHtml(execution.mode || "--")}</strong></div>
      <div><span>校验</span><strong>${review.passed ? "通过" : "未通过"}</strong></div>
      <div><span>修复</span><strong>${escapeHtml(factuality.repair_status || repair.mode || (repair.changed ? "changed" : "none"))}</strong></div>
    </div>
    <div class="trace-debug-metrics">
      <div><span>Claim 绑定</span><strong>${escapeHtml(String(claimBindingCount))}</strong></div>
      <div><span>Unsupported</span><strong>${escapeHtml(String(unsupportedClaimCount))}</strong></div>
      <div><span>Conflict</span><strong>${escapeHtml(String(conflictingClaimCount))}</strong></div>
      <div><span>Memory Ops</span><strong>${escapeHtml(String(memoryOperationCount))}</strong></div>
      <div><span>Patch Confidence</span><strong>${escapeHtml(memoryPatch.confidence || "--")}</strong></div>
      <div><span>Wiki Status</span><strong>${escapeHtml(wikiStatuses.join(", ") || "--")}</strong></div>
      <div><span>Wiki Quality</span><strong>${escapeHtml(wikiQualities.join(", ") || "--")}</strong></div>
    </div>
    <div class="trace-section">
      <h3>Factuality</h3>
      <div class="factuality-grid">
        <div class="factuality-card">
          <span>状态</span>
          <strong>${escapeHtml(factuality.status || "--")}</strong>
        </div>
        <div class="factuality-card">
          <span>覆盖率</span>
          <strong>${escapeHtml(factuality.coverage || "--")}</strong>
        </div>
        <div class="factuality-card">
          <span>已检查</span>
          <strong>${escapeHtml(factuality.checked_claims ?? "--")}</strong>
        </div>
        <div class="factuality-card">
          <span>已支持</span>
          <strong>${escapeHtml(factuality.supported_claims ?? "--")}</strong>
        </div>
      </div>
      <p class="trace-note">${escapeHtml(factuality.summary || "暂无 factuality 摘要。")}</p>
      <pre>${prettyJson(factuality)}</pre>
    </div>
    <div class="trace-section">
      <h3>输入</h3>
      <p>${escapeHtml(request.message || "")}</p>
    </div>
    <div class="trace-section">
      <h3>计划</h3>
      <pre>${prettyJson(plan)}</pre>
    </div>
    <div class="trace-section">
      <h3>Execution</h3>
      <pre>${prettyJson(execution)}</pre>
    </div>
    <div class="trace-section">
      <h3>工具结果</h3>
      <pre>${prettyJson(trace.tool_results || [])}</pre>
    </div>
    <div class="trace-section">
      <h3>Wiki 证据</h3>
      <pre>${prettyJson(trace.wiki_hits || [])}</pre>
    </div>
    <div class="trace-section">
      <h3>Review</h3>
      <pre>${prettyJson(review)}</pre>
    </div>
    <div class="trace-section">
      <h3>Repair</h3>
      <pre>${prettyJson(repair)}</pre>
    </div>
    <div class="trace-section">
      <h3>Memory Patch</h3>
      <pre>${prettyJson(memoryPatch)}</pre>
    </div>
    <div class="trace-section">
      <h3>最终回复</h3>
      <p>${escapeHtml(finalResponse.content || "")}</p>
    </div>
  `;
}

async function loadRadar() {
  els.dataStatus.textContent = "读取中";
  els.dataStatus.className = "status-pill";
  try {
    const res = await fetch("/api/radar");
    if (!res.ok) throw new Error(`读取失败：${res.status}`);
    state.data = await res.json();
    await loadHistory();
    await loadSignals();
    els.dataStatus.textContent = "已连接";
    els.dataStatus.className = "status-pill ok";
    renderAll(state.data);
  } catch (error) {
    els.dataStatus.textContent = "未连接";
    els.dataStatus.className = "status-pill warn";
    showToast(error.message);
  }
}

async function refreshRadar() {
  els.refreshBtn.disabled = true;
  els.dataStatus.textContent = "刷新中";
  try {
    const res = await fetch("/api/refresh", { method: "POST" });
    const payload = await res.json();
    if (!res.ok) throw new Error(payload.detail || payload.error || "刷新失败");
    state.data = payload;
    await loadHistory();
    await loadSignals();
    els.dataStatus.textContent = "已更新";
    els.dataStatus.className = "status-pill ok";
    renderAll(state.data);
    showToast("雪球数据已刷新");
  } catch (error) {
    els.dataStatus.textContent = "刷新失败";
    els.dataStatus.className = "status-pill warn";
    showToast(error.message);
  } finally {
    els.refreshBtn.disabled = false;
  }
}

async function loadSignals() {
  try {
    const res = await fetch("/api/signals");
    if (!res.ok) throw new Error(`信号读取失败：${res.status}`);
    const payload = await res.json();
    state.signals = payload.signals || null;
  } catch {
    state.signals = null;
  }
}

async function loadHistory() {
  try {
    const res = await fetch("/api/history");
    if (!res.ok) {
      state.history = state.data ? [{ indices: state.data.indices, generated_at: state.data.generated_at }] : [];
      return;
    }
    state.history = await res.json();
  } catch {
    state.history = state.data ? [{ indices: state.data.indices, generated_at: state.data.generated_at }] : [];
  }
}

function showToast(message) {
  const existing = document.querySelector(".toast");
  if (existing) existing.remove();
  const toast = document.createElement("div");
  toast.className = "toast";
  toast.textContent = message;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 2800);
}

document.querySelectorAll(".segment").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".segment").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    state.activeList = button.dataset.list;
    renderStocks();
  });
});

els.stockSearch.addEventListener("input", (event) => {
  state.search = event.target.value;
  renderStocks();
});

els.watchForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  state.watchList = els.watchInput.value
    .split(/[,，、\s]+/)
    .map((item) => item.trim())
    .filter(Boolean);
  localStorage.setItem("marketRadar.watchList", JSON.stringify(state.watchList));
  renderWatchList();
  try {
    await saveAgentMemory();
    showToast("自选已同步");
  } catch (error) {
    showToast(error.message);
  }
});

els.copySummaryBtn.addEventListener("click", async () => {
  const text = buildSummaryText();
  try {
    await navigator.clipboard.writeText(text);
    showToast("摘要已复制");
  } catch {
    showToast("浏览器未允许复制");
  }
});

els.copyRecapBtn.addEventListener("click", async () => {
  const text = state.data ? buildRecapText(state.data) : "";
  try {
    await navigator.clipboard.writeText(text);
    showToast("复盘已复制");
  } catch {
    showToast("浏览器未允许复制");
  }
});

els.agentChatForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const message = els.agentChatInput.value.trim();
  if (!message) return;
  els.agentChatInput.value = "";
  sendAgentChat(message);
});

els.refreshBtn.addEventListener("click", refreshRadar);
els.runAgentBtn.addEventListener("click", runAgentRecap);
els.refreshTracesBtn.addEventListener("click", () => loadAgentTraces());
els.traceSearch.addEventListener("input", (event) => {
  state.traceFilters.query = event.target.value;
  loadAgentTraces();
});
els.traceTaskFilter.addEventListener("change", (event) => {
  state.traceFilters.task = event.target.value;
  loadAgentTraces();
});
els.traceExecutionFilter.addEventListener("change", (event) => {
  state.traceFilters.execution = event.target.value;
  loadAgentTraces();
});
els.traceReviewFilter.addEventListener("change", (event) => {
  state.traceFilters.review = event.target.value;
  loadAgentTraces();
});
els.traceRepairFilter.addEventListener("change", (event) => {
  state.traceFilters.repair = event.target.value;
  loadAgentTraces();
});
els.clearTraceCompareBtn.addEventListener("click", async () => {
  state.compareTraceIds = [];
  renderTraceList();
  await renderTraceCompare();
});

async function init() {
  if (els.tracePanel) {
    els.tracePanel.hidden = !state.debugTraces;
  }
  await loadAgentStatus();
  await loadAgentMemory();
  await loadRadar();
  if (state.debugTraces) await loadAgentTraces();
}

init();
