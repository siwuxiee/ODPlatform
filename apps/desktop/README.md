# ODPlatform Desktop

PySide6 桌面推理客户端，支持四种检测模式：
- **摄像头** — 实时画面目标检测
- **图片** — 单张图片检测
- **视频** — 视频文件检测
- **文件夹** — 批量图片检测

## 运行

```bash
# 安装
pip install -e apps/desktop/

# 启动
odp-desktop
```

## Wayland 兼容性

如果 Qt 在 Wayland 下显示异常，强制使用 X11：
```bash
odp-desktop -platform xcb
```
