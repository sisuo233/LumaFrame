# 光笺 LumaFrame

一个用 Python 写的照片胶片边框小应用，支持导入照片、添加相纸边框与胶卷信息，并保存 JPEG 成片。

## 功能

- 打开相册选择照片
- 选择胶卷，支持品牌分类和搜索
- 选择相纸样式
- 调整底部文字位置
- 自定义上边框和左右边框大小
- 可选相机品牌、Logo 和型号信息
- 可选常用输出比例
- 保存 JPEG 成片

## 本地运行

本机已经安装了并行的 Python 3.12.10，并用它创建了 `.venv`。不要用默认 Python 3.14 跑 Kivy，Kivy 的 Windows 依赖包还没有完整支持 3.14。

```powershell
cd LumaFrame
.\.venv\Scripts\python.exe main.py
```

如果需要重建环境：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## 测试图片处理核心

```powershell
.\.venv\Scripts\python.exe film_frame.py input.jpg exports/output.jpg --film "Kodak Portra 400"
```

## 运行回归测试

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## Android 打包

请看 [BUILD_APK.md](BUILD_APK.md)。

简短版：

```bash
bash scripts/setup_android_build_env.sh
bash scripts/build_apk.sh
```

生成的 APK 会在：

```text
bin/
```

## 字体

程序会优先寻找系统中文字体。当前 Windows 环境下通常会使用：

```text
C:\Windows\Fonts\NotoSansSC-VF.ttf
```

如果安卓机型上中文显示不理想，可以把中文字体放到：

```text
assets/fonts/NotoSansSC-Regular.otf
```

然后重新打包。

