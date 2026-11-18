# -*- coding: utf-8 -*-
"""
转换结果校验 —— 逐条核对产出的 jpg / mp4 与源文件是否一一对应、规格是否正确

批量转换必须过这一道。转换脚本"没报错"不等于"转对了":
  * 少转/漏转的文件不会报错
  * 尺寸被意外缩小、ICC 色彩配置丢了、音频没了, 都不会报错
  * 视频时长对不上、帧率变了, 也不会报错

用法:
    python verify.py <源目录> <输出目录>

检查项:
    图片 —— 数量一一对应 / 尺寸与源一致 / ICC 有无与源一致 / 色彩模式
    视频 —— 数量一一对应 / 时长差 <0.2s / 分辨率不变 / 编码为 h264 /
            pix_fmt=yuv420p / 色彩标记=bt709 / 源有音频则输出也必须有
"""
import io
import json
import os
import subprocess
import sys

from PIL import Image
import pillow_heif

try:
    sys.stdout.reconfigure(errors="replace")
except Exception:
    pass

pillow_heif.register_heif_opener()

FFPROBE = "ffprobe"  # 从 PATH 查找；与转换脚本使用同一个 ffprobe
HEIC_EXT = (".heic", ".heif")
VID_EXT = (".mov", ".mp4", ".m4v")


def probe(path):
    """ffprobe 读元数据。必须显式指定 utf-8 —— 中文路径在 GBK 下会解崩。"""
    r = subprocess.run(
        [FFPROBE, "-v", "error", "-print_format", "json",
         "-show_format", "-show_streams", path],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    return json.loads(r.stdout)


def check_images(src, dst, problems):
    srcs = sorted(n for n in os.listdir(src) if n.lower().endswith(HEIC_EXT))
    outs = sorted(n for n in os.listdir(dst) if n.lower().endswith((".jpg", ".jpeg")))
    print(f"图片: 源 {len(srcs)} 张 / 产出 {len(outs)} 张")

    stem_in = {os.path.splitext(n)[0] for n in srcs}
    stem_out = {os.path.splitext(n)[0] for n in outs}
    if stem_in - stem_out:
        problems.append(f"缺少 JPG: {sorted(stem_in - stem_out)[:10]}")
    if stem_out - stem_in:
        problems.append(f"多余 JPG: {sorted(stem_out - stem_in)[:10]}")

    size = 0
    dim_bad, icc_lost, mode_bad = [], [], []
    for n in srcs:
        p = os.path.join(dst, os.path.splitext(n)[0] + ".jpg")
        if not os.path.exists(p):
            continue
        size += os.path.getsize(p)
        with Image.open(os.path.join(src, n)) as s:
            sw, sh, s_icc = s.size[0], s.size[1], bool(s.info.get("icc_profile"))
        with Image.open(p) as d:
            if (sw, sh) != d.size:
                dim_bad.append(f"{n}: {sw}x{sh} -> {d.size[0]}x{d.size[1]}")
            if s_icc and not d.info.get("icc_profile"):
                icc_lost.append(n)
            if d.mode != "RGB":
                mode_bad.append(f"{n}: mode={d.mode}")
    if dim_bad:
        problems.append(f"尺寸不符 {len(dim_bad)} 个: {dim_bad[:5]}")
    if icc_lost:
        problems.append(f"ICC 色彩配置丢失 {len(icc_lost)} 个: {icc_lost[:5]}")
    if mode_bad:
        problems.append(f"色彩模式异常: {mode_bad[:5]}")
    print(f"      JPG 合计 {size/1073741824:.2f} GB")


def check_videos(src, dst, problems):
    srcs = sorted(n for n in os.listdir(src) if n.lower().endswith(VID_EXT))
    outs = sorted(n for n in os.listdir(dst) if n.lower().endswith(".mp4"))
    print(f"\n视频: 源 {len(srcs)} 个 / 产出 {len(outs)} 个")

    stem_in = {os.path.splitext(n)[0] for n in srcs}
    stem_out = {os.path.splitext(n)[0] for n in outs}
    if stem_in - stem_out:
        problems.append(f"缺少 MP4: {sorted(stem_in - stem_out)}")
    if stem_out - stem_in:
        problems.append(f"多余 MP4: {sorted(stem_out - stem_in)}")

    size = 0
    for n in srcs:
        p = os.path.join(dst, os.path.splitext(n)[0] + ".mp4")
        if not os.path.exists(p):
            continue
        size += os.path.getsize(p)
        a, b = probe(os.path.join(src, n)), probe(p)
        av = next(s for s in a["streams"] if s["codec_type"] == "video")
        bv = next(s for s in b["streams"] if s["codec_type"] == "video")
        da, db = float(a["format"]["duration"]), float(b["format"]["duration"])

        bad = []
        if abs(da - db) > 0.2:
            bad.append(f"时长 {da:.2f}->{db:.2f}")
        if (int(av["width"]), int(av["height"])) != (int(bv["width"]), int(bv["height"])):
            bad.append(f"分辨率 {av['width']}x{av['height']}->{bv['width']}x{bv['height']}")
        if bv["codec_name"] != "h264":
            bad.append(f"编码 {bv['codec_name']}")
        if bv.get("pix_fmt") != "yuv420p":
            bad.append(f"pix_fmt {bv.get('pix_fmt')}")
        if bv.get("color_transfer") != "bt709" or bv.get("color_primaries") != "bt709":
            bad.append(f"色彩标记 trc={bv.get('color_transfer')} pri={bv.get('color_primaries')}")
        if any(s["codec_type"] == "audio" for s in a["streams"]) and \
           not any(s["codec_type"] == "audio" for s in b["streams"]):
            bad.append("音频丢失")
        if bad:
            problems.append(f"{n}: " + ", ".join(bad))

        print(f"      {os.path.splitext(n)[0]:<12} {os.path.getsize(p)/1048576:6.1f}MB  "
              f"{db:6.2f}s  {bv['width']}x{bv['height']}  {bv['codec_name']}/{bv.get('profile')}"
              f"  {'!!' + ','.join(bad) if bad else 'OK'}")
    print(f"      MP4 合计 {size/1073741824:.2f} GB")


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    src, dst = argv[0], argv[1]
    problems = []
    check_images(src, dst, problems)
    check_videos(src, dst, problems)

    print("\n" + "=" * 60)
    if problems:
        print(f"发现 {len(problems)} 个问题:")
        for x in problems:
            print("  -", x)
        return 1
    print("全部校验通过, 无问题")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
