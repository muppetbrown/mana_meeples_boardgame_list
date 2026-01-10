"""
Tests for BGG Parser Module
Comprehensive tests for all XML parsing functions
"""
import pytest
from xml.etree.ElementTree import Element, SubElement
from services.bgg_parser import (
    parse_basic_info,
    parse_images,
    parse_player_counts,
    parse_playtime,
    parse_links,
    parse_expansion_relationships,
    parse_statistics,
    strip_namespace,
)


class TestParseBasicInfo:
    """Tests for parse_basic_info function"""

    def test_parse_complete_basic_info(self):
        """Test parsing complete basic information"""
        item = Element("item", type="boardgame")
        name = SubElement(item, "name", type="primary", value="Test Game")
        year = SubElement(item, "yearpublished", value="2020")
        desc = SubElement(item, "description")
        desc.text = "A great game &amp; fun to play&#10;New line"

        result = parse_basic_info(item)

        assert result["title"] == "Test Game"
        assert result["year"] == 2020
        assert result["is_expansion"] is False
        assert result["item_type"] == "boardgame"
        assert "A great game & fun to play" in result["description"]
        assert "\nNew line" in result["description"]

    def test_parse_expansion_type(self):
        """Test parsing expansion item type"""
        item = Element("item", type="boardgameexpansion")
        name = SubElement(item, "name", type="primary", value="Test Expansion")

        result = parse_basic_info(item)

        assert result["is_expansion"] is True
        assert result["item_type"] == "boardgameexpansion"

    def test_parse_no_primary_name(self):
        """Test fallback to non-primary name"""
        item = Element("item", type="boardgame")
        name = SubElement(item, "name", value="Alternate Name")

        result = parse_basic_info(item)

        assert result["title"] == "Alternate Name"

    def test_parse_no_name(self):
        """Test handling missing name element"""
        item = Element("item", type="boardgame")

        result = parse_basic_info(item)

        assert result["title"] == ""

    def test_parse_invalid_year(self):
        """Test handling invalid year value"""
        item = Element("item", type="boardgame")
        name = SubElement(item, "name", type="primary", value="Test")
        year = SubElement(item, "yearpublished", value="invalid")

        result = parse_basic_info(item)

        assert result["year"] is None

    def test_parse_no_year(self):
        """Test handling missing year element"""
        item = Element("item", type="boardgame")
        name = SubElement(item, "name", type="primary", value="Test")

        result = parse_basic_info(item)

        assert result["year"] is None

    def test_parse_html_entities_in_description(self):
        """Test HTML entity decoding in description"""
        item = Element("item", type="boardgame")
        name = SubElement(item, "name", type="primary", value="Test")
        desc = SubElement(item, "description")
        desc.text = "&quot;Quoted&quot; text &amp; more &#10;with newline"

        result = parse_basic_info(item)

        assert '"Quoted" text & more' in result["description"]
        assert "\nwith newline" in result["description"]

    def test_parse_long_description_truncation(self):
        """Test description truncation at 2000 characters"""
        item = Element("item", type="boardgame")
        name = SubElement(item, "name", type="primary", value="Test")
        desc = SubElement(item, "description")
        desc.text = "A" * 3000  # 3000 characters

        result = parse_basic_info(item)

        assert len(result["description"]) == 2000
        assert result["description"] == "A" * 2000

    def test_parse_empty_description(self):
        """Test handling empty description"""
        item = Element("item", type="boardgame")
        name = SubElement(item, "name", type="primary", value="Test")
        desc = SubElement(item, "description")
        desc.text = ""

        result = parse_basic_info(item)

        assert result["description"] is None

    def test_parse_no_description(self):
        """Test handling missing description element"""
        item = Element("item", type="boardgame")
        name = SubElement(item, "name", type="primary", value="Test")

        result = parse_basic_info(item)

        assert result["description"] is None


