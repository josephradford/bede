import json


def test_record_price_check(client):
    item = client.post(
        "/api/config/monitored-items",
        json={"category": "deal", "name": "Camping Gear", "config": "{}"},
    ).json()

    response = client.post(
        "/api/deals/price-checks",
        json={
            "monitored_item_id": item["id"],
            "url": "https://anaconda.com.au/product/123",
            "price": 149.95,
            "currency": "AUD",
            "in_stock": True,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["price"] == 149.95
    assert data["in_stock"] is True


def test_record_price_check_out_of_stock(client):
    item = client.post(
        "/api/config/monitored-items",
        json={"category": "deal", "name": "Gear", "config": "{}"},
    ).json()

    response = client.post(
        "/api/deals/price-checks",
        json={
            "monitored_item_id": item["id"],
            "url": "https://example.com/product",
            "in_stock": False,
        },
    )
    assert response.status_code == 201
    assert response.json()["price"] is None
    assert response.json()["in_stock"] is False


def test_get_price_history(client):
    item = client.post(
        "/api/config/monitored-items",
        json={"category": "deal", "name": "Gear", "config": "{}"},
    ).json()

    client.post(
        "/api/deals/price-checks",
        json={
            "monitored_item_id": item["id"],
            "url": "https://example.com/p",
            "price": 100.0,
            "in_stock": True,
        },
    )
    client.post(
        "/api/deals/price-checks",
        json={
            "monitored_item_id": item["id"],
            "url": "https://example.com/p",
            "price": 89.95,
            "in_stock": True,
        },
    )

    response = client.get(f"/api/deals/price-history/{item['id']}")
    assert response.status_code == 200
    checks = response.json()["checks"]
    assert len(checks) == 2
    assert checks[0]["price"] == 89.95  # most recent first


def test_get_price_history_with_limit(client):
    item = client.post(
        "/api/config/monitored-items",
        json={"category": "deal", "name": "Gear", "config": "{}"},
    ).json()

    for i in range(5):
        client.post(
            "/api/deals/price-checks",
            json={
                "monitored_item_id": item["id"],
                "url": "https://example.com/p",
                "price": 100.0 + i,
                "in_stock": True,
            },
        )

    response = client.get(f"/api/deals/price-history/{item['id']}", params={"limit": 3})
    assert len(response.json()["checks"]) == 3


def test_report_dead_url(client):
    response = client.post(
        "/api/deals/dead-urls",
        json={
            "url": "https://broken.example.com/product",
            "category": "deal",
            "last_error": "404 Not Found",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["fail_count"] == 1
    assert data["url"] == "https://broken.example.com/product"


def test_report_dead_url_increments_fail_count(client):
    for _ in range(3):
        client.post(
            "/api/deals/dead-urls",
            json={
                "url": "https://broken.example.com",
                "category": "deal",
                "last_error": "timeout",
            },
        )

    response = client.get("/api/deals/dead-urls")
    urls = response.json()["urls"]
    assert len(urls) == 1
    assert urls[0]["fail_count"] == 3


def test_list_dead_urls(client):
    client.post(
        "/api/deals/dead-urls",
        json={"url": "https://a.com", "category": "deal", "last_error": "404"},
    )
    client.post(
        "/api/deals/dead-urls",
        json={"url": "https://b.com", "category": "news", "last_error": "403"},
    )

    response = client.get("/api/deals/dead-urls")
    assert len(response.json()["urls"]) == 2

    response = client.get("/api/deals/dead-urls", params={"category": "deal"})
    assert len(response.json()["urls"]) == 1


def test_list_dead_urls_excludes_disabled(client):
    resp = client.post(
        "/api/deals/dead-urls",
        json={"url": "https://old.com", "category": "deal", "last_error": "gone"},
    )
    url_id = resp.json()["id"]

    client.put(f"/api/deals/dead-urls/{url_id}", json={"disabled": True})

    response = client.get("/api/deals/dead-urls")
    assert len(response.json()["urls"]) == 0


def test_update_dead_url(client):
    resp = client.post(
        "/api/deals/dead-urls",
        json={"url": "https://old.com", "category": "deal", "last_error": "404"},
    )
    url_id = resp.json()["id"]

    response = client.put(f"/api/deals/dead-urls/{url_id}", json={"disabled": True})
    assert response.status_code == 200
    assert response.json()["disabled"] is True
