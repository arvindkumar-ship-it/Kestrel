from datetime import datetime, timezone

import pytest

from app.insider.graph_store import GraphStore


@pytest.mark.asyncio
async def test_new_edge_flagged_novel(db_session, redis):
    gs = GraphStore(lambda: db_session, redis)
    result = await gs.record_access(db_session, "u1", "r1", "database", datetime.now(timezone.utc))
    assert result.is_new_edge is True


@pytest.mark.asyncio
async def test_repeat_edge_not_novel(db_session, redis):
    gs = GraphStore(lambda: db_session, redis)
    ts = datetime.now(timezone.utc)
    await gs.record_access(db_session, "u1", "r1", "database", ts)
    result = await gs.record_access(db_session, "u1", "r1", "database", ts)
    assert result.is_new_edge is False


def test_novelty_score_zero_for_non_novel():
    from app.insider.graph_store import GraphStore, NoveltyResult

    gs = GraphStore(None, None)
    r = NoveltyResult(is_new_edge=False, actor_resource_count=5, resource_degree=3)
    assert gs.novelty_score(r) == 0.0


def test_novelty_score_high_for_rare_resource():
    from app.insider.graph_store import GraphStore, NoveltyResult

    gs = GraphStore(None, None)
    r = NoveltyResult(is_new_edge=True, actor_resource_count=5, resource_degree=1)
    assert gs.novelty_score(r) > 0.5
