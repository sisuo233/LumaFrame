# Android APK 打包说明

当前项目使用 `Kivy + Pillow + Buildozer` 打包 Android APK。建议在 WSL2 Ubuntu 或 Linux 中打包，不建议直接在 Windows PowerShell 里打。

## 方式一：GitHub Actions 云打包

项目已经包含：

```text
.github/workflows/build-apk.yml
```

把整个项目上传到 GitHub 后，可以在 GitHub 云端自动生成 APK。

### 1. 上传项目

如果当前文件夹还不是 Git 仓库，在项目目录执行：

```powershell
git init
git add .
git commit -m "Initial LumaFrame app"
git branch -M main
git remote add origin https://github.com/你的用户名/你的仓库名.git
git push -u origin main
```

如果已经是仓库，只需要：

```powershell
git add .
git commit -m "Add GitHub APK build workflow"
git push
```

### 2. 手动触发打包

打开 GitHub 仓库页面：

```text
Actions -> Build Android APK -> Run workflow
```

也可以直接 push 到 `main` 或 `master`，会自动打包。

### 3. 下载 APK

打包完成后进入对应 workflow 运行记录，在页面底部 `Artifacts` 下载：

```text
lumaframe-test-apk
```

下载后解压，里面就是 `.apk`。

第一次云打包会下载 Android SDK、NDK、Gradle 等依赖，通常比较慢；后续会使用缓存。

## 方式二：WSL Ubuntu 本地打包

### 1. 安装 WSL Ubuntu

在管理员 PowerShell 中执行：

```powershell
wsl --install -d Ubuntu
```

安装完成后按提示重启电脑，然后打开 Ubuntu。

### 2. 进入项目目录

在 Ubuntu 中执行：

```bash
cd /mnt/c/Users/sisuo/Desktop/胶片边框
```

### 3. 安装打包依赖

```bash
bash scripts/setup_android_build_env.sh
```

如果提示找不到 `buildozer`，执行：

```bash
export PATH="$HOME/.local/bin:$PATH"
```

### 4. 构建 APK

```bash
bash scripts/build_apk.sh
```

脚本会把项目同步到 `~/lumaframe-build` 再打包，避免中文路径影响 Android 工具链。

生成的 APK 会复制回：

```text
bin/
```

### 5. 安装到手机

把 `bin/` 里的 `.apk` 发到安卓手机安装即可。第一次安装可能需要允许“安装未知来源应用”。
