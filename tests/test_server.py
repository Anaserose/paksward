"""The local web server: what it serves, and what it refuses."""
import http.client
import json
import threading
import unittest
import unittest.mock

from tests.helpers import DataDirTest, read_text, write_text
from paksward.api import Api
from paksward.server import PakswardServer

PW = "Zebra-4-Quartz-Lantern-91"


class ServerTest(DataDirTest):
    def setUp(self):
        super().setUp()
        self.api = Api(copy_fn=lambda t, s: True)
        self.srv = PakswardServer(self.api, token="test-token-123")
        self.port = self.srv.server_address[1]
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.addCleanup(self._stop)

    def _stop(self):
        self.srv.shutdown()
        self.srv.server_close()

    def req(self, method, path, body=None, headers=None, host=None):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        h = {"Host": host or f"127.0.0.1:{self.port}"}
        h.update(headers or {})
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            h.setdefault("Content-Type", "application/json")
        c.request(method, path, body=data, headers=h)
        r = c.getresponse()
        raw = r.read()
        c.close()
        return r.status, r.headers, raw

    def call(self, name, *args, token="test-token-123", **kw):
        h = {"X-Paksward-Token": token} if token is not None else {}
        h.update(kw.pop("headers", {}))
        status, _, raw = self.req("POST", f"/api/{name}", {"args": list(args)}, headers=h, **kw)
        return status, json.loads(raw)


