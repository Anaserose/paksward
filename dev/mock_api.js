/* Stand-in for the Python backend, used only for previewing the UI in a browser.
 * The real app answers the same calls from Python (see API.md). Nothing here is secure:
 * the strength rules and the dashboard maths are placeholders that Python will own and test.
 * Preview account:  demo@paksward.app / demo-password-1  /  Recovery Key: see DEMO_RECOVERY below */
(function () {
  "use strict";
  var LABELS = ["Terrible", "Weak", "Fair", "Strong", "Excellent"];
  var DICT = ("summer winter spring autumn password welcome dragon monkey sunshine princess master login admin football baseball " +
    "alex love blue falcon harbor lantern quiet maple river stone cloud tiger orange purple silver garden window bridge forest " +
    "pepper rocket violet canyon meadow ember anchor basket candle copper desert engine feather glacier hammer island jungle " +
    "kettle ladder marble nectar oyster pillow quartz ribbon saddle thunder umbrella velvet walnut yellow zephyr hunter").split(" ");
  var COMMON = ["password", "123456", "qwerty", "letmein", "iloveyou", "abc123", "passw0rd", "admin", "welcome"];
  var WORDS = ("acorn amber anchor apple arrow atlas badge basil beach bench berry birch blaze bloom bonus brave bread brick brook " +
    "cabin cable camel candy canoe cargo cedar chair chalk charm cherry chess cider cliff clock cloud clover coast cobra coral cotton " +
    "crane crown daisy delta denim diver dolphin dragon dream eagle earth echo elder ember fable falcon fern ferry field flame flint " +
    "forest fossil fox frost galaxy garden garlic ginger glacier globe grape gravel harbor hazel heron honey horizon island ivory " +
    "jacket jade jelly jungle kayak kettle kiwi koala lagoon lantern lemon lilac lotus lunar magnet mango maple marble meadow melon " +
    "mirror mist mocha moss nectar noble nutmeg oasis olive onyx orbit orchid otter oyster paddle panda pearl pepper pine planet plum " +
    "pocket prism pumpkin quartz quill rabbit radar raven reef ribbon river robin rocket saddle sage sailor salmon sand scarlet shadow " +
    "silver sketch sky slate sparrow spice spruce summit sunset swan thistle thunder tiger timber topaz tulip tundra umber valley " +
    "velvet violet walnut willow window winter wolf yarrow yonder zebra zephyr").split(" ");

  function rnd(n) { var lim = Math.floor(4294967296 / n) * n, b = new Uint32Array(1); do { crypto.getRandomValues(b); } while (b[0] >= lim); return b[0] % n; }
  function pick(s) { return s[rnd(s.length)]; }
  function shuffle(a) { for (var i = a.length - 1; i > 0; i--) { var j = rnd(i + 1), t = a[i]; a[i] = a[j]; a[j] = t; } return a; }

  function strength(pw) {
    if (!pw) return { bits: 0, level: 0, label: LABELS[0] };
    var lower = pw.toLowerCase(), pool = 0;
    if (/[a-z]/.test(pw)) pool += 26; if (/[A-Z]/.test(pw)) pool += 26; if (/\d/.test(pw)) pool += 10; if (/[^A-Za-z0-9]/.test(pw)) pool += 33;
    var bits = pw.length * Math.log2(pool || 1);
    if (new Set(pw.split("")).size < pw.length / 2) bits *= 0.6;
    if (/(.)\1{2,}/.test(pw)) bits -= 8;
    if (/(012|123|234|345|456|567|678|789|abc|bcd|cde|qwe|wer|asd)/i.test(pw)) bits -= 10;
    // dictionary words make a password much easier to guess than its length suggests
    var left = lower.replace(/0/g, "o").replace(/[41@]/g, "a").replace(/3/g, "e").replace(/\$/g, "s"), words = 0, used = 0, found = true;
    while (found) {
      found = false;
      for (var i = 0; i < DICT.length; i++) {
        var w = DICT[i];
        if (w.length >= 4 && left.indexOf(w) > -1) { left = left.replace(w, "\u0000"); words++; used += w.length; found = true; break; }
      }
    }
    if (words) bits = Math.min(bits, words * 9 + (pw.length - used) * 3.5);
    for (var c = 0; c < COMMON.length; c++) if (lower.indexOf(COMMON[c]) > -1) bits = Math.min(bits, 12);
    if (/^\d+$/.test(pw)) bits = Math.min(bits, pw.length * 3.3);
    bits = Math.max(0, bits);
    var level = bits < 26 ? 0 : bits < 40 ? 1 : bits < 60 ? 2 : bits < 80 ? 3 : 4;
    return { bits: Math.round(bits), level: level, label: LABELS[level] };
  }

  var AMB = /[Il1O0o]/g;
  function generate(o) {
    o = o || {};
    if (o.mode === "passphrase") {
      var n = Math.min(10, Math.max(3, o.words || 5)), sep = o.separator == null ? "-" : o.separator, ws = [];
      for (var i = 0; i < n; i++) { var w = pick(WORDS); ws.push(o.capitalize ? w[0].toUpperCase() + w.slice(1) : w); }
      var pw = ws.join(sep), bits = n * Math.log2(WORDS.length);
      if (o.digits) { pw += sep + rnd(100); bits += Math.log2(100); }
      var level = bits < 26 ? 0 : bits < 40 ? 1 : bits < 60 ? 2 : bits < 80 ? 3 : 4;
      return { password: pw, bits: Math.round(bits), level: level, label: LABELS[level] };
    }
    var len = Math.min(64, Math.max(8, o.length || 16)), sets = [];
    var L = "abcdefghijklmnopqrstuvwxyz", U = "ABCDEFGHIJKLMNOPQRSTUVWXYZ", D = "0123456789", S = "!@#$%^&*()-_=+?";
    if (o.lower !== false) sets.push(L); if (o.upper !== false) sets.push(U); if (o.digits !== false) sets.push(D); if (o.symbols !== false) sets.push(S);
    if (!sets.length) sets.push(L);
    if (o.avoidAmbiguous) sets = sets.map(function (s) { return s.replace(AMB, ""); });
    var all = sets.join(""), chars = sets.map(pick);
    while (chars.length < len) chars.push(pick(all));
    var p = shuffle(chars).join("");
    var s = strength(p);
    return { password: p, bits: Math.round(len * Math.log2(all.length)), level: s.level, label: s.label };
  }

  function ago(d) { return new Date(Date.now() - d * 864e5).toISOString(); }
  var seq = 0;
  function mk(site, user, pw, cat, days, fav) { return { id: "e" + (++seq), website: site, username: user, password: pw, category: cat, favorite: !!fav, updated_at: ago(days) }; }
  function sample() {
    return [
      mk("github.com", "alex.rivera", "Vq8#nT2!mXz4Lp7R", "Work", 12, 1),
      mk("gmail.com", "alex.rivera@mail.com", "hF6$kD9@wBe3Yc5N", "Email", 40, 1),
      mk("chase.com", "arivera", "correct-harbor-lantern-quiet-maple-7", "Banking", 25, 1),
      mk("netflix.com", "alex.rivera@mail.com", "Summer2019!", "Entertainment", 410),
      mk("spotify.com", "alexr", "Summer2019!", "Entertainment", 395),
      mk("x.com", "@alexrivera", "password123", "Social", 700),
      mk("instagram.com", "alex.rivera", "tiger-orange-cloud-7", "Social", 520),
      mk("amazon.com", "alex.rivera@mail.com", "Jt4%pL8#qWn2Vb6Z", "Shopping", 60),
      mk("ebay.com", "arivera_", "Hunter2024", "Shopping", 200),
      mk("slack.com", "alex@northwind.io", "Rk3&zM7!cYd9Qs5X", "Work", 8),
      mk("notion.so", "alex@northwind.io", "Xc9@bN4#vLt6Hm2P", "Work", 30),
      mk("dropbox.com", "alex.rivera@mail.com", "Blue-Falcon-88", "Work", 230),
      mk("linkedin.com", "alex.rivera", "Blue-Falcon-88", "Social", 230),
      mk("paypal.com", "alex.rivera@mail.com", "Gz5!wQ8$rTe3Nk7M", "Banking", 90)
    ];
  }

  var DEMO_SECRET = "PWSK-DEMO-0000-0000-0000-0000-0000-0000-0000-0000", DEMO_RECOVERY = "PWRK-DEMO-1111-1111-1111-1111-1111-1111-1111-1111";
  function fakeKey(prefix) {
    var A = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567", g = [prefix];
    for (var i = 0; i < 9; i++) { var t = ""; for (var j = 0; j < 4; j++) t += A[rnd(32)]; g.push(t); }
    return g.join("-");
  }
  function norm(k) { return (k || "").toUpperCase().replace(/[^A-Z0-9]/g, ""); }
  function policy(pw) {
    if (!pw || pw.length < 10) return "Password must be at least 10 characters.";
    if (strength(pw).level < 2) return "That password is too easy to guess. Use more words, or a longer mix of characters.";
    return null;
  }
  var accounts = { "demo@paksward.app": { email: "demo@paksward.app", password: "demo-password-1", secret: DEMO_SECRET, recovery: DEMO_RECOVERY, entries: sample(), failed: 0, locked: false, autolock: 5 } };
  var session = null, recovering = null;
  function acct() { return accounts[session]; }
  function need() { if (!session) throw new Error("Vault is locked."); return acct(); }
  function days(e) { return Math.max(0, (Date.now() - Date.parse(e.updated_at)) / 864e5); }
  function groups(list) {
    var by = {}; list.forEach(function (e) { (by[e.password] = by[e.password] || []).push(e.id); });
    return Object.keys(by).map(function (k) { return by[k]; }).filter(function (g) { return g.length > 1; });
  }
  function meta(e, reuse) {
    var s = strength(e.password), g = reuse[e.id] || 1;
    return { id: e.id, website: e.website, username: e.username, category: e.category, favorite: e.favorite,
      updated_at: e.updated_at, age_days: Math.round(days(e)), level: s.level, label: s.label, reused: g };
  }
  function reuseMap(list) { var m = {}; groups(list).forEach(function (g) { g.forEach(function (id) { m[id] = g.length; }); }); return m; }
  var OLD = 180;
  var ok = function (x) { return Promise.resolve(Object.assign({ ok: true }, x || {})); };
  var bad = function (error, x) { return Promise.resolve(Object.assign({ ok: false, error: error }, x || {})); };
  var valid = function (e) { return /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(e); };

  window.MOCK_API = {
    status: function () { return ok({ unlocked: !!session, email: session, preview: true }); },
    login: function (email, pw, secret) {
      var a = accounts[(email || "").trim().toLowerCase()];
      if (!valid((email || "").trim())) return bad("Please enter a valid email address.");
      if (!a) return bad("No account found with this email.");
      if (a.locked) return bad("Too many failed attempts. Try again in 23h 59m.");
      if (a.password !== pw) {
        a.failed++; if (a.failed >= 5) { a.locked = true; return bad("Incorrect password. Account locked for 24 hours."); }
        return bad("Incorrect password. " + (5 - a.failed) + " attempt(s) left before a 24-hour lock.");
      }
      a.failed = 0; session = a.email; return ok({ email: a.email });
    },
    register: function (email, pw, confirm) {
      email = (email || "").trim();
      if (!email || !pw || !confirm) return bad("Please fill in every field before creating your account.");
      if (!valid(email)) return bad("Please enter a valid email address.");
      var problem = policy(pw); if (problem) return bad(problem);
      if (pw !== confirm) return bad("Passwords do not match.");
      if (accounts[email.toLowerCase()]) return bad("An account with this email already exists.");
      var a = { email: email, password: pw, secret: fakeKey("PWSK"), recovery: fakeKey("PWRK"), entries: [], failed: 0, locked: false, autolock: 5 };
      accounts[email.toLowerCase()] = a; session = email.toLowerCase();
      return ok({ email: email, kit: { secret_key: a.secret, recovery_key: a.recovery } });
    },
    recover_start: function (email) {
      var a = accounts[(email || "").trim().toLowerCase()];
      if (!a) return bad("No account found for this email.");
      recovering = { a: a, verified: false }; return ok();
    },
    recover_verify: function (key) {
      var r = recovering; if (!r) return bad("Start again.");
      if (norm(r.a.recovery) !== norm(key)) { r.a.failed++; return bad("That Recovery Key doesn't match. " + Math.max(0, 5 - r.a.failed) + " attempt(s) left."); }
      r.verified = true; return ok();
    },
    recover_reset: function (pw, confirm) {
      var r = recovering; if (!r || !r.verified) return bad("Verify your Recovery Key first.");
      var problem = policy(pw); if (problem) return bad(problem);
      if (pw !== confirm) return bad("Passwords do not match.");
      r.a.password = pw; r.a.secret = fakeKey("PWSK"); r.a.failed = 0; r.a.locked = false; session = r.a.email; recovering = null;
      return ok({ email: r.a.email, kit: { secret_key: r.a.secret } });
    },
    get_secret_key: function () { return ok({ secret_key: need().secret }); },
    new_recovery_key: function () { var a = need(); a.recovery = fakeKey("PWRK"); return ok({ recovery_key: a.recovery }); },
    change_password: function (cur, pw, confirm) {
      var a = need(); if (a.password !== cur) return bad("Your current password is not correct.");
      var problem = policy(pw); if (problem) return bad(problem);
      if (pw !== confirm) return bad("Passwords do not match.");
      a.password = pw; return ok();
    },
    lock: function () { session = null; return ok(); },
    quit: function () { session = null; return ok(); },
    touch: function () { return ok(); },
    list_entries: function () { var a = need(), rm = reuseMap(a.entries); return Promise.resolve(a.entries.map(function (e) { return meta(e, rm); })); },
    get_entry: function (id) {
      var e = need().entries.filter(function (x) { return x.id === id; })[0]; if (!e) return bad("Entry not found.");
      return ok({ entry: Object.assign({}, e) });
    },
    add_entry: function (d) {
      var a = need(); if (!d.website || !d.username || !d.password) return bad("Website, username and password are required.");
      var e = { id: "e" + (++seq), website: d.website.trim(), username: d.username.trim(), password: d.password, category: d.category || "Other", favorite: !!d.favorite, updated_at: new Date().toISOString() };
      a.entries.push(e); return ok({ id: e.id });
    },
    update_entry: function (id, d) {
      var e = need().entries.filter(function (x) { return x.id === id; })[0]; if (!e) return bad("Entry not found.");
      if (!d.website || !d.username || !d.password) return bad("Website, username and password are required.");
      if (d.password !== e.password) e.updated_at = new Date().toISOString();
      e.website = d.website.trim(); e.username = d.username.trim(); e.password = d.password; e.category = d.category || "Other"; e.favorite = !!d.favorite;
      return ok();
    },
    set_favorite: function (id, v) { var e = need().entries.filter(function (x) { return x.id === id; })[0]; if (e) e.favorite = !!v; return ok(); },
    delete_entry: function (id) { var a = need(); a.entries = a.entries.filter(function (x) { return x.id !== id; }); return ok(); },
    copy_text: function (text, clear_after) {
      return new Promise(function (res) {
        function done(okk) { res({ ok: okk }); }
        try { navigator.clipboard.writeText(text).then(function () { done(true); if (clear_after) setTimeout(function () { try { navigator.clipboard.writeText(" "); } catch (e) {} }, clear_after * 1000); }, function () { done(false); }); }
        catch (e) { done(false); }
      });
    },
    check_strength: function (pw) { return Promise.resolve(strength(pw)); },
    generate: function (o) { return Promise.resolve(generate(o)); },
    security_report: function () {
      var a = need(), rm = reuseMap(a.entries), levels = [0, 0, 0, 0, 0], weak = [], old = [], loss = 0;
      a.entries.forEach(function (e) {
        var s = strength(e.password), l = 0; levels[s.level]++;
        if (s.level <= 1) { weak.push(e.id); l += 40; } else if (s.level === 2) { l += 15; }
        if (rm[e.id]) l += 35;
        if (days(e) > OLD) { old.push(e.id); l += 15; }
        loss += Math.min(100, l);
      });
      var n = a.entries.length, score = n ? Math.round(100 - loss / n) : 100;
      var grade = score >= 85 ? "Excellent" : score >= 70 ? "Good" : score >= 50 ? "Fair" : "At risk";
      return Promise.resolve({ total: n, score: score, grade: grade, levels: levels, weak: weak, old: old, reused: groups(a.entries), old_after_days: OLD });
    },
    check_breaches: function () {
      var a = need(), found = {}, bad = ["Summer2019!", "password123", "Hunter2024"];
      a.entries.forEach(function (e) { if (bad.indexOf(e.password) > -1) found[e.id] = 1000 + rnd(900000); });
      return new Promise(function (res) { setTimeout(function () { res({ ok: true, checked: a.entries.length, failed: 0, compromised: found }); }, 700); });
    },
    get_settings: function () { return ok({ settings: { autolock_minutes: need().autolock } }); },
    set_settings: function (s) { if (s && s.autolock_minutes != null) need().autolock = s.autolock_minutes; return ok(); }
  };
})();
