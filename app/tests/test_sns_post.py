"""Tests for SnsPost domain model."""

from domain.models.sns_post import SnsPost


def test_generate_post_text_with_custom_hashtags() -> None:
    """Test generating post text with custom hashtags."""
    post = SnsPost(
        message="今回のテーマ: AIと未来\n\nAIが社会をどう変えるか議論しました。",
        platform_urls={
            "apple": "https://apple.com",
            "spotify": "https://spotify.com",
            "amazon": "https://amazon.com",
        },
        episode_number=42,
        hashtags=["#AI", "#Podcast"],
    )
    post_text = post.generate_text()
    assert "第42回" in post_text
    assert "今回のテーマ: AIと未来" in post_text
    assert "▼Apple\nhttps://apple.com" in post_text
    assert "▼Spotify\nhttps://spotify.com" in post_text
    assert "▼Amazon\nhttps://amazon.com" in post_text
    assert "#AI #Podcast" in post_text
    assert len(post_text) <= 280


def test_generate_post_text_with_default_hashtags() -> None:
    """Test generating post text with default hashtags."""
    post = SnsPost(
        message="AIの進化に驚しました。",
        platform_urls={"apple": "a", "spotify": "b", "amazon": "c"},
        episode_number=7,
    )
    post_text = post.generate_text()
    assert "第7回" in post_text
    assert "AIの進化に驚しました。" in post_text
    assert "#Podcast #新着エピソード #議事録" in post_text
    assert len(post_text) <= 280


def test_generate_post_text_is_truncated_when_too_long() -> None:
    """Test generating post text when message is extremely long."""
    post = SnsPost(
        message="a" * 400,
        platform_urls={"apple": "a", "spotify": "b", "amazon": "c"},
    )
    post_text = post.generate_text()
    assert "..." not in post_text
    assert len(post_text) > 280


def test_generate_post_text_uses_only_existing_platform_keys() -> None:
    """Test generating post text excludes empty platform urls."""
    post = SnsPost(
        message="テスト投稿",
        platform_urls={"apple": "https://apple.com", "spotify": ""},
        hashtags=["#test"],
    )
    post_text = post.generate_text()
    assert "▼Apple\nhttps://apple.com" in post_text
    assert "▼Spotify" not in post_text


def test_generate_post_text_without_episode_number() -> None:
    """Test generating post text without episode number prefix."""
    post = SnsPost(
        message="番号なし投稿",
        platform_urls={"apple": "https://apple.com", "spotify": "", "amazon": ""},
        hashtags=["#test"],
    )
    post_text = post.generate_text()
    assert "第" not in post_text
    assert "番号なし投稿" in post_text


def test_generate_post_text_without_platform_urls() -> None:
    """Test generating post text without platform urls footer."""
    post = SnsPost(
        message="URLなし投稿",
        hashtags=["#test"],
    )

    post_text = post.generate_text()
    assert "URLなし投稿" in post_text
    assert "▼Apple" not in post_text
    assert "#test" in post_text
