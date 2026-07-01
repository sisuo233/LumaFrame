[app]
title = Film Border
package.name = filmborder
package.domain = com.filmborder

source.dir = .
source.include_exts = py,png,jpg,jpeg,webp,bmp,json,kv,ttf,otf,ttc
source.exclude_dirs = .git,.github,.venv,__pycache__,exports,bin,.codex-remote-attachments

version = 0.1.3
requirements = python3,kivy,pillow,pyjnius
orientation = portrait
fullscreen = 0

android.permissions = READ_MEDIA_IMAGES,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE
android.api = 35
android.minapi = 24
android.ndk_api = 24
android.archs = arm64-v8a
android.accept_sdk_license = True
p4a.branch = v2026.05.09

[buildozer]
log_level = 2
warn_on_root = 1
