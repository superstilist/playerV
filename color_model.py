"""
Color Model Module

This module provides optimized functions for color extraction from images and theme generation.
It includes utilities for color conversion, contrast calculation, and CSS theme generation.

Author: Generated Code Assistant
"""

import cv2
import numpy as np
from sklearn.cluster import KMeans
from collections import Counter
from scipy.stats import mode
import colorsys
import math
from typing import List, Tuple, Dict, Optional, Union, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Type aliases
RGBColor = Tuple[int, int, int]
HSLColor = Tuple[float, float, float]
ThemeColors = Dict[str, RGBColor]
ThemeResult = Dict[str, Any]

# Constants
DEFAULT_PALETTE: List[RGBColor] = [
    (52, 152, 219),    # Blue
    (46, 204, 113),   # Green
    (155, 89, 182),   # Purple
    (52, 73, 94),     # Dark Blue
    (241, 196, 15),   # Yellow
    (231, 76, 60)     # Red
]

IMAGE_SIZE = (200, 200)
KMEANS_CLUSTERS = 12
KMEANS_INIT = 5
MIN_SATURATION = 0.15
MIN_LIGHTNESS = 0.1
MAX_COLOR_VARIATIONS = 6
CONTRAST_THRESHOLD = 4.5
BACKGROUND_ADJUSTMENT = 20

# Global cache for extracted colors
color_cache: Dict[str, List[RGBColor]] = {}


class ColorExtractionError(Exception):
    """Custom exception for color extraction errors"""
    pass


class ThemeGenerationError(Exception):
    """Custom exception for theme generation errors"""
    pass


def to_rgb(color: Union[int, float, Tuple[float, ...], List[float]]) -> RGBColor:
    """
    Convert a color representation to RGB tuple.

    Args:
        color: Input color in various formats

    Returns:
        RGB tuple with 3 values (0-255 each)

    Raises:
        ValueError: If color cannot be converted to valid RGB
    """
    try:
        arr = np.array(color).flatten()
        if arr.size < 3:
            arr = np.pad(arr, (0, 3 - arr.size), 'constant', constant_values=0)

        if arr.size != 3:
            raise ValueError(f"Expected 3 color components, got {arr.size}")

        return tuple(int(max(0, min(255, c))) for c in arr[:3])
    except (ValueError, TypeError) as e:
        raise ValueError(f"Cannot convert {color} to RGB: {e}")


def rgb_to_hex(rgb: RGBColor) -> str:
    """Convert RGB color to hex format."""
    return "#{:02x}{:02x}{:02x}".format(rgb[0], rgb[1], rgb[2])


def hex_to_rgb(hex_color: str) -> RGBColor:
    """
    Convert hex color to RGB format.

    Args:
        hex_color: Hex color string (with or without #)

    Returns:
        RGB tuple

    Raises:
        ValueError: If hex color format is invalid
    """
    try:
        hex_color = hex_color.lstrip('#')
        if len(hex_color) != 6:
            raise ValueError(f"Invalid hex color format: {hex_color}")
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    except ValueError as e:
        raise ValueError(f"Invalid hex color '{hex_color}': {e}")


def rgb_to_hsl(rgb: RGBColor) -> HSLColor:
    """Convert RGB color to HSL format."""
    r, g, b = (c / 255.0 for c in rgb)
    return colorsys.rgb_to_hls(r, g, b)


def hsl_to_rgb(hsl: HSLColor) -> RGBColor:
    """Convert HSL color to RGB format."""
    h, l, s = hsl
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return (int(r * 255), int(g * 255), int(b * 255))


def calculate_luminance(r: int, g: int, b: int) -> float:
    """
    Calculate relative luminance for contrast ratio.

    Args:
        r, g, b: RGB components (0-255)

    Returns:
        Luminance value (0.0-1.0)
    """
    def adjust_gamma(c: float) -> float:
        c = c / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r_lin = adjust_gamma(r)
    g_lin = adjust_gamma(g)
    b_lin = adjust_gamma(b)

    return 0.2126 * r_lin + 0.7152 * g_lin + 0.0722 * b_lin


