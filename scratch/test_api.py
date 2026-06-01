"""
Test kedua API: Primary (dramabos) dan Backup (sapimu.au)
"""
import asyncio
import sys
import os

# Fix encoding Windows
sys.stdout.reconfigure(encoding="utf-8")

# Tambah parent dir ke path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api import (
    PRIMARY_BASE_URL, PRIMARY_TOKEN,
    BACKUP_BASE_URL, BACKUP_TOKEN,
    search_drama,
    get_drama_detail,
    get_popular_feed,
    backup_search_drama,
    backup_get_drama_detail,
    backup_get_feed,
    backup_get_play_url,
    backup_get_home,
)

SEP = "=" * 55

def ok(msg):  print(f"  ✅ {msg}")
def fail(msg): print(f"  ❌ {msg}")
def info(msg): print(f"  ℹ️  {msg}")

# ────────────────────────────────────────────
async def test_primary():
    print(f"\n{SEP}")
    print("🔵  PRIMARY API — shortmax.dramabos.online")
    print(f"{SEP}")
    info(f"Base URL : {PRIMARY_BASE_URL}")
    info(f"Token    : {PRIMARY_TOKEN[:12]}…")

    # 1. Search
    print("\n[1] Search 'cinta'…")
    try:
        results = await search_drama("cinta")
        if results:
            ok(f"Search OK — {len(results)} hasil. Contoh: {results[0].get('title','?')}")
        else:
            fail("Search OK tapi hasil kosong (mungkin API butuh token valid)")
    except Exception as e:
        fail(f"Search error: {e}")

    # 2. Popular feed
    print("\n[2] Popular feed (page=1)…")
    try:
        items = await get_popular_feed(page=1)
        if items:
            ok(f"Popular feed OK — {len(items)} item")
        else:
            fail("Popular feed kosong")
    except Exception as e:
        fail(f"Popular feed error: {e}")

    # 3. Drama detail (pakai ID contoh dari ShortMax)
    SAMPLE_ID = "843852"
    print(f"\n[3] Drama detail (id={SAMPLE_ID})…")
    try:
        detail, err = await get_drama_detail(SAMPLE_ID)
        if detail:
            ok(f"Detail OK — judul: {detail.get('title','?')}, ep: {len(detail.get('episodes',[]))} eps")
        else:
            fail(f"Detail gagal: {err}")
    except Exception as e:
        fail(f"Detail error: {e}")

# ────────────────────────────────────────────
async def test_backup():
    print(f"\n{SEP}")
    print("🟡  BACKUP API — captain.sapimu.au/shortmax")
    print(f"{SEP}")
    info(f"Base URL : {BACKUP_BASE_URL}")
    info(f"Token    : {BACKUP_TOKEN[:16]}…")

    SAMPLE_ID = "843852"

    # 1. Search
    print("\n[1] backup_search_drama('cinta')…")
    try:
        results = await backup_search_drama("cinta")
        if results:
            ok(f"Search OK — {len(results)} hasil. Contoh: {results[0].get('title','?')}")
        else:
            fail("Search OK tapi hasil kosong")
    except Exception as e:
        fail(f"Search error: {e}")

    # 2. Home feed
    print("\n[2] backup_get_home(tab=1)…")
    try:
        items = await backup_get_home(tab=1)
        if items:
            ok(f"Home OK — {len(items)} item")
        else:
            fail("Home kosong")
    except Exception as e:
        fail(f"Home error: {e}")

    # 3. Feed recommend
    print("\n[3] backup_get_feed('recommend')…")
    try:
        items = await backup_get_feed("recommend")
        if items:
            ok(f"Feed recommend OK — {len(items)} item")
        else:
            fail("Feed recommend kosong")
    except Exception as e:
        fail(f"Feed recommend error: {e}")

    # 4. Feed vip
    print("\n[4] backup_get_feed('vip')…")
    try:
        items = await backup_get_feed("vip")
        if items:
            ok(f"Feed VIP OK — {len(items)} item")
        else:
            fail("Feed VIP kosong")
    except Exception as e:
        fail(f"Feed VIP error: {e}")

    # 5. Drama detail
    print(f"\n[5] backup_get_drama_detail('{SAMPLE_ID}')…")
    try:
        detail, err = await backup_get_drama_detail(SAMPLE_ID)
        if detail:
            ok(f"Detail OK — judul: {detail.get('title','?')}")
        else:
            fail(f"Detail gagal: {err}")
    except Exception as e:
        fail(f"Detail error: {e}")

    # 6. Play URL ep 1
    print(f"\n[6] backup_get_play_url('{SAMPLE_ID}', ep=1)…")
    try:
        url = await backup_get_play_url(SAMPLE_ID, ep=1)
        if url:
            ok(f"Play URL OK — {url[:80]}…")
        else:
            fail("Play URL kosong (mungkin VIP only atau token belum aktif)")
    except Exception as e:
        fail(f"Play URL error: {e}")

    # 7. For You feed
    print("\n[7] backup_get_feed('foryou', page=1)…")
    try:
        items = await backup_get_feed("foryou", page=1)
        if items:
            ok(f"ForYou feed OK — {len(items)} item")
        else:
            fail("ForYou feed kosong")
    except Exception as e:
        fail(f"ForYou feed error: {e}")

# ────────────────────────────────────────────
async def main():
    print(f"\n{'#'*55}")
    print("   SHORTMAX API TEST")
    print(f"{'#'*55}")

    await test_primary()
    await test_backup()

    print(f"\n{SEP}")
    print("✔  Test selesai.")
    print(SEP)

asyncio.run(main())
