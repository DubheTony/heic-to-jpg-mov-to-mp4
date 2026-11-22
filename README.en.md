# Photo and Video Format Conversion

[中文](README.md) | [English](README.en.md)

Batch-convert HEIC/HEIF photos to JPG and MOV, MP4, or M4V videos to H.264 MP4. When a video has recognizable HLG/PQ HDR, HDR→SDR tone mapping is applied first. Photos retain their original dimensions, ICC color profiles, and EXIF data. Source files are not modified; results are written to a separate directory.

## Requirements

- Python (tested on synthetic samples with Python 3.13), plus `pillow` and `pillow-heif`: `python -m pip install pillow pillow-heif`
- `ffmpeg` and `ffprobe`: after installation, make sure both commands are on `PATH`. Video conversion requires an FFmpeg build with `zscale`, `tonemap`, and `libx264`. Check for the required features with `ffmpeg -filters` and `ffmpeg -encoders`, respectively.
- The video script uses Bash and GNU `stat`. On Windows, you can use Git Bash.

## Usage

Run these commands in the project directory, substituting your own paths. For the first trial run, create an **empty output directory different from the source directory**:

```bash
python heic2jpg.py "照片和视频所在目录" "转换结果目录"
bash mov2mp4.sh "照片和视频所在目录" "转换结果目录"
python verify.py "照片和视频所在目录" "转换结果目录"
```

Both conversion scripts require a source directory. If the output directory is omitted, they create `<源目录名>_转换` alongside the source directory. The photo script skips JPG files that already exist unless you pass `-f` / `--force`. **The video script currently overwrites MP4 files with the same name**, so check the output directory before running it again. Both scripts process only files directly inside the source directory; they do not search subdirectories recursively.

`verify.py` checks output file names and counts against the source files, along with image dimensions, whether an ICC profile is **present or absent**, and video duration, resolution, codec, and audio. It does not compare the contents of ICC profiles or check whether EXIF is complete or contains GPS data. It does not replace a visual spot-check; check the colors and highlights of HDR tone-mapped output in particular.

## Conversion Details and Limitations

- Photos: `quality=95` and `subsampling=0` (4:4:4), with ICC and EXIF retained. Files are usually larger than with 4:2:0; for smaller files, adjust `SUBSAMPLING` near the top of [heic2jpg.py](heic2jpg.py).
- Videos: `ffprobe` reads the color transfer tag of the first video stream. If it detects `arib-std-b67` (HLG) or `smpte2084` (PQ), `zscale` and `tonemap=hable` map it to SDR BT.709 before `libx264` encoding at `CRF=17`. Other tags do not trigger HDR tone mapping, **but the video is still re-encoded**. Check videos with missing tags or other HDR formats yourself.
- Audio is copied without re-encoding. If the source audio format cannot be stored in MP4, conversion may fail; you will need to adjust the audio encoding in [mov2mp4.sh](mov2mp4.sh).
- The video script tags the output as BT.709; also spot-check the colors of SDR inputs that are not BT.709. The script does not retain auxiliary data streams from the original MOV file.

## Privacy

Converted JPG files **may still contain capture time, device information, and GPS coordinates** because the script retains EXIF. Before publishing or sharing photos, check and remove metadata that should not be public. The repository does not contain original media, conversion results, or before-and-after images showing real people.

The source code is under the [MIT License](LICENSE); this license does not apply to users' photos or videos or to third-party tools.
