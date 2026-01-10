"""
Seed script for E2E tests
Creates test game data in the database for E2E testing
"""
import os
import sys

# Add backend directory to path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Game
from database import Base


def seed_test_data():
    """Create test games for E2E tests"""
    # Get database URL from environment
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL environment variable not set")
        sys.exit(1)

    print(f"Connecting to database: {database_url}")

    # Create engine and session
    engine = create_engine(database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Ensure tables exist
    Base.metadata.create_all(engine)

    session = SessionLocal()

    try:
        # Check if we already have games
        existing_count = session.query(Game).count()
        if existing_count > 0:
            print(f"Database already has {existing_count} games. Skipping seed.")
            return

        # Create a diverse set of test games
        test_games = [
            {
                "title": "Pandemic",
                "bgg_id": 30549,
                "year": 2008,
                "players_min": 2,
                "players_max": 4,
                "playtime_min": 45,
                "playtime_max": 45,
                "mana_meeple_category": "COOP_ADVENTURE",
                "complexity": 2.43,
                "average_rating": 7.6,
                "designers": '["Matt Leacock"]',
                "mechanics": '["Action Points", "Cooperative Game", "Point to Point Movement"]',
                "description": "In Pandemic, several virulent diseases have broken out simultaneously all over the world! The players are disease-fighting specialists whose mission is to treat disease hotspots while researching cures for each of four plagues before they get out of hand.",
                "min_age": 8,
                "is_cooperative": True,
                "nz_designer": False,
                "status": "OWNED",
                "image": "https://cf.geekdo-images.com/S3ybV1LAp-8SnHIXLLjVqA__imagepage/img/kIBu-2Ljb_ml5n-S8uIbE6ehGFc=/fit-in/900x600/filters:no_upscale():strip_icc()/pic1534148.jpg"
            },
            {
                "title": "Catan",
                "bgg_id": 13,
                "year": 1995,
                "players_min": 3,
                "players_max": 4,
                "playtime_min": 60,
                "playtime_max": 120,
                "mana_meeple_category": "GATEWAY_STRATEGY",
                "complexity": 2.32,
                "average_rating": 7.1,
                "designers": '["Klaus Teuber"]',
                "mechanics": '["Dice Rolling", "Trading", "Network and Route Building"]',
                "description": "In CATAN, players try to be the dominant force on the island of Catan by building settlements, cities, and roads. On each turn dice are rolled to determine what resources the island produces.",
                "min_age": 10,
                "is_cooperative": False,
                "nz_designer": False,
                "status": "OWNED",
                "image": "https://cf.geekdo-images.com/W3Bsga_uLP9kO91gZ7H8yw__imagepage/img/M_3Vg1j2HlNgkv7PL2xl2BJE2sE=/fit-in/900x600/filters:no_upscale():strip_icc()/pic2419375.jpg"
            },
            {
                "title": "7 Wonders",
                "bgg_id": 68448,
                "year": 2010,
                "players_min": 2,
                "players_max": 7,
                "playtime_min": 30,
                "playtime_max": 30,
                "mana_meeple_category": "CORE_STRATEGY",
                "complexity": 2.33,
                "average_rating": 7.7,
                "designers": '["Antoine Bauza"]',
                "mechanics": '["Card Drafting", "Set Collection", "Simultaneous Action Selection"]',
                "description": "You are the leader of one of the 7 great cities of the Ancient World. Gather resources, develop commercial routes, and affirm your military supremacy. Build your city and erect an architectural wonder which will transcend future times.",
                "min_age": 10,
                "is_cooperative": False,
                "nz_designer": False,
                "status": "OWNED",
                "image": "https://cf.geekdo-images.com/35h9Za_JvMMMtx_92kT0Jg__imagepage/img/i_8sN91g7S3t1l-0j8BaIdiOAoY=/fit-in/900x600/filters:no_upscale():strip_icc()/pic7149798.jpg"
            },
            {
                "title": "Codenames",
                "bgg_id": 178900,
                "year": 2015,
                "players_min": 2,
                "players_max": 8,
                "playtime_min": 15,
                "playtime_max": 15,
                "mana_meeple_category": "PARTY_ICEBREAKERS",
                "complexity": 1.31,
                "average_rating": 7.6,
                "designers": '["Vlaada Chvátil"]',
                "mechanics": '["Memory", "Team-Based Game", "Communication Limits"]',
                "description": "Codenames is a social word game with a simple premise and challenging game play. Two teams compete to see who can make contact with all of their agents first.",
                "min_age": 14,
                "is_cooperative": False,
                "nz_designer": False,
                "status": "OWNED",
                "image": "https://cf.geekdo-images.com/F_KDEu0GjdClml8N7c8Imw__imagepage/img/rc_Do8f0IeaIZKTa5lH4EDEJ5EI=/fit-in/900x600/filters:no_upscale():strip_icc()/pic2582929.jpg"
            },
            {
                "title": "Ticket to Ride",
                "bgg_id": 9209,
                "year": 2004,
                "players_min": 2,
                "players_max": 5,
                "playtime_min": 30,
                "playtime_max": 60,
                "mana_meeple_category": "KIDS_FAMILIES",
                "complexity": 1.89,
                "average_rating": 7.4,
                "designers": '["Alan R. Moon"]',
                "mechanics": '["Card Drafting", "Hand Management", "Network and Route Building", "Set Collection"]',
                "description": "Ticket to Ride is a cross-country train adventure game. Players collect cards of various types of train cars that enable them to claim railway routes connecting cities in various countries around the world.",
                "min_age": 8,
                "is_cooperative": False,
                "nz_designer": False,
                "status": "OWNED",
                "image": "https://cf.geekdo-images.com/ZWJg0dCdrWHxbl4T7yOXVw__imagepage/img/bg5uLS74b6VVQ_2pCvhH5Q4hD6Y=/fit-in/900x600/filters:no_upscale():strip_icc()/pic2108725.jpg"
            },
            {
                "title": "Azul",
                "bgg_id": 230802,
                "year": 2017,
                "players_min": 2,
                "players_max": 4,
                "playtime_min": 30,
                "playtime_max": 45,
                "mana_meeple_category": "GATEWAY_STRATEGY",
                "complexity": 1.79,
                "average_rating": 7.8,
                "designers": '["Michael Kiesling"]',
                "mechanics": '["Drafting", "Pattern Building", "Set Collection", "Tile Placement"]',
                "description": "Introduced by the Moors, azulejos (originally white and blue ceramic tiles) were fully embraced by the Portuguese when their king Manuel I, on a visit to the Alhambra palace in Southern Spain, was mesmerized by the stunning beauty of the Moorish decorative tiles.",
                "min_age": 8,
                "is_cooperative": False,
                "nz_designer": False,
                "status": "OWNED",
                "image": "https://cf.geekdo-images.com/aPSHJO0d0XOpQR5X-wJonw__imagepage/img/q4uWd2nLPOyVlHCyXYi_VHi0gPE=/fit-in/900x600/filters:no_upscale():strip_icc()/pic6973671.png"
            },
            {
                "title": "Wingspan",
                "bgg_id": 266192,
                "year": 2019,
                "players_min": 1,
                "players_max": 5,
                "playtime_min": 40,
                "playtime_max": 70,
                "mana_meeple_category": "GATEWAY_STRATEGY",
                "complexity": 2.44,
                "average_rating": 8.0,
                "designers": '["Elizabeth Hargrave"]',
                "mechanics": '["Card Drafting", "Dice Rolling", "Hand Management", "Set Collection"]',
                "description": "Wingspan is a competitive, medium-weight, card-driven, engine-building board game from Stonemaier Games. You are bird enthusiasts—researchers, bird watchers, ornithologists, and collectors—seeking to discover and attract the best birds to your network of wildlife preserves.",
                "min_age": 10,
                "is_cooperative": False,
                "nz_designer": False,
                "status": "OWNED",
                "image": "https://cf.geekdo-images.com/yLZJCVLlIx4c7eJEWUNJ7w__imagepage/img/VNToqgS2wtBBhqsMqIyNKXEggHk=/fit-in/900x600/filters:no_upscale():strip_icc()/pic4458123.jpg"
            },
            {
                "title": "Splendor",
                "bgg_id": 148228,
                "year": 2014,
                "players_min": 2,
                "players_max": 4,
                "playtime_min": 30,
                "playtime_max": 30,
                "mana_meeple_category": "GATEWAY_STRATEGY",
                "complexity": 1.79,
                "average_rating": 7.4,
                "designers": '["Marc André"]',
                "mechanics": '["Card Drafting", "Engine Building", "Open Drafting", "Set Collection"]',
                "description": "Splendor is a game of chip-collecting and card development. Players are merchants of the Renaissance trying to buy gem mines, means of transportation, shops—all in order to acquire the most prestige points.",
                "min_age": 10,
                "is_cooperative": False,
                "nz_designer": False,
                "status": "OWNED",
                "image": "https://cf.geekdo-images.com/rwOMxx4q5yuElIvo-1-OFw__imagepage/img/OQHA7dEW1Y0z6qV-V0lqMb6Hpgg=/fit-in/900x600/filters:no_upscale():strip_icc()/pic1904079.jpg"
            }
        ]

        # Create game objects and add to database
        created_games = []
        for game_data in test_games:
            game = Game(**game_data)
            session.add(game)
            created_games.append(game.title)

        # Commit all games
        session.commit()

        print(f"✓ Successfully seeded {len(created_games)} games:")
        for title in created_games:
            print(f"  - {title}")

        # Verify the games were created
        total_count = session.query(Game).count()
        print(f"\nTotal games in database: {total_count}")

    except Exception as e:
        print(f"ERROR seeding data: {e}")
        session.rollback()
        sys.exit(1)
    finally:
        session.close()


if __name__ == "__main__":
    seed_test_data()