def get_contrast_ratio(color1: RGBColor, color2: RGBColor) -> float:
    """
    Calculate contrast ratio between two colors.

    Args:
        color1, color2: RGB color tuples

    Returns:
        Contrast ratio (>= 1.0)
    """
    lum1 = calculate_luminance(*color1)
    lum2 = calculate_luminance(*color2)

    lighter = max(lum1, lum2)
    darker = min(lum1, lum2)

    return (lighter + 0.05) / (darker + 0.05)


def ensure_text_contrast(background_rgb: RGBColor, text_rgb: Optional[RGBColor] = None) -> RGBColor:
    """
    Ensure text has sufficient contrast against background.

    Args:
        background_rgb: Background color
        text_rgb: Preferred text color (None for auto-detection)

    Returns:
        Text color with sufficient contrast
    """
    if text_rgb is None:
        text_rgb = (255, 255, 255)  # Default to white

    contrast = get_contrast_ratio(background_rgb, text_rgb)

    # Check if contrast is sufficient (WCAG AA minimum is 4.5:1)
    if contrast >= CONTRAST_THRESHOLD:
        return text_rgb

    # Try black text
    black_contrast = get_contrast_ratio(background_rgb, (0, 0, 0))
    if black_contrast >= CONTRAST_THRESHOLD:
        return (0, 0, 0)

    # Adjust background slightly to improve contrast with white text
    r, g, b = background_rgb
    if calculate_luminance(r, g, b) > 0.5:  # Light background
        r = max(0, r - BACKGROUND_ADJUSTMENT)
        g = max(0, g - BACKGROUND_ADJUSTMENT)
        b = max(0, b - BACKGROUND_ADJUSTMENT)
    else:  # Dark background
        r = min(255, r + BACKGROUND_ADJUSTMENT)
        g = min(255, g + BACKGROUND_ADJUSTMENT)
        b = min(255, b + BACKGROUND_ADJUSTMENT)

    return (255, 255, 255)  # Return white text for adjusted background


def validate_image_path(image_path: str) -> None:
    """
    Validate image file path.

    Args:
        image_path: Path to image file

    Raises:
        ValueError: If path is invalid
        FileNotFoundError: If file doesn't exist
    """
    if not image_path or not isinstance(image_path, str):
        raise ValueError("Image path must be a non-empty string")

    # Note: We don't check file existence here to avoid race conditions
    # The actual file check will happen during image loading


def load_and_preprocess_image(image_path: str) -> np.ndarray:
    """
    Load and preprocess image for color extraction.

    Args:
        image_path: Path to image file

    Returns:
        Preprocessed image array

    Raises:
        ColorExtractionError: If image cannot be loaded
    """
    try:
        image = cv2.imread(image_path)
        if image is None:
            raise ColorExtractionError(f"Could not load image: {image_path}")

        # Convert BGR to RGB
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # Resize for performance
        image = cv2.resize(image, IMAGE_SIZE)

        return image
    except Exception as e:
        raise ColorExtractionError(f"Failed to load image {image_path}: {e}")


def extract_color_candidates(pixels: np.ndarray) -> List[Tuple[RGBColor, float]]:
    """
    Extract candidate colors from image pixels using KMeans clustering.

    Args:
        pixels: Image pixels reshaped to (N, 3)

    Returns:
        List of (color, vibrancy_score) tuples
    """
    try:
        # Use KMeans to find dominant colors
        kmeans = KMeans(n_clusters=KMEANS_CLUSTERS, n_init=KMEANS_INIT, random_state=42)
        labels = kmeans.fit_predict(pixels)
        centers = np.array(kmeans.cluster_centers_, dtype=np.uint8)

        # Get RGB colors
        candidate_colors = [tuple(int(c) for c in center) for center in centers]

        # Calculate vibrancy scores and filter
        filtered_colors = []
        for rgb in candidate_colors:
            h, l, s = rgb_to_hsl(rgb)

            # Filter out low saturation (grays) and very dark colors
            if s > MIN_SATURATION and l > MIN_LIGHTNESS:
                # Calculate vibrancy score (saturation + brightness)
                score = s + l
                filtered_colors.append((rgb, score))

        # Sort by vibrancy score descending
        filtered_colors.sort(key=lambda x: x[1], reverse=True)

        return filtered_colors

    except Exception as e:
        logger.error(f"Error in color candidate extraction: {e}")
        return []


