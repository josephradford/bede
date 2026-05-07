from bede_data_mcp.server import (
    get_price_history,
    list_dead_urls,
    record_price_check,
    report_dead_url,
    update_dead_url,
)


async def test_record_price_check(api):
    api.post.return_value = {
        "id": 1,
        "monitored_item_id": 5,
        "url": "https://example.com/p",
        "price": 149.95,
        "in_stock": True,
    }
    result = await record_price_check(5, "https://example.com/p", 149.95, "AUD", True)
    api.post.assert_called_once_with(
        "/api/deals/price-checks",
        {
            "monitored_item_id": 5,
            "url": "https://example.com/p",
            "price": 149.95,
            "currency": "AUD",
            "in_stock": True,
        },
    )
    assert result["price"] == 149.95


async def test_record_price_check_out_of_stock(api):
    api.post.return_value = {"id": 2, "price": None, "in_stock": False}
    result = await record_price_check(5, "https://example.com/p", in_stock=False)
    api.post.assert_called_once_with(
        "/api/deals/price-checks",
        {
            "monitored_item_id": 5,
            "url": "https://example.com/p",
            "in_stock": False,
        },
    )
    assert result["in_stock"] is False


async def test_record_price_check_with_notes(api):
    api.post.return_value = {"id": 3}
    await record_price_check(5, "https://example.com/p", price=99.0, notes="sale ends Friday")
    call_body = api.post.call_args[0][1]
    assert call_body["notes"] == "sale ends Friday"


async def test_get_price_history(api):
    api.get.return_value = {
        "checks": [
            {"id": 2, "price": 89.95, "checked_at": "2026-05-07T12:00:00Z"},
            {"id": 1, "price": 99.95, "checked_at": "2026-05-06T12:00:00Z"},
        ]
    }
    result = await get_price_history(5)
    api.get.assert_called_once_with("/api/deals/price-history/5")
    assert len(result["checks"]) == 2


async def test_get_price_history_with_limit(api):
    api.get.return_value = {"checks": []}
    await get_price_history(5, limit=10)
    api.get.assert_called_once_with("/api/deals/price-history/5", limit=10)


async def test_get_price_history_with_url_filter(api):
    api.get.return_value = {"checks": []}
    await get_price_history(5, url="https://example.com/p")
    api.get.assert_called_once_with("/api/deals/price-history/5", url="https://example.com/p")


async def test_report_dead_url(api):
    api.post.return_value = {
        "id": 1,
        "url": "https://dead.com",
        "fail_count": 1,
    }
    result = await report_dead_url("https://dead.com", "deal", "404 Not Found")
    api.post.assert_called_once_with(
        "/api/deals/dead-urls",
        {"url": "https://dead.com", "category": "deal", "last_error": "404 Not Found"},
    )
    assert result["fail_count"] == 1


async def test_list_dead_urls(api):
    api.get.return_value = {"urls": [{"id": 1, "url": "https://dead.com"}]}
    result = await list_dead_urls()
    api.get.assert_called_once_with("/api/deals/dead-urls")
    assert len(result["urls"]) == 1


async def test_list_dead_urls_by_category(api):
    api.get.return_value = {"urls": []}
    await list_dead_urls(category="deal")
    api.get.assert_called_once_with("/api/deals/dead-urls", category="deal")


async def test_update_dead_url(api):
    api.put.return_value = {"id": 1, "disabled": True}
    result = await update_dead_url(1, disabled=True)
    api.put.assert_called_once_with("/api/deals/dead-urls/1", {"disabled": True})
    assert result["disabled"] is True
