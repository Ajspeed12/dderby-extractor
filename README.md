# DDerby Extractor

**v1.0 — first public release**

Extract images, cars and tracks from **Destruction Derby (1995) for PlayStation**
as PNG textures and textured OBJ models. This is an unofficial tool for DD1.
It does not support Destruction Derby 2 or extract audio. Game files are not included.

## Quick start — Windows

1. Install **Python 3.11 or newer**, enabling **Add Python to PATH**.
2. Unzip this tool and keep all its files together, including the `dd1` folder.
3. Drag your extracted game folder onto **`Extract_DDerby.bat`**, or double-click
   the BAT and paste the folder path.

The launcher installs missing NumPy, Pillow and Unicorn dependencies using pip.
Installation needs an internet connection; extraction uses your local files.
Unicorn executes bounded setup routines from the supported game executable to
recover car placements and materials.

Keep the source game's `LEVEL000`–`LEVEL010`, `BACKDROP`, `INTRO` and `TRAILERS`
folders intact, alongside `SCUS_943.02`, `PLAYCARS.RAW` and the other root files.
Supply extracted files, not a BIN/CUE image or ZIP. Model setup is verified only
for the supplied USA `SCUS_943.02` build; unsupported executables are refused.

Command-line alternative:

```console
python -m pip install -r requirements.txt
python dd1_extract.py "D:\Games\Destruction Derby"
```

Original game files are not modified. Output defaults to `Extracted_DD` inside
the input folder. An existing output folder is never overwritten; use
`-o "D:\Exports\DDerby"` to choose a new one.

## Output

| Folder | Contents |
|---|---|
| Root, `BACKDROP`, `INTRO`, `TRAILERS` | Standalone images, retaining source subfolders |
| `PLAYCARS(RAW)` | Six player liveries and damaged decals |
| `TRACKS(RAW)` | Six championship track thumbnails |
| `LEVEL000` | `garage.obj`, including driver trailer variants when their files are available |
| `LEVEL001 - Speedway` | `layout_0.obj`, `layout_1.obj`, `grid_0.obj`, `grid_1.obj` |
| `LEVEL002 - Crossover` | Same four layout/grid files |
| `LEVEL003 - Ocean Drive` | Same four files, including the unfinished alternate layout |
| `LEVEL004 - Cactus Creek` | Same four files |
| `LEVEL005 - City Heat` | Same four files |
| `LEVEL006 - Total Destruction` | Same four files; stored layouts may be identical |
| `LEVEL007` | `mmenu.obj`, initial menu choice 0 |
| `LEVEL008` | `3Dtext.obj`, components at their local origins |
| `LEVEL009 - Ruined Monastery` | `layout_0.obj`, `grid_0.obj` |
| `LEVEL010` | `Trophy.obj` |
| `STOCK` | `STOCK.obj`, 20 named cars, plus shared car textures |

Import a matching layout/grid pair for the track and starting cars. Grids use
forward starts, sequential car slots and player artwork choice 0, not every
possible championship order. STOCK cars overlap at their local origins;
select or separate by object.

Each model folder has `materials.mtl` and scenery textures where required.
**Keep `STOCK` alongside the level folders:** car materials use relative paths
to `../STOCK/Textures`. Moving a level alone breaks those links.

`STOCK/Textures` includes intact/damaged AI decals, five body selections per AI
car, and ten palette selections each for roof, windscreen and side windows.
Each of the six player artwork choices has **16 named material sections**:

- Five body selections; bonnet and boot.
- Normal decal, two damaged decals, and left/right decal crops.
- Front, front wing, rear and rear wing.

Exact duplicate pixels share a PNG, so 16 material sections need not mean 16 new
images. The material names use `car_00_player_01_` through `car_01_player_03_`.
Standalone PLAYCARS artwork stays in `PLAYCARS(RAW)`.

Garage trailer variants require `TRAILERS/TRAILERS.RAW` and `TRAIL2.RAW` through
`TRAIL20.RAW`. Twenty named trailer objects overlap at the original parked
position; select one or separate them. Missing files produce a warning and keep
the original single-trailer garage. No substitute livery is invented.

`extraction.log` records errors, unresolved records, palette-only resources and
texture mappings. Internal JSON files are temporary and are not published in
the output.

## Blender

Import using **Forward: -Z, Up: Y, Scale: 1**. Orientation and scale **0.0035**
are already applied. This scale is an approximate DD2 comparison, not verified
metres. Keep the OBJ, material library and referenced texture folders together.

Use Closest texture interpolation for crisp pixels. PNGs retain cutout alpha;
connect Image Alpha to material Alpha if the importer does not do so.

Static wheel repair is applied before splitting textures and includes both
opposite-winding lower faces. Source vertices and polygon winding are retained;
no welding or wheel-face deletion is performed. Splitting objects into separate
files rebases OBJ indices. Damage artwork is included; meshes are undeformed.

## Options

| Option | Purpose |
|---|---|
| `--levels 1 2` | Process selected levels; standalone images still export |
| `--images-only` | Extract standalone TIM/RAW images only |
| `--skip-grid` | Omit starting grids; STOCK setup still requires Unicorn |
| `--scale 1` | Choose a different output scale |
| `--source-coordinates --scale 1` | Preserve original axes and dimensions |
| `--source-wheels` | Preserve stored wheel UVs instead of static repair |
| `--transparent-zero` | Use cutout alpha for zero-colour standalone-image pixels |
| `--version` | Display the public release version |

## Scope and known limitations

- Confirmed structures and executable-assisted setup apply to the supplied USA
  build. Other releases/platforms are not established as supported.
- Ocean Drive's unfinished alternate references a missing model. Some City Heat
  materials lack recovered texture data and appear diagnostic magenta.
- Native track exports omit unsupported sprite records. LEVEL001 retains its
  validated static scenery planes when executable-assisted export is available.
  Camera-facing scenery uses a fixed viewing angle.
- Texture crops follow model UV references; they are not proven original authored
  boundaries. Only the primary barrier UV set is exported.
- Day/night lighting, reverse-race setup, live TV/digits, wheel animation, damage
  deformation and full PlayStation semi-transparency are not simulated.
- Secondary LODs, alternate menu selections and redundant model libraries are not
  published by this simplified release. Source records are still parsed/checked.

The public-release review checked archive integrity, Python 3.11 syntax, local
imports and basic CLI/image execution. Full-game extraction and native Windows /
Blender testing were not rerun during that review. Earlier development testing
covered the supplied levels; see the log for each extraction's actual results.
