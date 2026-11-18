# 照片视频格式转换

把 HEIC/HEIF 照片批量转为 JPG，把 MOV、MP4、M4V 视频转为 H.264 MP4。视频遇到可识别的 HLG/PQ HDR 时会先做 HDR→SDR 色调映射；照片保留原尺寸、ICC 色彩配置和 EXIF。源文件不修改，结果写入另一目录。

## 环境

- Python（已在 Python 3.13 上用合成素材试跑）及 `pillow`、`pillow-heif`：`python -m pip install pillow pillow-heif`
- `ffmpeg` 和 `ffprobe`：安装后确保两个命令都在 `PATH` 中。视频转换需要带 `zscale`、`tonemap`、`libx264` 的 FFmpeg 构建；可分别用 `ffmpeg -filters` 和 `ffmpeg -encoders` 查看构建是否包含所需功能。
- 视频脚本使用 Bash 和 GNU `stat`，Windows 可使用 Git Bash。

## 使用

在项目目录运行，路径可以写成自己的实际路径。第一次试跑建议先创建**与源目录不同的空输出目录**：

```bash
python heic2jpg.py "照片和视频所在目录" "转换结果目录"
bash mov2mp4.sh "照片和视频所在目录" "转换结果目录"
python verify.py "照片和视频所在目录" "转换结果目录"
```

前两个脚本必须传源目录；省略输出目录时，会在源目录同级创建 `<源目录名>_转换`。图片脚本默认跳过已有 JPG，只有加 `-f` / `--force` 才覆盖；**视频脚本当前会覆盖同名 MP4**，重跑前应先检查输出目录。两个转换脚本只处理源目录下的文件，不递归查找子目录。

`verify.py` 会核对源文件与结果的文件名、数量，以及图片尺寸、ICC **有无**、视频时长/分辨率/编码/音频等；不会比对 ICC 的具体内容，也不会核查 EXIF 是否完整或是否含 GPS。它不能替代肉眼抽看画面；尤其是 HDR 色调映射结果，要抽查颜色和亮部。

## 转换方式与限制

- 图片：`quality=95`、`subsampling=0`（4:4:4），保留 ICC 与 EXIF。文件通常会比使用 4:2:0 时大；需要小文件可调整 [heic2jpg.py](heic2jpg.py) 顶部的 `SUBSAMPLING`。
- 视频：`ffprobe` 读取首条视频流的色彩传递标记；识别到 `arib-std-b67`（HLG）或 `smpte2084`（PQ）时，用 `zscale` + `tonemap=hable` 映射到 SDR BT.709，再以 `libx264`、`CRF=17` 编码。其他标记不会做 HDR 色调映射，**但仍会重新编码视频**；标记缺失或其他 HDR 格式要自行检查。
- 音频直接复制。若源音频格式不能放进 MP4，转换可能失败，需要自行调整 [mov2mp4.sh](mov2mp4.sh) 中的音频编码方式。
- 视频脚本给输出标记 BT.709；非 BT.709 的 SDR 输入也应抽查颜色。脚本不保留原 MOV 的附加数据流。

## 隐私

转换后的 JPG **可能仍含拍摄时间、设备信息和 GPS 坐标**，因为脚本保留 EXIF。发布或分享照片前请自行检查并清除不应公开的元数据。仓库不包含原始素材、转码结果或真人出镜的效果对比图。

源码采用 [MIT 许可证](LICENSE)；这一许可不适用于用户的照片、视频或第三方工具。
