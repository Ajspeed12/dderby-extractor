#!/usr/bin/env python3
"""DDerby Extractor: export Destruction Derby (1995) PS1 images and OBJ models."""

import argparse
import csv
import importlib.util
import json
import math
from pathlib import Path
import pprint
import shutil
import sys
import tempfile

VERSION = "1.0"
MODULES = Path(__file__).resolve().parent / "dd1"
sys.dont_write_bytecode = True
sys.path.insert(0, str(MODULES))


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "game_folder",
        type=Path,
        help="Extracted game files, retaining LEVELxxx subfolders",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="New output folder; default: game_folder/Extracted_DD",
    )
    parser.add_argument(
        "--levels",
        nargs="+",
        type=int,
        choices=range(11),
        help="Process only these supplied levels",
    )
    parser.add_argument(
        "--images-only", action="store_true", help="Extract menu/root images only"
    )
    parser.add_argument(
        "--skip-grid",
        action="store_true",
        help="Skip starting grids (stock car extraction still uses Unicorn)",
    )
    parser.add_argument(
        "--scale",
        type=float,
        default=0.0035,
        help="OBJ scale; default 0.0035 (approximate DD2 comparison scale)",
    )
    parser.add_argument(
        "--source-coordinates",
        action="store_true",
        help="Keep original axes; use --scale 1 for original dimensions",
    )
    parser.add_argument(
        "--source-wheels",
        action="store_true",
        help="Keep stored wheel UVs instead of the static repair",
    )
    parser.add_argument(
        "--transparent-zero",
        action="store_true",
        help="Use cutout alpha for zero-colour menu/image pixels",
    )
    parser.add_argument("--version", action="version", version="DDerby Extractor " + VERSION)
    args = parser.parse_args()
    args.game_folder = args.game_folder.resolve()
    if not args.game_folder.is_dir():
        parser.error("Game folder does not exist")
    if not math.isfinite(args.scale) or args.scale <= 0:
        parser.error("--scale must be finite and greater than zero")
    args.output = (
        args.output.resolve() if args.output else args.game_folder / "Extracted_DD"
    )
    if args.output.exists():
        parser.error(
            "Output already exists. Choose a new folder with -o; existing files are never replaced."
        )
    args.levels = (
        sorted(set(args.levels))
        if args.levels is not None
        else [
            n
            for n in range(11)
            if (args.game_folder / f"LEVEL{n:03d}/LEVEL{n:03d}.001").is_file()
        ]
    )
    args.cars = (
        not args.images_only
        and any(n in (*range(7), 9) for n in args.levels)
        and (args.game_folder / "SCUS_943.02").is_file()
    )
    args.grid = (
        args.cars
        and not args.skip_grid
        and (args.game_folder / "PLAYCARS.RAW").is_file()
    )
    needed = {"numpy": "numpy", "PIL": "Pillow"}
    if args.cars:
        needed["unicorn"] = "unicorn"
    missing = [
        package
        for module, package in needed.items()
        if importlib.util.find_spec(module) is None
    ]
    if missing:
        parser.error(
            "Missing "
            + ", ".join(missing)
            + ". Run: python -m pip install -r requirements.txt"
        )
    return args


