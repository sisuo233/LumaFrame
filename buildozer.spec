[app]
title = 光笺
package.name = filmborder
package.domain = com.filmborder

source.dir = .
source.include_exts = py,png,jpg,jpeg,webp,bmp,json,kv,ttf,otf,ttc
source.exclude_dirs = .git,.github,.venv,__pycache__,exports,bin,tests,.codex-remote-attachments

version = 0.1.5
requirements = python3,kivy,pillow,pyjnius,charset-normalizer==3.3.2
orientation = portrait
fullscreen = 0
presplash.filename = %(source.dir)s/assets/app_icon.png
icon.filename = %(source.dir)s/assets/app_icon.png

android.permissions = READ_MEDIA_IMAGES,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE
android.presplash_color = #F2F2F7
android.api = 35
android.minapi = 24
android.ndk_api = 24
android.archs = arm64-v8a
android.debug_artifact = apk
android.release_artifact = apk
android.accept_sdk_license = True
p4a.branch = v2026.05.09

[buildozer]
log_level = 2
warn_on_root = 1
