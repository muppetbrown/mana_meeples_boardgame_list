"""
Board Game Label Generator Service
Generates PDF labels for board games using ReportLab
"""

from io import BytesIO
from pathlib import Path
from typing import List, Optional
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPDF

# Label dimensions - aspect ratio of 3:1 (width:height)
LABEL_WIDTH = 4 * inch
LABEL_HEIGHT = LABEL_WIDTH / 3  # ~1.33 inches

# Page settings for Letter size (8.5" x 11")
PAGE_WIDTH, PAGE_HEIGHT = letter
MARGIN = 0.25 * inch

# Layout dimensions
LOGO_WIDTH = LABEL_WIDTH / 3  # 33.3% for logo
INFO_WIDTH = (LABEL_WIDTH * 2) / 3  # 66.7% for info

# Grid layout (2 columns x 7 rows = 14 labels per page)
LABELS_PER_ROW = 2
LABELS_PER_COL = 7

# Colors (matching frontend theme)
COLOR_COOP_BG = colors.HexColor('#10b981')  # Green
COLOR_COMPETITIVE_BG = colors.HexColor('#ef4444')  # Red
COLOR_LOGO_BG = colors.HexColor('#f3f4f6')  # Light gray
COLOR_TEXT = colors.HexColor('#1f2937')  # Dark gray
COLOR_TEXT_LIGHT = colors.HexColor('#6b7280')  # Medium gray

# Category-specific colors (from mana_meeple_category)
CATEGORY_COLORS = {
    'KIDS_FAMILIES': colors.HexColor('#9C7788'),
    'PARTY_ICEBREAKERS': colors.HexColor('#9E2E28'),
    'GATEWAY_STRATEGY': colors.HexColor('#A89A1E'),
    'COOP_ADVENTURE': colors.HexColor('#8D9B47'),
    'CORE_STRATEGY': colors.HexColor('#70949F'),
}

# Default color for unknown categories
DEFAULT_CATEGORY_COLOR = colors.HexColor('#8b5cf6')  # Purple/indigo