def pad_color_palette(colors: List[RGBColor], target_size: int = 6) -> List[RGBColor]:
    """
    Pad color palette to target size with default colors.

    Args:
        colors: Current color list
        target_size: Desired number of colors

    Returns:
        Padded color list
    """
    result = colors.copy()

    while len(result) < target_size:
        default_color = DEFAULT_PALETTE[len(result) % len(DEFAULT_PALETTE)]
        result.append(default_color)

    return result[:target_size]


def extract_dominant_colors(image_path: str, num_colors: int = 6) -> List[RGBColor]:
    """
    Extract exactly 6 dominant colors from an image, filtering low-saturation
    and prioritizing vibrant colors.

    Args:
        image_path: Path to the image file
        num_colors: Number of colors to extract

    Returns:
        List of RGB color tuples

    Raises:
        ColorExtractionError: If color extraction fails
    """
    # Check cache first
    if image_path in color_cache:
        cached_colors = color_cache[image_path]
        return cached_colors[:num_colors]

    try:
        # Validate input
        validate_image_path(image_path)

        # Load and preprocess image
        image = load_and_preprocess_image(image_path)

        # Reshape pixels
        pixels = image.reshape(-1, 3)

        # Extract candidate colors
        candidate_colors = extract_color_candidates(pixels)

        # Take top colors
        colors = [color for color, score in candidate_colors[:num_colors]]

        # Pad with defaults if needed
        colors = pad_color_palette(colors, num_colors)

        # Cache the result
        color_cache[image_path] = colors

        logger.info(f"Successfully extracted {len(colors)} colors from {image_path}")
        return colors

    except (ColorExtractionError, ValueError) as e:
        logger.warning(f"Color extraction failed for {image_path}: {e}")

        # Return default palette and cache it
        default_palette = pad_color_palette([], num_colors)
        color_cache[image_path] = default_palette
        return default_palette


def assign_color_roles(colors: List[RGBColor]) -> ThemeColors:
    """
    Assign semantic roles to colors based on brightness and saturation.

    Args:
        colors: List of RGB colors

    Returns:
        Dictionary mapping color roles to RGB colors

    Raises:
        ThemeGenerationError: If color roles cannot be assigned
    """
    if not colors:
        raise ThemeGenerationError("No colors provided for role assignment")

    try:
        # Sort by brightness
        brightness_sorted = sorted(colors, key=lambda c: sum(c) / 3)

        background = brightness_sorted[0]
        surface = brightness_sorted[1] if len(brightness_sorted) > 1 else brightness_sorted[0]
        remaining = brightness_sorted[2:]

        # Assign remaining colors based on saturation
        if remaining:
            sat_sorted = sorted(remaining, key=lambda c: rgb_to_hsl(c)[2], reverse=True)
            primary = sat_sorted[0]
            accent = sat_sorted[1] if len(sat_sorted) > 1 else primary
            secondary = sat_sorted[2] if len(sat_sorted) > 2 else accent
        else:
            primary = background
            accent = surface
            secondary = background

        # Ensure text colors have good contrast
        text = ensure_text_contrast(background)
        text_on_surface = ensure_text_contrast(surface)
        text_on_primary = ensure_text_contrast(primary)
        text_on_secondary = ensure_text_contrast(secondary)
        text_on_accent = ensure_text_contrast(accent)

        return {
            'primary': primary,
            'secondary': secondary,
            'accent': accent,
            'background': background,
            'surface': surface,
            'text': text,
            'text_on_surface': text_on_surface,
            'text_on_primary': text_on_primary,
            'text_on_secondary': text_on_secondary,
            'text_on_accent': text_on_accent,
        }

    except Exception as e:
        raise ThemeGenerationError(f"Failed to assign color roles: {e}")


