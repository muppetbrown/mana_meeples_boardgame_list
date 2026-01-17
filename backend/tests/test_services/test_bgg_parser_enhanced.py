"""
Comprehensive tests for BGG parser (services/bgg_parser.py)
Target: 7.4% → 90% coverage
Focus: All parser functions, edge cases, HTML decoding, namespace handling
"""
import pytest
import xml.etree.ElementTree as ET

from services.bgg_parser import (
    parse_basic_info,
    parse_images,
    parse_player_counts,
    parse_playtime,
    parse_links,
    parse_expansion_relationships,
    parse_statistics,
    strip_namespace
)


class TestParseBasicInfo:
    """Test basic info parsing (title, year, description, expansion flag)"""

    def test_parse_complete_basic_info(self):
        """Should parse all basic fields from complete XML"""
        xml = '''<item type="boardgame" id="1">
            <name type="primary" value="Gloomhaven"/>
            <name type="alternate" value="Alt Name"/>
            <yearpublished value="2017"/>
            <description>Epic tactical combat game&amp;test&#10;New line</description>
        </item>'''
        item = ET.fromstring(xml)

        result = parse_basic_info(item)

        assert result['title'] == 'Gloomhaven'
        assert result['year'] == 2017
        assert result['description'] == 'Epic tactical combat game&test\nNew line'
        assert result['is_expansion'] is False
        assert result['item_type'] == 'boardgame'

    def test_parse_expansion_type(self):
        """Should correctly identify expansions"""
        xml = '''<item type="boardgameexpansion" id="1">
            <name type="primary" value="Expansion Pack"/>
            <yearpublished value="2020"/>
        </item>'''
        item = ET.fromstring(xml)

        result = parse_basic_info(item)

        assert result['is_expansion'] is True
        assert result['item_type'] == 'boardgameexpansion'

    def test_parse_missing_primary_name_fallback(self):
        """Should fallback to first name if no primary name"""
        xml = '''<item type="boardgame" id="1">
            <name value="Fallback Name"/>
            <yearpublished value="2020"/>
        </item>'''
        item = ET.fromstring(xml)

        result = parse_basic_info(item)

        assert result['title'] == 'Fallback Name'

    def test_parse_invalid_year(self):
        """Should handle invalid year gracefully"""
        xml = '''<item type="boardgame" id="1">
            <name type="primary" value="Test"/>
            <yearpublished value="invalid"/>
        </item>'''
        item = ET.fromstring(xml)

        result = parse_basic_info(item)

        assert result['year'] is None

    def test_parse_missing_year(self):
        """Should handle missing year"""
        xml = '''<item type="boardgame" id="1">
            <name type="primary" value="Test"/>
        </item>'''
        item = ET.fromstring(xml)

        result = parse_basic_info(item)

        assert result['year'] is None

    def test_parse_html_entities_in_description(self):
        """Should decode HTML entities in description"""
        xml = '''<item type="boardgame" id="1">
            <name type="primary" value="Test"/>
            <description>&lt;b&gt;Bold&lt;/b&gt; &amp; &quot;quoted&quot; &#10;newline</description>
        </item>'''
        item = ET.fromstring(xml)

        result = parse_basic_info(item)

        assert '<b>Bold</b>' in result['description']
        assert '&' in result['description']
        assert '"quoted"' in result['description']
        assert '\n' in result['description']

    def test_parse_truncate_long_description(self):
        """Should truncate descriptions longer than 2000 characters"""
        long_desc = 'A' * 3000
        xml = f'''<item type="boardgame" id="1">
            <name type="primary" value="Test"/>
            <description>{long_desc}</description>
        </item>'''
        item = ET.fromstring(xml)

        result = parse_basic_info(item)

        assert len(result['description']) == 2000

    def test_parse_empty_description(self):
        """Should handle empty/missing description"""
        xml = '''<item type="boardgame" id="1">
            <name type="primary" value="Test"/>
        </item>'''
        item = ET.fromstring(xml)

        result = parse_basic_info(item)

        assert result['description'] is None


class TestParseImages:
    """Test image URL parsing"""

    def test_parse_both_images(self):
        """Should parse both thumbnail and full image"""
        xml = '''<item type="boardgame" id="1">
            <thumbnail>//cf.geekdo-images.com/thumb.jpg</thumbnail>
            <image>//cf.geekdo-images.com/full.jpg</image>
        </item>'''
        item = ET.fromstring(xml)

        result = parse_images(item)

        assert result['thumbnail'] == '//cf.geekdo-images.com/thumb.jpg'
        assert result['image'] == '//cf.geekdo-images.com/full.jpg'

    def test_parse_missing_images(self):
        """Should handle missing images"""
        xml = '''<item type="boardgame" id="1"></item>'''
        item = ET.fromstring(xml)

        result = parse_images(item)

        assert result['thumbnail'] is None
        assert result['image'] is None

    def test_parse_empty_image_elements(self):
        """Should handle empty image elements"""
        xml = '''<item type="boardgame" id="1">
            <thumbnail></thumbnail>
            <image></image>
        </item>'''
        item = ET.fromstring(xml)

        result = parse_images(item)

        assert result['thumbnail'] is None
        assert result['image'] is None