class LabelGenerator:
    """Service for generating PDF labels for board games"""

    def __init__(self):
        self.assets_path = Path(__file__).parent.parent / "assets"
        self.logo_path = self.assets_path / "mana_meeples_logo_v3.svg"

        # Icon paths for stats
        self.icon_players = self.assets_path / "group.png"
        self.icon_time = self.assets_path / "clock.png"
        self.icon_age = self.assets_path / "cake.png"
        self.icon_complexity = self.assets_path / "puzzle.png"
        self.icon_coop = self.assets_path / "partners.png"
        self.icon_competitive = self.assets_path / "swords.png"

    def _get_contrast_text_color(self, bg_color: colors.Color) -> colors.Color:
        """Get contrasting text color (white or black) based on background color"""
        # Get RGB values (0-1 range)
        r, g, b = bg_color.red, bg_color.green, bg_color.blue

        # Calculate relative luminance
        luminance = 0.299 * r + 0.587 * g + 0.114 * b

        # Return white for dark backgrounds, black for light backgrounds
        return colors.white #if luminance < 0.5 else colors.black

    def generate_pdf(self, games: List[dict]) -> BytesIO:
        """
        Generate PDF with labels for the given games

        Args:
            games: List of game dictionaries with required fields:
                - title, players_min, players_max, playtime_min, playtime_max,
                  min_age, complexity, game_type, is_cooperative

        Returns:
            BytesIO buffer containing the PDF
        """
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)

        label_count = 0
        for game in games:
            # Calculate position (3 columns, 4 rows per page)
            col = label_count % LABELS_PER_ROW
            row = (label_count // LABELS_PER_ROW) % LABELS_PER_COL

            # Start new page after 12 labels
            if label_count > 0 and label_count % (LABELS_PER_ROW * LABELS_PER_COL) == 0:
                c.showPage()

            # Calculate label position (origin at bottom-left)
            x = MARGIN + (col * LABEL_WIDTH)
            y = PAGE_HEIGHT - MARGIN - ((row + 1) * LABEL_HEIGHT)

            self._draw_label(c, game, x, y)
            label_count += 1

        c.save()
        buffer.seek(0)
        return buffer

    def _draw_label(self, c: canvas.Canvas, game: dict, x: float, y: float):
        """Draw a single game label at the specified position"""

        # Draw label border
        c.setStrokeColor(colors.grey)
        c.setLineWidth(0.5)
        c.rect(x, y, LABEL_WIDTH, LABEL_HEIGHT)

        # Logo section (left 1/3)
        self._draw_logo_section(c, x, y)

        # Info section (right 2/3)
        info_x = x + LOGO_WIDTH
        self._draw_info_section(c, game, info_x, y)

    def _draw_logo_section(self, c: canvas.Canvas, x: float, y: float):
        """Draw the logo section (left 1/3 of label)"""

        # Background
        c.setFillColor(COLOR_LOGO_BG)
        c.rect(x, y, LOGO_WIDTH, LABEL_HEIGHT, fill=1, stroke=0)

        # Logo image (if exists)
        if self.logo_path.exists():
            try:
                # Convert SVG to ReportLab drawing
                drawing = svg2rlg(str(self.logo_path))
                if drawing:
                    # Scale to fit in logo section (80% of available space)
                    target_size = min(LOGO_WIDTH * 0.8, LABEL_HEIGHT * 0.8)
                    scale = target_size / max(drawing.width, drawing.height)
                    drawing.width *= scale
                    drawing.height *= scale
                    drawing.scale(scale, scale)

                    # Center the logo
                    logo_x = x + (LOGO_WIDTH - drawing.width) / 2
                    logo_y = y + (LABEL_HEIGHT - drawing.height) / 2

                    # Render SVG
                    renderPDF.draw(drawing, c, logo_x, logo_y)
            except Exception:
                # If logo fails to load, just leave the background
                pass

    def _draw_info_section(self, c: canvas.Canvas, game: dict, x: float, y: float):
        """Draw the info section (right 2/3 of label)"""

        # Split vertically: 60% for title/badges, 40% for stats
        title_section_height = LABEL_HEIGHT * 0.6
        stats_section_height = LABEL_HEIGHT * 0.4

        # Draw title and badges (top section)
        self._draw_title_and_badges(c, game, x, y + stats_section_height, INFO_WIDTH, title_section_height)

        # Draw stats grid (bottom section)
        self._draw_stats_grid(c, game, x, y, INFO_WIDTH, stats_section_height)

    def _draw_title_and_badges(self, c: canvas.Canvas, game: dict, x: float, y: float, width: float, height: float):
        """Draw game title and badges"""

        padding = 0.1 * inch
        available_width = width - (2 * padding)

        # Game title
        title = game.get('title', 'Unknown Game')
        c.setFillColor(COLOR_TEXT)

        # Dynamic font sizing to fit title on one line
        font_size = 16  # Start with max
        min_font_size = 8
        c.setFont('Helvetica-Bold', font_size)
        title_width = c.stringWidth(title, 'Helvetica-Bold', font_size)

        # Reduce font size until it fits
        while title_width > available_width and font_size > min_font_size:
            font_size -= 1
            c.setFont('Helvetica-Bold', font_size)
            title_width = c.stringWidth(title, 'Helvetica-Bold', font_size)

        # Draw title on single line
        title_y = y + height - padding - font_size - 2
        c.drawString(x + padding, title_y, title)

        # Badges positioned with fixed spacing below title
        badge_y = title_y - 20  # Fixed 20pt spacing below title
        self._draw_badges(c, game, x + padding, badge_y)

    def _split_title(self, words: List[str], max_length: int) -> tuple:
        """Split title into two lines"""
        line1 = []
        line2 = []
        current_length = 0

        for word in words:
            if current_length + len(word) + 1 <= max_length:
                line1.append(word)
                current_length += len(word) + 1
            else:
                line2.append(word)

        return (' '.join(line1), ' '.join(line2))

    def _draw_badges(self, c: canvas.Canvas, game: dict, x: float, y: float):
        """Draw cooperative/competitive and game type badges"""

        badge_height = 14
        current_x = x
        icon_size = 10  # Icon size in points

        # Cooperative/Competitive badge
        is_coop = game.get('is_cooperative', False)
        coop_text = 'Co-op' if is_coop else 'Competitive'
        coop_color = COLOR_COOP_BG if is_coop else COLOR_COMPETITIVE_BG
        icon_path = self.icon_coop if is_coop else self.icon_competitive

        c.setFillColor(coop_color)
        c.setFont('Helvetica-Bold', 8)
        # Calculate actual text width using stringWidth
        text_width = c.stringWidth(coop_text, 'Helvetica-Bold', 8)
        badge_width = text_width + icon_size + 12  # Text width + icon + padding
        c.roundRect(current_x, y, badge_width, badge_height, 4, fill=1, stroke=0)

        # Draw text
        c.setFillColor(colors.white)
        c.drawString(current_x + 4, y + 4, coop_text)

        # Draw icon if exists
        if icon_path.exists():
            try:
                icon_x = current_x + text_width + 6
                icon_y = y + 2
                c.drawImage(
                    str(icon_path),
                    icon_x, icon_y,
                    width=icon_size,
                    height=icon_size,
                    preserveAspectRatio=True,
                    mask='auto'
                )
            except Exception:
                pass  # If icon fails, just show text

        current_x += badge_width + 4

        # Game type badge with category-based coloring
        game_type = game.get('game_type', 'Strategy')
        if game_type:
            # Get category color based on mana_meeple_category
            category = game.get('mana_meeple_category')
            category_color = CATEGORY_COLORS.get(category, DEFAULT_CATEGORY_COLOR)

            c.setFillColor(category_color)
            c.setFont('Helvetica-Bold', 8)
            # Calculate actual text width
            type_text_width = c.stringWidth(game_type, 'Helvetica-Bold', 8)
            type_badge_width = type_text_width + 8  # Text width + padding
            c.roundRect(current_x, y, type_badge_width, badge_height, 4, fill=1, stroke=0)

            # Use contrasting text color based on background
            text_color = self._get_contrast_text_color(category_color)
            c.setFillColor(text_color)
            c.drawString(current_x + 4, y + 4, game_type)

    def _draw_stats_grid(self, c: canvas.Canvas, game: dict, x: float, y: float, width: float, height: float):
        """Draw stats grid (players, time, age, complexity)"""

        padding = 0.1 * inch
        stat_y = y + height / 2 + 10  # Center vertically

        # First row: Players and Time
        col1_x = x + padding
        col2_x = x + width / 2 + padding / 2

        # Players
        players = self._format_player_count(game.get('players_min'), game.get('players_max'))
        self._draw_stat(c, col1_x, stat_y, self.icon_players, players, 10)

        # Time
        playtime = self._format_playtime(game.get('playtime_min'), game.get('playtime_max'))
        self._draw_stat(c, col2_x, stat_y, self.icon_time, playtime, 10)

        # Second row: Age and Complexity
        stat_y -= 20

        # Age
        age = self._format_age(game.get('min_age'))
        if age:
            self._draw_stat(c, col1_x, stat_y, self.icon_age, age, 10)

        # Complexity
        complexity = self._create_complexity_display(game.get('complexity'))
        self._draw_stat(c, col2_x, stat_y, self.icon_complexity, complexity, 10)

    def _draw_stat(self, c: canvas.Canvas, x: float, y: float, icon_path: Path, value: str, font_size: int):
        """Draw a single stat with icon and value"""

        icon_size = 12  # Icon size in points (0.17 inches)

        # Draw icon if exists
        if icon_path.exists():
            try:
                c.drawImage(
                    str(icon_path),
                    x, y,
                    width=icon_size,
                    height=icon_size,
                    preserveAspectRatio=True,
                    mask='auto'
                )
            except Exception:
                pass  # If icon fails, skip it

        # Draw value
        c.setFillColor(COLOR_TEXT)
        c.setFont('Helvetica', font_size)
        c.drawString(x + icon_size + 3, y, value)

    def _format_player_count(self, min_players: Optional[int], max_players: Optional[int]) -> str:
        """Format player count range"""
        if not min_players and not max_players:
            return "? players"

        if min_players == max_players:
            return f"{min_players} player" if min_players == 1 else f"{min_players} players"

        if min_players and max_players:
            return f"{min_players}-{max_players} players"

        return f"{min_players or max_players} players"

    def _format_playtime(self, min_time: Optional[int], max_time: Optional[int]) -> str:
        """Format playtime range"""
        if not min_time and not max_time:
            return "? min"

        if min_time == max_time:
            return f"{min_time} min"

        if min_time and max_time:
            # If times are very close, just show one
            if abs(min_time - max_time) <= 5:
                return f"~{max_time} min"
            return f"{min_time}-{max_time} min"

        return f"{min_time or max_time} min"

    def _format_age(self, min_age: Optional[int]) -> str:
        """Format minimum age"""
        if not min_age:
            return ""
        return f"Age {min_age}+"

    def _create_complexity_display(self, complexity: Optional[float]) -> str:
        """Create numeric display for complexity rating (X.X/5.0)"""
        if complexity is None:
            return "?/5.0"

        # Clamp to 0-5 range
        w = max(0.0, min(5.0, complexity))
        return f"{w:.1f}/5.0"