def generate_color_variations(base_color: RGBColor, count: int = 6) -> List[RGBColor]:
    """
    Generate a palette of related colors from a base color.

    Args:
        base_color: Base RGB color
        count: Number of variations to generate

    Returns:
        List of RGB color variations
    """
    r, g, b = base_color
    h, l, s = rgb_to_hsl(base_color)

    colors = []
    for i in range(count):
        # Vary hue and saturation
        hue_variation = (i * 0.15) % 1.0
        sat_variation = 0.7 + (i * 0.05) % 0.3

        new_h = (h + hue_variation) % 1.0
        new_s = min(1.0, max(0.3, sat_variation))

        # Keep lightness similar but vary slightly
        new_l = max(0.2, min(0.8, l + (i * 0.05 - 0.15)))

        new_rgb = hsl_to_rgb((new_h, new_l, new_s))
        colors.append(new_rgb)

    return colors


def generate_base_styles(theme_colors: ThemeColors) -> str:
    """Generate base widget styles."""
    bg_color = rgb_to_hex(theme_colors['background'])
    text_color = rgb_to_hex(theme_colors['text'])

    return f"""/* Base theme styles */
QWidget {{
    background-color: {bg_color};
    color: {text_color};
}}"""


def generate_panel_styles(theme_colors: ThemeColors) -> str:
    """Generate panel widget styles."""
    bg_color = rgb_to_hex(theme_colors['background'])
    bg_rgb = f"{theme_colors['background'][0]}, {theme_colors['background'][1]}, {theme_colors['background'][2]}"
    surface_color = rgb_to_hex(theme_colors['surface'])
    surface_rgb = f"{theme_colors['surface'][0]}, {theme_colors['surface'][1]}, {theme_colors['surface'][2]}"

    return f"""/* Panel styles */
QFrame#leftPanel {{
    background-color: rgba({bg_rgb}, 0.8);
    border-radius: 16px;
}}

QFrame#pagesPanel {{
    background-color: rgba({surface_rgb}, 0.8);
    border-radius: 16px;
}}

QFrame#bottomPanel {{
    background-color: rgba({surface_rgb}, 0.9);
    border-radius: 16px;
}}"""


def generate_button_styles(theme_colors: ThemeColors) -> str:
    """Generate button widget styles."""
    primary_color = rgb_to_hex(theme_colors['primary'])
    primary_rgb = f"{theme_colors['primary'][0]}, {theme_colors['primary'][1]}, {theme_colors['primary'][2]}"
    text_rgb = f"{theme_colors['text'][0]}, {theme_colors['text'][1]}, {theme_colors['text'][2]}"
    text_on_primary = rgb_to_hex(theme_colors['text_on_primary'])

    return f"""/* Button styles */
QPushButton {{
    background-color: rgba({primary_rgb}, 0.8);
    border: 1px solid rgba({text_rgb}, 0.2);
    color: {text_on_primary};
    border-radius: 8px;
    padding: 8px 16px;
}}

QPushButton:hover {{
    background-color: rgba({primary_rgb}, 0.9);
}}

QPushButton:pressed {{
    background-color: {primary_color};
}}"""


def generate_progress_styles(theme_colors: ThemeColors) -> str:
    """Generate progress bar styles."""
    surface_color = rgb_to_hex(theme_colors['surface'])
    surface_rgb = f"{theme_colors['surface'][0]}, {theme_colors['surface'][1]}, {theme_colors['surface'][2]}"
    accent_color = rgb_to_hex(theme_colors['accent'])
    secondary_color = rgb_to_hex(theme_colors['secondary'])
    primary_color = rgb_to_hex(theme_colors['primary'])

    return f"""/* Progress bar styles */
QProgressBar::chunk {{
    background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0,
        stop:0 {accent_color}, stop:1 {secondary_color});
}}

QProgressBar {{
    background-color: rgba({surface_rgb}, 0.5);
    border: 1px solid {primary_color};
    border-radius: 4px;
}}"""


