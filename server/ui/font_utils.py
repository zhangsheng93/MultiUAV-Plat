import os
import pygame
import sys

_BUNDLED_FONT_FILES = {
    "alibabapuhuiti": "AlibabaPuHuiTi-3-55-Regular.ttf",
    "arial": "Arial.ttf",
    "helvetica": "Helvetica.ttc",
}


def _bundled_font_path(name: str) -> str | None:
    """Return the bundled font file for the requested family when it exists."""
    normalized_name = name.lower()
    filename = _BUNDLED_FONT_FILES.get(normalized_name)

    if not filename:
        return None

    candidate_paths = []

    if getattr(sys, "frozen", False):
        candidate_paths.append(os.path.join(sys._MEIPASS, "ui", "font", filename))

    candidate_paths.append(os.path.join(os.path.dirname(__file__), "font", filename))

    for path in candidate_paths:
        if os.path.exists(path):
            return path

    return None


def safe_sys_font(name: str, size: int, bold: bool = False, italic: bool = False) -> pygame.font.Font:
    """Create a system font with a bundled-family fallback and a final default fallback."""
    safe_size = max(1, int(size))

    if not pygame.font.get_init():
        pygame.font.init()

    bundled_font = _bundled_font_path(name)

    try:
        matched_font = pygame.font.match_font(name, bold=bold, italic=italic)
        if not matched_font and bundled_font:
            fallback = pygame.font.Font(bundled_font, safe_size)
            fallback.set_bold(bold)
            fallback.set_italic(italic)
            return fallback

        return pygame.font.SysFont(name, safe_size, bold=bold, italic=italic)
    except (TypeError, OSError, ValueError) as e:
        # print(f"Warning: Failed to load system font '{name}' (Size: {size}). Falling back to default font.", file=sys.stderr)
        # print(f"Details: {type(e).__name__}: {e}", file=sys.stderr)
        
        # if sys.platform == "win32" and isinstance(e, TypeError) and "not int" in str(e):
        #     print("Hint: Your Windows Font Registry is likely corrupt. One or more fonts have an integer value instead of a file path.", file=sys.stderr)
        #     print("To fix: Open 'regedit', go to 'HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Fonts', and look for any entries that are NOT strings (REG_SZ). Delete or fix those entries.", file=sys.stderr)
        
        if bundled_font:
            fallback = pygame.font.Font(bundled_font, safe_size)
        else:
            fallback = pygame.font.Font(None, safe_size)
        fallback.set_bold(bold)
        fallback.set_italic(italic)
        return fallback
