[app]
title = Film Border
package.name = filmborder
package.domain = com.filmborder

source.dir = .
source.include_exts = py,png,jpg,jpeg,webp,bmp,json,kv,ttf,otf,ttc

version = 0.1.0
requirements = python3,kivy,pillow,plyer,pyjnius
orientation = portrait
fullscreen = 0

android.permissions = READ_MEDIA_IMAGES,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE
android.minapi = 24
android.archs = arm64-v8a, armeabi-v7a
android.accept_sdk_license = True
p4a.branch = v2026.05.09

[buildozer]
log_level = 2
warn_on_root = 1