class TestParsePlayerCounts:
    """Test player count parsing"""

    def test_parse_valid_player_counts(self):
        """Should parse valid min/max player counts"""
        xml = '''<item type="boardgame" id="1">
            <minplayers value="2"/>
            <maxplayers value="4"/>
        </item>'''
        item = ET.fromstring(xml)

        result = parse_player_counts(item)

        assert result['players_min'] == 2
        assert result['players_max'] == 4

    def test_parse_missing_player_counts(self):
        """Should handle missing player counts"""
        xml = '''<item type="boardgame" id="1"></item>'''
        item = ET.fromstring(xml)

        result = parse_player_counts(item)

        assert result['players_min'] is None
        assert result['players_max'] is None

    def test_parse_invalid_player_counts(self):
        """Should handle invalid player count values"""
        xml = '''<item type="boardgame" id="1">
            <minplayers value="invalid"/>
            <maxplayers value="also invalid"/>
        </item>'''
        item = ET.fromstring(xml)

        result = parse_player_counts(item)

        assert result['players_min'] is None
        assert result['players_max'] is None

    def test_parse_solo_game(self):
        """Should handle solo games (1 player)"""
        xml = '''<item type="boardgame" id="1">
            <minplayers value="1"/>
            <maxplayers value="1"/>
        </item>'''
        item = ET.fromstring(xml)

        result = parse_player_counts(item)

        assert result['players_min'] == 1
        assert result['players_max'] == 1


class TestParsePlaytime:
    """Test playtime and age parsing"""

    def test_parse_complete_playtime(self):
        """Should parse min/max playtime and age"""
        xml = '''<item type="boardgame" id="1">
            <minplaytime value="60"/>
            <maxplaytime value="120"/>
            <minage value="14"/>
        </item>'''
        item = ET.fromstring(xml)

        result = parse_playtime(item)

        assert result['playtime_min'] == 60
        assert result['playtime_max'] == 120
        assert result['min_age'] == 14

    def test_parse_fallback_to_playingtime(self):
        """Should fallback to playingtime if min/max missing"""
        xml = '''<item type="boardgame" id="1">
            <playingtime value="90"/>
            <minage value="10"/>
        </item>'''
        item = ET.fromstring(xml)

        result = parse_playtime(item)

        assert result['playtime_min'] == 90
        assert result['playtime_max'] == 90

    def test_parse_missing_playtime(self):
        """Should handle missing playtime"""
        xml = '''<item type="boardgame" id="1"></item>'''
        item = ET.fromstring(xml)

        result = parse_playtime(item)

        assert result['playtime_min'] is None
        assert result['playtime_max'] is None
        assert result['min_age'] is None

    def test_parse_invalid_playtime(self):
        """Should handle invalid playtime values"""
        xml = '''<item type="boardgame" id="1">
            <minplaytime value="invalid"/>
            <maxplaytime value="also invalid"/>
            <minage value="not a number"/>
        </item>'''
        item = ET.fromstring(xml)

        result = parse_playtime(item)

        assert result['playtime_min'] is None
        assert result['playtime_max'] is None
        assert result['min_age'] is None

    def test_parse_zero_playtime_handled_as_none(self):
        """Should treat zero playtime as None"""
        xml = '''<item type="boardgame" id="1">
            <minplaytime value="0"/>
            <maxplaytime value="0"/>
        </item>'''
        item = ET.fromstring(xml)

        result = parse_playtime(item)

        assert result['playtime_min'] is None
        assert result['playtime_max'] is None


