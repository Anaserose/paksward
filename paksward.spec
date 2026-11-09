# PyInstaller recipe:  pyinstaller paksward.spec
#   Windows -> dist/Paksward/Paksward.exe     macOS -> dist/Paksward.app     Linux -> dist/Paksward/Paksward
import sys

ICONS = "packaging/icon/"
windowed = sys.platform in ("win32", "darwin")        # no terminal window on Windows/macOS; Linux keeps one
a = Analysis(["main.py"], datas=[("frontend", "frontend"), (ICONS + "icon-256.png", ".")], excludes=["tkinter"])
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="Paksward", console=not windowed,
          icon=ICONS + "Paksward.ico" if sys.platform == "win32" else None)
coll = COLLECT(exe, a.binaries, a.datas, name="Paksward")
if sys.platform == "darwin":
    app = BUNDLE(coll, name="Paksward.app", icon=ICONS + "Paksward.icns", bundle_identifier="app.paksward.desktop",
                 info_plist={"CFBundleDisplayName": "Paksward", "NSHighResolutionCapable": True})