class TestParseImages:
    """Tests for parse_images function"""

    def test_parse_both_images(self):
        """Test parsing thumbnail and full image"""
        item = Element("item")
        thumbnail = SubElement(item, "thumbnail")
        thumbnail.text = "  https://example.com/thumb.jpg  "
        image = SubElement(item, "image")
        image.text = "  https://example.com/image.jpg  "

        result = parse_images(item)

        assert result["thumbnail"] == "https://example.com/thumb.jpg"
        assert result["image"] == "https://example.com/image.jpg"

    def test_parse_no_thumbnail(self):
        """Test handling missing thumbnail"""
        item = Element("item")
        image = SubElement(item, "image")
        image.text = "https://example.com/image.jpg"

        result = parse_images(item)

        assert result["thumbnail"] is None
        assert result["image"] == "https://example.com/image.jpg"

    def test_parse_no_image(self):
        """Test handling missing image"""
        item = Element("item")
        thumbnail = SubElement(item, "thumbnail")
        thumbnail.text = "https://example.com/thumb.jpg"

        result = parse_images(item)

        assert result["thumbnail"] == "https://example.com/thumb.jpg"
        assert result["image"] is None

    def test_parse_empty_images(self):
        """Test handling empty image elements"""
        item = Element("item")
        thumbnail = SubElement(item, "thumbnail")
        thumbnail.text = ""
        image = SubElement(item, "image")
        image.text = ""

        result = parse_images(item)

        assert result["thumbnail"] is None
        assert result["image"] is None

    def test_parse_no_images(self):
        """Test handling no image elements"""
        item = Element("item")

        result = parse_images(item)

        assert result["thumbnail"] is None
        assert result["image"] is None


class TestParsePlayerCounts:
    """Tests for parse_player_counts function"""

    def test_parse_player_counts(self):
        """Test parsing min/max player counts"""
        item = Element("item")
        min_players = SubElement(item, "minplayers", value="2")
        max_players = SubElement(item, "maxplayers", value="4")

        result = parse_player_counts(item)

        assert result["players_min"] == 2
        assert result["players_max"] == 4

    def test_parse_solo_game(self):
        """Test parsing solo game (1-1 players)"""
        item = Element("item")
        min_players = SubElement(item, "minplayers", value="1")
        max_players = SubElement(item, "maxplayers", value="1")

        result = parse_player_counts(item)

        assert result["players_min"] == 1
        assert result["players_max"] == 1

    def test_parse_invalid_player_counts(self):
        """Test handling invalid player count values"""
        item = Element("item")
        min_players = SubElement(item, "minplayers", value="invalid")
        max_players = SubElement(item, "maxplayers", value="invalid")

        result = parse_player_counts(item)

        assert result["players_min"] is None
        assert result["players_max"] is None

    def test_parse_missing_player_counts(self):
        """Test handling missing player count elements"""
        item = Element("item")

        result = parse_player_counts(item)

        assert result["players_min"] is None
        assert result["players_max"] is None


class TestParsePlaytime:
    """Tests for parse_playtime function"""

    def test_parse_playtime_range(self):
        """Test parsing min/max playtime"""
        item = Element("item")
        min_time = SubElement(item, "minplaytime", value="30")
        max_time = SubElement(item, "maxplaytime", value="60")
        age = SubElement(item, "minage", value="10")

        result = parse_playtime(item)

        assert result["playtime_min"] == 30
        assert result["playtime_max"] == 60
        assert result["min_age"] == 10

    def test_parse_zero_playtime(self):
        """Test handling zero playtime values (should be None)"""
        item = Element("item")
        min_time = SubElement(item, "minplaytime", value="0")
        max_time = SubElement(item, "maxplaytime", value="0")

        result = parse_playtime(item)

        assert result["playtime_min"] is None
        assert result["playtime_max"] is None

    def test_parse_fallback_to_playingtime(self):
        """Test fallback to playingtime when min/max not present"""
        item = Element("item")
        play_time = SubElement(item, "playingtime", value="45")

        result = parse_playtime(item)

        assert result["playtime_min"] == 45
        assert result["playtime_max"] == 45

    def test_parse_zero_playingtime_fallback(self):
        """Test fallback with zero playingtime (should be None)"""
        item = Element("item")
        play_time = SubElement(item, "playingtime", value="0")

        result = parse_playtime(item)

        assert result["playtime_min"] is None
        assert result["playtime_max"] is None

    def test_parse_no_playtime(self):
        """Test handling missing playtime elements"""
        item = Element("item")

        result = parse_playtime(item)

        assert result["playtime_min"] is None
        assert result["playtime_max"] is None
        assert result["min_age"] is None

    def test_parse_invalid_age(self):
        """Test handling invalid age value"""
        item = Element("item")
        age = SubElement(item, "minage", value="invalid")

        result = parse_playtime(item)

        assert result["min_age"] is None


