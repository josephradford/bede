from bede_data_mcp.server import (
    check_article_exists,
    list_articles,
    mark_article_in_digest,
    save_article,
)


async def test_save_article(api):
    api.post.return_value = {
        "id": 1,
        "url": "https://example.com/article",
        "title": "AI News",
        "source_name": "TLDR AI",
        "category": "ai",
    }
    result = await save_article(
        "https://example.com/article", "AI News", "TLDR AI", category="ai", summary="Big things."
    )
    api.post.assert_called_once_with(
        "/api/news/articles",
        {
            "url": "https://example.com/article",
            "title": "AI News",
            "source_name": "TLDR AI",
            "category": "ai",
            "summary": "Big things.",
        },
    )
    assert result["id"] == 1


async def test_save_article_minimal(api):
    api.post.return_value = {"id": 2}
    await save_article("https://example.com/a", "Title", "Source")
    api.post.assert_called_once_with(
        "/api/news/articles",
        {"url": "https://example.com/a", "title": "Title", "source_name": "Source"},
    )


async def test_list_articles(api):
    api.get.return_value = {"articles": [{"id": 1, "title": "A"}]}
    result = await list_articles()
    api.get.assert_called_once_with("/api/news/articles")
    assert len(result["articles"]) == 1


async def test_list_articles_filtered(api):
    api.get.return_value = {"articles": []}
    await list_articles(category="ai", unsent=True)
    api.get.assert_called_once_with("/api/news/articles", category="ai", unsent=True)


async def test_list_articles_by_source(api):
    api.get.return_value = {"articles": []}
    await list_articles(source_name="Hacker News")
    api.get.assert_called_once_with("/api/news/articles", source_name="Hacker News")


async def test_check_article_exists(api):
    api.get.return_value = {"exists": True, "url": "https://example.com"}
    result = await check_article_exists("https://example.com")
    api.get.assert_called_once_with("/api/news/articles/exists", url="https://example.com")
    assert result["exists"] is True


async def test_mark_article_in_digest(api):
    api.put.return_value = {"id": 1, "digest_date": "2026-05-07"}
    result = await mark_article_in_digest(1, "2026-05-07")
    api.put.assert_called_once_with(
        "/api/news/articles/1/digest", {"digest_date": "2026-05-07"}
    )
    assert result["digest_date"] == "2026-05-07"