class TestParseLinks:
    """Test link parsing for categories, mechanics, designers, etc."""

    def test_parse_categories(self):
        """Should parse boardgamecategory links"""
        xml = '''<item type="boardgame" id="1">
            <link type="boardgamecategory" id="1" value="Adventure"/>
            <link type="boardgamecategory" id="2" value="Fantasy"/>
            <link type="boardgamemechanic" id="3" value="Deck Building"/>
        </item>'''
        item = ET.fromstring(xml)

        result = parse_links(item, 'boardgamecategory')

        assert 'Adventure' in result
        assert 'Fantasy' in result
        assert 'Deck Building' not in result  # Different type
        assert len(result) == 2

    def test_parse_mechanics(self):
        """Should parse boardgamemechanic links"""
        xml = '''<item type="boardgame" id="1">
            <link type="boardgamemechanic" id="1" value="Hand Management"/>
            <link type="boardgamemechanic" id="2" value="Worker Placement"/>
        </item>'''
        item = ET.fromstring(xml)

        result = parse_links(item, 'boardgamemechanic')

        assert 'Hand Management' in result
        assert 'Worker Placement' in result

    def test_parse_designers(self):
        """Should parse boardgamedesigner links"""
        xml = '''<item type="boardgame" id="1">
            <link type="boardgamedesigner" id="1" value="Jamey Stegmaier"/>
            <link type="boardgamedesigner" id="2" value="Uwe Rosenberg"/>
        </item>'''
        item = ET.fromstring(xml)

        result = parse_links(item, 'boardgamedesigner')

        assert 'Jamey Stegmaier' in result
        assert 'Uwe Rosenberg' in result

    def test_parse_publishers(self):
        """Should parse boardgamepublisher links"""
        xml = '''<item type="boardgame" id="1">
            <link type="boardgamepublisher" id="1" value="Stonemaier Games"/>
        </item>'''
        item = ET.fromstring(xml)

        result = parse_links(item, 'boardgamepublisher')

        assert 'Stonemaier Games' in result

    def test_parse_artists(self):
        """Should parse boardgameartist links"""
        xml = '''<item type="boardgame" id="1">
            <link type="boardgameartist" id="1" value="Beth Sobel"/>
        </item>'''
        item = ET.fromstring(xml)

        result = parse_links(item, 'boardgameartist')

        assert 'Beth Sobel' in result

    def test_parse_empty_links(self):
        """Should handle missing links"""
        xml = '''<item type="boardgame" id="1"></item>'''
        item = ET.fromstring(xml)

        result = parse_links(item, 'boardgamecategory')

        assert result == []

    def test_parse_ignores_empty_values(self):
        """Should ignore links with empty values"""
        xml = '''<item type="boardgame" id="1">
            <link type="boardgamecategory" id="1" value=""/>
            <link type="boardgamecategory" id="2" value="  "/>
            <link type="boardgamecategory" id="3" value="Valid"/>
        </item>'''
        item = ET.fromstring(xml)

        result = parse_links(item, 'boardgamecategory')

        assert len(result) == 1
        assert result[0] == 'Valid'


class TestParseExpansionRelationships:
    """Test expansion relationship parsing"""

    def test_parse_expansion_with_base_game(self):
        """Should parse base game link for expansions"""
        xml = '''<item type="boardgameexpansion" id="1">
            <name type="primary" value="Test Expansion"/>
            <link type="boardgameexpansion" id="100" value="Base Game" inbound="true"/>
        </item>'''
        item = ET.fromstring(xml)

        result = parse_expansion_relationships(item, "Test Expansion", True)

        assert result['base_game_bgg_id'] == 100
        assert result['base_game_name'] == 'Base Game'

    def test_parse_base_game_with_expansions(self):
        """Should parse expansion links for base games"""
        xml = '''<item type="boardgame" id="1">
            <name type="primary" value="Base Game"/>
            <link type="boardgameexpansion" id="101" value="Expansion 1"/>
            <link type="boardgameexpansion" id="102" value="Expansion 2"/>
        </item>'''
        item = ET.fromstring(xml)

        result = parse_expansion_relationships(item, "Base Game", False)

        assert len(result['expansion_bgg_ids']) == 2
        assert any(exp['bgg_id'] == 101 for exp in result['expansion_bgg_ids'])
        assert any(exp['bgg_id'] == 102 for exp in result['expansion_bgg_ids'])

    def test_parse_player_count_modification_pattern(self):
        """Should detect player count modifications from title"""
        xml = '''<item type="boardgameexpansion" id="1">
            <name type="primary" value="5-6 Player Extension"/>
        </item>'''
        item = ET.fromstring(xml)

        result = parse_expansion_relationships(item, "5-6 Player Extension", True)

        assert result['modifies_players_min'] == 5
        assert result['modifies_players_max'] == 6

    def test_parse_standalone_expansion_detection(self):
        """Should detect standalone expansions"""
        xml = '''<item type="boardgameexpansion" id="1">
            <name type="primary" value="Standalone Expansion"/>
        </item>'''
        item = ET.fromstring(xml)

        result = parse_expansion_relationships(item, "Standalone Expansion", True)

        assert result['expansion_type'] == 'both'

    def test_parse_requires_base_expansion(self):
        """Should default to requires_base for non-standalone expansions"""
        xml = '''<item type="boardgameexpansion" id="1">
            <name type="primary" value="Regular Expansion"/>
        </item>'''
        item = ET.fromstring(xml)

        result = parse_expansion_relationships(item, "Regular Expansion", True)

        assert result['expansion_type'] == 'requires_base'

    def test_parse_no_base_game_for_standalone(self):
        """Should handle expansions without base game link"""
        xml = '''<item type="boardgameexpansion" id="1">
            <name type="primary" value="Expansion"/>
        </item>'''
        item = ET.fromstring(xml)

        result = parse_expansion_relationships(item, "Expansion", True)

        assert result['base_game_bgg_id'] is None
        assert result['base_game_name'] is None


