"""
VideoStyle configuration for video creation workflow
Separated from video_creator.py to avoid circular imports
"""

from dataclasses import dataclass
from typing import Dict, Optional
import random


# Theme definitions for different educational subjects and audiences
THEMES = {
    "tech": {
        "name": "Tech & Programming",
        "background_color": "#0a0a0a",
        "background_gradient": "linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 50%, #16213e 100%)",
        "primary_color": "#00ff88",
        "secondary_color": "#b4b4b4",
        "accent_color": "#00d4ff",
        "success_color": "#00ff88",
        "warning_color": "#ffa500",
        "error_color": "#ff4757",
        "code_background": "linear-gradient(145deg, #1a1a2e 0%, #16213e 100%)",
        "card_background": "rgba(0, 212, 255, 0.1)",
        "glow_shadow": "0 0 20px rgba(0, 255, 136, 0.3)",
        "voice_name": "Leda"  # Youthful - good for tech content
    },
    "science": {
        "name": "Science & Research",
        "background_color": "#0d1b2a",
        "background_gradient": "linear-gradient(135deg, #0d1b2a 0%, #1b263b 50%, #415a77 100%)",
        "primary_color": "#e0e1dd",
        "secondary_color": "#778da9",
        "accent_color": "#4cc9f0",
        "success_color": "#7209b7",
        "warning_color": "#f77f00",
        "error_color": "#d62828",
        "code_background": "linear-gradient(145deg, #1b263b 0%, #415a77 100%)",
        "card_background": "rgba(76, 201, 240, 0.1)",
        "glow_shadow": "0 0 20px rgba(76, 201, 240, 0.3)",
        "voice_name": "Charon"  # Informative - perfect for science
    },
    "business": {
        "name": "Business & Finance",
        "background_color": "#1a1a2e",
        "background_gradient": "linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)",
        "primary_color": "#eee2dc",
        "secondary_color": "#bab2b5",
        "accent_color": "#123c69",
        "success_color": "#ac3b61",
        "warning_color": "#edc7b7",
        "error_color": "#ee6c4d",
        "code_background": "linear-gradient(145deg, #16213e 0%, #0f3460 100%)",
        "card_background": "rgba(18, 60, 105, 0.1)",
        "glow_shadow": "0 0 20px rgba(18, 60, 105, 0.3)",
        "voice_name": "Sadaltager"  # Knowledgeable - good for business
    },
    "creative": {
        "name": "Art & Design",
        "background_color": "#2d1b69",
        "background_gradient": "linear-gradient(135deg, #2d1b69 0%, #11998e 50%, #38ef7d 100%)",
        "primary_color": "#f8f9fa",
        "secondary_color": "#e9ecef",
        "accent_color": "#ff6b6b",
        "success_color": "#51cf66",
        "warning_color": "#ffd43b",
        "error_color": "#ff8787",
        "code_background": "linear-gradient(145deg, #2d1b69 0%, #11998e 100%)",
        "card_background": "rgba(255, 107, 107, 0.1)",
        "glow_shadow": "0 0 20px rgba(255, 107, 107, 0.3)",
        "voice_name": "Aoede"  # Breezy - good for creative content
    },
    "health": {
        "name": "Health & Medicine",
        "background_color": "#0f4c75",
        "background_gradient": "linear-gradient(135deg, #0f4c75 0%, #3282b8 50%, #bbe1fa 100%)",
        "primary_color": "#ffffff",
        "secondary_color": "#f0f8ff",
        "accent_color": "#1e90ff",
        "success_color": "#32cd32",
        "warning_color": "#ffa500",
        "error_color": "#dc143c",
        "code_background": "linear-gradient(145deg, #0f4c75 0%, #3282b8 100%)",
        "card_background": "rgba(30, 144, 255, 0.1)",
        "glow_shadow": "0 0 20px rgba(30, 144, 255, 0.3)",
        "voice_name": "Iapetus"  # Clear - good for health/medical content
    },
    "language": {
        "name": "Language & Literature",
        "background_color": "#3c096c",
        "background_gradient": "linear-gradient(135deg, #3c096c 0%, #5a189a 50%, #7209b7 100%)",
        "primary_color": "#f72585",
        "secondary_color": "#b5179e",
        "accent_color": "#f72585",
        "success_color": "#4cc9f0",
        "warning_color": "#ffb3c6",
        "error_color": "#fb8500",
        "code_background": "linear-gradient(145deg, #3c096c 0%, #5a189a 100%)",
        "card_background": "rgba(247, 37, 133, 0.1)",
        "glow_shadow": "0 0 20px rgba(247, 37, 133, 0.3)",
        "voice_name": "Vindemiatrix"  # Gentle - good for language/literature
    },
    "kids": {
        "name": "Kids & Education",
        "background_color": "#ff6b6b",
        "background_gradient": "linear-gradient(135deg, #ff6b6b 0%, #4ecdc4 50%, #45b7d1 100%)",
        "primary_color": "#ffffff",
        "secondary_color": "#f8f9fa",
        "accent_color": "#feca57",
        "success_color": "#48dbfb",
        "warning_color": "#ff9ff3",
        "error_color": "#ff5722",
        "code_background": "linear-gradient(145deg, #ff6b6b 0%, #4ecdc4 100%)",
        "card_background": "rgba(254, 202, 87, 0.2)",
        "glow_shadow": "0 0 20px rgba(254, 202, 87, 0.4)",
        "voice_name": "Laomedeia"  # Upbeat - perfect for kids content
    },
    "professional": {
        "name": "Professional & Corporate",
        "background_color": "#2c3e50",
        "background_gradient": "linear-gradient(135deg, #2c3e50 0%, #34495e 50%, #3498db 100%)",
        "primary_color": "#ecf0f1",
        "secondary_color": "#bdc3c7",
        "accent_color": "#3498db",
        "success_color": "#2ecc71",
        "warning_color": "#f39c12",
        "error_color": "#e74c3c",
        "code_background": "linear-gradient(145deg, #2c3e50 0%, #34495e 100%)",
        "card_background": "rgba(52, 152, 219, 0.1)",
        "glow_shadow": "0 0 20px rgba(52, 152, 219, 0.3)",
        "voice_name": "Kore"  # Firm - good for professional content
    },
    "minimal": {
        "name": "Minimal & Clean",
        "background_color": "#f8f9fa",
        "background_gradient": "linear-gradient(135deg, #f8f9fa 0%, #e9ecef 50%, #dee2e6 100%)",
        "primary_color": "#212529",
        "secondary_color": "#495057",
        "accent_color": "#007bff",
        "success_color": "#28a745",
        "warning_color": "#ffc107",
        "error_color": "#dc3545",
        "code_background": "linear-gradient(145deg, #f8f9fa 0%, #e9ecef 100%)",
        "card_background": "rgba(0, 123, 255, 0.05)",
        "glow_shadow": "0 0 20px rgba(0, 123, 255, 0.2)",
        "voice_name": "Schedar"  # Even - good for minimal/clean content
    }
}


