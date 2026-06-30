# Place Helper Changelog

## 2.0.1 — 2026-06-30

**Minimum Blender version:** 5.0.0

### Place Tool
- Drag to place objects on surfaces with normal alignment and collision detection
- **Shift + drag** to duplicate while placing
- **Alt + click** to set the placement axis via gizmo
- **Use Object Up Axis** — per-object up axis (same behavior as BAS Place); scene-wide axis when disabled
- **Alt + drag** for box selection; first selected object is promoted to active after box select
- **Limit to Ground** — prevents objects from going below Z = 0 while moving
- Rotate / scale gizmos; **drag + mouse wheel** to spin; **Ctrl + Alt + wheel** for 90° steps

### Transform Pro
- **Left-drag** to move objects directly in the viewport
- **Shift / Alt + drag** to duplicate while moving (Instance / Object via toolbar)
- **Double-click object** to enter Edit Mode; **double-click empty space** to exit (auto-switches to Transform Pro Edit)
- Optional **Show Gizmo** toggle (off by default)
- **Shift + drag** in Edit Mode to extrude mesh geometry

### Scatter Tool *(New)*
- Brush-based scattering with **density** (instances per unit area)
- **Radius**, **density**, and **scale** support **pressure sensitivity** and **random** ranges (via popover menus)
- Random spacing, random height, and **stacking mode**
- Source probability weights with randomize; **Apply** and **Clear** scatter
- **Limit to Surface** — skip samples outside the target surface
- Slope / height filters and image-based density mask
- **Alt + wheel** or **[ / ]** to adjust brush radius; **Ctrl + drag** to erase
- **Alt + drag** on empty space to box-select scatter sources
- Custom UI icons: `STYLUS_PRESSURE` for pressure, dice icon for random

### Dynamic Place
- **Gravity Dynamic Place** — drag objects with gravity simulation
- **Force Field Dynamic Place** — drag or scale to apply force field effects

### General UX
- **Tool Help** overlay in the lower-left corner (English / Chinese), toggle in toolbar
- Help offset defaults: **60, 60** (configurable in preferences)
- **Esc** on any tool exits to the built-in **Box Select** tool
- Streamlined scatter toolbar — height and duplicate moved into the settings popover

### Other
- Improved overall **code quality** and maintainability across all tools
- Fixed **crashes on undo** in the scatter tool (stale RNA / collection references)
- Fixed tools becoming **inactive after opening a new scene** or reloading a file
- Fixed placement tool **losing the active object** after box selection
- Fixed **box select conflicting with object move** in Place and Transform Pro
- Fixed **double icons** on scatter popover buttons
- Fixed **circular import** error on addon registration (`resolve_place_axis`)
- Fixed scatter instances placed **outside the target surface** when brush radius exceeds the plane
- Fixed **SyntaxWarning** and **keymap not found** warnings on startup
- Minimum supported Blender version raised to **5.0.0**

### Code Quality & Architecture
- All custom operators migrated to standard `object.ph_*` / `mesh.ph_*` prefixes (Blender extension compliance)
- Placement axis logic extracted to `axis.py` to resolve circular imports
- RNA pointers re-fetched after undo / scene changes; defensive handling to prevent crashes
- Explicit box-select keymap definitions; eliminated “keymap not found” warnings
- Complete `blender_manifest.toml` metadata; cross-platform zip packaging
- Draw handlers registered on demand and unregistered on tool exit
- Scatter header controls grouped with popovers for pressure / random ranges

---

## 2.0.0 — 2026-06-30

Initial major release consolidating all tools and features listed above.

**Requires:** Blender 5.0.0 or later  
**License:** GPL-3.0-or-later  
**Links:** [GitHub](https://github.com/AIGODLIKE/PlaceHelper) · [Issues](https://github.com/AIGODLIKE/PlaceHelper/issues)
