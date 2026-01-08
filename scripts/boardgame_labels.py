#!/usr/bin/env python3
"""
Enhanced Board Game Label Generator
Creates responsive, attractive labels for board games
"""

import csv
from pathlib import Path
from typing import Dict, List, Optional
import config

class LabelGenerator:
    def __init__(self):
        self.games_data = []
        self.template_parts = []
    
    def load_game_data(self, csv_path: Path) -> bool:
        """Load game data from CSV file"""
        if not csv_path.exists():
            print(f"Error: {csv_path} not found. Run the BGG lookup script first.")
            return False
        
        try:
            with open(csv_path, newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                self.games_data = [row for row in reader if row.get('status') in ['OK', 'CACHED']]
            
            if config.VERBOSE_OUTPUT:
                total_rows = sum(1 for _ in open(csv_path, encoding='utf-8')) - 1  # -1 for header
                print(f"Loaded {len(self.games_data)} successful games out of {total_rows} total")
            
            return len(self.games_data) > 0
            
        except Exception as e:
            print(f"Error loading game data: {e}")
            return False
    
    def _create_star_display(self, weight: str) -> str:
        """Create star display for complexity rating - fixed half star"""
        try:
            w = float(weight) if weight else 0.0
        except (ValueError, TypeError):
            w = 0.0
        
        # Clamp to 0-5 range
        w = max(0.0, min(5.0, w))
        
        full_stars = int(w)
        remainder = w - full_stars
        
        if remainder >= 0.75:
            full_stars += 1
            half_stars = 0
        elif remainder >= 0.25:
            half_stars = 1
        else:
            half_stars = 0
        
        empty_stars = 5 - full_stars - half_stars
        
        # Check if image files exist - properly handle Path objects
        icon_paths = [Path(config.ICON_FULL), Path(config.ICON_HALF), Path(config.ICON_EMPTY)]
        icons_exist = all(icon_path.exists() for icon_path in icon_paths)
        
        if icons_exist and not config.USE_UNICODE_STARS:
            # Use image-based stars
            parts = []
            parts.extend([f'<img src="{config.ICON_FULL}" class="star" alt="★">' for _ in range(full_stars)])
            parts.extend([f'<img src="{config.ICON_HALF}" class="star" alt="☆½">' for _ in range(half_stars)])
            parts.extend([f'<img src="{config.ICON_EMPTY}" class="star" alt="☆">' for _ in range(empty_stars)])
            return ''.join(parts)
        else:
            # Use Unicode stars - fixed half star
            stars = ""
            stars += "★" * full_stars        # Full stars (filled)
            stars += "✩" * half_stars        # Half stars (different character)
            stars += "☆" * empty_stars       # Empty stars (outline)
            return stars
    
    def _format_player_count(self, min_players: str, max_players: str) -> str:
        """Format player count range"""
        min_p = min_players.strip()
        max_p = max_players.strip()
        
        if not min_p and not max_p:
            return "? players"
        
        if min_p == max_p:
            return f"{min_p} player{'s' if min_p != '1' else ''}"
        
        if min_p and max_p:
            return f"{min_p}–{max_p} players"
        
        return f"{min_p or max_p} players"
    
    def _format_playtime(self, min_time: str, max_time: str) -> str:
        """Format playtime range"""
        min_t = min_time.strip()
        max_t = max_time.strip()
        
        if not min_t and not max_t:
            return "? min"
        
        if min_t == max_t:
            return f"{min_t} min"
        
        if min_t and max_t:
            # If times are very close, just show one
            try:
                if abs(int(min_t) - int(max_t)) <= 5:
                    return f"~{max_t} min"
            except (ValueError, TypeError):
                pass
            return f"{min_t}–{max_t} min"
        
        return f"{min_t or max_t} min"
    
    def _format_age(self, min_age: str) -> str:
        """Format minimum age"""
        if not min_age.strip():
            return ""
        return f"Age {min_age}+"
    
    def _get_coop_indicator(self, coop_type: str) -> str:
        """Get cooperative/competitive indicator"""
        if coop_type.lower().startswith('coop'):
            return "Co-op 🤝"
        return "Competitive ⚔️"
    
    def _format_rating(self, avg_rating: str) -> str:
        """Format BGG average rating"""
        if not avg_rating.strip():
            return ""
        try:
            rating = float(avg_rating)
            return f"BGG: {rating:.1f}"
        except (ValueError, TypeError):
            return ""
    
    def _sanitize_text(self, text: str) -> str:
        """Sanitize text for HTML output"""
        if not text:
            return ""
        return (text.replace('&', '&amp;')
                   .replace('<', '&lt;')
                   .replace('>', '&gt;')
                   .replace('"', '&quot;')
                   .replace("'", '&#39;'))
    
    def _create_game_label(self, game: Dict) -> str:
        """Create HTML for a single game label - logo left layout"""
        title = self._sanitize_text(game.get('title', 'Unknown Game'))
        game_type = self._sanitize_text(game.get('game_type', 'Strategy'))
        
        # Split game types and create individual badges
        game_types = [t.strip() for t in game_type.split('•')] if '•' in game_type else [game_type]
        
        # Create coop badge as first badge
        coop_indicator = self._get_coop_indicator(game.get('coop_type', ''))
        coop_class = 'coop' if game.get('coop_type', '').lower().startswith('coop') else 'competitive'
        
        # Combine coop badge with type badges
        all_badges = f'<div class="type-badge coop-badge {coop_class}">{coop_indicator}</div>'
        for gtype in game_types:
            all_badges += f'<div class="type-badge">{gtype}</div>'
        
        # Format game details
        players = self._format_player_count(game.get('min_players', ''), game.get('max_players', ''))
        playtime = self._format_playtime(game.get('min_playtime', ''), game.get('max_playtime', ''))
        age = self._format_age(game.get('min_age', ''))
        stars = self._create_star_display(game.get('weight', ''))

        return f'''
<div class="label">
    <div class="header">
        <div class="logo-placeholder">
            <img src="mana_meeples_logo.svg" alt="M&M" class="logo" onerror="this.style.display='none'" />
        </div>
        <div class="title-section">
            <div class="title">{title}</div>
            <div class="type-badges">{all_badges}</div>
        </div>
    </div>
    
    <div class="stats-grid">
        <div class="stat-item">
            <div class="stat-icon">👥</div>
            <div class="stat-value">{players}</div>
        </div>
        
        <div class="stat-item">
            <div class="stat-icon">⏱️</div>
            <div class="stat-value">{playtime}</div>
        </div>
        
        {f'<div class="stat-item"><div class="stat-icon">🎂</div><div class="stat-value">{age}</div></div>' if age else ''}
        
        <div class="stat-item complexity-item">
            <div class="stat-icon">🧩</div>
            <div class="stat-value complexity-stars">{stars}</div>
        </div>
    </div>
</div>'''
    
    def _create_html_document(self, labels_html: str) -> str:
        """Create complete HTML document - FIXED path handling"""
        # Use relative path for CSS - assumes CSS is in same directory as HTML
        css_path = "label_styles.css"
        
        # Alternative: If you want CSS in a specific location, use Path resolution
        # css_path = Path(config.LABELS_HTML).parent / "label_styles.css"
        # css_path = css_path.as_posix()  # Convert to forward slashes for web
        
        return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>Board Game Labels</title>
    <link rel="stylesheet" href="{css_path}">
</head>
<body>
    <div class="sheet">
        {labels_html}
    </div>
</body>
</html>'''
    
    def generate_labels(self) -> bool:
        """Generate HTML labels file"""
        if not self.games_data:
            print("No game data loaded. Load data first.")
            return False
        
        if config.VERBOSE_OUTPUT:
            print(f"Generating labels for {len(self.games_data)} games...")
        
        # Generate label HTML for each game
        labels_html = ""
        successful_labels = 0
        
        for game in self.games_data:
            try:
                label_html = self._create_game_label(game)
                labels_html += label_html
                successful_labels += 1
            except Exception as e:
                print(f"Error creating label for game {game.get('title', 'Unknown')}: {e}")
        
        if successful_labels == 0:
            print("No labels could be generated!")
            return False
        
        # Create complete HTML document
        html_document = self._create_html_document(labels_html)
        
        # Write to file - properly handle Path objects
        try:
            output_path = Path(config.LABELS_HTML)
            # Ensure parent directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(html_document, encoding='utf-8')
            
            print(f"\n✅ Generated {successful_labels} labels!")
            print(f"📄 Saved to: {output_path}")
            print(f"🖨️ Open {output_path} in your browser and print with background graphics enabled")
            print(f"📏 Labels are {config.LABEL_HEIGHT} tall, {config.MIN_LABEL_WIDTH}-{config.MAX_LABEL_WIDTH} wide")
            
            return True
            
        except Exception as e:
            print(f"Error saving HTML file: {e}")
            return False
    
    def print_summary(self):
        """Print a summary of the loaded games"""
        if not self.games_data:
            print("No game data loaded.")
            return
        
        print(f"\n📊 Game Summary ({len(self.games_data)} games):")
        
        # Count by game type
        type_counts = {}
        for game in self.games_data:
            game_type = game.get('game_type', 'Unknown')
            type_counts[game_type] = type_counts.get(game_type, 0) + 1
        
        print("Game Types:")
        for game_type, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  {game_type}: {count}")
        
        # Count cooperative vs competitive
        coop_count = sum(1 for g in self.games_data if g.get('coop_type', '').lower().startswith('coop'))
        comp_count = len(self.games_data) - coop_count
        print(f"\nCoop/Competitive: {coop_count} co-op, {comp_count} competitive")
        
        # Complexity distribution
        complexities = []
        for game in self.games_data:
            try:
                weight = float(game.get('weight', 0))
                if weight > 0:
                    complexities.append(weight)
            except (ValueError, TypeError):
                pass
        
        if complexities:
            avg_complexity = sum(complexities) / len(complexities)
            print(f"Average Complexity: {avg_complexity:.1f}/5.0 stars")

def main():
    """Main execution function"""
    generator = LabelGenerator()
    
    # Load game data
    csv_path = Path(config.OUTPUT_CSV)
    if not generator.load_game_data(csv_path):
        print(f"Failed to load game data from {csv_path}")
        print("Make sure you've run the BGG lookup script first!")
        return
    
    # Print summary
    if config.VERBOSE_OUTPUT:
        generator.print_summary()
    
    # Generate labels
    success = generator.generate_labels()
    
    if success:
        print("\n🎲 Your board game labels are ready!")
        print("💡 Tip: Print on sticker paper and cut to size for best results")
    else:
        print("❌ Failed to generate labels")

if __name__ == "__main__":
    main()