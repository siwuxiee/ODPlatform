# frame_source

统一帧输入源抽象层 —— 把"摄像头 / 视频 / 图片 / 文件夹"封装成同一套接口,
推理脚本只关心 `for frame in source: ...`, 不再操心后端协商、双线程、跳帧逻辑。

## 依赖
- opencv-python
- numpy (随 opencv 来)
- pydantic >= 2.0
- Python >= 3.10

★ 不依赖任何宿主项目代码, 可整包拷贝到任意 Python 项目使用。

## 30 秒上手
    from frame_source import create_frame_source
    with create_frame_source("0") as src:      # 0=摄像头 / x.mp4=视频 / x.jpg=图 / ./dir=文件夹
        for frame in src:
            results = model(frame.image)        # frame.image 是 BGR ndarray
            print(frame.width, frame.height, frame.info.frame_index)

## 三种形态
| 工厂 | 用途 | 形态 |
|---|---|---|
| `create_frame_source`    | 通用(图片/视频/单摄像头) | `with ... for ...` |
| `create_threaded_source` | 实时推理(摄像头满速) | `with ... for ...`, 后台采集 |
| `create_async_source`    | async 调用方(web 服务) | `async with ... async for ...` |

## 拷走
    cp -r frame_source/ 你的项目/
    # 改一下 import 前缀即可, 包内全是相对 import