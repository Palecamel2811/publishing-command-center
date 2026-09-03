"""
Deterministic database seeder for Publishing Command Center.
Seeds sample works, splits, royalties, sync licenses, and document chunks.
Executes in ~100ms without remote network dependencies.
"""

import uuid
import logging
from datetime import datetime
from sqlmodel import Session, select
from app.db.models import Work, Split, RoyaltyEntry, SyncLicense, DocumentChunk

logger = logging.getLogger("seed")

def seed_sample_catalog(session: Session) -> dict:
    """Populate full sample catalog dataset if database is empty."""
    existing_work = session.exec(select(Work)).first()
    if existing_work:
        logger.info("Catalog already has data. Skipping seed.")
        return {"status": "skipped", "message": "Catalog already seeded"}

    logger.info("Seeding complete sample catalog...")

    # ── 1. Works ─────────────────────────────────────────────────────────────
    works_data = [
        {
            "title": "Golden Hour",
            "isrc": "US-AT2-24-00101",
            "iswc": "T-070.234.567-1",
            "label": "Neon Horizon Records",
            "status": "active",
            "total_earnings": 38450.20,
            "splits": [
                {"party_name": "Brian Johnson", "share_percentage": 50.0, "share_type": "songwriter_share", "pro": "ASCAP", "source": "golden_hour_split.pdf.txt"},
                {"party_name": "Sarah Chen", "share_percentage": 30.0, "share_type": "producer_share", "pro": "BMI", "source": "golden_hour_split.pdf.txt"},
                {"party_name": "Neon Horizon Publishing", "share_percentage": 20.0, "share_type": "publisher_share", "pro": "ASCAP", "source": "golden_hour_split.pdf.txt"},
            ],
            "syncs": [
                {"title": "Golden Hour - HBO Trailer", "licensee": "HBO Max", "media_type": "TV / Streaming", "territory": "Worldwide", "fee": 15000.0, "status": "active"},
            ],
            "royalties": [
                {"platform": "Spotify", "type": "streaming", "start": "2024-01-01", "end": "2024-03-31", "gross": 5200.00, "fees": 780.00, "net": 4420.00, "source": "golden_hour_spotify_q1_2024.pdf.txt"},
                {"platform": "Apple Music", "type": "streaming", "start": "2024-01-01", "end": "2024-03-31", "gross": 3800.00, "fees": 570.00, "net": 3230.00, "source": "golden_hour_apple_music_q1_2024.pdf.txt"},
                {"platform": "YouTube", "type": "ad_supported", "start": "2024-01-01", "end": "2024-03-31", "gross": 1950.00, "fees": 292.50, "net": 1657.50, "source": "golden_hour_youtube_q1_2024.pdf.txt"},
                {"platform": "Spotify", "type": "streaming", "start": "2024-04-01", "end": "2024-06-30", "gross": 6400.00, "fees": 960.00, "net": 5440.00, "source": "golden_hour_spotify_q2_2024.pdf.txt"},
                {"platform": "Apple Music", "type": "streaming", "start": "2024-04-01", "end": "2024-06-30", "gross": 4100.00, "fees": 615.00, "net": 3485.00, "source": "golden_hour_apple_music_q2_2024.pdf.txt"},
            ]
        },
        {
            "title": "Midnight Echoes",
            "isrc": "US-AT2-24-00102",
            "iswc": "T-070.234.567-2",
            "label": "Neon Horizon Records",
            "status": "active",
            "total_earnings": 42180.50,
            "splits": [
                {"party_name": "Brian Johnson", "share_percentage": 60.0, "share_type": "songwriter_share", "pro": "ASCAP", "source": "midnight_echoes_split.pdf.txt"},
                {"party_name": "Marcus Miller", "share_percentage": 25.0, "share_type": "songwriter_share", "pro": "BMI", "source": "midnight_echoes_split.pdf.txt"},
                {"party_name": "Neon Horizon Publishing", "share_percentage": 15.0, "share_type": "publisher_share", "pro": "ASCAP", "source": "midnight_echoes_split.pdf.txt"},
            ],
            "syncs": [
                {"title": "Midnight Echoes - Nike Commercial", "licensee": "Nike Inc.", "media_type": "Commercial / Web", "territory": "North America", "fee": 22000.0, "status": "active"},
            ],
            "royalties": [
                {"platform": "Spotify", "type": "streaming", "start": "2024-01-01", "end": "2024-03-31", "gross": 7100.00, "fees": 1065.00, "net": 6035.00, "source": "midnight_echoes_spotify_q1_2024.pdf.txt"},
                {"platform": "Apple Music", "type": "streaming", "start": "2024-01-01", "end": "2024-03-31", "gross": 4900.00, "fees": 735.00, "net": 4165.00, "source": "midnight_echoes_apple_music_q1_2024.pdf.txt"},
                {"platform": "YouTube", "type": "ad_supported", "start": "2024-01-01", "end": "2024-03-31", "gross": 2800.00, "fees": 420.00, "net": 2380.00, "source": "midnight_echoes_youtube_q1_2024.pdf.txt"},
            ]
        },
        {
            "title": "Neon Dreams",
            "isrc": "US-AT2-24-00103",
            "iswc": "T-070.234.567-3",
            "label": "Horizon Soundworks",
            "status": "active",
            "total_earnings": 29640.00,
            "splits": [
                {"party_name": "Brian Johnson", "share_percentage": 45.0, "share_type": "songwriter_share", "pro": "ASCAP", "source": "neon_dreams_split.pdf.txt"},
                {"party_name": "Elena Rostova", "share_percentage": 35.0, "share_type": "producer_share", "pro": "PRS", "source": "neon_dreams_split.pdf.txt"},
                {"party_name": "Horizon Soundworks Pub", "share_percentage": 20.0, "share_type": "publisher_share", "pro": "ASCAP", "source": "neon_dreams_split.pdf.txt"},
            ],
            "syncs": [
                {"title": "Neon Dreams - Netflix Series", "licensee": "Netflix", "media_type": "TV Series", "territory": "Worldwide", "fee": 18000.0, "status": "active"},
            ],
            "royalties": [
                {"platform": "Spotify", "type": "streaming", "start": "2024-01-01", "end": "2024-03-31", "gross": 4800.00, "fees": 720.00, "net": 4080.00, "source": "neon_dreams_spotify_q1_2024.pdf.txt"},
                {"platform": "Apple Music", "type": "streaming", "start": "2024-01-01", "end": "2024-03-31", "gross": 3100.00, "fees": 465.00, "net": 2635.00, "source": "neon_dreams_apple_music_q1_2024.pdf.txt"},
            ]
        },
        {
            "title": "Summer Vibe",
            "isrc": "US-AT2-24-00104",
            "iswc": "T-070.234.567-4",
            "label": "Sunburst Music",
            "status": "active",
            "total_earnings": 31920.80,
            "splits": [
                {"party_name": "Brian Johnson", "share_percentage": 50.0, "share_type": "songwriter_share", "pro": "ASCAP", "source": "summer_vibe_split.pdf.txt"},
                {"party_name": "David Thorne", "share_percentage": 50.0, "share_type": "songwriter_share", "pro": "BMI", "source": "summer_vibe_split.pdf.txt"},
            ],
            "syncs": [],
            "royalties": [
                {"platform": "Spotify", "type": "streaming", "start": "2024-01-01", "end": "2024-03-31", "gross": 5800.00, "fees": 870.00, "net": 4930.00, "source": "summer_vibe_spotify_q1_2024.pdf.txt"},
                {"platform": "Apple Music", "type": "streaming", "start": "2024-01-01", "end": "2024-03-31", "gross": 3950.00, "fees": 592.50, "net": 3357.50, "source": "summer_vibe_apple_music_q1_2024.pdf.txt"},
            ]
        },
        {
            "title": "Lost Signal",
            "isrc": "US-AT2-24-00105",
            "iswc": "T-070.234.567-5",
            "label": "Eclipse Audio",
            "status": "active",
            "total_earnings": 18750.40,
            "splits": [
                {"party_name": "Brian Johnson", "share_percentage": 70.0, "share_type": "songwriter_share", "pro": "ASCAP", "source": "lost_signal_split.pdf.txt"},
                {"party_name": "Kavita Rao", "share_percentage": 30.0, "share_type": "producer_share", "pro": "SESAC", "source": "lost_signal_split.pdf.txt"},
            ],
            "syncs": [],
            "royalties": [
                {"platform": "Spotify", "type": "streaming", "start": "2024-01-01", "end": "2024-03-31", "gross": 3200.00, "fees": 480.00, "net": 2720.00, "source": "lost_signal_spotify_q1_2024.pdf.txt"},
                {"platform": "YouTube", "type": "ad_supported", "start": "2024-01-01", "end": "2024-03-31", "gross": 1450.00, "fees": 217.50, "net": 1232.50, "source": "lost_signal_youtube_q1_2024.pdf.txt"},
            ]
        }
    ]

    total_chunks = 0
    for w_idx, w_data in enumerate(works_data):
        work = Work(
            title=w_data["title"],
            isrc=w_data["isrc"],
            iswc=w_data["iswc"],
            label=w_data["label"],
            status=w_data["status"],
            total_earnings=w_data["total_earnings"],
        )
        session.add(work)
        session.flush()

        # Splits
        split_doc_name = f"{w_data['title'].lower().replace(' ', '_')}_split.pdf.txt"
        for s in w_data["splits"]:
            split = Split(
                work_id=work.id,
                party_name=s["party_name"],
                share_percentage=s["share_percentage"],
                share_type=s["share_type"],
                pro=s["pro"],
                notes=f"Source: {s['source']}",
            )
            session.add(split)

        # DocumentChunk for Split Sheet
        chunk_split = DocumentChunk(
            doc_id=str(uuid.uuid4()),
            doc_type="split_sheet",
            source_filename=split_doc_name,
            content=f"SPLIT SHEET AGREEMENT\nWork: {w_data['title']}\nISRC: {w_data['isrc']}\nISWC: {w_data['iswc']}\n" + "\n".join([f"{s['party_name']}: {s['share_percentage']}% ({s['share_type']}, {s['pro']})" for s in w_data['splits']]),
            work_title=w_data["title"],
            chunk_index=0,
            confidence=0.98,
        )
        session.add(chunk_split)
        total_chunks += 1

        # Sync Licenses
        for syn in w_data["syncs"]:
            sync_lic = SyncLicense(
                work_id=work.id,
                title=syn["title"],
                licensee=syn["licensee"],
                media_type=syn["media_type"],
                territory=syn["territory"],
                fee=syn["fee"],
                currency="USD",
                status=syn["status"],
            )
            session.add(sync_lic)
            
            contract_doc = f"{w_data['title'].lower().replace(' ', '_')}_sync_contract.pdf.txt"
            chunk_sync = DocumentChunk(
                doc_id=str(uuid.uuid4()),
                doc_type="sync_contract",
                source_filename=contract_doc,
                content=f"SYNC LICENSE AGREEMENT\nWork: {w_data['title']}\nLicensee: {syn['licensee']}\nFee: ${syn['fee']:,.2f}\nMedia: {syn['media_type']}\nTerritory: {syn['territory']}",
                work_title=w_data["title"],
                chunk_index=0,
                confidence=0.95,
            )
            session.add(chunk_sync)
            total_chunks += 1

        # Royalties
        for roy in w_data["royalties"]:
            r_entry = RoyaltyEntry(
                work_id=work.id,
                platform=roy["platform"],
                royalty_type=roy["type"],
                period_start=roy["start"],
                period_end=roy["end"],
                gross_amount=roy["gross"],
                fees_deducted=roy["fees"],
                net_amount=roy["net"],
                currency="USD",
                source_document=roy["source"],
            )
            session.add(r_entry)

            chunk_roy = DocumentChunk(
                doc_id=str(uuid.uuid4()),
                doc_type="royalty_statement",
                source_filename=roy["source"],
                content=f"ROYALTY STATEMENT\nWork: {w_data['title']}\nPlatform: {roy['platform']}\nPeriod: {roy['start']} to {roy['end']}\nGross: ${roy['gross']:,.2f} | Net: ${roy['net']:,.2f}",
                work_title=w_data["title"],
                chunk_index=0,
                confidence=0.92,
            )
            session.add(chunk_roy)
            total_chunks += 1

    session.commit()
    logger.info(f"Seeded {len(works_data)} works and {total_chunks} document chunks successfully.")
    return {
        "status": "success",
        "works_seeded": len(works_data),
        "chunks_seeded": total_chunks,
    }
