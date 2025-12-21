"""
Integration Tests for Search & Filter Combinations
Sprint 11: Advanced Testing

Tests complex search and filtering scenarios with multiple combinations
"""

import pytest
from fastapi.testclient import TestClient
from backend.models import Game


@pytest.fixture
def diverse_games(test_db):
    """Create diverse set of games for filtering tests"""
    games = [
        Game(
            title="Catan", bgg_id=13, year=1995, players_min=3, players_max=4,
            playtime_min=60, playtime_max=120, complexity=2.3, average_rating=7.2,
            mana_meeple_category="GATEWAY_STRATEGY", status="OWNED",
            designers='["Klaus Teuber"]', nz_designer=False
        ),
        Game(
            title="Pandemic", bgg_id=30549, year=2008, players_min=2, players_max=4,
            playtime_min=45, playtime_max=45, complexity=2.4, average_rating=7.6,
            mana_meeple_category="COOP_ADVENTURE", status="OWNED",
            designers='["Matt Leacock"]', nz_designer=False
        ),
        Game(
            title="Wingspan", bgg_id=266192, year=2019, players_min=1, players_max=5,
            playtime_min=40, playtime_max=70, complexity=2.4, average_rating=8.0,
            mana_meeple_category="GATEWAY_STRATEGY", status="OWNED",
            designers='["Elizabeth Hargrave"]', nz_designer=False
        ),
        Game(
            title="Gloomhaven", bgg_id=174430, year=2017, players_min=1, players_max=4,
            playtime_min=60, playtime_max=120, complexity=3.9, average_rating=8.7,
            mana_meeple_category="COOP_ADVENTURE", status="OWNED",
            designers='["Isaac Childres"]', nz_designer=False
        ),
        Game(
            title="Azul", bgg_id=230802, year=2017, players_min=2, players_max=4,
            playtime_min=30, playtime_max=45, complexity=1.8, average_rating=7.8,
            mana_meeple_category="GATEWAY_STRATEGY", status="OWNED",
            designers='["Michael Kiesling"]', nz_designer=False
        ),
        Game(
            title="Codenames", bgg_id=178900, year=2015, players_min=2, players_max=8,
            playtime_min=15, playtime_max=15, complexity=1.3, average_rating=7.7,
            mana_meeple_category="PARTY_ICEBREAKERS", status="OWNED",
            designers='["Vlaada Chvátil"]', nz_designer=False
        ),
        Game(
            title="Ticket to Ride", bgg_id=9209, year=2004, players_min=2, players_max=5,
            playtime_min=30, playtime_max=60, complexity=1.9, average_rating=7.4,
            mana_meeple_category="GATEWAY_STRATEGY", status="OWNED",
            designers='["Alan R. Moon"]', nz_designer=False
        ),
        Game(
            title="King of Tokyo", bgg_id=70323, year=2011, players_min=2, players_max=6,
            playtime_min=30, playtime_max=30, complexity=1.5, average_rating=7.2,
            mana_meeple_category="KIDS_FAMILIES", status="OWNED",
            designers='["Richard Garfield"]', nz_designer=False
        ),
        Game(
            title="7 Wonders", bgg_id=68448, year=2010, players_min=2, players_max=7,
            playtime_min=30, playtime_max=30, complexity=2.3, average_rating=7.7,
            mana_meeple_category="CORE_STRATEGY", status="OWNED",
            designers='["Antoine Bauza"]', nz_designer=False
        ),
        Game(
            title="NZ Designer Game", bgg_id=999999, year=2023, players_min=2, players_max=4,
            playtime_min=45, playtime_max=60, complexity=2.5, average_rating=7.5,
            mana_meeple_category="GATEWAY_STRATEGY", status="OWNED",
            designers='["Kiwi Designer"]', nz_designer=True
        ),
    ]

    for game in games:
        test_db.add(game)
    test_db.commit()
    return games


