import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

SCHEMA = "ad_reference_dash"

def migrate():
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()

    # Create schema
    cur.execute(f'CREATE SCHEMA IF NOT EXISTS "{SCHEMA}"')
    cur.execute(f'SET search_path TO "{SCHEMA}"')

    # 1. users table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            email VARCHAR(255) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            name VARCHAR(100) NOT NULL,
            company VARCHAR(100),
            job_title VARCHAR(100),
            avatar_url TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    # 2. ads table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ads (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            platform VARCHAR(20) NOT NULL,
            format VARCHAR(20) NOT NULL,
            advertiser_name VARCHAR(255) NOT NULL,
            advertiser_handle VARCHAR(255),
            advertiser_avatar_url TEXT,
            thumbnail_url TEXT NOT NULL,
            preview_url TEXT,
            media_type VARCHAR(20) NOT NULL,
            ad_copy TEXT,
            cta_text VARCHAR(255),
            likes INTEGER,
            comments INTEGER,
            shares INTEGER,
            start_date DATE,
            end_date DATE,
            tags TEXT[] DEFAULT '{}',
            landing_page_url TEXT,
            source_id VARCHAR(255),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            saved_at TIMESTAMPTZ,
            UNIQUE(source_id, platform)
        )
    """)

    # 3. boards table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS boards (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            name VARCHAR(255) NOT NULL,
            description TEXT DEFAULT '',
            cover_image_url TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    # 4. board_items table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS board_items (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            board_id UUID NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
            ad_id UUID NOT NULL REFERENCES ads(id) ON DELETE CASCADE,
            added_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE(board_id, ad_id)
        )
    """)

    # 5. token_blacklist table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS token_blacklist (
            token TEXT PRIMARY KEY,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    # Create indexes
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ads_platform ON ads(platform)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ads_format ON ads(format)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ads_advertiser ON ads(advertiser_name)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ads_created ON ads(created_at DESC)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ads_source ON ads(source_id, platform)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_boards_user ON boards(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_board_items_board ON board_items(board_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_board_items_ad ON board_items(ad_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")

    conn.commit()
    cur.close()
    conn.close()
    print("Migration complete! Schema and tables created.")

if __name__ == "__main__":
    migrate()
