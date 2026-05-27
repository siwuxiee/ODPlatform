#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @FileName  : config.py
# @Author    : 雨霓同学
# @Project   : ODPlatform / frame_source
# @Function  : 摄像头硬件配置 (Pydantic v2)
"""
摄像头配置类(基于 Pydantic v2 BaseModel,不继承宿主项目内部配置基类)。

设计原则:
    - 配置层不绑 logger:验证失败直接 raise ValidationError,
      由调用方决定记录方式
    - 字段封闭取值用 Literal,拼写错误第一时间被 Pydantic 拦下
    - 不可冻结:factory.py 需要 model_copy(update=...) 替换 camera_id
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


# 封闭取值(IDE 自动补全 + 错拼立刻 raise)
CameraBackend = Literal["auto", "msmf", "dshow", "v4l2"]
CameraCodec   = Literal["MJPG", "YUYV", "H264", "MP4V"]


class CameraConfig(BaseModel):
    """
    摄像头配置(Pydantic v2)。

    示例:
        # 默认配置
        config = CameraConfig()

        # 高帧率(Windows 必须 MSMF 后端 + MJPG 编码)
        config = CameraConfig(width=1280, height=720, fps=90, backend="msmf")

    字段说明:
        camera_id : OpenCV 设备 ID(≥ 0)
        width     : 请求分辨率宽(实际生效以 set+get 协商结果为准)
        height    : 请求分辨率高
        fps       : 请求帧率(高帧率必须配 MJPG codec + msmf 后端)
        backend   : 摄像头后端
            "auto"  跨平台默认,系统自选
            "msmf"  Windows Media Foundation,支持高帧率
            "dshow" DirectShow,Windows 兼容性好
            "v4l2"  Linux Video4Linux2
        codec     : FOURCC 编码,高帧率必须 MJPG
    """

    model_config = ConfigDict(
        extra="forbid",              # 拼错字段名第一时间拦下
        validate_assignment=True,    # 后续赋值也走验证
    )

    camera_id: int = Field(default=0,    ge=0,            description="OpenCV 设备 ID")
    width:     int = Field(default=1280, gt=0, le=7680,   description="请求分辨率宽")
    height:    int = Field(default=720,  gt=0, le=4320,   description="请求分辨率高")
    fps:       int = Field(default=30,   gt=0, le=1000,   description="请求帧率")

    backend: CameraBackend = Field(default="auto", description="摄像头后端")
    codec:   CameraCodec   = Field(default="MJPG", description="FOURCC 编码")

    def get_resolution(self) -> tuple[int, int, int]:
        """返回 (width, height, fps) 三元组"""
        return (self.width, self.height, self.fps)