def run(args):
    from image_formats import extract as extract_images
    from local_models import export as export_models
    from export_level_native import export as export_track
    from scene_data import TRACK_SCENES
    from split_textures import convert
    from car_damage import export as export_damage
    from output_layout import Publisher
    from level_names import folder_name

    root, out = args.game_folder, args.output
    out.mkdir(parents=True)
    errors = 0
    with (out / "extraction.log").open("w", encoding="utf-8") as log:

        def note(message, console=True):
            log.write(message + "\n")
            log.flush()
            if console:
                print(message, flush=True)

        note(f"DDerby Extractor v{VERSION}")
        note(
            f"OBJ scale: {args.scale:g}. Axes: "
            + (
                "source"
                if args.source_coordinates
                else "Y-up; Blender -Z forward / Y up"
            )
        )
        note(
            "Scale 0.0035 is an approximate comparison preference, not a confirmed unit conversion.",
            False,
        )
        note(
            "Static export: no runtime deformation, wheel spin, lighting, TV/digits or full PS1 blending.",
            False,
        )

        def component(label, action):
            nonlocal errors
            note(label + "...")
            try:
                action()
            except Exception as exc:
                errors += 1
                note(f"ERROR {label}: {type(exc).__name__}: {exc}")

        publishers = {}

        def publisher(level):
            if level not in publishers:
                publishers[level] = Publisher(
                    out / folder_name(root, level), args, note
                )
            return publishers[level]

        def copy_pngs(source, destination):
            for p in sorted(source.rglob("*.png")):
                if p.name.startswith(("Texture_preview_", "Damage_preview")):
                    continue
                target = destination / p.relative_to(source)
                target.parent.mkdir(parents=True, exist_ok=True)
                if target.exists():
                    raise ValueError(f"Output collision: {target}")
                shutil.copyfile(p, target)

        def retain_unknowns(audit, label):
            """Keep source evidence for unexported records, without a JSON sidecar."""
            note("\nSOURCE NOTES: " + label, False)
            for model in audit.get("models", []):
                for packet in model["packets"]:
                    if "indices" not in packet:
                        note(
                            f"UNEXPORTED model={model['id']} lod={model['lod']} "
                            + pprint.pformat(packet, sort_dicts=False),
                            False,
                        )
            for key in (
                "unresolved_geometry_records",
                "unresolved_texture_records",
                "unresolved_model_instances",
                "unresolved_cropped_materials",
            ):
                if audit.get(key):
                    note(
                        key + ": " + pprint.pformat(audit[key], sort_dicts=False), False
                    )
            exports = audit.get("exports", {})
            if isinstance(exports, dict):
                for name, details in exports.items():
                    if details.get("missing_models"):
                        note(
                            f"UNEXPORTED {name}: missing_models="
                            + pprint.pformat(details["missing_models"]),
                            False,
                        )
            for scene in audit.get("source_scenes", []):
                note(
                    scene["name"]
                    + ": "
                    + str(scene.get("classification", scene.get("status", ""))),
                    False,
                )
                for assumption in scene.get("assumptions", []):
                    note("  " + assumption, False)

        with tempfile.TemporaryDirectory(prefix="dd1_extract_") as folder:
            temp = Path(folder)

            def images():
                _, count, failures = extract_images(
                    root, lambda msg: None, args.transparent_zero, temp / "Images"
                )
                for p in sorted((temp / "Images").rglob("*.png")):
                    relative = p.relative_to(temp / "Images")
                    if len(relative.parts) == 1 and p.name.startswith("PLAYCARS_"):
                        relative = Path("PLAYCARS(RAW)") / p.name
                    elif len(relative.parts) == 1 and p.name.startswith("TRACKS_"):
                        relative = Path("TRACKS(RAW)") / p.name
                    target = out / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    if target.exists():
                        raise ValueError(f"Output collision: {target}")
                    shutil.copyfile(p, target)
                # Palette-only TIMs have no PNG. Preserve their resource/colour data in text.
                for p in sorted((temp / "Images").rglob("*.json")):
                    note(
                        "IMAGE RESOURCE "
                        + str(p.relative_to(temp / "Images"))
                        + ":\n"
                        + pprint.pformat(json.loads(p.read_text()), sort_dicts=False),
                        False,
                    )
                with (temp / "Images/extraction_report.csv").open(
                    encoding="utf-8", newline=""
                ) as f:
                    for record in csv.DictReader(f):
                        if record["type"] in (
                            "error",
                            "skipped_non_image",
                            "palette_only",
                            "backdrop_pair_incomplete",
                        ):
                            note("IMAGE " + str(record), record["type"] == "error")
                note(f"  {count} image PNGs; {failures} errors")
                if failures:
                    raise ValueError(f"{failures} image errors; details above")

            component("Menu and standalone images", images)
            if not args.images_only:
                menus = {
                    0: ("garage_static.obj", "garage.obj", False),
                    7: ("menu_initial_choice_0.obj", "mmenu.obj", False),
                    8: ("all_models_local.obj", "3Dtext.obj", True),
                    10: ("trophy_initial.obj", "Trophy.obj", False),
                }
                for level in args.levels:
                    if level not in menus:
                        continue

                    def menu(level=level):
                        dest = temp / f"models_{level:03d}"
                        result = export_models(
                            root, level, temp / f"pages_{level:03d}", dest,
                            source_wheels=args.source_wheels
                        )
                        audit = json.loads((dest / "audit.json").read_text())
                        retain_unknowns(audit, f"LEVEL{level:03d} models")
                        if level == 0:
                            from garage_trailers import extend_garage

                            trailers = extend_garage(root, dest)
                            note("GARAGE TRAILERS " + pprint.pformat(trailers, sort_dicts=False), False)
                            for warning in trailers.get("warnings", []):
                                note("WARNING: " + warning)
                        filename, output_name, local = menus[level]
                        publisher(level).add(
                            dest, filename, output_name=output_name, local=local
                        )
                        note(
                            f"  Published {filename}; other model/LOD libraries and alternate menu selections are not included.",
                            False,
                        )
                        note(
                            f"  Verified texture samples: {result['checked_colour_samples']}",
                            False,
                        )

                    component(f"LEVEL{level:03d} scene", menu)

                for level in args.levels:
                    if level not in TRACK_SCENES:
                        continue

                    def track(level=level):
                        if level == 1 and args.grid:
                            # Retain the already validated static scenery planes as well as the track.
                            from dd1_level001_to_obj import export as export_combined

                            for layout in (0, 1):
                                source, dest = (
                                    temp / f"combined_{layout}",
                                    temp / f"split_{layout}",
                                )
                                export_combined(
                                    root, source, layout=layout, diagnostics=True,
                                    source_wheels=args.source_wheels
                                )
                                filename = f"LEVEL001_layout{layout}_track_and_grid.obj"
                                result = convert(
                                    source,
                                    dest,
                                    [filename],
                                    "LEVEL001.mtl",
                                    source / "diagnostics.json",
                                )
                                publisher(level).add(
                                    dest,
                                    filename,
                                    output_name=f"layout_{layout}.obj",
                                    select=lambda name: name.startswith("track_"),
                                )
                                publisher(level).add(
                                    dest,
                                    filename,
                                    output_name=f"grid_{layout}.obj",
                                    select=lambda name: name.startswith("car_"),
                                )
                                note(
                                    f"  Verified texture samples: {result['checked_colour_samples']}",
                                    False,
                                )
                            return
                        source, dest = (
                            temp / f"track_source_{level:03d}",
                            temp / f"track_{level:03d}",
                        )
                        audit = export_track(root, TRACK_SCENES[level], source)
                        retain_unknowns(audit, f"LEVEL{level:03d} assembled tracks")
                        names = sorted(
                            e["file"]
                            for e in audit["exports"]
                            if e["barrier_uv_set"] == 0
                        )
                        result = convert(source, dest, names)
                        for layout, filename in enumerate(names):
                            publisher(level).add(
                                dest, filename, output_name=f"layout_{layout}.obj"
                            )
                        note(
                            f"  Verified texture samples: {result['checked_colour_samples']}",
                            False,
                        )

                    component(f"LEVEL{level:03d} track layouts", track)
                    if level in (*range(2, 7), 9) and args.grid:

                        def grids(level=level):
                            from car_exports import export as export_cars

                            dest, audit = export_cars(
                                root, level, temp / f"cars_{level:03d}",
                                source_wheels=args.source_wheels
                            )
                            for layout in ((0,) if level == 9 else (0, 1)):
                                publisher(level).add(dest, f"grid_{layout}.obj")
                            note(
                                "GRID EVIDENCE "
                                + pprint.pformat(audit["placements"], sort_dicts=False),
                                False,
                            )
                            note(
                                f"  Verified texture samples: {audit['export']['checked_colour_samples']}",
                                False,
                            )

                        component(f"LEVEL{level:03d} starting grids", grids)
                if (
                    not args.grid
                    and not args.skip_grid
                    and any(n in (*range(1, 7), 9) for n in args.levels)
                ):
                    note(
                        "WARNING: grids omitted; SCUS_943.02 and PLAYCARS.RAW are required."
                    )

                if args.cars:

                    def stock():
                        from car_exports import export as export_cars

                        level = (
                            1
                            if 1 in args.levels
                            else next(n for n in args.levels if n in (*range(7), 9))
                        )
                        dest, audit = export_cars(
                            root, level, temp / "stock", stock=True,
                            source_wheels=args.source_wheels
                        )
                        Publisher(out / "STOCK", args, note).add(
                            dest, "STOCK.obj", local=True
                        )
                        result = export_damage(root, temp / "damage", level=level)
                        copy_pngs(temp / "damage", out / "STOCK/Textures")
                        note(
                            f"  20 stock cars at original local origins; {result['images']} AI car/decal/body PNGs; complete player sets follow"
                        )
                        note(
                            f"  Verified stock texture samples: {audit['export']['checked_colour_samples']}",
                            False,
                        )

                    component("STOCK cars and damage textures", stock)
                elif any(n in (*range(7), 9) for n in args.levels):
                    note("WARNING: stock cars/damage omitted; SCUS_943.02 is required.")
        if not args.images_only and (
            any(out.rglob("grid_*.obj")) or (out / "STOCK/STOCK.obj").is_file()
        ):

            def share_cars():
                from shared_cars import consolidate

                consolidate(out, note)

            component("Shared car textures and descriptive names", share_cars)
        if not args.images_only and args.cars:
            def extra_palettes():
                from palette_exports import export

                report = export(root, out, args.levels)
                note("PALETTE EXPORTS " + pprint.pformat(report, sort_dicts=False), False)
                for resource in report.get("truck_missing_resources", []):
                    note("WARNING: truck variants omitted; missing " + resource)
                note(f"  {report['player_panels']} unique player textures (16 sections per choice); "
                     f"{report['roof_palettes']} unique roof colours; "
                     f"{len(report['windscreen_palettes'])} windscreen and "
                     f"{len(report['side_windows_palettes'])} side-window palettes; "
                     f"{report['truck_palettes']} unique truck palette crops")

            component("Additional player, roof and truck palettes", extra_palettes)
        note(f"Finished: {errors} component errors. Output: {out}")
    return 1 if errors else 0


def main():
    try:
        return run(arguments())
    except KeyboardInterrupt:
        print(
            "\nCancelled. Original files are unchanged; choose a fresh output folder to retry.",
            file=sys.stderr,
        )
        return 130
    except OSError as exc:
        print(f"Cannot complete extraction: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
