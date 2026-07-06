const state = {
  data: null,
  history: [],
  activeList: "hot_popularity",
  search: "",
  watchList: JSON.parse(localStorage.getItem("marketRadar.watchList") || "[]"),
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

function renderBrief(data) {
  const m = deriveMarket(data);
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
  const themes = deriveMarket(data).themes.slice(0, 6);
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
  const m = deriveMarket(data);
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
  const m = deriveMarket(data);
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
  const m = deriveMarket(state.data);
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
    showToast("Agent 已回复");
  } catch (error) {
    pending.querySelector("p").textContent = error.message;
    showToast("Agent 回复失败");
  } finally {
    els.agentChatSend.disabled = false;
  }
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
    showToast("Agent 复盘已生成");
  } catch (error) {
    els.agentOutput.textContent = error.message;
    showToast("Agent 复盘未生成");
  } finally {
    els.runAgentBtn.disabled = false;
  }
}

async function loadRadar() {
  els.dataStatus.textContent = "读取中";
  els.dataStatus.className = "status-pill";
  try {
    const res = await fetch("/api/radar");
    if (!res.ok) throw new Error(`读取失败：${res.status}`);
    state.data = await res.json();
    await loadHistory();
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

els.watchForm.addEventListener("submit", (event) => {
  event.preventDefault();
  state.watchList = els.watchInput.value
    .split(/[,，、\s]+/)
    .map((item) => item.trim())
    .filter(Boolean);
  localStorage.setItem("marketRadar.watchList", JSON.stringify(state.watchList));
  renderWatchList();
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
loadAgentStatus();
loadRadar();
