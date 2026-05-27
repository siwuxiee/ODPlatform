#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @FileName  : 美化_ex03plus_帧源与美化全自定义.py
# @Project   : visualization + frame_source examples
# @Function  : ex03 进阶版 —— 帧源任意定制 + 美化任意定制,两者联立
"""
ex03 的进阶版。ex03 是"能跑就行",这一版是"想改啥都能改":

    帧源侧:摄像头分辨率/帧率/后端/编码、是否线程化、丢前几帧、缓冲策略 …… 全可调
    美化侧:中文映射、每类颜色、字号、边框粗细、圆角、内边距、文字颜色、字体 …… 全可调
    模型侧:权重路径、置信度阈值、IoU、推理尺寸、设备 …… 全可调

用法:所有开关集中在下面【配置区】,改那里就行,主流程不用动。
源也可以用命令行临时覆盖:

    python 美化_ex03plus_帧源与美化全自定义.py                # 用配置区里的 SOURCE
    python 美化_ex03plus_帧源与美化全自定义.py 0              # 摄像头
    python 美化_ex03plus_帧源与美化全自定义.py demo.mp4       # 视频
    python 美化_ex03plus_帧源与美化全自定义.py ./images/      # 文件夹

目录摆放(本脚本同级):
    .
    ├── frame_source/        ← 帧源捕获模块
    ├── visualization/       ← 美化模块
    └── 美化_ex03plus_帧源与美化全自定义.py
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional, Tuple

import cv2
from ultralytics import YOLO

from odp_platform.frame_source import (
    create_frame_source,      # 普通同步源
    create_threaded_source,   # 线程化源(实时推理首选)
    CameraConfig,             # 摄像头硬件参数
    SourceType,               # 源类型枚举(保存时判断图片还是视频用)
)
from odp_platform.visualization import BeautifyVisualizer, DrawStyle


# ════════════════════════════════════════════════════════════════════
#                              配置区
#            想改什么都在这三块里改,下面的主流程不用动
# ════════════════════════════════════════════════════════════════════

@dataclass
class ModelCfg:
    """模型 / 推理参数。"""
    weights = "/home/siwuxie/Projects/ODPlatform/apps/platform/tests/美化测试/train3-20250704-165500-yolo11n-best.pt"
    conf: float = 0.55          # 置信度阈值,低于此的框丢掉
    iou: float = 0.45           # NMS 的 IoU 阈值
    imgsz: int = 640            # 推理输入尺寸
    device: Optional[str] = None  # None=自动; "cpu" / "0"(第0张GPU) / "0,1"


@dataclass
class SourceCfg:
    """帧源参数。SOURCE 决定输入,其余决定怎么取帧。"""
    source: str = "0"           # "0"摄像头 / "x.mp4"视频 / "x.jpg"图 / "./dir/"文件夹

    # —— 是否线程化 ——
    # 摄像头实时推理 -> True;视频 -> True/False 均可;
    # ★ 单张图片 / 文件夹 -> 必须 False(图片帧太少,线程化会来不及读就采完,导致取不到帧)
    threaded: bool = True
    warmup_frames: int = 30     # 线程化时丢掉前 N 帧(摄像头刚启动帧率不稳),非摄像头设 0 也行
    buffer: str = "latest"      # "latest"只留最新帧(实时) / "bounded"有界队列(不丢帧)
    buffer_size: int = 1        # buffer="bounded" 时的队列长度

    # —— 摄像头硬件参数(source 是数字时才生效;视频/图片忽略)——
    cam_width: int = 1280
    cam_height: int = 720
    cam_fps: int = 30
    cam_backend: str = "v4l2"   # "auto" / "msmf"(Win高帧率) / "dshow"(Win) / "v4l2"(Linux)
    cam_codec: str = "MJPG"     # "MJPG" / "YUYV" / "H264" / "MP4V"


@dataclass
class BeautifyCfg:
    """美化参数。"""
    use_label_mapping: bool =  True # True 才会把英文类别显示成中文

    # 英文类别 -> 中文。键必须是模型 names 里的英文名(启动时脚本会打印 names 给你对照)
    label_mapping: Dict[str, str] = field(default_factory=lambda: {
        "person": "人员",
        "head": "头",
        "ordinary_clothes":"普通衣服",
        # "dog": "狗", ...  按你的模型类别补
    })

    # 英文类别 -> 框颜色(BGR!不是 RGB)。没写的类别用 default_color
    color_mapping: Dict[str, Tuple[int, int, int]] = field(default_factory=lambda: {
        "person": (0, 255, 0),   # 绿
        "head": (0, 0, 255),      # 蓝(BGR)
        "ordinary_clothes": (227, 133, 93), # 红色
    })
    default_color: Tuple[int, int, int] = (0, 255, 0)

    font_path: Optional[str] = r"/home/siwuxie/Projects/ODPlatform/apps/platform/src/odp_platform/visualization/assets/LXGWWenKaiGB-Bold.ttf" # None=用模块内置字体; 也可填中文 ttf 的绝对路径

    # —— 样式 ——
    style_auto_adapt: bool = True    # True=按画面尺寸自动算样式(下面几个数被当作 720p 基准缩放)
    font_size: int = 26              # 字号
    line_width: int = 4              # 边框粗细
    padding_x: int = 10              # 标签左右内边距
    padding_y: int = 10              # 标签上下内边距
    radius: int = 8                  # 圆角半径
    text_color: Tuple[int, int, int] = (0, 0, 0)  # 文字颜色 BGR


@dataclass
class OutputCfg:
    """显示 / 保存。"""
    show_window: bool = True         # 弹窗实时预览(无显示器的服务器请设 False)
    window_name: str = "frame_source + visualization (plus)"
    save: bool = False               # 是否把美化结果存盘
    save_dir: str = "./outputs"      # 存哪
    draw_fps: bool = True            # 左上角叠加实时 FPS


# 三块配置实例(改上面 dataclass 的默认值,或在这里临时覆盖都行)
MODEL = ModelCfg()
SRC = SourceCfg()
BEAUTY = BeautifyCfg()
OUT = OutputCfg()

# ════════════════════════════════════════════════════════════════════
#                          以下为主流程
#                  一般不用改,改配置区就够了
# ════════════════════════════════════════════════════════════════════


def build_source(src: SourceCfg):
    """按配置造帧源,返回一个可 with 的源对象。"""
    # 摄像头硬件参数(只有 source 是数字时这套才会被用上)
    cam_cfg = CameraConfig(
        width=src.cam_width,
        height=src.cam_height,
        fps=src.cam_fps,
        backend=src.cam_backend,
        codec=src.cam_codec,
    )
    if src.threaded:
        return create_threaded_source(
            src.source,
            camera_config=cam_cfg,
            buffer=src.buffer,
            buffer_size=src.buffer_size,
            warmup_frames=src.warmup_frames,
        )
    return create_frame_source(src.source, camera_config=cam_cfg)


def build_visualizer(beauty: BeautifyCfg, class_names) -> BeautifyVisualizer:
    """按配置造美化器。class_names 用模型的 names。"""
    return BeautifyVisualizer(
        labels=list(class_names),
        label_mapping=beauty.label_mapping,
        color_mapping=beauty.color_mapping,
        default_color=beauty.default_color,
        font_path=beauty.font_path,
    )


def build_style(beauty: BeautifyCfg, h: int, w: int) -> DrawStyle:
    """按配置造绘制样式。自适应模式下按画面尺寸缩放,否则用固定值。"""
    if beauty.style_auto_adapt:
        return DrawStyle.from_image_size(
            h, w,
            base_font_size=beauty.font_size,
            base_line_width=beauty.line_width,
            base_padding_x=beauty.padding_x,
            base_padding_y=beauty.padding_y,
            base_radius=beauty.radius,
            font_path=beauty.font_path,
            text_color=beauty.text_color,
        )
    return DrawStyle(
        font_size=beauty.font_size,
        line_width=beauty.line_width,
        padding_x=beauty.padding_x,
        padding_y=beauty.padding_y,
        radius=beauty.radius,
        font_path=beauty.font_path,
        text_color=beauty.text_color,
    )


def annotate(model, viz, style, image, mcfg: ModelCfg):
    """一帧的完整处理:YOLO 推理 -> 打包 Detection -> 美化绘制。"""
    result = model(
        image,
        conf=mcfg.conf,
        iou=mcfg.iou,
        imgsz=mcfg.imgsz,
        device=mcfg.device,
        verbose=False,
    )[0]

    detections = BeautifyVisualizer.from_yolo_results(
        boxes=result.boxes.xyxy.cpu().numpy(),
        confidences=result.boxes.conf.cpu().numpy(),
        labels=[model.names[i] for i in result.boxes.cls.int().cpu().tolist()],
    )
    return viz.draw(image, detections, style=style, use_label_mapping=BEAUTY.use_label_mapping)


class Saver:
    """按源类型把结果存盘:图片源逐张存图,视频/摄像头存成一个 mp4。"""

    def __init__(self, out: OutputCfg):
        self.out = out
        self.writer = None
        self.img_idx = 0
        if out.save:
            Path(out.save_dir).mkdir(parents=True, exist_ok=True)

    def write(self, frame_image, info):
        if not self.out.save:
            return
        is_image = info.source_type in (SourceType.IMAGE, SourceType.IMAGE_FOLDER)
        if is_image:
            name = info.filename or f"frame_{self.img_idx:06d}.jpg"
            cv2.imwrite(str(Path(self.out.save_dir) / Path(name).name), frame_image)
            self.img_idx += 1
        else:
            if self.writer is None:
                h, w = frame_image.shape[:2]
                fps = info.fps or 25.0
                fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                path = str(Path(self.out.save_dir) / "annotated.mp4")
                self.writer = cv2.VideoWriter(path, fourcc, fps, (w, h))
            self.writer.write(frame_image)

    def release(self):
        if self.writer is not None:
            self.writer.release()


def main():
    # 命令行可临时覆盖源(不写就用配置区的 SRC.source)
    if len(sys.argv) > 1:
        SRC.source = sys.argv[1]

    print(f"加载模型: {MODEL.weights}")
    model = YOLO(MODEL.weights)
    print(f"模型类别 names = {model.names}")
    print("  ↑ 把上面这些英文名填进 BeautifyCfg 的 label_mapping / color_mapping 即可定制中文与颜色")

    viz = build_visualizer(BEAUTY, model.names.values())
    saver = Saver(OUT)

    style = None  # 第一帧拿到尺寸后再建(尺寸自适应需要 h/w)
    tick = cv2.getTickCount()
    fps_val = 0.0

    try:
        with build_source(SRC) as src:
            for frame in src:
                if style is None:
                    h, w = frame.image.shape[:2]
                    style = build_style(BEAUTY, h, w)

                annotated = annotate(model, viz, style, frame.image, MODEL)

                # 叠加 FPS(可选)
                if OUT.draw_fps:
                    now = cv2.getTickCount()
                    fps_val = cv2.getTickFrequency() / (now - tick)
                    tick = now
                    cv2.putText(annotated, f"FPS: {fps_val:.1f}", (10, 30),
                                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)

                saver.write(annotated, frame.info)

                if OUT.show_window:
                    cv2.imshow(OUT.window_name, annotated)
                    if cv2.waitKey(1) & 0xFF in (ord("q"), 27):  # q / Esc 退出
                        break
    finally:
        saver.release()
        if OUT.show_window:
            cv2.destroyAllWindows()
    print("结束。" + (f" 输出已存到 {OUT.save_dir}" if OUT.save else ""))


if __name__ == "__main__":
    main()