class TestParseStatistics:
    """Test statistics parsing (ratings, complexity, rank)"""

    def test_parse_complete_statistics(self):
        """Should parse all statistics fields"""
        xml = '''<item type="boardgame" id="1">
            <statistics>
                <ratings>
                    <usersrated value="10000"/>
                    <average value="7.5"/>
                    <averageweight value="2.8"/>
                    <ranks>
                        <rank type="subtype" id="1" name="boardgame" value="100"/>
                        <rank type="family" id="2" name="strategygames" value="50"/>
                    </ranks>
                </ratings>
            </statistics>
        </item>'''
        item = ET.fromstring(xml)

        result = parse_statistics(item)

        assert result['users_rated'] == 10000
        assert result['average_rating'] == 7.5
        assert result['complexity'] == 2.8
        assert result['bgg_rank'] == 100
        assert result['game_type'] == 'strategygames'

    def test_parse_not_ranked_game(self):
        """Should handle not ranked games"""
        xml = '''<item type="boardgame" id="1">
            <statistics>
                <ratings>
                    <average value="7.0"/>
                    <ranks>
                        <rank type="subtype" id="1" name="boardgame" value="Not Ranked"/>
                        <rank type="family" id="2" name="partygames" value="Not Ranked"/>
                    </ranks>
                </ratings>
            </statistics>
        </item>'''
        item = ET.fromstring(xml)

        result = parse_statistics(item)

        assert result['bgg_rank'] is None
        assert result['game_type'] == 'partygames'  # Uses not ranked category

    def test_parse_missing_statistics(self):
        """Should handle missing statistics section"""
        xml = '''<item type="boardgame" id="1"></item>'''
        item = ET.fromstring(xml)

        result = parse_statistics(item)

        assert result['average_rating'] is None
        assert result['complexity'] is None
        assert result['bgg_rank'] is None
        assert result['game_type'] is None

    def test_parse_multiple_ranked_categories(self):
        """Should choose best ranked category"""
        xml = '''<item type="boardgame" id="1">
            <statistics>
                <ratings>
                    <ranks>
                        <rank type="subtype" id="1" name="boardgame" value="100"/>
                        <rank type="family" id="2" name="strategygames" value="10"/>
                        <rank type="family" id="3" name="thematic" value="50"/>
                    </ranks>
                </ratings>
            </statistics>
        </item>'''
        item = ET.fromstring(xml)

        result = parse_statistics(item)

        assert result['game_type'] == 'strategygames'  # Best rank (10)

    def test_parse_invalid_rating_values(self):
        """Should handle invalid rating values"""
        xml = '''<item type="boardgame" id="1">
            <statistics>
                <ratings>
                    <average value="invalid"/>
                    <averageweight value="not a number"/>
                </ratings>
            </statistics>
        </item>'''
        item = ET.fromstring(xml)

        result = parse_statistics(item)

        assert result['average_rating'] is None
        assert result['complexity'] is None


class TestStripNamespace:
    """Test namespace stripping from XML elements"""

    def test_strip_namespace_from_elements(self):
        """Should remove namespace from element tags"""
        xml = '''<ns:item xmlns:ns="http://example.com">
            <ns:name ns:type="primary" value="Test"/>
        </ns:item>'''
        root = ET.fromstring(xml)

        strip_namespace(root)

        assert root.tag == 'item'
        assert root[0].tag == 'name'

    def test_strip_namespace_from_attributes(self):
        """Should remove namespace from attributes"""
        xml = '''<ns:item xmlns:ns="http://example.com">
            <ns:name ns:type="primary" value="Test"/>
        </ns:item>'''
        root = ET.fromstring(xml)

        strip_namespace(root)

        # Namespace should be removed from attributes
        assert 'type' in root[0].attrib

    def test_strip_namespace_preserves_values(self):
        """Should preserve attribute values when stripping namespace"""
        xml = '''<ns:item xmlns:ns="http://example.com">
            <ns:name ns:type="primary" value="Test Game"/>
        </ns:item>'''
        root = ET.fromstring(xml)

        strip_namespace(root)

        assert root[0].attrib['value'] == 'Test Game'

    def test_strip_namespace_handles_no_namespace(self):
        """Should handle XML without namespaces"""
        xml = '''<item><name type="primary" value="Test"/></item>'''
        root = ET.fromstring(xml)

        # Should not raise errors
        strip_namespace(root)

        assert root.tag == 'item'
        assert root[0].tag == 'name'
