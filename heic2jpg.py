# -*- coding: utf-8 -*-
"""
HEIC -> JPEG 批量转换

用途: 手机(尤其 iPhone)拍的 HEIC 照片转成到处都能看的 JPG。

用法:
    python heic2jpg.py <源目录>                  # 输出目录 = 同级的 "<源目录名>_转换"
    python heic2jpg.py <源目录> <输出目录>
    python heic2jpg.py <源目录> <输出目录> -f    # 强制覆盖已存在的 jpg

特点:
  * quality=95 + subsampling=0 (4:4:4 无色度抽样) —— JPEG 能达到的最高画质档,
    红色文字/彩边不会糊。代价是文件约为 HEIC 的 2 倍左右。
  * 原样保留 HEIC 内嵌的 ICC 色彩配置 (iPhone 是 Display P3 广色域) 与 EXIF
    (拍摄时间、机型，也可能包含 GPS 位置信息)。共享产出前请自行检查并清除敏感 EXIF。
  * 分辨率不缩放, 4800 万像素的原样出。

依赖: pillow, pillow-heif   (pip install pillow pillow-heif)
"""
import os
import sys
import time

from PIL import Image
import pillow_heif

# stdout 在 Windows 控制台被重定向到文件时用的是 GBK, 遇到生僻字会崩,
# 这里只改错误处理方式, 不换编码 —— 控制台里照常显示中文。
try:
    sys.stdout.reconfigure(errors="replace")
except Exception:
    pass

pillow_heif.register_heif_opener()

QUALITY = 95      # JPEG 质量 1-100
SUBSAMPLING = 0   # 0 = 4:4:4 无色度抽样 (最高画质); 2 = 4:2:0 (文件约减半)


def main(argv):
    force = "-f" in argv or "--force" in argv
    args = [arg for arg in argv if arg not in ("-f", "--force")]
    if not 1 <= len(args) <= 2:
        print("用法: python heic2jpg.py <源目录> [输出目录] [-f]")
        return 2
    src = args[0]
    dst = (args[1] if len(args) == 2 else
           os.path.join(os.path.dirname(os.path.abspath(src)),
                        os.path.basename(os.path.normpath(src)) + "_转换"))

    if not os.path.isdir(src):
        print(f"源目录不存在: {src}")
        return 1
    os.makedirs(dst, exist_ok=True)

    names = sorted(n for n in os.listdir(src) if n.lower().endswith((".heic", ".heif")))
    if not names:
        print(f"{src} 下没找到 HEIC/HEIF 文件")
        return 1

    print(f"源:   {src}")
    print(f"输出: {dst}")
    print(f"共 {len(names)} 张, 质量 {QUALITY} / 色度抽样 {'4:4:4' if SUBSAMPLING == 0 else '4:2:0'}\n")

    total = len(names)
    ok = skip = fail = 0
    odd_mode = []
    t0 = time.time()

    for i, name in enumerate(names, 1):
        s = os.path.join(src, name)
        d = os.path.join(dst, os.path.splitext(name)[0] + ".jpg")

        if os.path.exists(d) and not force:
            skip += 1
            print(f"[{i:3d}/{total}] 跳过(已存在) {name}", flush=True)
            continue

        try:
            im = Image.open(s)
            mode = im.mode
            icc = im.info.get("icc_profile")
            ex = im.getexif()
            exif_bytes = ex.tobytes() if ex else None
            rgb = im.convert("RGB")
            im.close()

            save_options = dict(quality=QUALITY,
                                subsampling=SUBSAMPLING,
                                optimize=True,     # 多花点时间换更小的体积
                                progressive=True) # 渐进式, 网页/微信预览更友好
            if icc:
                save_options["icc_profile"] = icc
            if exif_bytes:
                save_options["exif"] = exif_bytes
            rgb.save(d, "JPEG", **save_options)
            if mode != "RGB":
                odd_mode.append(f"{name}({mode})")
            ok += 1
            print(f"[{i:3d}/{total}] {name}  {rgb.size[0]}x{rgb.size[1]}  "
                  f"{os.path.getsize(d)/1048576:.2f}MB  icc={len(icc) if icc else 0}B", flush=True)
        except Exception as e:
            fail += 1
            print(f"[{i:3d}/{total}] 失败 {name}: {e}", flush=True)

    print(f"\n完成: 成功 {ok} / 跳过 {skip} / 失败 {fail} / 共 {total}, 用时 {time.time()-t0:.1f}s")
    if odd_mode:
        print("注意, 以下源文件不是 8bit RGB (可能是 10bit HDR 或有透明通道), 请抽查:")
        print("  " + ", ".join(odd_mode))
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
