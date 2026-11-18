#!/bin/bash
# -*- coding: utf-8 -*-
#
# MOV -> MP4 批量转换 (手机视频转通用格式)
#
# 用途: iPhone/安卓拍的视频转成 H.264 + AAC 的 MP4, 任何设备/软件都能放。
#
# 用法:
#   bash mov2mp4.sh <源目录>
#   bash mov2mp4.sh <源目录> <输出目录>
#
# 关键: HDR 视频必须做色调映射, 否则画面惨白过曝。
#       本脚本会探测源文件是不是 HLG/PQ HDR, 只对识别出的 HDR 做映射。
#
# 依赖: ffmpeg / ffprobe（须在 PATH 中）

if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
    printf '用法: bash mov2mp4.sh <源目录> [输出目录]\n' >&2
    exit 2
fi

SRC="$1"
if [ "$#" -eq 2 ]; then
    DST="$2"
else
    DST="$(dirname "$SRC")/$(basename "$SRC")_转换"
fi

for tool in ffmpeg ffprobe; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        printf '缺少依赖: %s（请先将其加入 PATH）\n' "$tool" >&2
        exit 127
    fi
done

CRF=17          # 质量: 越小越好越大文件。17 近乎透明, 18 也很够用, 23 是 x264 默认
PRESET=slow     # 编码速度/压缩率权衡。slow 比默认 medium 同画质更小, 慢一倍

# HDR(HLG 或 PQ) -> SDR(BT.709) 色调映射链
#   zscale 线性化 -> hable 曲线压亮度 -> 重新按 BT.709 编码
#   注意最后一步 zscale 会同时把"帧的色彩标记"改成 bt709, 这一步不能省 ——
#   ffmpeg 写文件时以帧自带的色彩标记为准, 命令行的 -color_trc 覆盖不了它。
VF_HDR="zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p"
# 源文件不是 HLG/PQ 时: 仅做像素格式转换, 不进行 HDR 色调映射；视频仍会重编码
VF_SDR="format=yuv420p"

if [ ! -d "$SRC" ]; then
    echo "源目录不存在: $SRC"
    exit 1
fi
mkdir -p "$DST"

shopt -s nullglob nocaseglob
files=("$SRC"/*.mov "$SRC"/*.mp4 "$SRC"/*.m4v)
total=${#files[@]}
if [ "$total" -eq 0 ]; then
    echo "$SRC 下没找到视频文件"
    exit 1
fi

echo "源:   $SRC"
echo "输出: $DST"
echo "共 $total 个, CRF $CRF / preset $PRESET"
echo ""

n=0; fail=0; t0=$(date +%s)

for f in "${files[@]}"; do
    n=$((n + 1))
    base=$(basename "$f")
    base="${base%.*}"
    out="$DST/$base.mp4"

    # 探测是否 HDR
    #   必须用 nokey=1 取值。别用 csv=p=0 —— 它只查一个字段时仍会输出尾随逗号
    #   (得到 "arib-std-b67,"), 拿去比较永远匹配不上, 会静默地把 HDR 当 SDR 转。
    trc=$(ffprobe -v error -select_streams v:0 -show_entries stream=color_transfer \
                  -of default=noprint_wrappers=1:nokey=1 "$f" 2>/dev/null | tr -d '\r\n')
    case "$trc" in
        arib-std-b67|smpte2084) vf="$VF_HDR"; kind="HDR($trc) 需色调映射" ;;
        *)                      vf="$VF_SDR"; kind="非 HLG/PQ($trc), 不做色调映射" ;;
    esac

    s=$(date +%s)
    if ffmpeg -y -v error -i "$f" \
        -map 0:v:0 -map "0:a:0?" \
        -vf "$vf" \
        -c:v libx264 -crf "$CRF" -preset "$PRESET" \
        -profile:v high -level 4.2 -pix_fmt yuv420p \
        -color_primaries bt709 -color_trc bt709 -colorspace bt709 \
        -c:a copy -movflags +faststart \
        "$out" 2>/dev/null; then
        e=$(date +%s)
        sz=$(( $(stat -c %s "$out") / 1048576 ))
        echo "[$n/$total] 完成  $base  ${sz}MB  $((e - s))s  [$kind]"
    else
        fail=$((fail + 1))
        echo "[$n/$total] 失败  $base"
    fi
done

t1=$(date +%s)
echo ""
echo "完成: 共 $total, 失败 $fail, 总用时 $((t1 - t0))s"
