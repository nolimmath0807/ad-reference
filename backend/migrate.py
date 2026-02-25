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

    # 6. monitored_domains table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS monitored_domains (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            domain VARCHAR(255) NOT NULL UNIQUE,
            platform VARCHAR(20) NOT NULL DEFAULT 'google',
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            notes TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    # 7. batch_runs table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS batch_runs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            finished_at TIMESTAMPTZ,
            status VARCHAR(20) NOT NULL DEFAULT 'running',
            total_domains INTEGER DEFAULT 0,
            total_ads_scraped INTEGER DEFAULT 0,
            total_ads_new INTEGER DEFAULT 0,
            total_ads_updated INTEGER DEFAULT 0,
            domain_results JSONB DEFAULT '{}',
            errors JSONB DEFAULT '[]',
            trigger_type VARCHAR(20) DEFAULT 'manual'
        )
    """)

    # 8. ads table - add columns
    cur.execute("ALTER TABLE ads ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW()")
    cur.execute("ALTER TABLE ads ADD COLUMN IF NOT EXISTS raw_data JSONB")
    cur.execute("ALTER TABLE ads ADD COLUMN IF NOT EXISTS domain VARCHAR(255)")
    cur.execute("ALTER TABLE ads ADD COLUMN IF NOT EXISTS creative_id VARCHAR(255)")

    # Backfill domain from landing_page_url (www. 제거하여 정규화)
    cur.execute("""
        UPDATE ads
        SET domain = REPLACE(substring(landing_page_url from 'https?://([^/]+)'), 'www.', '')
        WHERE domain IS NULL AND landing_page_url IS NOT NULL
    """)

    # Normalize existing domain values: strip www. prefix
    cur.execute("""
        UPDATE ads SET domain = REPLACE(domain, 'www.', '')
        WHERE domain LIKE 'www.%'
    """)

    # Create indexes
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ads_platform ON ads(platform)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ads_format ON ads(format)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ads_advertiser ON ads(advertiser_name)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ads_created ON ads(created_at DESC)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ads_source ON ads(source_id, platform)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ads_domain ON ads(domain)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ads_creative_id ON ads(creative_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_boards_user ON boards(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_board_items_board ON board_items(board_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_board_items_ad ON board_items(ad_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_monitored_domains_active ON monitored_domains(is_active, platform)")

    # 9. brands table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS brands (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            brand_name VARCHAR(255) NOT NULL UNIQUE,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            notes TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    # 10. brand_sources table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS brand_sources (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            brand_id UUID NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
            platform VARCHAR(20) NOT NULL,
            source_type VARCHAR(20) NOT NULL,
            source_value VARCHAR(255) NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE(brand_id, platform, source_value)
        )
    """)

    # 11. ads table - add brand_id column
    cur.execute("ALTER TABLE ads ADD COLUMN IF NOT EXISTS brand_id UUID REFERENCES brands(id) ON DELETE SET NULL")

    # Brand-related indexes
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ads_brand_id ON ads(brand_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_brand_sources_brand ON brand_sources(brand_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_brand_sources_platform ON brand_sources(platform, is_active)")

    # 12. Data migration: monitored_domains -> brands + brand_sources
    # Step 1: Create brands from monitored_domains
    cur.execute("""
        INSERT INTO brands (id, brand_name, is_active, notes, created_at, updated_at)
        SELECT id, domain, is_active, notes, created_at, updated_at
        FROM monitored_domains
        ON CONFLICT (brand_name) DO NOTHING
    """)

    # Step 2: Create brand_sources from monitored_domains
    cur.execute("""
        INSERT INTO brand_sources (brand_id, platform, source_type, source_value)
        SELECT id, platform, 'domain', domain
        FROM monitored_domains
        ON CONFLICT (brand_id, platform, source_value) DO NOTHING
    """)

    # Step 3: Backfill ads.brand_id from brand_sources
    cur.execute("""
        UPDATE ads SET brand_id = bs.brand_id
        FROM brand_sources bs
        WHERE ads.brand_id IS NULL
          AND ads.domain IS NOT NULL
          AND bs.source_type = 'domain'
          AND REPLACE(LOWER(ads.domain), 'www.', '') = REPLACE(LOWER(bs.source_value), 'www.', '')
    """)

    # 13. activity_logs table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS activity_logs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            event_type VARCHAR(50) NOT NULL,
            event_subtype VARCHAR(50),
            title VARCHAR(255) NOT NULL,
            message TEXT,
            metadata JSONB DEFAULT '{}',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_activity_logs_type ON activity_logs(event_type)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_activity_logs_created ON activity_logs(created_at DESC)")

    # 14. daily_brand_stats table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS daily_brand_stats (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            brand_id UUID NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
            stat_date DATE NOT NULL DEFAULT CURRENT_DATE,
            platform VARCHAR(20) NOT NULL,
            new_count INTEGER NOT NULL DEFAULT 0,
            updated_count INTEGER NOT NULL DEFAULT 0,
            total_scraped INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE(brand_id, stat_date, platform)
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_daily_brand_stats_date ON daily_brand_stats(stat_date DESC)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_daily_brand_stats_brand ON daily_brand_stats(brand_id, stat_date DESC)")

    conn.commit()
    cur.close()
    conn.close()
    print("Migration complete! Schema and tables created.")

if __name__ == "__main__":
    migrate()