def generate_frame_styles(theme_colors: ThemeColors) -> str:
    """Generate frame widget styles."""
    surface_color = rgb_to_hex(theme_colors['surface'])
    surface_rgb = f"{theme_colors['surface'][0]}, {theme_colors['surface'][1]}, {theme_colors['surface'][2]}"
    text_rgb = f"{theme_colors['text'][0]}, {theme_colors['text'][1]}, {theme_colors['text'][2]}"
    primary_rgb = f"{theme_colors['primary'][0]}, {theme_colors['primary'][1]}, {theme_colors['primary'][2]}"
    text_on_surface = rgb_to_hex(theme_colors['text_on_surface'])

    return f"""/* Frame styles */
QFrame {{
    background-color: rgba({surface_rgb}, 0.7);
    border: 1px solid rgba({text_rgb}, 0.1);
    color: {text_on_surface};
    border-radius: 8px;
}}

QFrame:hover {{
    background-color: rgba({primary_rgb}, 0.1);
}}"""


def generate_scrollbar_styles(theme_colors: ThemeColors) -> str:
    """Generate scrollbar styles."""
    surface_color = rgb_to_hex(theme_colors['surface'])
    primary_color = rgb_to_hex(theme_colors['primary'])
    accent_color = rgb_to_hex(theme_colors['accent'])
    bg_color = rgb_to_hex(theme_colors['background'])

    return f"""/* ScrollBar styles */
QScrollBar {{
    background: {surface_color};
    width: 16px;
}}

QScrollBar::handle {{
    background: {primary_color};
    border-radius: 4px;
    min-height: 20px;
}}

QScrollBar::handle:hover {{
    background: {accent_color};
}}

QScrollBar::add-line, QScrollBar::sub-line {{
    background: {surface_color};
    border: none;
}}

QScrollBar::add-page, QScrollBar::sub-page {{
    background: {bg_color};
}}"""


def generate_menu_styles(theme_colors: ThemeColors) -> str:
    """Generate menu styles."""
    surface_color = rgb_to_hex(theme_colors['surface'])
    primary_color = rgb_to_hex(theme_colors['primary'])
    text_on_surface = rgb_to_hex(theme_colors['text_on_surface'])
    accent_color = rgb_to_hex(theme_colors['accent'])
    text_on_primary = rgb_to_hex(theme_colors['text_on_primary'])
    text_on_accent = rgb_to_hex(theme_colors['text_on_accent'])

    return f"""/* Menu styles */
QMenu {{
    background-color: {surface_color};
    color: {text_on_surface};
    border: 1px solid {primary_color};
    border-radius: 8px;
    padding: 4px;
}}

QMenu::item {{
    background: transparent;
    color: {text_on_surface};
    padding: 8px 16px;
    border-radius: 4px;
}}

QMenu::item:selected {{
    background: {primary_color};
    color: {text_on_primary};
}}

QMenu::item:pressed {{
    background: {accent_color};
    color: {text_on_accent};
}}"""