class TestParseLinks:
    """Tests for parse_links function"""

    def test_parse_categories(self):
        """Test parsing category links"""
        item = Element("item")
        link1 = SubElement(item, "link", type="boardgamecategory", value="Strategy")
        link2 = SubElement(item, "link", type="boardgamecategory", value="Economic")

        result = parse_links(item, "boardgamecategory")

        assert len(result) == 2
        assert "Strategy" in result
        assert "Economic" in result

    def test_parse_mechanics(self):
        """Test parsing mechanic links"""
        item = Element("item")
        link1 = SubElement(item, "link", type="boardgamemechanic", value="Deck Building")
        link2 = SubElement(item, "link", type="boardgamemechanic", value="Worker Placement")

        result = parse_links(item, "boardgamemechanic")

        assert len(result) == 2
        assert "Deck Building" in result
        assert "Worker Placement" in result

    def test_parse_designers(self):
        """Test parsing designer links"""
        item = Element("item")
        link = SubElement(item, "link", type="boardgamedesigner", value="Jamey Stegmaier")

        result = parse_links(item, "boardgamedesigner")

        assert len(result) == 1
        assert "Jamey Stegmaier" in result

    def test_parse_empty_values(self):
        """Test filtering out empty link values"""
        item = Element("item")
        link1 = SubElement(item, "link", type="boardgamecategory", value="Strategy")
        link2 = SubElement(item, "link", type="boardgamecategory", value="  ")  # Whitespace only
        link3 = SubElement(item, "link", type="boardgamecategory", value="")  # Empty

        result = parse_links(item, "boardgamecategory")

        assert len(result) == 1
        assert "Strategy" in result

    def test_parse_no_links(self):
        """Test handling no links of specified type"""
        item = Element("item")

        result = parse_links(item, "boardgamecategory")

        assert len(result) == 0
        assert result == []


class TestParseExpansionRelationships:
    """Tests for parse_expansion_relationships function"""

    def test_parse_base_game_link(self):
        """Test parsing base game link for expansion"""
        item = Element("item")
        link = SubElement(
            item,
            "link",
            type="boardgameexpansion",
            inbound="true",
            id="12345",
            value="Base Game Name"
        )

        result = parse_expansion_relationships(item, "Test Expansion", True)

        assert result["base_game_bgg_id"] == 12345
        assert result["base_game_name"] == "Base Game Name"

    def test_parse_expansion_links(self):
        """Test parsing expansion links for base game"""
        item = Element("item")
        link1 = SubElement(item, "link", type="boardgameexpansion", id="100", value="Expansion 1")
        link2 = SubElement(item, "link", type="boardgameexpansion", id="200", value="Expansion 2")

        result = parse_expansion_relationships(item, "Base Game", False)

        assert len(result["expansion_bgg_ids"]) == 2
        assert result["expansion_bgg_ids"][0]["bgg_id"] == 100
        assert result["expansion_bgg_ids"][0]["name"] == "Expansion 1"
        assert result["expansion_bgg_ids"][1]["bgg_id"] == 200
        assert result["expansion_bgg_ids"][1]["name"] == "Expansion 2"

    def test_parse_player_expansion_pattern(self):
        """Test auto-detecting player count modifications"""
        item = Element("item")

        # Test 5-6 Player pattern
        result = parse_expansion_relationships(item, "Catan: 5-6 Player Extension", True)
        assert result.get("modifies_players_min") == 5
        assert result.get("modifies_players_max") == 6

        # Test with hyphen
        result = parse_expansion_relationships(item, "Game: 7–8 Player Expansion", True)
        assert result.get("modifies_players_min") == 7
        assert result.get("modifies_players_max") == 8

    def test_parse_standalone_expansion(self):
        """Test detecting standalone expansions"""
        item = Element("item")

        result = parse_expansion_relationships(item, "Test: Standalone Expansion", True)
        assert result.get("expansion_type") == "both"

        result = parse_expansion_relationships(item, "Game: Stand-Alone Edition", True)
        assert result.get("expansion_type") == "both"

    def test_parse_requires_base_expansion(self):
        """Test default expansion type (requires base)"""
        item = Element("item")

        result = parse_expansion_relationships(item, "Regular Expansion", True)
        assert result.get("expansion_type") == "requires_base"

    def test_parse_no_expansion_data_for_base_game(self):
        """Test base game has no expansion-specific fields"""
        item = Element("item")

        result = parse_expansion_relationships(item, "Base Game", False)

        assert result.get("base_game_bgg_id") is None
        assert result.get("base_game_name") is None
        assert "modifies_players_min" not in result
        assert "modifies_players_max" not in result
        assert "expansion_type" not in result

    def test_parse_invalid_base_game_id(self):
        """Test handling invalid base game ID"""
        item = Element("item")
        link = SubElement(
            item,
            "link",
            type="boardgameexpansion",
            inbound="true",
            id="invalid",
            value="Base Game"
        )

        result = parse_expansion_relationships(item, "Expansion", True)

        assert result["base_game_bgg_id"] is None
        assert result["base_game_name"] is None

    def test_parse_skip_inbound_expansion_links(self):
        """Test skipping inbound links (base games, not expansions)"""
        item = Element("item")
        link1 = SubElement(item, "link", type="boardgameexpansion", inbound="true", id="100", value="Base Game")
        link2 = SubElement(item, "link", type="boardgameexpansion", id="200", value="Real Expansion")

        result = parse_expansion_relationships(item, "Base Game", False)

        # Should only have the non-inbound expansion
        assert len(result["expansion_bgg_ids"]) == 1
        assert result["expansion_bgg_ids"][0]["bgg_id"] == 200


