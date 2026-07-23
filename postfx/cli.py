"""Command-line interface: run (single/batch), sheet, list.

    python -m postfx run   --input <file|folder> --theme portra_400 \\
                           --scene day_outdoor --strength 1.0 --out <folder>
    python -m postfx sheet --input <single image> --out contact_sheet.jpg
    python -m postfx list
"""

import argparse
import os
import sys
from functools import partial
from multiprocessing import Pool, cpu_count

from . import imgio
from .pipeline import process
from .scenes import DEFAULT_SCENE, SCENES, get_scene
from .sheet import build_contact_sheet
from .theme import DEFAULT_CATEGORY, list_categories, list_themes, load_theme


def _process_one(job, theme, scene_cfg, strength):
    """Batch worker (picklable). job = (in_path, out_path)."""
    in_path, out_path = job
    rgb, alpha = imgio.load_image(in_path)
    seed = imgio.seed_from_path(in_path)
    out = process(rgb, theme, scene_cfg, strength, seed)
    imgio.save_image(out_path, out, alpha,
                     jpeg_quality=theme["jpeg"]["quality"],
                     jpeg_cycles=theme["jpeg"]["cycles"])
    return out_path


def _out_path(in_path, out_dir, out_ext):
    stem = os.path.splitext(os.path.basename(in_path))[0]
    ext = out_ext or os.path.splitext(in_path)[1] or ".png"
    if not ext.startswith("."):
        ext = "." + ext
    return os.path.join(out_dir, stem + ext)


def cmd_run(args):
    theme = load_theme(args.theme)
    scene_cfg = get_scene(args.scene)

    if os.path.isdir(args.input):
        inputs = imgio.list_images(args.input)
        if not inputs:
            print(f"No images in folder: {args.input}", file=sys.stderr)
            return 1
    elif os.path.isfile(args.input):
        inputs = [args.input]
    else:
        print(f"Input not found: {args.input}", file=sys.stderr)
        return 1

    os.makedirs(args.out, exist_ok=True)
    jobs = [(p, _out_path(p, args.out, args.format)) for p in inputs]

    worker = partial(_process_one, theme=theme, scene_cfg=scene_cfg,
                     strength=args.strength)

    print(f"{len(jobs)} image(s) | theme={theme['name']} | scene={args.scene} "
          f"| strength={args.strength}")

    if len(jobs) > 1 and args.jobs != 1:
        workers = args.jobs if args.jobs > 0 else min(cpu_count(), len(jobs))
        with Pool(workers) as pool:
            for done in pool.imap_unordered(worker, jobs):
                print(f"  done {os.path.basename(done)}")
    else:
        for job in jobs:
            print(f"  done {os.path.basename(worker(job))}")

    print(f"Finished -> {args.out}")
    return 0


def cmd_sheet(args):
    if not os.path.isfile(args.input):
        print(f"Provide a single image file: {args.input}", file=sys.stderr)
        return 1
    rgb, _ = imgio.load_image(args.input)
    out = build_contact_sheet(rgb, args.out, category=args.category,
                              scene=args.scene, strength=args.strength,
                              cols=args.cols)
    print(f"Contact sheet -> {out}")
    return 0


def cmd_list(args):
    themes = list_themes(category=args.category)
    width = max((len(name) for name, _, _ in themes), default=10)
    current = None
    print(f"{len(themes)} theme(s):\n")
    for name, desc, category in themes:
        if category != current:
            current = category
            print(f"[{category}]")
        print(f"  {name.ljust(width)}  {desc}")
    print(f"\nCategories: {', '.join(list_categories())}")
    print(f"Scenes: {', '.join(SCENES)}  (default: {DEFAULT_SCENE})")
    return 0


def build_parser():
    p = argparse.ArgumentParser(
        prog="postfx",
        description="Theme-based image post-processing & film-emulation pipeline.")
    sub = p.add_subparsers(dest="command", required=True)

    r = sub.add_parser("run", help="process a single image or a folder")
    r.add_argument("--input", required=True, help="file or folder")
    r.add_argument("--theme", required=True, help="theme name or YAML path")
    r.add_argument("--scene", default=DEFAULT_SCENE, choices=list(SCENES))
    r.add_argument("--strength", type=float, default=1.0,
                   help="0=original, 1=full theme, 1.5=over")
    r.add_argument("--out", required=True, help="output folder")
    r.add_argument("--format", default=None,
                   help="output extension (png/jpg); defaults to the input's")
    r.add_argument("--jobs", type=int, default=0,
                   help="parallel workers (0=auto, 1=serial)")
    r.set_defaults(func=cmd_run)

    s = sub.add_parser("sheet", help="apply a category of themes to one image (grid)")
    s.add_argument("--input", required=True, help="single image file")
    s.add_argument("--out", default="contact_sheet.jpg")
    s.add_argument("--category", default=DEFAULT_CATEGORY,
                   help="theme category to render (signature/experimental/all)")
    s.add_argument("--scene", default=DEFAULT_SCENE, choices=list(SCENES))
    s.add_argument("--strength", type=float, default=1.0)
    s.add_argument("--cols", type=int, default=5)
    s.set_defaults(func=cmd_sheet)

    lst = sub.add_parser("list", help="list themes and their descriptions")
    lst.add_argument("--category", default=None,
                     help="limit to a category (default: all)")
    lst.set_defaults(func=cmd_list)

    return p


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