# Host/Guest voice pairs for dialog videos
# Ensures all theme voices are included as hosts with appropriate guest pairings
HOST_GUEST_VOICE_PAIRS = {
    # Theme voices (all included as hosts)
    "Leda": "Puck",           # Youthful -> Upbeat (tech)
    "Charon": "Aoede",        # Informative -> Breezy (science)
    "Sadaltager": "Leda",     # Knowledgeable -> Youthful (business)
    "Aoede": "Charon",        # Breezy -> Informative (creative)
    "Iapetus": "Callirrhoe",  # Clear -> Easy-going (health)
    "Vindemiatrix": "Fenrir", # Gentle -> Excitable (language)
    "Laomedeia": "Sulafat",   # Upbeat -> Warm (kids)
    "Kore": "Puck",           # Firm -> Upbeat (professional)
    "Schedar": "Achird",      # Even -> Friendly (minimal)
    
    # Additional voice pairs for variety
    "Zephyr": "Umbriel",      # Bright -> Easy-going
    "Alnilam": "Vindemiatrix", # Firm -> Gentle
    "Gacrux": "Sadachbia",    # Mature -> Lively
    "Algieba": "Laomedeia",   # Smooth -> Upbeat
    "Despina": "Sulafat",     # Smooth -> Warm
    "Erinome": "Autonoe",     # Clear -> Bright
    "Rasalgethi": "Aoede",    # Informative -> Breezy
    "Achernar": "Fenrir",     # Soft -> Excitable
    "Orus": "Zubenelgenubi",  # Firm -> Casual
    "Enceladus": "Pulcherrima", # Breathy -> Forward
    "Puck": "Kore",           # Upbeat -> Firm
    "Fenrir": "Achernar",     # Excitable -> Soft
    "Umbriel": "Zephyr",      # Easy-going -> Bright
    "Callirrhoe": "Iapetus",  # Easy-going -> Clear
    "Autonoe": "Erinome",     # Bright -> Clear
    "Algenib": "Despina",     # Gravelly -> Smooth
    "Achird": "Schedar",      # Friendly -> Even
    "Zubenelgenubi": "Orus",  # Casual -> Firm
    "Sadachbia": "Gacrux",    # Lively -> Mature
    "Sulafat": "Laomedeia",   # Warm -> Upbeat
    "Pulcherrima": "Enceladus", # Forward -> Breathy
}


