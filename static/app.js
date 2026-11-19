const $ = id => document.getElementById(id);
const platform = $("platform"), url = $("url"), analyzeBtn = $("analyzeBtn");
let currentInfo = null;

platform.addEventListener("change", () => {
  const chosen = !!platform.value;
  url.disabled = !chosen;
  analyzeBtn.disabled = !chosen || !url.value.trim();
  url.placeholder = chosen ? "Paste the " + platform.options[platform.selectedIndex].text + " video URL..." : "Choose a platform first...";
  $("result").classList.add("hidden");
  $("status").textContent = "";
});
url.addEventListener("input", () => analyzeBtn.disabled = !platform.value || !url.value.trim());

function setStatus(message, type="") {
  $("status").textContent = message;
  $("status").className = "status " + type;
}
function addHistory(item) {
  const items = JSON.parse(localStorage.getItem("downlyHistory") || "[]");
  items.unshift({...item, time: new Date().toLocaleString()});
  localStorage.setItem("downlyHistory", JSON.stringify(items.slice(0,30)));
  renderHistory();
}
function renderHistory() {
  const items = JSON.parse(localStorage.getItem("downlyHistory") || "[]");
  $("historyList").innerHTML = items.length ? items.map(x =>
    `<div class="history-item"><div><strong>${escapeHtml(x.title)}</strong><small>${escapeHtml(x.platform)} · ${escapeHtml(x.mode)} · ${escapeHtml(x.time)}</small></div><span>✓ Saved</span></div>`
  ).join("") : '<p class="empty">Your download history will appear here on this device.</p>';
}
function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
}

analyzeBtn.addEventListener("click", async () => {
  if (!platform.value || !url.value.trim()) return;
  setStatus("Analyzing link…");
  analyzeBtn.disabled = true;
  try {
    const res = await fetch("/api/extract", {
      method:"POST", headers:{"Content-Type":"application/json"},
      body:JSON.stringify({platform:platform.value, url:url.value.trim()})
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Could not analyze this link.");
    currentInfo = data;
    $("videoTitle").textContent = data.title;
    $("videoMeta").textContent = data.uploader || data.extractor || "Video information loaded";
    $("thumb").src = data.thumbnail || "";
    $("thumb").style.display = data.thumbnail ? "block" : "none";
    $("result").classList.remove("hidden");
    setStatus("Video information loaded successfully.", "success");
  } catch(e) { setStatus(e.message, "error"); }
  finally { analyzeBtn.disabled = !platform.value || !url.value.trim(); }
});

$("mode").addEventListener("change", () => {
  $("qualityWrap").style.display = $("mode").value === "video" ? "block" : "none";
});

$("downloadBtn").addEventListener("click", async () => {
  if (!currentInfo) return;
  const mode = $("mode").value;
  const btn = $("downloadBtn");
  btn.disabled = true; btn.textContent = "Preparing download…";
  setStatus("Preparing your file. Please wait…");
  try {
    const res = await fetch("/api/download", {
      method:"POST", headers:{"Content-Type":"application/json"},
      body:JSON.stringify({platform:platform.value,url:url.value.trim(),mode,quality:$("quality").value})
    });
    if (!res.ok) {
      const err = await res.json(); throw new Error(err.detail || "Download failed.");
    }
    const blob = await res.blob();
    const disposition = res.headers.get("content-disposition") || "";
    const match = disposition.match(/filename="?([^"]+)"?/i);
    const filename = match ? match[1] : `downly-${mode}`;
    const a = document.createElement("a");
    const objectUrl = URL.createObjectURL(blob);
    a.href = objectUrl; a.download = filename; document.body.appendChild(a); a.click(); a.remove();
    URL.revokeObjectURL(objectUrl);
    addHistory({title:currentInfo.title,platform:platform.options[platform.selectedIndex].text,mode});
    setStatus("Download started. Check your device's Downloads folder.", "success");
  } catch(e) { setStatus(e.message, "error"); }
  finally { btn.disabled = false; btn.textContent = "Download now ↓"; }
});

$("clearHistory").addEventListener("click", () => {
  localStorage.removeItem("downlyHistory"); renderHistory();
});
$("themeBtn").addEventListener("click", () => {
  document.body.classList.toggle("dark");
  const dark = document.body.classList.contains("dark");
  localStorage.setItem("downlyTheme", dark ? "dark" : "light");
  $("themeBtn").textContent = dark ? "☀" : "☾";
});
if (localStorage.getItem("downlyTheme") === "dark") {
  document.body.classList.add("dark"); $("themeBtn").textContent = "☀";
}
renderHistory();
