"""X (formerly Twitter) API client wrapper using Tweepy."""

from __future__ import annotations

import logging
import re
import unicodedata
from typing import Any

import tweepy

logger = logging.getLogger(__name__)

MAX_X_POST_LENGTH = 280


def _extract_tweepy_error_details(exc: Exception) -> dict[str, Any]:
    response = getattr(exc, "response", None)
    status_code = getattr(response, "status_code", None)

    payload: dict[str, Any] | None = None
    raw_text: str | None = None
    if response is not None:
        try:
            payload = response.json()
        except Exception:  # noqa: BLE001
            raw_text = (getattr(response, "text", "") or "")[:500]

    errors = payload.get("errors") if isinstance(payload, dict) else None
    first_error = errors[0] if isinstance(errors, list) and errors else {}
    title = payload.get("title") if isinstance(payload, dict) else None
    detail = payload.get("detail") if isinstance(payload, dict) else None
    error_type = payload.get("type") if isinstance(payload, dict) else None

    if isinstance(first_error, dict):
        title = first_error.get("title") or title
        detail = first_error.get("detail") or detail
        error_type = first_error.get("type") or error_type

    return {
        "status_code": status_code,
        "title": title,
        "detail": detail,
        "type": error_type,
        "raw": raw_text,
    }


class XClient:
    """Wrapper around Tweepy client for posting threads and health check."""

    def __init__(self, api_key: str, api_secret: str, access_token: str, access_token_secret: str) -> None:
        """Initialize Tweepy client."""
        self.api_key = api_key
        self.api_secret = api_secret
        self.access_token = access_token
        self.access_token_secret = access_token_secret
        self.client = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_token_secret,
        )

    def verify_auth(self) -> bool:
        """Verify client authentication credentials."""
        try:
            response = self.client.get_me(user_auth=True)
            is_verified = bool(response and response.data)
            if is_verified:
                logger.info("event=x_auth_check_succeeded user_id=%s", response.data.id)
            else:
                logger.error("event=x_auth_check_failed reason=empty_response")
            return is_verified
        except tweepy.errors.TweepyException as exc:
            details = _extract_tweepy_error_details(exc)
            logger.exception(
                "event=x_auth_check_failed reason=tweepy_exception status_code=%s title=%s detail=%s type=%s raw=%s",
                details["status_code"],
                details["title"],
                details["detail"],
                details["type"],
                details["raw"],
            )
            return False
        except Exception:  # noqa: BLE001
            logger.exception("event=x_auth_check_failed reason=exception")
            return False

    @staticmethod
    def x_weighted_length(text: str) -> int:
        """Calculate weighted character length for X post."""
        # Treat full-width and wide characters as 2 to keep chunks within X limits.
        return sum(2 if unicodedata.east_asian_width(char) in {"F", "W", "A"} else 1 for char in text)

    @classmethod
    def _safe_cut_position(cls, text: str, max_length: int) -> int:
        weighted = 0
        for idx, char in enumerate(text, start=1):
            char_weight = cls.x_weighted_length(char)
            if weighted + char_weight > max_length:
                return idx - 1
            weighted += char_weight
        return len(text)

    @staticmethod
    def split_for_x(text: str, max_length: int = MAX_X_POST_LENGTH) -> list[str]:
        """Split a long text string into multiple post-sized chunks for a thread."""
        if max_length <= 0:
            raise ValueError("max_length must be greater than 0")

        normalized = text.strip()
        if not normalized:
            return []

        if XClient.x_weighted_length(normalized) <= max_length:
            return [normalized]

        chunks: list[str] = []
        remaining = normalized
        separator_pattern = r"\n\n|\n|。|！|？|\.\s|!\s|\?\s|、|,\s|\s"  # noqa: RUF001

        while remaining:
            if XClient.x_weighted_length(remaining) <= max_length:
                chunks.append(remaining.strip())
                break

            safe_cut_position = XClient._safe_cut_position(remaining, max_length)
            if safe_cut_position <= 0:
                safe_cut_position = 1

            segment = remaining[:safe_cut_position]
            cut_position = None

            for match in re.finditer(separator_pattern, segment):
                cut_position = match.end()

            if cut_position is None or cut_position <= 0:
                cut_position = safe_cut_position

            chunk = remaining[:cut_position].strip()
            if not chunk:
                chunk = remaining[:safe_cut_position]
                cut_position = safe_cut_position

            chunks.append(chunk)
            remaining = remaining[cut_position:].lstrip()

        return chunks

    def _post_single(self, text: str, in_reply_to_tweet_id: str | None = None) -> str | None:
        try:
            create_args: dict[str, Any] = {"text": text}
            if in_reply_to_tweet_id:
                create_args["in_reply_to_tweet_id"] = in_reply_to_tweet_id

            response = self.client.create_tweet(**create_args)
            tweet_id = response.data.get("id") if response and response.data else None
            if tweet_id:
                logger.info(
                    "event=x_post_api_succeeded tweet_id=%s in_reply_to_tweet_id=%s",
                    tweet_id,
                    in_reply_to_tweet_id,
                )
            else:
                logger.error("event=x_post_api_failed reason=empty_response")
            return tweet_id
        except tweepy.errors.Forbidden as exc:
            details = _extract_tweepy_error_details(exc)
            logger.error(  # noqa: TRY400
                "event=x_post_api_forbidden status_code=%s title=%s detail=%s type=%s in_reply_to_tweet_id=%s raw=%s",
                details["status_code"],
                details["title"],
                details["detail"],
                details["type"],
                in_reply_to_tweet_id,
                details["raw"],
            )
            return None
        except tweepy.errors.TweepyException as exc:
            details = _extract_tweepy_error_details(exc)
            logger.exception(
                "event=x_post_api_failed reason=tweepy_exception status_code=%s title=%s "
                "detail=%s type=%s in_reply_to_tweet_id=%s raw=%s",
                details["status_code"],
                details["title"],
                details["detail"],
                details["type"],
                in_reply_to_tweet_id,
                details["raw"],
            )
            return None
        except Exception:  # noqa: BLE001
            logger.exception("event=x_post_api_failed reason=exception")
            return None

    def post(self, text: str) -> bool:
        """Post a single tweet to X."""
        return self._post_single(text) is not None

    def post_thread(self, text: str) -> bool:
        """Post a thread of tweets (replies in sequence) to X."""
        chunks = self.split_for_x(text)
        if not chunks:
            logger.warning("event=x_post_skipped reason=empty_text")
            return False

        parent_tweet_id: str | None = None
        for chunk in chunks:
            tweet_id = self._post_single(chunk, in_reply_to_tweet_id=parent_tweet_id)
            if tweet_id is None:
                logger.error(
                    "event=x_thread_post_failed posted_chunks=%s total_chunks=%s",
                    0 if parent_tweet_id is None else 1,
                    len(chunks),
                )
                return False
            parent_tweet_id = tweet_id

        logger.info("event=x_thread_post_succeeded chunks=%s", len(chunks))
        return True
