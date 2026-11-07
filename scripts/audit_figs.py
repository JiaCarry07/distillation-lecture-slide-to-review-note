#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""全量核验「紧凑纯图」没有削掉图形内容。

对每张图比较：
  - 墨迹量比（非白像素数，new/orig）：抹掉说明文字会小幅下降，骤降说明连图一起抹了
  - 宽度比 / 高度比：宽度骤减说明裁掉了一侧图形
输出可疑清单 tools/fig_audit.txt，并生成最可疑的若干组对比图。
"""
import pathlib

import numpy as np
from PIL import Image, ImageDraw, ImageFont

BUILD = pathlib.Path(__file__).resolve().parents[1]
ORIG = BUILD / 'assets' / 'figs_orig'
NEW = BUILD / 'assets' / 'figs'
THUMBS = BUILD / 'thumbs'


def ink(im):
    """原尺寸统计墨迹像素，不做缩放——缩略会让紧凑图的线条显得更密，造成假阳性。"""
    a = np.asarray(im.convert('L'))
    return int((a < 236).sum()), im.size


def main():
    rows = []
    for p in sorted(ORIG.glob('*.png')):
        q = NEW / p.name
        if not q.exists():
            rows.append((p.name, 'missing', 0, 0, 0, 0))
            continue
        try:
            oi, osz = ink(Image.open(p))
            ni, nsz = ink(Image.open(q))
        except Exception as e:
            rows.append((p.name, 'error', 0, 0, 0, 0))
            continue
        ri = ni / max(1, oi)
        rw = nsz[0] / max(1, osz[0])
        rh = nsz[1] / max(1, osz[1])
        flag = 'OK'
        if ri < 0.55:
            flag = ' InkLoss'          # 墨迹骤降
        elif rw < 0.62:
            flag = 'WidthLoss'        # 一侧图形可能被裁
        elif ri > 1.45:
            flag = 'InkGain'          # 异常：多了东西
        rows.append((p.name, flag, ri, rw, rh, oi))

    bad = [r for r in rows if r[1] not in ('OK',)]
    print('总图数 %d | 可疑 %d (墨迹骤降 %d / 宽度骤减 %d / 其他 %d)' % (
        len(rows), len(bad),
        sum(1 for r in bad if r[1] == 'InkLoss'),
        sum(1 for r in bad if r[1] == 'WidthLoss'),
        sum(1 for r in bad if r[1] not in ('InkLoss', 'WidthLoss'))))
    ok = [r[2] for r in rows if r[1] == 'OK']
    print('正常图墨迹比: 中位数 %.2f, 5%%分位 %.2f, 95%%分位 %.2f' % (
        np.median(ok), np.percentile(ok, 5), np.percentile(ok, 95)))

    lines = ['紧凑纯图全量核验', '=' * 60,
             '总图 %d，可疑 %d' % (len(rows), len(bad)), '',
             '文件  标记  墨迹比  宽比  高比']
    for r in sorted(bad, key=lambda x: x[2]):
        lines.append('%-18s %-10s %.2f  %.2f  %.2f' % (r[0], r[1], r[2], r[3], r[4]))
    (BUILD / 'tools' / 'fig_audit.txt').write_text('\n'.join(lines), encoding='utf-8')

    # 最可疑 10 组：左原图 右新图
    picks = sorted(bad, key=lambda x: x[2])[:10]
    font = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 15)
    cw, rh = 340, 240
    sheet = Image.new('RGB', (cw * 2, rh * max(1, len(picks))), '#ffffff')
    dr = ImageDraw.Draw(sheet)
    for k, r in enumerate(picks):
        for j, folder in enumerate([ORIG, NEW]):
            p = folder / r[0]
            if not p.exists():
                continue
            im = Image.open(p).convert('RGB')
            im.thumbnail((cw - 16, rh - 30))
            sheet.paste(im, (j * cw + (cw - im.width) // 2, k * rh + 24))
        dr.text((6, k * rh + 4), '%s  %s  墨迹%.2f 宽%.2f' % (r[0], r[1], r[2], r[3]),
                fill='#a81d1d', font=font)
        dr.line([(cw, k * rh), (cw, (k + 1) * rh)], fill='#d3dfec')
        dr.line([(0, (k + 1) * rh - 1), (cw * 2, (k + 1) * rh - 1)], fill='#e8eff7')
    sheet.save(THUMBS / 'suspect_figs.png')
    print('可疑对比图 -> thumbs/suspect_figs.png | 清单 -> tools/fig_audit.txt')


if __name__ == '__main__':
    main()