def get_guest_voice(host_voice: str) -> str:
    """Get the best guest voice for a given host voice"""
    return HOST_GUEST_VOICE_PAIRS.get(host_voice, "Puck")  # Default to Puck if no pair found


@dataclass
class VideoStyle:
    """HTML5-based style configuration for consistent video design"""
    # Theme configuration
    theme: Optional[str] = None  # Theme name or None for random selection
    
    # Layout dimensions
    width: int = 1080
    height: int = 1920
    
    # Background styling - Will be set by theme
    background_color: str = "#0f0f0f"
    background_gradient: Optional[str] = "linear-gradient(135deg, #0f0f0f 0%, #1a1a1a 50%, #0f0f0f 100%)"
    background_image: Optional[str] = None
    
    # Typography - Mobile-optimized
    primary_font_family: str = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"
    secondary_font_family: str = "'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, 'Courier New', monospace"
    base_font_size: int = 28  # Larger base font size for mobile readability
    line_height: float = 1.6  # Better line spacing for mobile
    
    # Color palette - Will be set by theme
    primary_color: str = "#ffffff"
    secondary_color: str = "#e5e5e5"
    accent_color: str = "#007AFF"  # iOS-style blue
    success_color: str = "#30D158"  # iOS-style green
    warning_color: str = "#FF9F0A"  # iOS-style orange
    error_color: str = "#FF453A"   # iOS-style red
    
    # Text styling - Mobile-optimized sizes
    title_font_size: int = 54
    subtitle_font_size: int = 38
    body_font_size: int = 28
    code_font_size: int = 26  # Specific code font size
    caption_font_size: int = 22
    title_font_weight: str = "bold"
    body_font_weight: str = "normal"
    
    # Layout spacing - Mobile-optimized
    margin: int = 48
    padding: int = 32
    inner_padding: int = 24  # For nested elements
    border_radius: int = 16
    small_radius: int = 8
    
    # Animation settings - Enhanced for mobile
    animation_duration: str = "0.6s"
    animation_easing: str = "cubic-bezier(0.2, 0, 0.2, 1)"  # Material design easing
    
    # Border and shadow - Enhanced for mobile
    border_width: int = 1
    border_color: str = "rgba(255, 255, 255, 0.1)"
    box_shadow: str = "0 8px 32px rgba(0, 0, 0, 0.3)"
    glow_shadow: str = "0 0 20px rgba(0, 122, 255, 0.2)"
    
    # Content-specific styling - Will be set by theme
    code_background: str = "linear-gradient(145deg, #1e1e1e 0%, #2a2a2a 100%)"
    code_border: str = "rgba(255, 255, 255, 0.15)"
    header_background: str = "rgba(0, 0, 0, 0.3)"
    code_color: str = "#e5e5e5"
    quote_border_color: str = "#007AFF"
    table_border_color: str = "rgba(255, 255, 255, 0.1)"
    table_header_background: str = "rgba(0, 0, 0, 0.3)"
    
    # Enhanced visual effects for modern design
    card_background: str = "rgba(255, 255, 255, 0.05)"
    card_border_width: int = 8
    card_gap: int = 24
    backdrop_blur: str = "blur(10px)"
    glow_intensity: int = 24
    bullet_font_size: int = 36
    
    # Logo and branding
    logo_url: Optional[str] = None
    brand_color: Optional[str] = None
    
    # Voice configuration for TTS
    voice_name: str = "Kore"  # Default Gemini voice
    
    def __post_init__(self):
        """Apply theme configuration after initialization"""
        self.apply_theme()
    
    def apply_theme(self):
        """Apply the selected theme or choose a random one"""
        if self.theme is None:
            # Select a random theme
            self.theme = random.choice(list(THEMES.keys()))
        
        if self.theme in THEMES:
            theme_config = THEMES[self.theme]
            # Apply theme colors and settings (but keep default code styling)
            self.background_color = theme_config["background_color"]
            self.background_gradient = theme_config["background_gradient"]
            self.primary_color = theme_config["primary_color"]
            self.secondary_color = theme_config["secondary_color"]
            self.accent_color = theme_config["accent_color"]
            self.success_color = theme_config["success_color"]
            self.warning_color = theme_config["warning_color"]
            self.error_color = theme_config["error_color"]
            # Keep default code_background for consistent dark theme
            self.card_background = theme_config["card_background"]
            self.glow_shadow = theme_config["glow_shadow"]
            self.voice_name = theme_config["voice_name"]
            
            # Don't override Dart-style code highlighting colors - use defaults
            # This ensures consistent dark theme for code panels across all themes
            
            # Update dependent colors
            self.quote_border_color = self.accent_color
            # Keep default code_color for consistent dark theme
            
            # Adjust borders based on theme (except for code borders)
            if self.theme == "minimal":
                self.border_color = "rgba(0, 0, 0, 0.1)"
                self.table_border_color = "rgba(0, 0, 0, 0.1)"
                # Keep default code_border for consistent dark theme
            else:
                self.border_color = f"rgba({self._hex_to_rgba(self.primary_color)}, 0.1)"
                self.table_border_color = f"rgba({self._hex_to_rgba(self.primary_color)}, 0.1)"
                # Keep default code_border for consistent dark theme
    
    def _hex_to_rgba(self, hex_color: str) -> str:
        """Convert hex color to RGB values string"""
        hex_color = hex_color.lstrip('#')
        try:
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            return f"{r}, {g}, {b}"
        except (ValueError, IndexError):
            return "255, 255, 255"  # Default to white if conversion fails
    
    @classmethod
    def get_available_themes(cls) -> Dict[str, str]:
        """Get available themes with their display names"""
        return {key: value["name"] for key, value in THEMES.items()}
    
    def get_theme_info(self) -> Dict[str, str]:
        """Get information about the current theme"""
        if self.theme and self.theme in THEMES:
            return {
                "theme_key": self.theme,
                "theme_name": THEMES[self.theme]["name"],
                "description": f"Optimized for {THEMES[self.theme]['name'].lower()} content"
            }
        return {"theme_key": "default", "theme_name": "Default", "description": "Default theme"}
    
    def to_css_vars(self) -> Dict[str, str]:
        """Convert style configuration to CSS custom properties"""
        css_vars = {
            "--video-width": f"{self.width}px",
            "--video-height": f"{self.height}px",
            "--bg-color": self.background_color,
            "--bg-gradient": self.background_gradient or "none",
            "--primary-font": self.primary_font_family,
            "--secondary-font": self.secondary_font_family,
            "--code-font": self.secondary_font_family,
            "--base-font-size": f"{self.base_font_size}px",
            "--line-height": str(self.line_height),
            "--primary-color": self.primary_color,
            "--secondary-color": self.secondary_color,
            "--accent-color": self.accent_color,
            "--success-color": self.success_color,
            "--warning-color": self.warning_color,
            "--error-color": self.error_color,
            "--title-size": f"{self.title_font_size}px",
            "--subtitle-size": f"{self.subtitle_font_size}px",
            "--body-size": f"{self.body_font_size}px",
            "--code-size": f"{self.code_font_size}px",
            "--caption-size": f"{self.caption_font_size}px",
            "--title-weight": self.title_font_weight,
            "--body-weight": self.body_font_weight,
            "--margin": f"{self.margin}px",
            "--padding": f"{self.padding}px",
            "--inner-padding": f"{self.inner_padding}px",
            "--border-radius": f"{self.border_radius}px",
            "--small-radius": f"{self.small_radius}px",
            "--animation-duration": self.animation_duration,
            "--animation-easing": self.animation_easing,
            "--border-width": f"{self.border_width}px",
            "--border-color": self.border_color,
            "--box-shadow": self.box_shadow,
            "--glow-shadow": self.glow_shadow,
            "--code-bg": self.code_background,
            "--code-border": self.code_border,
            "--header-bg": self.header_background,
            "--code-color": self.code_color,
            "--quote-border": self.quote_border_color,
            "--table-border": self.table_border_color,
            "--table-header-bg": self.table_header_background,
            "--card-bg": self.card_background,
            "--card-border-width": f"{self.card_border_width}px",
            "--card-gap": f"{self.card_gap}px",
            "--backdrop-blur": self.backdrop_blur,
            "--glow-intensity": f"{self.glow_intensity}px",
            "--bullet-font-size": f"{self.bullet_font_size}px",
        }
        
        # Add theme information
        theme_info = self.get_theme_info()
        css_vars.update({
            "--theme-name": theme_info["theme_name"],
            "--theme-key": theme_info["theme_key"],
        })
        
        return css_vars
