/* Paksward UI. Talks only to the API object: Python over HTTP when served by Paksward, or MOCK_API in dev/preview.html. */
(function () {
  "use strict";
  var CATS = [["Work", "#4c9aff"], ["Email", "#9b87f5"], ["Banking", "#3ecf8e"], ["Shopping", "#f5a524"], ["Social", "#f0629e"], ["Entertainment", "#22c3e6"], ["Other", "#8a9dab"]];
  var LV = ["Terrible", "Weak", "Fair", "Strong", "Excellent"];
  var AV = ["#4c9aff", "#9b87f5", "#3ecf8e", "#f5a524", "#f0629e", "#22c3e6", "#ef6b4a", "#7bd24a"];
  var ICONS = {
    lock: '<rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
    star: '<path d="M12 3l2.6 5.6 6.1.7-4.5 4.2 1.2 6L12 16.6 6.6 19.5l1.2-6L3.3 9.3l6.1-.7z"/>',
    shield: '<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/><path d="M9 12l2 2 4-4"/>',
    all: '<path d="M4 6h16M4 12h16M4 18h16"/>',
    spark: '<path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5L18 18M18 6l-2.5 2.5M8.5 15.5L6 18"/>',
    sliders: '<path d="M4 7h10M18 7h2M4 17h2M10 17h10"/><circle cx="16" cy="7" r="2"/><circle cx="8" cy="17" r="2"/>',
    plus: '<path d="M12 5v14M5 12h14"/>', search: '<circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/>',
    copy: '<rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V6a2 2 0 0 1 2-2h9"/>',
    eye: '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
    eyeoff: '<path d="M3 3l18 18M10.6 6.2A9.8 9.8 0 0 1 12 5c6.5 0 10 7 10 7a17 17 0 0 1-3.2 4M6.5 7.5C3.8 9.3 2 12 2 12s3.5 7 10 7c1.6 0 3-.4 4.3-1"/>',
    trash: '<path d="M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3"/>', edit: '<path d="M4 20h4L19 9l-4-4L4 16z"/>',
    back: '<path d="M15 5l-7 7 7 7"/>', refresh: '<path d="M20 11a8 8 0 0 0-14-4L4 9M4 4v5h5M4 13a8 8 0 0 0 14 4l2-2M20 20v-5h-5"/>',
    x: '<path d="M6 6l12 12M18 6L6 18"/>', arrow: '<path d="M5 12h14M13 6l6 6-6 6"/>'
  };
  function ic(n) { return '<svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + ICONS[n] + "</svg>"; }
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; }); }
  function $(s, el) { return (el || document).querySelector(s); }
  function lvc(l) { return "var(--lv" + l + ")"; }
  function catColor(c) { for (var i = 0; i < CATS.length; i++) if (CATS[i][0] === c) return CATS[i][1]; return CATS[6][1]; }
  function site(w) { return String(w).replace(/^https?:\/\//, "").replace(/^www\./, "").replace(/\/.*$/, ""); }
  function avColor(s) { var h = 0; for (var i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0; return AV[h % AV.length]; }
  function ava(w) { var s = site(w); return '<span class="ava" style="background:' + avColor(s) + '">' + esc((s[0] || "?").toUpperCase()) + "</span>"; }
  function ago(d) { if (d == null) return "not recorded"; if (d < 1) return "today"; if (d < 2) return "yesterday"; if (d < 60) return Math.round(d) + " days ago"; if (d < 730) return Math.round(d / 30) + " months ago"; return Math.round(d / 365) + " years ago"; }
  function bar(l) { var h = '<div class="sbar" role="img" aria-label="' + LV[l] + '">'; for (var i = 0; i < 5; i++) h += '<i style="' + (i <= l ? "background:" + lvc(l) : "") + '"></i>'; return h + "</div>"; }
  function stag(l) { return '<span class="stag" style="background:' + lvc(l) + '">' + LV[l] + "</span>"; }

  /* Transport. Served by Paksward: calls go to /api/<name> with the session token from the start-up link.
     In dev/preview.html: calls go to MOCK_API with sample data. */
  var REAL = !!document.querySelector('meta[name="paksward-server"]'), TOKEN = "";
  if (REAL) {
    var m = /[#&]t=([\w-]+)/.exec(location.hash);
    try { if (m) sessionStorage.setItem("pk_t", m[1]); TOKEN = (m && m[1]) || sessionStorage.getItem("pk_t") || ""; } catch (e) { TOKEN = m ? m[1] : ""; }
    if (m) { try { history.replaceState(null, "", location.pathname); } catch (e) {} }
  }
  function http(name, args) {
    return fetch("/api/" + name, { method: "POST", headers: { "Content-Type": "application/json", "X-Paksward-Token": TOKEN }, body: JSON.stringify({ args: args }) })
      .then(function (r) { return r.json(); });
  }
  var api = new Proxy({}, { get: function (_, name) { return function () {
    var a = Array.prototype.slice.call(arguments);
    var p = REAL ? http(name, a) : Promise.resolve(window.MOCK_API[name].apply(null, a));
    return p.then(function (res) {
      if (res && res.locked) { if (S.screen === "main") A.lock("idle"); return Promise.reject(new Error("locked")); }
      return res;
    });
  }; } });
  window.addEventListener("unhandledrejection", function (e) { if (e.reason && e.reason.message === "locked") e.preventDefault(); });

  var S = { screen: "auth", mode: "login", email: "", entries: [], report: null, nav: "all", query: "", sel: null, detail: null, showPw: false,
    mobileDetail: false, autolock: 5, note: "", armed: false, preview: false,
    gen: { mode: "chars", length: 20, upper: true, lower: true, digits: true, symbols: true, avoidAmbiguous: false, words: 6, separator: "-", capitalize: false, out: null } };
  var root = $("#root"), toastT;
  function toast(m) { var t = $("#toast"); t.textContent = m; t.className = "on"; clearTimeout(toastT); toastT = setTimeout(function () { t.className = ""; }, 2400); }

  /* ================= AUTH ================= */
  function brand() {
    return '<aside class="brand"><div><div class="logo"><span class="mark">' + ic("lock") + '</span>Paksward</div>' +
      '<h2>Every password, locked on your own device.</h2><p>No cloud, no account on someone else’s server. Your vault is encrypted and stays on this device.</p></div>' +
      '<ul class="pts"><li><b>' + ic("shield") + '</b>Encrypted with a key only your master password can open</li>' +
      '<li><b>' + ic("spark") + '</b>Watchtower flags weak, reused, old and (optionally) leaked passwords</li>' +
      '<li><b>' + ic("lock") + '</b>Locks itself after you step away</li></ul></aside>';
  }
  function authView() {
    var m = S.mode, h = '<div class="auth">' + brand() + '<div class="formside"><div class="formbox">';
    if (S.note) h += '<div class="notice">' + esc(S.note) + "</div>";
    if (m === "login") {
      h += (S.preview ? '<div class="preview-note"><span>' + ic("shield") + '</span><span><b>Preview with sample data.</b> The demo account is filled in. Nothing is saved or encrypted in this preview.</span></div>' : "") +
        "<h1>Welcome back</h1><p class=\"sub\">Unlock your vault to continue.</p>" +
        field("Email", '<input class="inp" id="a-email" type="email" autocomplete="username" value="' + (S.preview ? "demo@paksward.app" : "") + '">') +
        field("Master password", pwInput("a-pw", S.preview ? "demo-password-1" : "", "current-password")) +
        '<div id="a-secret-wrap" hidden>' + field("Secret Key", '<input class="inp mono" id="a-secret" autocomplete="off" spellcheck="false" placeholder="PWSK-XXXX-XXXX-…"><div class="hint" style="margin-top:4px">This device does not have it yet. It is in your saved keys (the Emergency Kit).</div>') + "</div>" +
        '<div class="err" id="a-err" role="alert"></div><button class="btn primary block" data-act="login">Unlock</button>' +
        '<div class="row" style="justify-content:space-between;margin-top:16px"><button class="link muted" data-act="mode" data-arg="recover">Forgot password?</button>' +
        '<span class="hint">New here? <button class="link" data-act="mode" data-arg="register">Create account</button></span></div>' +
        '<p style="margin-top:24px"><button class="link muted" data-act="restorepick">Restore from a backup file</button> &nbsp;·&nbsp; <button class="link muted" data-act="quit">Quit Paksward</button></p>' +
        '<input type="file" id="a-file" accept=".pkbackup,application/json" hidden>';
    } else if (m === "register") {
      h += "<h1>Create your vault</h1><p class=\"sub\">Your master password never leaves this device.</p>" +
        field("Email", '<input class="inp" id="a-email" type="email" autocomplete="username">') +
        field("Master password", pwInput("a-pw", "", "new-password") + '<div id="a-meter" style="margin-top:8px"></div>') +
        field("Confirm password", pwInput("a-pw2", "", "new-password")) +
        '<p class="hint" style="margin:-4px 0 14px">At least 10 characters. Next, Paksward makes two random keys for you to save. You do not have to invent or remember anything else.</p>' +
        '<div class="notice" style="margin-bottom:14px"><b>Important:</b> If you lose your password <b>and</b> your keys, your vault cannot be opened by anyone. There is no reset and nobody can help.</div>' +
        '<div class="err" id="a-err" role="alert"></div><button class="btn primary block" data-act="register">Create account</button>' +
        '<p class="hint" style="margin-top:16px">Already have an account? <button class="link" data-act="mode" data-arg="login">Log in</button></p>';
    } else if (m === "recover") {
      h += "<h1>Recover your account</h1><p class=\"sub\">Enter your email, then your Recovery Key.</p>" +
        field("Email", '<input class="inp" id="a-email" type="email">') + '<div class="err" id="a-err" role="alert"></div><button class="btn primary block" data-act="rec1">Continue</button>' + backLink();
    } else if (m === "recover2") {
      h += "<h1>Recovery Key</h1><p class=\"sub\">It starts with PWRK. Capitals and dashes do not matter.</p>" + (S.preview ? '<p class="hint">Preview Recovery Key: PWRK-DEMO-1111-1111-1111-1111-1111-1111-1111-1111</p>' : "") +
        field("Recovery Key", '<input class="inp mono" id="a-ph" autocomplete="off" spellcheck="false" placeholder="PWRK-XXXX-XXXX-…">') + '<div class="err" id="a-err" role="alert"></div><button class="btn primary block" data-act="rec2">Verify</button>' + backLink();
    } else {
      h += "<h1>Set a new password</h1><p class=\"sub\">Your vault stays exactly as it was. You will get a new Secret Key to save.</p>" +
        field("New password", pwInput("a-pw", "", "new-password")) + field("Confirm new password", pwInput("a-pw2", "", "new-password")) +
        '<div class="err" id="a-err" role="alert"></div><button class="btn primary block" data-act="rec3">Reset and log in</button>' + backLink();
    }
    return h + "</div></div></div>";
  }
  function backLink() { return '<p style="margin-top:16px"><button class="link muted" data-act="mode" data-arg="login">Back to log in</button></p>'; }
  function field(l, inner) { return '<div class="field"><label class="f">' + l + "</label>" + inner + "</div>"; }
  function pwInput(id, v, ac) { return '<div class="pwrow"><input class="inp" id="' + id + '" type="password" autocomplete="' + ac + '" value="' + esc(v) + '"><button type="button" class="iconbtn" data-act="peek" data-arg="' + id + '" aria-label="Show or hide">' + ic("eye") + "</button></div>"; }
  function v(id) { var e = $("#" + id); return e ? e.value : ""; }
  function aerr(m) { var e = $("#a-err"); if (e) { e.textContent = m || ""; e.style.color = ""; } }
  function keyBox(label, text, what) {
    return '<div class="keybox"><div class="keylabel">' + label + '</div><div class="keyval mono">' + esc(text) + '</div><div class="hint">' + what + '</div>' +
      '<button class="btn" data-act="copykey" data-arg="' + esc(text) + '">Copy</button></div>';
  }
  function kitView() {
    var k = S.kit, h = '<div class="auth"><div class="formside" style="grid-column:1/-1"><div class="formbox kit"><h1>Save your keys</h1>' +
      '<p class="sub">Paksward cannot show these again later, and cannot recover them for you. If you lose your password <b>and</b> these keys, you are locked out for good: nobody can open or reset your vault.</p>';
    if (k.secret_key) h += keyBox("Secret Key", k.secret_key, "Needed together with your password to open the vault on a new device. A copy of your data folder is useless without it.");
    if (k.recovery_key) h += keyBox("Recovery Key", k.recovery_key, "The only way back in if you forget your password. Keep it somewhere different from your password.");
    h += '<div class="row" style="margin:6px 0 14px"><button class="btn" data-act="printkit">Print or save as PDF</button></div>' +
      '<label class="row" style="margin-bottom:14px"><input class="sw" type="checkbox" id="kit-ok"><b>I have saved these somewhere safe</b></label>' +
      '<button class="btn primary block" data-act="kitdone" id="kit-go" disabled>Continue</button></div></div></div>';
    return h;
  }
  function showKit(kit, back) { S.kit = kit; S.kitBack = back || false; S.screen = "kit"; render(); }
  function afterAuth(r) {
    if (!r.ok) return aerr(r.error);
    S.pendingEmail = r.email;
    if (r.kit) showKit(r.kit, false); else enterVault(r.email);
  }
  function enterVault(email) { S.email = email; S.note = ""; S.nav = "all"; S.query = ""; S.sel = null; return loadAll().then(function () { S.screen = "main"; render(); resetIdle(); }); }
  function loadAll() {
    return Promise.all([api.list_entries(), api.security_report(), api.get_settings()]).then(function (r) {
      S.entries = r[0]; S.report = r[1]; S.breach = null; S.autolock = (r[2].settings || {}).autolock_minutes; if (S.autolock == null) S.autolock = 5;
    });
  }

  /* ================= SHELL ================= */
  function counts() { var c = {}, f = 0; S.entries.forEach(function (e) { c[e.category] = (c[e.category] || 0) + 1; if (e.favorite) f++; }); c._fav = f; return c; }
  function navBtn(id, icon, label, extra) { return '<button class="nav" data-act="nav" data-arg="' + id + '" aria-current="' + (S.nav === id) + '">' + (icon.charAt(0) === "<" ? icon : ic(icon)) + "<span>" + label + "</span>" + (extra || "") + "</button>"; }
  function shellView() {
    var c = counts(), issues = S.entries.filter(function (e) { return e.level <= 1 || e.reused > 1; }).length;
    var h = '<div class="shell"><nav class="side" aria-label="Main"><div class="logo"><span class="mark">' + ic("lock") + '</span>Paksward</div>' +
      '<div class="vault">' + '<span class="ava" style="background:' + avColor(S.email) + '">' + esc((S.email[0] || "?").toUpperCase()) + '</span><div><b>' + esc(S.email) + "</b><small>Local vault</small></div></div>" +
      navBtn("all", "all", "All items", '<span class="n">' + S.entries.length + "</span>") + navBtn("fav", "star", "Favorites", '<span class="n">' + c._fav + "</span>") +
      navBtn("watch", "shield", "Watchtower", issues ? '<span class="badge">' + issues + "</span>" : "") +
      '<div class="sec">Categories</div>';
    CATS.forEach(function (k) { if (c[k[0]]) h += navBtn("cat:" + k[0], '<span class="dot" style="background:' + k[1] + '"></span>', k[0], '<span class="n">' + c[k[0]] + "</span>"); });
    h += '<div class="sec">Tools</div>' + navBtn("gen", "spark", "Generator") + navBtn("set", "sliders", "Settings") +
      '<div class="spacer"></div><button class="nav" data-act="lock">' + ic("lock") + "<span>Lock vault</span></button></nav>" +
      '<div class="main"><div class="top"><div class="search">' + ic("search") + '<input class="inp" id="q" type="search" placeholder="Search websites and usernames" value="' + esc(S.query) + '" aria-label="Search"></div>' +
      '<button class="btn primary" data-act="new">' + ic("plus") + "<span>New item</span></button></div>" +
      '<div class="content" id="content"></div></div></div>';
    return h;
  }
  function filtered() {
    var q = S.query.trim().toLowerCase(), n = S.nav, r = S.report || {};
    return S.entries.filter(function (e) {
      if (n === "fav" && !e.favorite) return false;
      if (n.indexOf("cat:") === 0 && e.category !== n.slice(4)) return false;
      if (n === "f:weak" && (r.weak || []).indexOf(e.id) < 0) return false;
      if (n === "f:old" && (r.old || []).indexOf(e.id) < 0) return false;
      if (n === "f:reused" && e.reused < 2) return false;
      return !q || e.website.toLowerCase().indexOf(q) > -1 || e.username.toLowerCase().indexOf(q) > -1;
    }).sort(function (a, b) { return site(a.website).localeCompare(site(b.website)); });
  }
  var FNAME = { "f:weak": "Weak passwords", "f:old": "Old passwords", "f:reused": "Reused passwords" };
  function renderContent() {
    var n = S.nav, el = $("#content");
    if (n === "watch") el.innerHTML = watchView(); else if (n === "gen") el.innerHTML = genView(); else if (n === "set") el.innerHTML = setView();
    else { itemsView(el); }
    if (n === "gen" && !S.gen.out) regen();
  }
  function itemsView(el) {
    var list = filtered(), ids = list.map(function (e) { return e.id; });
    if (S.sel && ids.indexOf(S.sel) < 0) S.sel = null;
    if (!S.sel && list.length && !S.mobileDetail) S.sel = list[0].id;
    var h = '<div class="split' + (S.mobileDetail ? " showdetail" : "") + '"><div class="list">';
    if (FNAME[S.nav]) h += '<span class="chip">' + FNAME[S.nav] + '<button data-act="nav" data-arg="all" aria-label="Clear filter">' + ic("x") + "</button></span>";
    if (!list.length) h += '<div class="empty"><b>' + (S.entries.length ? "Nothing matches" : "Your vault is empty") + "</b>" + (S.entries.length ? "Try a different search or filter." : "Add your first password with New item.") + "</div>";
    list.forEach(function (e) {
      var flag = e.level <= 1 || e.reused > 1 ? '<span class="flag" title="Needs attention" style="background:' + (e.level <= 1 ? lvc(e.level) : "var(--lv1)") + '"></span>' : "";
      h += '<button class="item" data-act="sel" data-arg="' + esc(e.id) + '" aria-current="' + (S.sel === e.id) + '">' + ava(e.website) + '<span class="t"><b>' + esc(site(e.website)) + "</b><small>" + esc(e.username) + "</small></span>" + flag + "</button>";
    });
    h += '</div><div class="detail" id="detail"></div></div>';
    el.innerHTML = h; renderDetail();
  }
  function renderDetail() {
    var d = $("#detail"); if (!d) return;
    var m = S.entries.filter(function (e) { return e.id === S.sel; })[0];
    if (!m) { d.innerHTML = '<div class="empty"><b>Select an item</b>Pick something from the list to see its details.</div>'; return; }
    var tags = "";
    if (m.level <= 1) tags += '<span class="tag" style="color:' + lvc(m.level) + ";border-color:" + lvc(m.level) + '">' + LV[m.level] + " password</span>";
    if (S.breach && S.breach.compromised && S.breach.compromised[m.id]) tags += '<span class="tag" style="color:var(--danger);border-color:var(--danger)">Found in a breach</span>';
    if (m.reused > 1) tags += '<span class="tag" style="color:var(--danger);border-color:var(--danger)">Reused on ' + m.reused + " items</span>";
    if (m.age_days > ((S.report || {}).old_after_days || 180)) tags += '<span class="tag" style="color:#9b87f5;border-color:#9b87f5">Not changed in ' + ago(m.age_days).replace(" ago", "") + "</span>";
    tags += '<span class="tag" style="color:' + catColor(m.category) + ";border-color:" + catColor(m.category) + '">' + esc(m.category) + "</span>";
    var shown = S.detail && S.detail.id === m.id ? S.detail.password : null;
    d.innerHTML = '<button class="btn back" data-act="back">' + ic("back") + "Back</button>" +
      '<div class="dhead">' + ava(m.website) + "<h2>" + esc(site(m.website)) + '</h2><div class="acts">' +
      '<button class="btn" data-act="fav" data-arg="' + esc(m.id) + '" aria-pressed="' + m.favorite + '">' + ic("star").replace('fill="none"', 'fill="' + (m.favorite ? "currentColor" : "none") + '"') + (m.favorite ? "Favorited" : "Favorite") + "</button>" +
      '<button class="btn" data-act="edit" data-arg="' + esc(m.id) + '">' + ic("edit") + 'Edit</button>' +
      '<button class="btn danger' + (S.armed ? " armed" : "") + '" data-act="del" data-arg="' + esc(m.id) + '">' + ic("trash") + (S.armed ? "Confirm delete" : "Delete") + "</button></div></div>" +
      '<div class="tags">' + tags + "</div>" +
      '<div class="card"><div class="kv"><span class="k">Username</span><span class="v">' + esc(m.username) + '</span><button class="iconbtn" data-act="copyu" data-arg="' + esc(m.id) + '" aria-label="Copy username">' + ic("copy") + "</button></div>" +
      '<div class="kv"><span class="k">Password</span><span class="v mono">' + (shown != null ? esc(shown) : "•".repeat(12)) + "</span>" +
      '<button class="iconbtn" data-act="reveal" data-arg="' + esc(m.id) + '" aria-label="Show or hide password">' + ic(shown != null ? "eyeoff" : "eye") + "</button>" +
      '<button class="iconbtn" data-act="copyp" data-arg="' + esc(m.id) + '" aria-label="Copy password">' + ic("copy") + "</button></div>" +
      '<div class="kv"><span class="k">Strength</span><span class="v">' + bar(m.level) + '</span>' + stag(m.level) + "</div>" +
      '<div class="kv"><span class="k">Changed</span><span class="v">' + ago(m.age_days) + "</span></div></div>";
  }

  /* ================= WATCHTOWER ================= */
  function tile(tone, n, title, text, filter, cta) {
    return '<div class="card tile"><div class="body"><div class="num" style="color:' + tone + '">' + n + "</div><h3>" + title + "</h3><p>" + text + "</p></div>" +
      '<button class="go" data-act="nav" data-arg="' + filter + '"' + (n ? "" : " disabled") + "><span>" + (n ? cta : "All clear") + "</span>" + (n ? ic("arrow") : ic("shield")) + "</button></div>";
  }
  function breachCard() {
    var b = S.breach, head = '<div class="card" style="margin-bottom:16px;padding:16px 18px"><div class="sec" style="padding:0 0 6px">Leaked passwords (online, optional)</div>';
    var note = '<div class="hint" style="margin:0 0 10px">This is the only feature that uses the internet. For each password, Paksward sends only the <b>first 5 characters</b> of its SHA-1 fingerprint to haveibeenpwned.com and compares the reply here. Your passwords, and the rest of each fingerprint, never leave this computer.</div>';
    if (b && b.busy) return head + note + '<button class="btn" disabled>Checking…</button></div>';
    var result = "";
    if (b && b.error) result = '<div class="err" role="alert" style="margin-bottom:10px">' + esc(b.error) + "</div>";
    else if (b) { var n = Object.keys(b.compromised).length; result = '<p style="margin:0 0 10px"><b>' + (n ? n + (n === 1 ? " password was" : " passwords were") + " found in known breaches." : "None of your " + b.checked + " checked passwords were found in known breaches.") + "</b>" + (b.failed ? " " + b.failed + " could not be checked." : "") + "</p>"; }
    return head + note + result + '<button class="btn" data-act="breach">' + (b && !b.error ? "Check again" : "Check now") + "</button></div>";
  }
  function watchView() {
    var r = S.report; if (!r) return "";
    var total = r.total || 0, weak = r.weak.length, old = r.old.length, reusedItems = r.reused.reduce(function (a, g) { return a + g.length; }, 0);
    var scoreCol = r.score >= 85 ? "var(--lv4)" : r.score >= 70 ? "var(--lv3)" : r.score >= 50 ? "var(--lv2)" : "var(--lv0)";
    var seg = "", leg = "";
    for (var l = 4; l >= 0; l--) { if (r.levels[l]) seg += '<i style="flex:' + r.levels[l] + ";background:" + lvc(l) + '" title="' + LV[l] + ": " + r.levels[l] + '"></i>'; leg += '<span><b style="background:' + lvc(l) + '">' + r.levels[l] + "</b>" + LV[l] + "</span>"; }
    var byId = {}; S.entries.forEach(function (e) { byId[e.id] = e; });
    var fixes = [];
    r.reused.forEach(function (g) { g.forEach(function (id) { var others = g.filter(function (x) { return x !== id; }).map(function (x) { return site(byId[x].website); }); fixes.push({ id: id, kind: "Reused", col: "var(--danger)", text: "Shares its password with " + esc(others.join(", ")) }); }); });
    r.weak.forEach(function (id) { fixes.push({ id: id, kind: LV[byId[id].level], col: lvc(byId[id].level), text: "Easy to guess. Replace it with a generated password." }); });
    r.old.forEach(function (id) { if (r.weak.indexOf(id) < 0 && byId[id].reused < 2) fixes.push({ id: id, kind: "Old", col: "#9b87f5", text: "Unchanged for " + ago(byId[id].age_days).replace(" ago", "") + "." }); });
    if (S.breach && S.breach.compromised) Object.keys(S.breach.compromised).forEach(function (id) { if (byId[id]) fixes.unshift({ id: id, kind: "Leaked", col: "var(--danger)", text: "Found " + S.breach.compromised[id].toLocaleString() + " times in known data breaches. Change it everywhere you use it." }); });
    var seen = {}, rows = fixes.filter(function (f) { if (seen[f.id + f.kind]) return false; seen[f.id + f.kind] = 1; return true; }).slice(0, 8).map(function (f) {
      return '<div class="fix">' + ava(byId[f.id].website) + '<div class="t"><b>' + esc(site(byId[f.id].website)) + '</b> <span class="stag" style="background:' + f.col + '">' + f.kind + "</span><small>" + f.text + '</small></div><button class="btn" data-act="fixit" data-arg="' + esc(f.id) + '">Change password</button></div>';
    }).join("");
    return '<div class="panel"><h1>Watchtower</h1><p class="sub">Strength, reuse and age are checked on this device only.</p>' +
      '<div class="card hero"><div class="top2"><div><div class="sec" style="padding:0 0 6px">Overall password strength</div><div class="score" style="color:' + scoreCol + '">' + r.score + "<small> / 100</small></div></div>" +
      '<div style="text-align:right"><span class="stag" style="background:' + scoreCol + '">' + r.grade + '</span><div class="hint" style="margin-top:6px">' + total + " passwords checked</div></div></div>" +
      '<div class="bigbar">' + (seg || '<i style="flex:1;background:var(--line)"></i>') + '</div><div class="legend">' + leg + "</div></div>" +
      breachCard() + '<div class="tiles">' + tile("var(--lv1)", weak, "Weak passwords", "Short or predictable passwords that are quick to guess.", "f:weak", "Show items") +
      tile("var(--danger)", reusedItems, "Reused passwords", "One leaked password would open every account that shares it.", "f:reused", "Show items") +
      tile("#9b87f5", old, "Old passwords", "Not changed in over " + r.old_after_days + " days.", "f:old", "Show items") +
      tile("var(--lv4)", r.levels[3] + r.levels[4], "Strong passwords", "Rated Strong or Excellent.", "all", "Show all") + "</div>" +
      '<h2 style="font-family:var(--display);font-size:19px;margin:0 0 10px">What to fix first</h2>' +
      '<div class="card">' + (rows || '<div class="empty"><b>Nothing to fix</b>Your passwords are strong, unique and recent.</div>') + "</div></div>";
  }

  /* ================= GENERATOR & SETTINGS ================= */
  function sw(id, label, on, sub) { return '<label class="opt"><span><b>' + label + "</b>" + (sub ? '<div class="hint">' + sub + "</div>" : "") + '</span><input class="sw" type="checkbox" role="switch" data-g="' + id + '"' + (on ? " checked" : "") + "></label>"; }
  function genView() {
    var g = S.gen, o = g.out || { password: "", level: 0, bits: 0 };
    return '<div class="panel"><div class="gen"><h1>Password generator</h1><p class="sub">Random, made on this device.</p>' +
      '<div class="card out"><code id="g-out">' + esc(o.password) + '</code><button class="iconbtn" data-act="regen" aria-label="Generate another">' + ic("refresh") + '</button><button class="iconbtn" data-act="copyg" aria-label="Copy">' + ic("copy") + "</button></div>" +
      '<div id="g-meter" style="margin-bottom:16px">' + gmeter(o) + "</div>" +
      '<div class="card opts"><div class="opt"><b>Type</b><div class="seg"><button data-act="gmode" data-arg="chars" aria-pressed="' + (g.mode === "chars") + '">Characters</button><button data-act="gmode" data-arg="passphrase" aria-pressed="' + (g.mode === "passphrase") + '">Passphrase</button></div></div>' +
      (g.mode === "chars"
        ? '<div class="opt" style="display:block"><div class="row" style="justify-content:space-between"><b>Length</b><span id="g-len" class="mono" style="font-family:var(--mono)">' + g.length + '</span></div><input type="range" min="8" max="64" value="' + g.length + '" data-g="length" aria-label="Length"></div>' +
          sw("lower", "Lowercase", g.lower, "a-z") + sw("upper", "Uppercase", g.upper, "A-Z") + sw("digits", "Digits", g.digits, "0-9") + sw("symbols", "Symbols", g.symbols, "!@#$%") + sw("avoidAmbiguous", "Avoid look-alikes", g.avoidAmbiguous, "Skips I, l, 1, O and 0")
        : '<div class="opt" style="display:block"><div class="row" style="justify-content:space-between"><b>Words</b><span id="g-len" style="font-family:var(--mono)">' + g.words + '</span></div><input type="range" min="3" max="10" value="' + g.words + '" data-g="words" aria-label="Number of words"></div>' +
          sw("capitalize", "Capitalize words", g.capitalize) + sw("digits", "Add a number", g.digits === true && g.mode === "passphrase" ? true : false)) + "</div>" +
      '<div class="row" style="margin-top:16px"><button class="btn primary" data-act="usegen">' + ic("plus") + "Use in a new item</button></div></div></div>";
  }
  function gmeter(o) { return bar(o.level) + '<div class="row" style="justify-content:space-between;margin-top:8px"><span>' + stag(o.level) + '</span><span class="hint">about ' + o.bits + " bits of entropy</span></div>"; }
  function regen() {
    var g = S.gen; return api.generate({ mode: g.mode, length: g.length, upper: g.upper, lower: g.lower, digits: g.digits, symbols: g.symbols, avoidAmbiguous: g.avoidAmbiguous, words: g.words, separator: g.separator, capitalize: g.capitalize }).then(function (o) {
      g.out = o; var c = $("#g-out"); if (c) { c.textContent = o.password; $("#g-meter").innerHTML = gmeter(o); }
    });
  }
  function setView() {
    var opts = [[0, "Off"], [2, "2 min"], [5, "5 min"], [10, "10 min"]];
    return '<div class="panel"><div class="gen"><h1>Settings</h1><p class="sub">' + esc(S.email) + '</p><div class="card opts"><div class="opt" style="display:block"><b>Auto-lock</b><div class="hint" style="margin:2px 0 10px">Lock the vault after this much time with no activity. You will need your master password to unlock it.</div>' +
      '<div class="seg">' + opts.map(function (o) { return '<button data-act="autolock" data-arg="' + o[0] + '" aria-pressed="' + (S.autolock === o[0]) + '">' + o[1] + "</button>"; }).join("") + "</div></div>" +
      '<div class="opt" style="display:block"><b>Keys and password</b><div class="hint" style="margin:2px 0 10px">Your Secret Key is stored on this device, outside the data folder.</div>' +
      '<div class="row" style="flex-wrap:wrap;gap:8px"><button class="btn" data-act="showsk">Show Secret Key</button><button class="btn" id="rk-btn" data-act="newrk">Make a new Recovery Key</button><button class="btn" data-act="chpw">Change master password</button></div><div id="keys-out" style="margin-top:12px"></div></div>' +
      '<div class="opt" style="display:block"><b>Backup</b><div class="hint" style="margin:2px 0 10px">An encrypted copy of your vault. It holds no password and no keys, so you still need your keys to open it. Keep it somewhere other than this computer.</div><button class="btn" data-act="backup">Download backup</button></div>' +
      '<div class="opt"><span><b>Quit Paksward</b><div class="hint">Locks the vault and stops the app on this computer.</div></span><button class="btn" data-act="quit">Quit</button></div>' +
      '<div class="opt"><span><b>Storage</b><div class="hint">Your vault stays in the data folder on this computer and is never uploaded. The only internet use is the optional leaked-password check on the Watchtower page.</div></span></div></div></div></div>';
  }

  /* ================= EDITOR ================= */
  function openEditor(entry, pw) {
    var e = entry || { website: "", username: "", password: pw || "", category: S.nav.indexOf("cat:") === 0 ? S.nav.slice(4) : "Other", favorite: false };
    var opts = CATS.map(function (c) { return '<option' + (c[0] === e.category ? " selected" : "") + ">" + c[0] + "</option>"; }).join("");
    var m = $("#modal"); m.className = "scrim"; m.dataset.id = entry ? entry.id : "";
    m.innerHTML = '<div class="modal card" role="dialog" aria-modal="true" aria-label="' + (entry ? "Edit item" : "New item") + '"><h2>' + (entry ? "Edit item" : "New item") + "</h2>" +
      field("Website", '<input class="inp" id="e-site" value="' + esc(e.website) + '" autocomplete="off">') + field("Username or email", '<input class="inp" id="e-user" value="' + esc(e.username) + '" autocomplete="off">') +
      field("Password", '<div class="pwrow"><input class="inp mono" id="e-pw" type="text" value="' + esc(e.password) + '" autocomplete="off" spellcheck="false"><button type="button" class="iconbtn" data-act="egen" aria-label="Generate password" title="Generate">' + ic("spark") + '</button></div><div id="e-meter" style="margin-top:8px"></div>') +
      field("Category", '<select class="inp" id="e-cat">' + opts + "</select>") +
      '<label class="row" style="margin-bottom:8px"><input class="sw" type="checkbox" id="e-fav"' + (e.favorite ? " checked" : "") + "><b>Favorite</b></label>" +
      '<div class="err" id="e-err" role="alert"></div><div class="foot"><button class="btn" data-act="ecancel">Cancel</button><button class="btn primary" data-act="esave">Save</button></div></div>';
    meter(); var first = $(e.website ? "#e-pw" : "#e-site"); if (first) first.focus();
  }
  function closeEditor() { var m = $("#modal"); m.className = "hide"; m.innerHTML = ""; }
  function meter() { var p = $("#e-pw"), t = $("#e-meter"); if (!p || !t) return; api.check_strength(p.value).then(function (s) { t.innerHTML = p.value ? bar(s.level) + '<div class="hint" style="margin-top:4px">' + s.label + " · about " + s.bits + " bits</div>" : ""; }); }
  function meterReg() { var p = $("#a-pw"), t = $("#a-meter"); if (!p || !t) return; api.check_strength(p.value).then(function (s) { t.innerHTML = p.value ? bar(s.level) + '<div class="hint" style="margin-top:4px">' + s.label + "</div>" : ""; }); }

  /* ================= ACTIONS ================= */
  var A = {
    mode: function (m) { S.mode = m; S.note = ""; render(); },
    peek: function (id) { var e = $("#" + id); if (e) e.type = e.type === "password" ? "text" : "password"; },
    login: function () {
      aerr();
      api.login(v("a-email").trim(), v("a-pw"), v("a-secret").trim() || null).then(function (r) {
        if (r.need_secret) { var w = $("#a-secret-wrap"); w.hidden = false; $("#a-secret").focus(); }
        afterAuth(r);
      });
    },
    register: function () { api.register(v("a-email"), v("a-pw"), v("a-pw2")).then(afterAuth); },
    rec1: function () { api.recover_start(v("a-email")).then(function (r) { if (!r.ok) return aerr(r.error); S.mode = "recover2"; render(); }); },
    rec2: function () { api.recover_verify(v("a-ph")).then(function (r) { if (!r.ok) return aerr(r.error); S.mode = "recover3"; render(); }); },
    rec3: function () { api.recover_reset(v("a-pw"), v("a-pw2")).then(afterAuth); },
    copykey: function (text) { copyOut(text, 60).then(function (r) { toast(r.ok ? "Copied. Clipboard clears in 60 seconds." : "Could not copy. Select the key and copy it by hand."); }); },
    printkit: function () { window.print(); },
    kitdone: function () {
      var back = S.kitBack; S.kit = null; S.kitBack = false;
      if (back) { S.screen = "main"; render(); } else enterVault(S.pendingEmail);
    },
    showsk: function () { api.get_secret_key().then(function (r) { $("#keys-out").innerHTML = r.ok ? keyBox("Secret Key", r.secret_key, "Keep it with your Recovery Key. Anyone who has this and your password can open your vault.") : '<div class="err">' + esc(r.error) + "</div>"; }); },
    newrk: function () {
      if (!S.rkArmed) { S.rkArmed = true; var b = $("#rk-btn"); b.textContent = "Click again to replace it (the old one stops working)"; return setTimeout(function () { S.rkArmed = false; var x = $("#rk-btn"); if (x) x.textContent = "Make a new Recovery Key"; }, 4000); }
      S.rkArmed = false; api.new_recovery_key().then(function (r) { if (r.ok) showKit({ recovery_key: r.recovery_key }, true); else toast(r.error); });
    },
    chpw: function () {
      var m = $("#modal"); m.className = "scrim"; m.dataset.id = "";
      m.innerHTML = '<div class="modal card" role="dialog" aria-modal="true" aria-label="Change master password"><h2>Change master password</h2>' +
        field("Current password", pwInput("c-cur", "", "current-password")) + field("New password", pwInput("c-new", "", "new-password")) + field("Confirm new password", pwInput("c-new2", "", "new-password")) +
        '<div class="err" id="c-err" role="alert"></div><div class="foot"><button class="btn" data-act="ecancel">Cancel</button><button class="btn primary" data-act="chpwsave">Change password</button></div></div>';
      $("#c-cur").focus();
    },
    chpwsave: function () { api.change_password(v("c-cur"), v("c-new"), v("c-new2")).then(function (r) { if (!r.ok) { $("#c-err").textContent = r.error; return; } closeEditor(); toast("Master password changed."); }); },
    lock: function (why) { api.lock().then(function () { S.screen = "auth"; S.mode = "login"; S.kit = null; S.breach = null; S.detail = null; S.entries = []; S.report = null; S.note = why === "idle" ? "Locked after a period of inactivity." : ""; closeEditor(); render(); }); },
    nav: function (n) { S.nav = n; S.armed = false; S.mobileDetail = false; S.sel = null; S.detail = null; if (n.indexOf("f:") !== 0 && n !== "all") S.query = ""; var q = $("#q"); if (q) q.value = S.query; render(); },
    sel: function (id) { S.sel = id; S.armed = false; S.detail = null; S.mobileDetail = true; document.querySelectorAll(".item").forEach(function (b) { b.setAttribute("aria-current", String(b.dataset.arg === id)); }); itemsView($("#content")); },
    back: function () { S.mobileDetail = false; renderContent(); },
    reveal: function (id) { if (S.detail && S.detail.id === id) { S.detail = null; return renderDetail(); } api.get_entry(id).then(function (r) { if (r.ok) { S.detail = { id: id, password: r.entry.password }; renderDetail(); } }); },
    copyp: function (id) { api.get_entry(id).then(function (r) { return r.ok ? copyOut(r.entry.password, 30) : { ok: false }; }).then(function (r) { toast(r.ok ? (r.cleared ? "Password copied. Clipboard clears in 30 seconds." : "Password copied.") : "Could not copy. Reveal the password and copy it by hand."); }); },
    copyu: function (id) { var m = byId(id); copyOut(m.username, 0).then(function (r) { toast(r.ok ? "Username copied." : "Could not copy."); }); },
    fav: function (id) { var m = byId(id); api.set_favorite(id, !m.favorite).then(function () { return loadAll(); }).then(function () { render(); }); },
    del: function (id) { if (!S.armed) { S.armed = true; renderDetail(); return setTimeout(function () { if (S.armed) { S.armed = false; renderDetail(); } }, 3500); }
      S.armed = false; api.delete_entry(id).then(function () { S.sel = null; S.detail = null; S.mobileDetail = false; return loadAll(); }).then(function () { render(); toast("Item deleted."); }); },
    "new": function () { openEditor(null); },
    edit: function (id) { api.get_entry(id).then(function (r) { if (r.ok) openEditor(Object.assign({ id: id }, r.entry)); }); },
    fixit: function (id) { S.nav = "all"; api.get_entry(id).then(function (r) { if (!r.ok) return; var e = Object.assign({ id: id }, r.entry); return api.generate({ length: 20 }).then(function (g) { e.password = g.password; render(); S.sel = id; openEditor(e); }); }); },
    egen: function () { api.generate({ length: S.gen.length, upper: S.gen.upper, lower: S.gen.lower, digits: S.gen.digits, symbols: S.gen.symbols, avoidAmbiguous: S.gen.avoidAmbiguous }).then(function (g) { $("#e-pw").value = g.password; meter(); }); },
    ecancel: closeEditor,
    esave: function () {
      var m = $("#modal"), id = m.dataset.id, d = { website: v("e-site"), username: v("e-user"), password: v("e-pw"), category: v("e-cat"), favorite: $("#e-fav").checked };
      var p = id ? api.update_entry(id, d) : api.add_entry(d);
      p.then(function (r) { if (!r.ok) { $("#e-err").textContent = r.error; return; } closeEditor(); return loadAll().then(function () { S.sel = id || r.id; S.mobileDetail = false; S.detail = null; render(); toast(id ? "Item updated." : "Item saved to your vault."); }); });
    },
    regen: function () { regen(); },
    copyg: function () { if (S.gen.out) copyOut(S.gen.out.password, 30).then(function (r) { toast(r.ok ? (r.cleared ? "Copied. Clipboard clears in 30 seconds." : "Copied.") : "Could not copy."); }); },
    gmode: function (m) { S.gen.mode = m; if (m === "passphrase") S.gen.digits = false; else S.gen.digits = true; S.gen.out = null; renderContent(); },
    usegen: function () { if (!S.gen.out) return; S.nav = "all"; render(); openEditor(null, S.gen.out.password); },
    breach: function () {
      S.breach = { busy: true }; renderContent();
      api.check_breaches().then(function (r) {
        S.breach = r.ok ? { checked: r.checked, failed: r.failed, compromised: r.compromised } : { error: r.error };
        if (S.nav === "watch") renderContent();
      }, function () { S.breach = null; });
    },
       backup: function () {
         api.export_backup().then(function (r) {
           if (!r.ok) return toast(r.error);
           var url = URL.createObjectURL(new Blob([r.data], { type: "application/octet-stream" })), a = document.createElement("a");
           a.href = url; a.download = r.filename; document.body.appendChild(a); a.click(); a.remove();
           setTimeout(function () { URL.revokeObjectURL(url); }, 4000);
           toast("Backup downloaded. Keep it somewhere safe.");
         });
       },
       restorepick: function () { $("#a-file").click(); },
    
    quit: function () { api.quit().then(function () { document.body.innerHTML = '<div class="auth" style="grid-template-columns:1fr"><div class="formside"><div class="formbox"><h1>Paksward has stopped</h1><p class="sub">Your vault is locked. You can close this tab.</p></div></div></div>'; }); },
    autolock: function (n) { n = +n; S.autolock = n; api.set_settings({ autolock_minutes: n }).then(function () { renderContent(); resetIdle(); toast(n ? "Auto-lock set to " + n + " minutes." : "Auto-lock is off."); }); }
  };
  /* Python owns the clipboard (it can clear it only if unchanged). If that is unavailable, use the browser's. */
  function copyOut(text, clearAfter) {
    return api.copy_text(text, clearAfter).then(function (r) { return { ok: r.ok, cleared: r.ok && clearAfter > 0 }; }, function () { return { ok: false }; })
      .then(function (r) {
        if (r.ok) return r;
        try { return navigator.clipboard.writeText(text).then(function () { return { ok: true, cleared: false }; }, function () { return { ok: false }; }); } catch (e) { return { ok: false }; }
      });
  }
  function byId(id) { return S.entries.filter(function (e) { return e.id === id; })[0]; }

  document.addEventListener("click", function (e) {
    var t = e.target.closest("[data-act]"); if (!t) { if (e.target.classList && e.target.classList.contains("scrim")) closeEditor(); return; }
    var f = A[t.dataset.act]; if (f) f(t.dataset.arg);
  });
  document.addEventListener("change", function (e) {
       if (e.target.id !== "a-file" || !e.target.files[0]) return;
       var reader = new FileReader();
       reader.onload = function () {
         api.restore_backup(String(reader.result)).then(function (r) {
           if (!r.ok) return aerr(r.error);
           $("#a-email").value = r.email; aerr();
           $("#a-err").style.color = "var(--ok, #1a7f4b)";
           $("#a-err").textContent = "Backup restored. Enter your password and your Secret Key to unlock it.";
           $("#a-secret-wrap").hidden = false;
         });
       };
       reader.readAsText(e.target.files[0]);
     });
  document.addEventListener("input", function (e) {
    var t = e.target;
    if (t.id === "q") { S.query = t.value; S.sel = null; if (S.nav === "watch" || S.nav === "gen" || S.nav === "set") { S.nav = "all"; render(); var q = $("#q"); q.focus(); q.setSelectionRange(q.value.length, q.value.length); } else renderContent(); }
    else if (t.id === "kit-ok") { $("#kit-go").disabled = !t.checked; }
    else if (t.id === "e-pw") meter(); else if (t.id === "a-pw" && S.mode === "register") meterReg();
    else if (t.dataset && t.dataset.g) {
      var k = t.dataset.g, g = S.gen;
      if (t.type === "range") { g[k] = +t.value; $("#g-len").textContent = t.value; } else g[k] = t.checked;
      regen();
    }
  });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && !$("#modal").classList.contains("hide")) closeEditor();
    if (e.key === "Enter" && S.screen === "auth" && e.target.tagName === "INPUT") { var b = $(".formbox .btn.primary"); if (b) b.click(); }
  });

  /* ================= AUTO-LOCK (UI side; Python enforces the same rule) ================= */
  var lastAct = Date.now();
  var lastPing = 0;
  function resetIdle() { lastAct = Date.now(); if (REAL && S.screen === "main" && lastAct - lastPing > 20000) { lastPing = lastAct; api.touch().catch(function () {}); } }
  ["mousemove", "mousedown", "keydown", "touchstart", "scroll", "wheel"].forEach(function (ev) { document.addEventListener(ev, resetIdle, { passive: true }); });
  setInterval(function () { if (S.screen === "main" && S.autolock > 0 && Date.now() - lastAct > S.autolock * 60000) A.lock("idle"); }, 5000);

  function render() {
    root.innerHTML = S.screen === "auth" ? authView() : S.screen === "kit" ? kitView() : shellView();
    if (S.screen === "main") renderContent();
  }
  if (REAL && !TOKEN) { root.innerHTML = '<div class="auth" style="grid-template-columns:1fr"><div class="formside"><div class="formbox"><h1>Open Paksward from your terminal</h1><p class="sub">This page needs the private link that Paksward prints when it starts. Look for the line starting with http://127.0.0.1 and open it.</p></div></div></div>'; return; }
  api.status().then(function (s) { S.preview = !!s.preview; if (s.unlocked) return enterVault(s.email); render(); });
  window.__paksward = { S: S, A: A };
})();