class TestParseStatistics:
    """Tests for parse_statistics function"""

    def test_parse_complete_statistics(self):
        """Test parsing complete statistics data"""
        item = Element("item")
        statistics = SubElement(item, "statistics")
        ratings = SubElement(statistics, "ratings")

        average = SubElement(ratings, "average", value="7.5")
        weight = SubElement(ratings, "averageweight", value="3.2")
        users_rated = SubElement(ratings, "usersrated", value="1000")

        ranks = SubElement(ratings, "ranks")
        rank1 = SubElement(ranks, "rank", type="subtype", name="boardgame", value="150")
        rank2 = SubElement(ranks, "rank", type="family", name="strategygames", value="75")

        result = parse_statistics(item)

        assert result["average_rating"] == 7.5
        assert result["complexity"] == 3.2
        assert result["users_rated"] == 1000
        assert result["bgg_rank"] == 150
        assert result["game_type"] == "strategygames"

    def test_parse_zero_rating(self):
        """Test handling zero rating (should be None)"""
        item = Element("item")
        statistics = SubElement(item, "statistics")
        ratings = SubElement(statistics, "ratings")
        average = SubElement(ratings, "average", value="0")

        result = parse_statistics(item)

        assert result["average_rating"] is None

    def test_parse_zero_complexity(self):
        """Test handling zero complexity (should be None)"""
        item = Element("item")
        statistics = SubElement(item, "statistics")
        ratings = SubElement(statistics, "ratings")
        weight = SubElement(ratings, "averageweight", value="0")

        result = parse_statistics(item)

        assert result["complexity"] is None

    def test_parse_not_ranked(self):
        """Test handling 'Not Ranked' rank value"""
        item = Element("item")
        statistics = SubElement(item, "statistics")
        ratings = SubElement(statistics, "ratings")
        ranks = SubElement(ratings, "ranks")
        rank = SubElement(ranks, "rank", type="subtype", name="boardgame", value="Not Ranked")

        result = parse_statistics(item)

        assert result["bgg_rank"] is None

    def test_parse_multiple_ranked_categories(self):
        """Test selecting best (lowest) ranked category"""
        item = Element("item")
        statistics = SubElement(item, "statistics")
        ratings = SubElement(statistics, "ratings")
        ranks = SubElement(ratings, "ranks")

        rank1 = SubElement(ranks, "rank", type="family", name="strategygames", value="100")
        rank2 = SubElement(ranks, "rank", type="family", name="familygames", value="50")  # Best rank
        rank3 = SubElement(ranks, "rank", type="family", name="thematic", value="150")

        result = parse_statistics(item)

        # Should select the lowest rank (best) = familygames
        assert result["game_type"] == "familygames"

    def test_parse_not_ranked_category(self):
        """Test handling 'Not Ranked' category without consensus"""
        item = Element("item")
        statistics = SubElement(item, "statistics")
        ratings = SubElement(statistics, "ratings")
        ranks = SubElement(ratings, "ranks")

        rank1 = SubElement(ranks, "rank", type="family", name="partygames", value="Not Ranked")

        result = parse_statistics(item)

        assert result["game_type"] == "partygames"

    def test_parse_cooperative_game_type(self):
        """Test is_cooperative flag for thematic/cgs games"""
        item = Element("item")
        statistics = SubElement(item, "statistics")
        ratings = SubElement(statistics, "ratings")
        ranks = SubElement(ratings, "ranks")

        rank = SubElement(ranks, "rank", type="family", name="thematic", value="100")

        result = parse_statistics(item)

        assert result["is_cooperative"] is None  # Can't determine from thematic

    def test_parse_non_cooperative_game_type(self):
        """Test is_cooperative flag for strategy games"""
        item = Element("item")
        statistics = SubElement(item, "statistics")
        ratings = SubElement(statistics, "ratings")
        ranks = SubElement(ratings, "ranks")

        rank = SubElement(ranks, "rank", type="family", name="strategygames", value="100")

        result = parse_statistics(item)

        assert result["is_cooperative"] is False

    def test_parse_no_statistics(self):
        """Test handling missing statistics element"""
        item = Element("item")

        result = parse_statistics(item)

        assert result["average_rating"] is None
        assert result["complexity"] is None
        assert result["bgg_rank"] is None
        assert result["users_rated"] is None
        assert result["game_type"] is None
        assert result["is_cooperative"] is None

    def test_parse_no_ratings(self):
        """Test handling missing ratings element"""
        item = Element("item")
        statistics = SubElement(item, "statistics")

        result = parse_statistics(item)

        assert result["average_rating"] is None
        assert result["complexity"] is None
        assert result["bgg_rank"] is None

    def test_parse_invalid_statistics_values(self):
        """Test handling invalid statistic values"""
        item = Element("item")
        statistics = SubElement(item, "statistics")
        ratings = SubElement(statistics, "ratings")

        average = SubElement(ratings, "average", value="invalid")
        weight = SubElement(ratings, "averageweight", value="invalid")
        users_rated = SubElement(ratings, "usersrated", value="invalid")

        result = parse_statistics(item)

        assert result["average_rating"] is None
        assert result["complexity"] is None
        assert result["users_rated"] is None