class TestStaticFiles(ServerTest):
    def test_index_is_served_and_marked_as_real_backend(self):
        status, headers, raw = self.req("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn(b'name="paksward-server"', raw)
        self.assertIn("text/html", headers["Content-Type"])

    def test_assets_served(self):
        for path, kind in (("/app.js", "javascript"), ("/styles.css", "css")):
            status, headers, _ = self.req("GET", path)
            self.assertEqual(status, 200, path)
            self.assertIn(kind, headers["Content-Type"])

    def test_security_headers(self):
        _, h, _ = self.req("GET", "/")
        self.assertIn("default-src 'self'", h["Content-Security-Policy"])
        self.assertEqual(h["X-Content-Type-Options"], "nosniff")
        self.assertEqual(h["Cache-Control"], "no-store")
        self.assertEqual(h["X-Frame-Options"], "DENY")

    def test_cannot_escape_the_frontend_folder(self):
        for p in ("/../main.py", "/%2e%2e/main.py", "/..%2fmain.py", "/../../etc/passwd", "/../data/users.json",
                  "/%2e%2e%2fpaksward%2fapi.py", "//etc/passwd", "/paksward/api.py"):
            status, _, raw = self.req("GET", p)
            self.assertEqual(status, 404, p)
            self.assertNotIn(b"class Api", raw)

    def test_allowed_file_types_outside_the_folder_are_also_refused(self):
        # assets/logo.png is a servable type but lives outside frontend/, so only the folder check stops it.
        self.assertEqual(self.req("GET", "/../assets/logo.png")[0], 404)
        self.assertEqual(self.req("GET", "/%2e%2e/assets/logo.png")[0], 404)
        self.assertEqual(self.req("GET", "/..%2fassets%2flogo.png")[0], 404)

    def test_symlink_pointing_outside_the_folder_is_refused(self):
        import os, tempfile
        outside = tempfile.mkdtemp()
        write_text(os.path.join(outside, "secret.js"), "TOP-SECRET")
        site = tempfile.mkdtemp()
        write_text(os.path.join(site, "index.html"), "<html></head></html>")
        try:
            os.symlink(os.path.join(outside, "secret.js"), os.path.join(site, "link.js"))
        except (OSError, NotImplementedError):
            self.skipTest("symlinks not supported here")
        srv = PakswardServer(self.api, token="t", frontend_dir=site)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        self.addCleanup(lambda: (srv.shutdown(), srv.server_close()))
        c = http.client.HTTPConnection("127.0.0.1", srv.server_address[1], timeout=5)
        c.request("GET", "/link.js", headers={"Host": f"127.0.0.1:{srv.server_address[1]}"})
        r = c.getresponse()
        self.assertEqual(r.status, 404)
        self.assertNotIn(b"TOP-SECRET", r.read())

    def test_only_listed_file_types_are_served(self):
        self.assertEqual(self.req("GET", "/API.md")[0], 404)       # exists in frontend/ but is not a served type

    def test_data_folder_is_never_reachable(self):
        self.assertEqual(self.req("GET", "/users.json")[0], 404)
        self.assertEqual(self.req("GET", "/vaults/x.enc")[0], 404)


class TestOfflineOnly(ServerTest):
    def test_interface_files_reference_no_external_addresses(self):
        import glob, os, re
        from paksward.server import FRONTEND_DIR
        for path in glob.glob(os.path.join(FRONTEND_DIR, "*")):
            if path.endswith((".html", ".css", ".js")):
                text = read_text(path)
                found = re.findall(r"(?:https?:)?//[A-Za-z0-9.-]+\.[a-z]{2,}", text)
                self.assertEqual(found, [], f"{os.path.basename(path)} refers to {found}")

    def test_csp_forbids_remote_loading(self):
        _, h, _ = self.req("GET", "/")
        csp = h["Content-Security-Policy"]
        self.assertNotIn("http", csp)
        self.assertIn("connect-src 'self'", csp)
        self.assertIn("font-src 'none'", csp)


class TestApiProtection(ServerTest):
    def test_token_is_required(self):
        self.assertEqual(self.call("status", token=None)[0], 401)
        self.assertEqual(self.call("status", token="wrong")[0], 401)
        self.assertEqual(self.call("status", token="")[0], 401)
        self.assertEqual(self.call("status")[0], 200)

    def test_wrong_host_header_is_refused(self):                  # DNS rebinding
        self.assertEqual(self.req("GET", "/", host="evil.example.com")[0], 403)
        self.assertEqual(self.call("status", host="evil.example.com")[0], 403)
        self.assertEqual(self.call("status", host=f"localhost:{self.port}")[0], 200)

    def test_foreign_origin_is_refused(self):                     # another web page in the browser
        self.assertEqual(self.call("status", headers={"Origin": "https://evil.example.com"})[0], 403)
        self.assertEqual(self.call("status", headers={"Origin": f"http://127.0.0.1:{self.port}"})[0], 200)

    def test_json_content_type_required(self):
        s, _, _ = self.req("POST", "/api/status", {"args": []}, headers={"X-Paksward-Token": "test-token-123", "Content-Type": "text/plain"})
        self.assertEqual(s, 415)

    def test_unknown_and_private_methods_refused(self):
        for name in ("nope", "_enter", "__init__", "users", "entries", "vault_key", "../status", ""):
            self.assertEqual(self.call(name)[0], 404, name)

    def test_bad_bodies(self):
        h = {"X-Paksward-Token": "test-token-123", "Content-Type": "application/json", "Host": f"127.0.0.1:{self.port}"}
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        c.request("POST", "/api/status", body=b"{not json", headers=h)
        self.assertEqual(c.getresponse().status, 400)
        c.close()
        self.assertEqual(self.req("POST", "/api/status", {"args": "not-a-list"}, headers={"X-Paksward-Token": "test-token-123"})[0], 400)
        self.assertEqual(self.call("login", 1, 2, 3, 4, 5, 6)[0], 400)             # wrong argument count

    def test_oversized_body_refused(self):
        h = {"X-Paksward-Token": "test-token-123", "Content-Type": "application/json", "Content-Length": "5000000",
             "Host": f"127.0.0.1:{self.port}"}
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        c.putrequest("POST", "/api/status", skip_host=True)
        for k, v in h.items():
            c.putheader(k, v)
        c.endheaders()
        self.assertEqual(c.getresponse().status, 413)
        c.close()

    def test_get_is_not_an_api_call(self):
        self.assertEqual(self.req("GET", "/api/status", headers={"X-Paksward-Token": "test-token-123"})[0], 404)

    def test_server_listens_on_loopback_only(self):
        self.assertEqual(self.srv.server_address[0], "127.0.0.1")

    def test_internal_errors_do_not_leak_details(self):
        self.call("register", "a@b.co", PW, PW)
        with unittest.mock.patch.object(Api, "list_entries", side_effect=RuntimeError("SECRET-DETAIL")):
            status, body = self.call("list_entries")
        self.assertEqual(status, 500)
        self.assertNotIn("SECRET-DETAIL", json.dumps(body))


class TestHardening(ServerTest):
    def test_odd_token_header_is_refused_not_a_crash(self):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        c.request("POST", "/api/status", body=b'{"args":[]}',
                  headers={"Host": f"127.0.0.1:{self.port}", "Content-Type": "application/json", "X-Paksward-Token": "caf\u00e9"})
        self.assertEqual(c.getresponse().status, 401)

    def test_browser_isolation_headers_are_sent(self):
        _, headers, _ = self.req("GET", "/")
        names = {k.lower(): v for k, v in headers.items()}
        for h in ("cross-origin-opener-policy", "cross-origin-resource-policy", "permissions-policy",
                  "x-content-type-options", "content-security-policy"):
            self.assertIn(h, names)

    def test_idle_connections_time_out(self):
        from paksward.server import Handler
        self.assertLessEqual(Handler.timeout, 30)

    def test_oversized_fields_are_cut_off(self):
        self.call("register", "a@b.co", PW, PW)
        _, r = self.call("add_entry", {"website": "w" * 5000, "username": "u" * 5000, "password": "p" * 5000})
        entry = self.call("get_entry", r["id"])[1]["entry"]
        self.assertEqual((len(entry["website"]), len(entry["username"]), len(entry["password"])), (500, 500, 1024))

    def test_non_object_entry_data_is_rejected_cleanly(self):
        self.call("register", "a@b.co", PW, PW)
        self.assertFalse(self.call("add_entry", "not-an-object")[1]["ok"])


class TestQuit(ServerTest):
    def test_quit_needs_the_token_and_then_stops_the_server_and_locks(self):
        self.call("register", "a@b.co", PW, PW)
        self.assertEqual(self.call("quit", token="wrong")[0], 401)
        self.assertTrue(self.api.status()["unlocked"])
        status, body = self.call("quit")
        self.assertEqual((status, body["ok"]), (200, True))
        self.assertFalse(self.api.status()["unlocked"])
        for _ in range(100):
            try:
                self.req("GET", "/")
            except OSError:
                break
            threading.Event().wait(0.05)
        else:
            self.fail("server kept running after quit")


class TestEndToEndOverHttp(ServerTest):
    def test_full_session(self):
        self.assertEqual(self.call("status")[1]["unlocked"], False)
        s, r = self.call("register", "Alice@Example.com", PW, PW)
        self.assertTrue(r["ok"], r)
        s, r = self.call("add_entry", {"website": "github.com", "username": "alice", "password": "SECRET-VALUE-123", "category": "Work"})
        self.assertTrue(r["ok"])
        entry_id = r["id"]
        s, listing = self.call("list_entries")
        self.assertEqual(len(listing), 1)
        self.assertNotIn("SECRET-VALUE-123", json.dumps(listing))
        self.assertEqual(self.call("get_entry", entry_id)[1]["entry"]["password"], "SECRET-VALUE-123")
        self.assertIn("score", self.call("security_report")[1])
        self.assertIn("password", self.call("generate", {"length": 12})[1])
        self.assertEqual(self.call("check_strength", "password123")[1]["label"], "Terrible")
        self.call("lock")
        s, r = self.call("list_entries")
        self.assertEqual((s, r.get("locked")), (200, True))                          # locked is a normal answer, not a crash
        self.assertTrue(self.call("login", "alice@example.com", PW)[1]["ok"])

    def test_unicode_survives_the_round_trip(self):
        self.call("register", "a@b.co", PW, PW)
        _, r = self.call("add_entry", {"website": "réseau.fr", "username": "aliçe", "password": "pässwörd ✓"})
        self.assertEqual(self.call("get_entry", r["id"])[1]["entry"]["password"], "pässwörd ✓")


if __name__ == "__main__":
    unittest.main()
