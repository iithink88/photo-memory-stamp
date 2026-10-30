#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
photo-memory-stamp / stampkit.py

子命令:
  prepare <图...>                        预处理: EXIF矫正 + sRGB + 长边限制 → *_clean.jpg
  palette <图>                           提取主色，给出 1/2/3 色套印建议（JSON）
  compose <照片> --stamp <印章图>         合成 3:4 摄影记忆印章档案卡
  sheet   <目录或图...>                   多版拼对比图

典型用法:
  PY=~/.workbuddy/binaries/python/envs/default/Scripts/python.exe
  $PY stampkit.py prepare photo.jpg --info
  $PY stampkit.py palette photo_clean.jpg
  $PY stampkit.py compose photo_clean.jpg --stamp stamp.png --out out/final.jpg \
      --title "ORANGE PYLON" --keywords "bridge / cable / sky" --layout auto
  $PY stampkit.py sheet out/ --out out/compare.jpg
"""
import argparse
import json
import os
import sys
from glob import glob

try:
    from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageOps, ImageStat
except ImportError:
    sys.exit("需要 Pillow：pip install pillow")

SUPPORTED = (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff", ".heic", ".heif")

PAPER_DEFAULT = "F4EFE7"     # 暖白档案纸
INK_DEFAULT = "2B2621"       # 主文字


# ---------------------------------------------------------------- 基础工具
def human(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}TB"


def hex2rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def to_srgb_rgb(im, icc_profile=None):
    if icc_profile is not None:
        try:
            from PIL import ImageCms
            src = ImageCms.ImageCmsProfile(icc_profile)
            dst = ImageCms.createProfile("sRGB")
            im = ImageCms.profileToProfile(im, src, dst, outputMode="RGB")
        except Exception:
            pass
    if im.mode != "RGB":
        if im.mode in ("RGBA", "LA", "P"):
            im = im.convert("RGBA")
            bg = Image.new("RGB", im.size, (255, 255, 255))
            bg.paste(im, mask=im.split()[-1])
            im = bg
        else:
            im = im.convert("RGB")
    return im


def dominant_colors(im, k=6):
    small = im.resize((64, 64), Image.LANCZOS).convert("RGB")
    q = small.quantize(colors=12, method=Image.Quantize.FASTOCTREE)
    pal = q.getpalette() or []
    counts = sorted(q.getcolors() or [], reverse=True)
    out = []
    for cnt, idx in counts[:k]:
        r, g, b = pal[idx * 3: idx * 3 + 3]
        out.append({"hex": "#%02X%02X%02X" % (r, g, b),
                    "share": round(cnt / (64 * 64), 3),
                    "rgb": [r, g, b]})
    return out


def info_of(im):
    w, h = im.size
    st = ImageStat.Stat(im.convert("L"))
    from math import gcd
    d = gcd(w, h) or 1
    return {
        "size": [w, h],
        "aspect": f"{w // d}:{h // d}",
        "ratio_wh": round(w / h, 4),
        "orientation": "竖版" if h > w else ("横版" if w > h else "方图"),
        "brightness": round(st.mean[0] / 255, 3),
        "contrast": round(st.stddev[0] / 128, 3),
        "dominant": dominant_colors(im, 5),
    }


def load_font(size, bold=False):
    names = (["georgiab.ttf", "timesbd.ttf", "constanb.ttf"] if bold
             else ["georgia.ttf", "times.ttf", "constan.ttf"])
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    for path in ("C:/Windows/Fonts/georgia.ttf", "C:/Windows/Fonts/times.ttf",
                 "/System/Library/Fonts/Times.ttc"):
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    try:
        return ImageFont.load_default(size=size)
    except Exception:
        return ImageFont.load_default()


def cover_crop(im, box_w, box_h):
    """等比缩放并居中裁切，铺满目标框（不留白、不变形）。"""
    w, h = im.size
    s = max(box_w / w, box_h / h)
    im2 = im.resize((max(1, round(w * s)), max(1, round(h * s))), Image.LANCZOS)
    x = (im2.size[0] - box_w) // 2
    y = (im2.size[1] - box_h) // 2
    return im2.crop((x, y, x + box_w, y + box_h))


# ---------------------------------------------------------------- prepare
def cmd_prepare(args):
    paths = []
    for p in args.files:
        if os.path.isdir(p):
            paths += [f for f in glob(os.path.join(p, "*")) if f.lower().endswith(SUPPORTED)]
        else:
            paths.append(p)
    if not paths:
        sys.exit("没有找到可处理的图片")

    report = []
    for p in paths:
        if not os.path.isfile(p):
            print(f"[跳过] 不存在: {p}", file=sys.stderr)
            continue
        try:
            im = Image.open(p)
            im.load()
        except Exception as e:
            print(f"[跳过] 无法读取 {p}: {e}", file=sys.stderr)
            continue

        icc = im.info.get("icc_profile")
        im = ImageOps.exif_transpose(im) or im
        im = to_srgb_rgb(im, icc)

        w, h = im.size
        if max(w, h) > args.max:
            s = args.max / max(w, h)
            im = im.resize((max(1, int(w * s)), max(1, int(h * s))), Image.LANCZOS)

        if args.out and len(paths) == 1:
            out = args.out
        else:
            d = os.path.dirname(os.path.abspath(p))
            stem = os.path.splitext(os.path.basename(p))[0]
            out = os.path.join(d, f"{stem}_clean.jpg")
        os.makedirs(os.path.dirname(os.path.abspath(out)) or ".", exist_ok=True)
        im.save(out, "JPEG", quality=args.quality, optimize=True, progressive=True)

        rec = {"input": p, "output": out, "bytes_human": human(os.path.getsize(out)), **info_of(im)}
        report.append(rec)
        print(f"[OK] {out}  {rec['size'][0]}x{rec['size'][1]}  {rec['orientation']}  {rec['bytes_human']}")

    if args.info:
        print("\n--- INFO ---")
        print(json.dumps(report if len(report) > 1 else (report[0] if report else {}),
                         ensure_ascii=False, indent=2))


# ---------------------------------------------------------------- palette
def _is_neutral(rgb, tol=14):
    r, g, b = rgb
    return max(r, g, b) - min(r, g, b) < tol


def _is_extreme(rgb):
    r, g, b = rgb
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    return lum > 238 or lum < 22


def cmd_palette(args):
    im = Image.open(args.file)
    im = ImageOps.exif_transpose(im) or im
    im = to_srgb_rgb(im, im.info.get("icc_profile"))
    cols = dominant_colors(im, 10)

    chromatic = [c for c in cols if not _is_extreme(c["rgb"]) and not _is_neutral(c["rgb"])]
    neutral = [c for c in cols if not _is_extreme(c["rgb"]) and _is_neutral(c["rgb"])]
    pool = chromatic or neutral or cols

    scheme = {}
    scheme["1color"] = [pool[0]["hex"]]
    if len(pool) >= 2:
        scheme["2color"] = [pool[0]["hex"], pool[1]["hex"]]
    if len(chromatic) >= 3:
        scheme["3color"] = [c["hex"] for c in chromatic[:3]]
    elif len(pool) >= 3:
        scheme["3color"] = [c["hex"] for c in pool[:3]]

    out = {"file": args.file, "dominant": cols, "scheme": scheme,
           "note": "印章用色从原图取；1 色最像档案编号，2-3 色更接近真实套色印刷"}
    print(json.dumps(out, ensure_ascii=False, indent=2))


# ---------------------------------------------------------------- compose
def paper_canvas(w, h, paper_hex, noise=5):
    base = Image.new("RGB", (w, h), hex2rgb(paper_hex))
    if noise > 0:
        n = Image.effect_noise((w, h), noise).convert("L")
        n = n.filter(ImageFilter.GaussianBlur(0.4))
        base = ImageChops.blend(base, Image.merge("RGB", (n, n, n)), 0.06)
        # 保留纸色，不整体变灰
        base = Image.blend(base, Image.new("RGB", (w, h), hex2rgb(paper_hex)), 0.72)
    return base


def stamp_layer(stamp_path, max_w, max_h):
    """印章图 → 白底 RGB + 墨迹遮罩，便于 multiply 叠加。"""
    im = Image.open(stamp_path)
    im.load()
    im = ImageOps.exif_transpose(im) or im
    im = im.convert("RGBA")

    alpha = im.split()[-1]
    if alpha.getextrema()[0] > 250:          # 无透明通道 → 用"离白的距离"反推墨量
        rgb = im.convert("RGB")
        lum = rgb.convert("L")
        alpha = ImageChops.invert(lum).point(lambda v: 0 if v < 6 else 255)

    # 裁掉四周空白
    bbox = alpha.point(lambda v: 255 if v > 12 else 0).getbbox()
    if bbox:
        im = im.crop(bbox)
        alpha = alpha.crop(bbox)

    # 等比缩放到目标区域
    w, h = im.size
    s = min(max_w / w, max_h / h)
    nw, nh = max(1, round(w * s)), max(1, round(h * s))
    im = im.resize((nw, nh), Image.LANCZOS)
    alpha = alpha.resize((nw, nh), Image.LANCZOS)

    flat = Image.new("RGB", (nw, nh), (255, 255, 255))
    flat.paste(im.convert("RGB"), (0, 0), alpha)
    return flat, alpha


def draw_tracked(draw, xy, text, font, fill, tracking):
    """带字距的居中绘制；返回总宽。"""
    widths = [draw.textlength(ch, font=font) for ch in text]
    total = sum(widths) + tracking * (len(text) - 1)
    x = xy[0] - total / 2
    for ch, w in zip(text, widths):
        draw.text((x, xy[1]), ch, font=font, fill=fill)
        x += w + tracking
    return total


def cmd_compose(a):
    photo = Image.open(a.photo)
    photo.load()
    photo = ImageOps.exif_transpose(photo) or photo
    photo = to_srgb_rgb(photo, photo.info.get("icc_profile"))

    rw, rh = (a.ratio.split(":") + ["1"])[:2]
    base_w = a.width
    base_h = round(base_w * float(rh) / float(rw))
    W, H = base_w, base_h

    layout = a.layout
    if layout == "auto":
        layout = "top" if photo.size[0] > photo.size[1] * 1.05 else "left"

    share = min(0.68, max(0.45, a.share))
    if layout == "left":
        pw = round(W * share)
        photo_cell = (0, 0, pw, H)
        panel_box = (pw, 0, W - pw, H)          # (x, y, w, h)
    else:
        ph = round(H * share)
        photo_cell = (0, 0, W, ph)
        panel_box = (0, ph, W, H - ph)

    canvas = Image.new("RGB", (W, H), hex2rgb(a.paper))
    pc_w = photo_cell[2] - photo_cell[0]
    pc_h = photo_cell[3] - photo_cell[1]
    canvas.paste(cover_crop(photo, pc_w, pc_h), (photo_cell[0], photo_cell[1]))

    p_x, p_y = panel_box[0], panel_box[1]
    p_w, p_h = panel_box[2], panel_box[3]
    panel = paper_canvas(p_w, p_h, a.paper, noise=a.noise)
    canvas.paste(panel, (p_x, p_y))

    # ---- 文字排版（先量字，再定印章可用区域）
    short = min(p_w, p_h)
    t_size = max(18, round(short * a.title_scale))
    k_size = max(12, round(t_size * a.keyword_scale))
    title = (a.title or "").strip().upper()
    kws = (a.keywords or "").strip()

    probe = ImageDraw.Draw(canvas)
    max_text_w = p_w * 0.88          # 文字可用宽度，超出就缩字号
    t_font = load_font(t_size, bold=a.title_bold)
    k_font = load_font(k_size)
    if title:
        while t_size > 10:
            t_font = load_font(t_size, bold=a.title_bold)
            tw = sum(probe.textlength(ch, font=t_font) for ch in title) + \
                t_size * a.tracking * max(0, len(title) - 1)
            if tw <= max_text_w:
                break
            t_size -= 2
    if kws:
        while k_size > 8:
            k_font = load_font(k_size)
            kw = sum(probe.textlength(ch, font=k_font) for ch in kws) + \
                k_size * a.tracking * 0.8 * max(0, len(kws) - 1)
            if kw <= max_text_w:
                break
            k_size -= 1
    gap_tk = round(t_size * 0.85)
    t_h = t_size if title else 0
    k_h = k_size if kws else 0
    text_h = t_h + (gap_tk if (title and kws) else 0) + k_h

    margin = round(min(p_w, p_h) * a.margin)
    text_bottom = p_y + p_h - margin
    text_top = text_bottom - text_h

    # ---- 印章
    if a.stamp:
        region_top = p_y + round(p_h * 0.05)
        avail_h = max(60, (text_top - round(p_h * 0.06)) - region_top)
        flat, alpha = stamp_layer(a.stamp, max_w=round(p_w * a.stamp_size),
                                  max_h=round(avail_h * 0.98))
        if a.rotate:
            flat = flat.rotate(a.rotate, resample=Image.BICUBIC, expand=True,
                               fillcolor=(255, 255, 255))
            alpha = alpha.rotate(a.rotate, resample=Image.BICUBIC, expand=True, fillcolor=0)
        cx = p_x + p_w // 2
        cy = region_top + avail_h // 2
        ox, oy = cx - flat.size[0] // 2, cy - flat.size[1] // 2

        strip = canvas.crop((ox, oy, ox + flat.size[0], oy + flat.size[1]))
        w2, h2 = flat.size[0] - 3, flat.size[1] - 3
        corners = [flat.getpixel(p) for p in ((2, 2), (w2, 2), (2, h2), (w2, h2))]
        bg_lum = sum(0.299 * r + 0.587 * g + 0.114 * b for r, g, b in corners) / 4.0
        if bg_lum > 200:
            # 浅底 → 正片叠底：等价于油墨印在纸上，浅色专色不会被吃掉
            canvas.paste(ImageChops.multiply(strip, flat), (ox, oy))
        else:
            # 深底 / 透明底 → 按遮罩贴
            canvas.paste(flat, (ox, oy), alpha)

    # ---- 文字落位
    draw = ImageDraw.Draw(canvas)
    ink = hex2rgb(a.ink)
    sub = hex2rgb(a.ink_sub)
    y = text_top
    if title:
        draw_tracked(draw, (p_x + p_w / 2, y), title, t_font, ink, t_size * a.tracking)
        y += t_h + (gap_tk if kws else 0)
    if kws:
        draw_tracked(draw, (p_x + p_w / 2, y), kws, k_font, sub, k_size * a.tracking * 0.8)

    out = a.out or os.path.join(os.path.dirname(os.path.abspath(a.photo)), "stamp_card.jpg")
    os.makedirs(os.path.dirname(os.path.abspath(out)) or ".", exist_ok=True)
    canvas.save(out, "JPEG", quality=94, optimize=True, progressive=True)
    print(f"[OK] {out}  {W}x{H}  layout={layout}  photo_share={share}")
    print(f"     标题: {title or '(无)'}   关键词: {kws or '(无)'}")


# ---------------------------------------------------------------- sheet
def cmd_sheet(args):
    paths = []
    for p in args.items:
        if os.path.isdir(p):
            paths += sorted(f for f in glob(os.path.join(p, "*"))
                            if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp")))
        else:
            paths.append(p)
    if not paths:
        sys.exit("没有找到图片")
    if args.limit:
        paths = paths[:args.limit]

    H, gap, pad = args.height, args.gap, 16
    thumbs = []
    for p in paths:
        try:
            im = Image.open(p)
            im.load()
            im = ImageOps.exif_transpose(im) or im
            im = to_srgb_rgb(im, im.info.get("icc_profile"))
        except Exception as e:
            print(f"[跳过] {p}: {e}", file=sys.stderr)
            continue
        s = H / im.size[1]
        thumbs.append((p, im.resize((max(1, int(im.size[0] * s)), H), Image.LANCZOS)))
    if not thumbs:
        sys.exit("没有可用图片")

    cols = args.cols or len(thumbs)
    rows = (len(thumbs) + cols - 1) // cols
    cw = max(t[1].size[0] for t in thumbs)
    W = pad * 2 + cols * cw + (cols - 1) * gap
    Hh = pad * 2 + rows * (H + 26) + (rows - 1) * gap

    sheet = Image.new("RGB", (W, Hh), (246, 246, 244))
    draw = ImageDraw.Draw(sheet)
    font = load_font(16)
    for i, (p, t) in enumerate(thumbs):
        r, c = divmod(i, cols)
        x = pad + c * (cw + gap) + (cw - t.size[0]) // 2
        y = pad + r * (H + 26 + gap)
        sheet.paste(t, (x, y))
        draw.text((pad + c * (cw + gap), y + H + 4), f"#{i + 1}", fill=(70, 70, 70), font=font)

    out = args.out or os.path.join(os.path.dirname(os.path.abspath(paths[0])) or ".", "compare.jpg")
    sheet.save(out, "JPEG", quality=92, optimize=True, progressive=True)
    print(f"[OK] {out}  {sheet.size[0]}x{sheet.size[1]}  ({len(thumbs)} 张)")


def main():
    ap = argparse.ArgumentParser(description="photo-memory-stamp 图像工具")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("prepare", help="预处理为干净 JPG")
    p1.add_argument("files", nargs="+")
    p1.add_argument("--out")
    p1.add_argument("--max", type=int, default=2048)
    p1.add_argument("--quality", type=int, default=92)
    p1.add_argument("--info", action="store_true")
    p1.set_defaults(func=cmd_prepare)

    p2 = sub.add_parser("palette", help="主色提取 + 套印配色建议")
    p2.add_argument("file")
    p2.set_defaults(func=cmd_palette)

    p3 = sub.add_parser("compose", help="合成档案卡")
    p3.add_argument("photo")
    p3.add_argument("--stamp")
    p3.add_argument("--out")
    p3.add_argument("--layout", default="auto", choices=["auto", "left", "top"])
    p3.add_argument("--ratio", default="3:4")
    p3.add_argument("--width", type=int, default=1800)
    p3.add_argument("--share", type=float, default=0.54, help="照片占比 0.45-0.68")
    p3.add_argument("--paper", default=PAPER_DEFAULT)
    p3.add_argument("--ink", default=INK_DEFAULT)
    p3.add_argument("--ink-sub", dest="ink_sub", default="5B5348")
    p3.add_argument("--noise", type=int, default=5, help="纸张颗粒 0=纯净")
    p3.add_argument("--stamp-size", dest="stamp_size", type=float, default=0.78)
    p3.add_argument("--rotate", type=float, default=-1.2)
    p3.add_argument("--title", default="")
    p3.add_argument("--keywords", default="")
    p3.add_argument("--title-scale", dest="title_scale", type=float, default=0.048)
    p3.add_argument("--keyword-scale", dest="keyword_scale", type=float, default=0.60)
    p3.add_argument("--title-bold", dest="title_bold", action="store_true", default=True)
    p3.add_argument("--tracking", type=float, default=0.13)
    p3.add_argument("--margin", type=float, default=0.075)
    p3.set_defaults(func=cmd_compose)

    p4 = sub.add_parser("sheet", help="拼对比图")
    p4.add_argument("items", nargs="+")
    p4.add_argument("--out")
    p4.add_argument("--height", type=int, default=700)
    p4.add_argument("--cols", type=int, default=0)
    p4.add_argument("--gap", type=int, default=12)
    p4.add_argument("--limit", type=int, default=0)
    p4.set_defaults(func=cmd_sheet)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