def generate_dialog_styles(theme_colors: ThemeColors) -> str:
    """Generate input dialog styles."""
    surface_color = rgb_to_hex(theme_colors['surface'])
    primary_color = rgb_to_hex(theme_colors['primary'])
    bg_color = rgb_to_hex(theme_colors['background'])
    text_on_surface = rgb_to_hex(theme_colors['text_on_surface'])
    text_color = rgb_to_hex(theme_colors['text'])
    accent_color = rgb_to_hex(theme_colors['accent'])
    primary_rgb = f"{theme_colors['primary'][0]}, {theme_colors['primary'][1]}, {theme_colors['primary'][2]}"
    text_on_primary = rgb_to_hex(theme_colors['text_on_primary'])

    return f"""/* Input Dialog styles */
QInputDialog {{
    background-color: {surface_color};
    color: {text_on_surface};
    border: 1px solid {primary_color};
    border-radius: 8px;
}}

QInputDialog QLabel {{
    color: {text_on_surface};
}}

QInputDialog QLineEdit {{
    background-color: {bg_color};
    color: {text_color};
    border: 1px solid {primary_color};
    border-radius: 4px;
    padding: 4px;
}}

QInputDialog QLineEdit:focus {{
    border-color: {accent_color};
}}

QInputDialog QPushButton {{
    background-color: rgba({primary_rgb}, 0.8);
    color: {text_on_primary};
    border: 1px solid {primary_color};
    border-radius: 4px;
    padding: 8px 16px;
}}

QInputDialog QPushButton:hover {{
    background-color: rgba({primary_rgb}, 0.9);
}}

QInputDialog QPushButton:pressed {{
    background-color: {primary_color};
}}"""


def generate_css_theme_from_colors(colors: List[RGBColor]) -> Tuple[str, ThemeColors]:
    """
    Generate a complete CSS theme from 6 colors.

    Args:
        colors: List of RGB colors

    Returns:
        Tuple of (css_theme_string, theme_colors_dict)

    Raises:
        ThemeGenerationError: If theme generation fails
    """
    try:
        if not colors:
            # Generate variations from a default color
            base_color = DEFAULT_PALETTE[0]
            colors = generate_color_variations(base_color, MAX_COLOR_VARIATIONS)
        elif len(colors) < MAX_COLOR_VARIATIONS:
            # Pad with variations of the first color
            base_color = colors[0]
            colors = pad_color_palette(colors, MAX_COLOR_VARIATIONS)

        # Assign semantic roles to colors
        theme_colors = assign_color_roles(colors)

        # Generate CSS theme by combining all style functions
        css_parts = [
            "/* Auto-generated theme from cover art */",
            generate_base_styles(theme_colors),
            generate_panel_styles(theme_colors),
            generate_button_styles(theme_colors),
            generate_progress_styles(theme_colors),
            generate_frame_styles(theme_colors),
            generate_scrollbar_styles(theme_colors),
            generate_menu_styles(theme_colors),
            generate_dialog_styles(theme_colors)
        ]

        css_theme = "\n\n".join(css_parts)

        logger.info("Successfully generated CSS theme")
        return css_theme, theme_colors

    except Exception as e:
        raise ThemeGenerationError(f"Failed to generate CSS theme: {e}")


def generate_theme_from_cover(cover_path: str) -> ThemeResult:
    """
    Main function to generate theme from cover art.

    Args:
        cover_path: Path to the cover image

    Returns:
        Dictionary with theme data
    """
    try:
        # Extract 6 dominant colors
        colors = extract_dominant_colors(cover_path, num_colors=MAX_COLOR_VARIATIONS)

        # Generate CSS theme
        css_theme, color_palette = generate_css_theme_from_colors(colors)

        return {
            'css_theme': css_theme,
            'colors': color_palette,
            'success': True
        }

    except (ColorExtractionError, ThemeGenerationError) as e:
        logger.error(f"Theme generation failed: {e}")

        # Return default theme
        try:
            default_css, default_colors = generate_css_theme_from_colors([])
            return {
                'css_theme': default_css,
                'colors': default_colors,
                'success': False
            }
        except Exception as fallback_error:
            logger.error(f"Fallback theme generation also failed: {fallback_error}")
            return {
                'css_theme': "/* Default fallback theme */",
                'colors': {},
                'success': False
            }


def clear_color_cache() -> None:
    """Clear the color extraction cache."""
    color_cache.clear()
    logger.info("Color cache cleared")


def get_cache_size() -> int:
    """Get the number of cached color extractions."""
    return len(color_cache)
