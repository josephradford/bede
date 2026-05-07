def test_save_article(client):
    response = client.post(
        "/api/news/articles",
        json={
            "url": "https://example.com/article-1",
            "title": "AI Breakthrough",
            "source_name": "Hacker News",
            "category": "ai",
            "summary": "Researchers achieved...",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "AI Breakthrough"
    assert data["digest_date"] is None


def test_save_article_duplicate_returns_existing(client):
    client.post(
        "/api/news/articles",
        json={
            "url": "https://example.com/dupe",
            "title": "Original",
            "source_name": "HN",
            "category": "tech",
        },
    )
    response = client.post(
        "/api/news/articles",
        json={
            "url": "https://example.com/dupe",
            "title": "Duplicate Attempt",
            "source_name": "HN",
            "category": "tech",
        },
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Original"
    assert response.json()["already_existed"] is True


def test_list_articles(client):
    client.post(
        "/api/news/articles",
        json={
            "url": "https://a.com",
            "title": "A",
            "source_name": "HN",
            "category": "tech",
        },
    )
    client.post(
        "/api/news/articles",
        json={
            "url": "https://b.com",
            "title": "B",
            "source_name": "HN",
            "category": "ai",
        },
    )

    response = client.get("/api/news/articles")
    assert len(response.json()["articles"]) == 2


def test_list_articles_filter_category(client):
    client.post(
        "/api/news/articles",
        json={
            "url": "https://a.com",
            "title": "A",
            "source_name": "HN",
            "category": "tech",
        },
    )
    client.post(
        "/api/news/articles",
        json={
            "url": "https://b.com",
            "title": "B",
            "source_name": "HN",
            "category": "ai",
        },
    )

    response = client.get("/api/news/articles", params={"category": "ai"})
    articles = response.json()["articles"]
    assert len(articles) == 1
    assert articles[0]["category"] == "ai"


def test_list_articles_unsent_only(client):
    client.post(
        "/api/news/articles",
        json={
            "url": "https://a.com",
            "title": "A",
            "source_name": "HN",
            "category": "tech",
        },
    )
    resp = client.post(
        "/api/news/articles",
        json={
            "url": "https://b.com",
            "title": "B",
            "source_name": "HN",
            "category": "tech",
        },
    )
    article_id = resp.json()["id"]
    client.put(
        f"/api/news/articles/{article_id}/digest",
        json={"digest_date": "2026-05-07"},
    )

    response = client.get("/api/news/articles", params={"unsent": "true"})
    articles = response.json()["articles"]
    assert len(articles) == 1
    assert articles[0]["url"] == "https://a.com"


def test_mark_article_in_digest(client):
    resp = client.post(
        "/api/news/articles",
        json={
            "url": "https://a.com",
            "title": "A",
            "source_name": "HN",
            "category": "tech",
        },
    )
    article_id = resp.json()["id"]

    response = client.put(
        f"/api/news/articles/{article_id}/digest",
        json={"digest_date": "2026-05-07"},
    )
    assert response.status_code == 200
    assert response.json()["digest_date"] == "2026-05-07"


def test_check_article_exists(client):
    response = client.get(
        "/api/news/articles/exists",
        params={"url": "https://nonexistent.com"},
    )
    assert response.json()["exists"] is False

    client.post(
        "/api/news/articles",
        json={
            "url": "https://exists.com",
            "title": "X",
            "source_name": "HN",
            "category": "tech",
        },
    )
    response = client.get(
        "/api/news/articles/exists",
        params={"url": "https://exists.com"},
    )
    assert response.json()["exists"] is True