class TestStripNamespace:
    """Tests for strip_namespace function"""

    def test_strip_namespace_from_tags(self):
        """Test removing namespace from element tags"""
        root = Element("{http://example.com}root")
        child = SubElement(root, "{http://example.com}child")

        strip_namespace(root)

        assert root.tag == "root"
        assert child.tag == "child"

    def test_strip_namespace_from_attributes(self):
        """Test removing namespace from attribute keys"""
        root = Element("root")
        root.attrib["{http://example.com}attr"] = "value"
        root.attrib["normal_attr"] = "normal"

        strip_namespace(root)

        assert "attr" in root.attrib
        assert root.attrib["attr"] == "value"
        assert "normal_attr" in root.attrib
        assert "{http://example.com}attr" not in root.attrib

    def test_strip_namespace_nested_elements(self):
        """Test removing namespace from deeply nested elements"""
        root = Element("{http://example.com}root")
        child1 = SubElement(root, "{http://example.com}child1")
        child2 = SubElement(child1, "{http://example.com}child2")
        child3 = SubElement(child2, "{http://example.com}child3")

        strip_namespace(root)

        assert root.tag == "root"
        assert child1.tag == "child1"
        assert child2.tag == "child2"
        assert child3.tag == "child3"

    def test_strip_namespace_no_namespace(self):
        """Test handling elements without namespace"""
        root = Element("root")
        child = SubElement(root, "child")

        strip_namespace(root)

        assert root.tag == "root"
        assert child.tag == "child"

    def test_strip_namespace_mixed_elements(self):
        """Test handling mix of namespaced and non-namespaced elements"""
        root = Element("{http://example.com}root")
        child1 = SubElement(root, "child1")  # No namespace
        child2 = SubElement(root, "{http://example.com}child2")  # With namespace

        strip_namespace(root)

        assert root.tag == "root"
        assert child1.tag == "child1"
        assert child2.tag == "child2"