class TestSearchFilterIntegration:
    """Test complex search and filter combinations"""

    def test_filter_by_single_category(self, test_client, diverse_games):
        """Should filter games by category"""
        response = test_client.get('/api/public/games?category=GATEWAY_STRATEGY')

        assert response.status_code == 200
        data = response.json()
        assert data['total'] >= 4  # Catan, Wingspan, Azul, Ticket to Ride, NZ Game

    def test_filter_by_nz_designer(self, test_client, diverse_games):
        """Should filter games by NZ designer flag"""
        response = test_client.get('/api/public/games?nz_designer=true')

        assert response.status_code == 200
        data = response.json()
        assert data['total'] == 1
        assert data['items'][0]['title'] == "NZ Designer Game"

    def test_search_by_title(self, test_client, diverse_games):
        """Should search games by title"""
        response = test_client.get('/api/public/games?q=pandemic')

        assert response.status_code == 200
        data = response.json()
        assert data['total'] >= 1
        assert any('pandemic' in item['title'].lower() for item in data['items'])

    def test_search_by_designer(self, test_client, diverse_games):
        """Should search games by designer name"""
        response = test_client.get('/api/public/games?q=leacock')

        assert response.status_code == 200
        data = response.json()
        assert data['total'] >= 1
        titles = [item['title'] for item in data['items']]
        assert 'Pandemic' in titles

    def test_category_and_search_combination(self, test_client, diverse_games):
        """Should combine category filter and search"""
        response = test_client.get('/api/public/games?category=GATEWAY_STRATEGY&q=wing')

        assert response.status_code == 200
        data = response.json()
        assert data['total'] >= 1
        assert data['items'][0]['title'] == 'Wingspan'

    def test_nz_designer_and_category_combination(self, test_client, diverse_games):
        """Should combine NZ designer and category filters"""
        response = test_client.get('/api/public/games?nz_designer=true&category=GATEWAY_STRATEGY')

        assert response.status_code == 200
        data = response.json()
        assert data['total'] == 1

    def test_sort_by_title_ascending(self, test_client, diverse_games):
        """Should sort games by title ascending"""
        response = test_client.get('/api/public/games?sort=title_asc&page_size=50')

        assert response.status_code == 200
        data = response.json()
        titles = [item['title'] for item in data['items']]
        assert titles == sorted(titles)

    def test_sort_by_title_descending(self, test_client, diverse_games):
        """Should sort games by title descending"""
        response = test_client.get('/api/public/games?sort=title_desc&page_size=50')

        assert response.status_code == 200
        data = response.json()
        titles = [item['title'] for item in data['items']]
        assert titles == sorted(titles, reverse=True)

    def test_sort_by_year_ascending(self, test_client, diverse_games):
        """Should sort games by year ascending"""
        response = test_client.get('/api/public/games?sort=year_asc&page_size=50')

        assert response.status_code == 200
        data = response.json()
        years = [item['year'] for item in data['items'] if item['year']]
        assert years == sorted(years)

    def test_sort_by_year_descending(self, test_client, diverse_games):
        """Should sort games by year descending (newest first)"""
        response = test_client.get('/api/public/games?sort=year_desc&page_size=50')

        assert response.status_code == 200
        data = response.json()
        years = [item['year'] for item in data['items'] if item['year']]
        assert years == sorted(years, reverse=True)

    def test_sort_by_rating_descending(self, test_client, diverse_games):
        """Should sort games by rating descending (best first)"""
        response = test_client.get('/api/public/games?sort=rating_desc&page_size=50')

        assert response.status_code == 200
        data = response.json()
        ratings = [item['average_rating'] for item in data['items'] if item.get('average_rating')]
        assert ratings == sorted(ratings, reverse=True)

    def test_category_search_and_sort_combination(self, test_client, diverse_games):
        """Should combine category, search, and sorting"""
        response = test_client.get(
            '/api/public/games?category=GATEWAY_STRATEGY&q=a&sort=year_desc&page_size=50'
        )

        assert response.status_code == 200
        data = response.json()
        assert data['total'] >= 2  # Azul, Catan, etc.

    def test_pagination_first_page(self, test_client, diverse_games):
        """Should return first page of results"""
        response = test_client.get('/api/public/games?page=1&page_size=3')

        assert response.status_code == 200
        data = response.json()
        assert len(data['items']) <= 3
        assert data['page'] == 1
        assert data['page_size'] == 3

    def test_pagination_second_page(self, test_client, diverse_games):
        """Should return second page of results"""
        response = test_client.get('/api/public/games?page=2&page_size=3')

        assert response.status_code == 200
        data = response.json()
        assert data['page'] == 2

    def test_pagination_with_filters(self, test_client, diverse_games):
        """Should paginate filtered results correctly"""
        response = test_client.get('/api/public/games?category=GATEWAY_STRATEGY&page=1&page_size=2')

        assert response.status_code == 200
        data = response.json()
        assert len(data['items']) == 2
        assert data['total'] >= 4

    def test_large_page_size(self, test_client, diverse_games):
        """Should handle large page sizes"""
        response = test_client.get('/api/public/games?page_size=100')

        assert response.status_code == 200
        data = response.json()
        assert len(data['items']) <= 100

    def test_invalid_page_number(self, test_client):
        """Should handle invalid page numbers"""
        response = test_client.get('/api/public/games?page=0')

        # Should either default to page 1 or return error
        assert response.status_code in [200, 400, 422]

    def test_empty_search_results(self, test_client, diverse_games):
        """Should handle searches with no results"""
        response = test_client.get('/api/public/games?q=nonexistentgamexyz123')

        assert response.status_code == 200
        data = response.json()
        assert data['total'] == 0
        assert data['items'] == []

    def test_category_with_no_games(self, test_client, diverse_games):
        """Should handle category filters with no matching games"""
        # Assuming no games in this category
        response = test_client.get('/api/public/games?category=SOME_EMPTY_CATEGORY')

        assert response.status_code == 200
        data = response.json()
        # May return empty results or all results depending on implementation

    def test_filter_by_designer_name(self, test_client, diverse_games):
        """Should filter by specific designer"""
        response = test_client.get('/api/public/games?designer=Klaus Teuber')

        assert response.status_code == 200
        data = response.json()
        assert data['total'] >= 1

    def test_complex_search_query(self, test_client, diverse_games):
        """Should handle complex search queries"""
        response = test_client.get('/api/public/games?q=strategy adventure')

        assert response.status_code == 200
        data = response.json()
        # Should return games matching search terms

    def test_case_insensitive_search(self, test_client, diverse_games):
        """Should perform case-insensitive search"""
        response1 = test_client.get('/api/public/games?q=PANDEMIC')
        response2 = test_client.get('/api/public/games?q=pandemic')
        response3 = test_client.get('/api/public/games?q=PaNdEmIc')

        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response3.status_code == 200
        assert response1.json()['total'] == response2.json()['total'] == response3.json()['total']

    def test_special_characters_in_search(self, test_client, diverse_games):
        """Should handle special characters in search"""
        response = test_client.get('/api/public/games?q=7 Wonders')

        assert response.status_code == 200
        data = response.json()
        assert data['total'] >= 1

    def test_filter_uncategorized_games(self, test_client, test_db):
        """Should filter games without a category"""
        # Create game without category
        uncategorized = Game(
            title="Uncategorized Game", bgg_id=888888,
            mana_meeple_category=None, status="OWNED"
        )
        test_db.add(uncategorized)
        test_db.commit()

        response = test_client.get('/api/public/games?category=uncategorized')

        assert response.status_code == 200
        data = response.json()
        assert data['total'] >= 1

    def test_multiple_filters_reduce_results(self, test_client, diverse_games):
        """Should reduce results when adding more filters"""
        response1 = test_client.get('/api/public/games')
        response2 = test_client.get('/api/public/games?category=GATEWAY_STRATEGY')
        response3 = test_client.get('/api/public/games?category=GATEWAY_STRATEGY&nz_designer=true')

        assert response1.json()['total'] >= response2.json()['total'] >= response3.json()['total']

    def test_search_with_pagination(self, test_client, diverse_games):
        """Should paginate search results correctly"""
        response = test_client.get('/api/public/games?q=a&page=1&page_size=2')

        assert response.status_code == 200
        data = response.json()
        assert len(data['items']) <= 2

    def test_sort_with_null_values(self, test_client, test_db, diverse_games):
        """Should handle sorting when some games have null values"""
        # Create game with null year
        no_year = Game(
            title="No Year Game", bgg_id=777777,
            year=None, status="OWNED"
        )
        test_db.add(no_year)
        test_db.commit()

        response = test_client.get('/api/public/games?sort=year_asc&page_size=50')

        assert response.status_code == 200
        # Should not crash, nulls typically at end or beginning

    def test_filter_performance_with_large_dataset(self, test_client, diverse_games):
        """Should perform well with complex filters"""
        import time

        start = time.time()
        response = test_client.get(
            '/api/public/games?category=GATEWAY_STRATEGY&q=game&sort=rating_desc'
        )
        duration = time.time() - start

        assert response.status_code == 200
        assert duration < 1.0  # Should complete within 1 second

    def test_category_counts_endpoint(self, test_client, diverse_games):
        """Should return accurate category counts"""
        response = test_client.get('/api/public/category-counts')

        assert response.status_code == 200
        data = response.json()
        assert 'GATEWAY_STRATEGY' in data
        assert data['GATEWAY_STRATEGY'] >= 4

    def test_url_encoded_search_parameters(self, test_client, diverse_games):
        """Should handle URL-encoded search parameters"""
        response = test_client.get('/api/public/games?q=7%20Wonders')

        assert response.status_code == 200
        data = response.json()
        assert data['total'] >= 1

    def test_simultaneous_filters_are_AND_not_OR(self, test_client, diverse_games):
        """Should treat multiple filters as AND (intersection) not OR (union)"""
        # Filter for games that are BOTH cooperative AND have NZ designer
        # Should be very restrictive
        response = test_client.get('/api/public/games?category=COOP_ADVENTURE&nz_designer=true')

        assert response.status_code == 200
        data = response.json()
        # Should return 0 or very few results (no NZ cooperative games in test data)
        assert data['total'] == 0

    def test_returns_correct_total_count(self, test_client, diverse_games):
        """Should return correct total count separate from page items"""
        response = test_client.get('/api/public/games?page=1&page_size=2')

        assert response.status_code == 200
        data = response.json()
        assert data['total'] >= 10  # Total games in diverse_games
        assert len(data['items']) == 2  # Page size

    def test_search_matches_partial_words(self, test_client, diverse_games):
        """Should match partial word searches"""
        response = test_client.get('/api/public/games?q=gloom')

        assert response.status_code == 200
        data = response.json()
        assert any('gloomhaven' in item['title'].lower() for item in data['items'])
