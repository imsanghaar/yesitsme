"""Instagram API client for yesitsme."""

import hashlib
import hmac
import json
import urllib.parse
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)


@dataclass
class UserInfo:
    """Container for Instagram user information."""

    username: str
    user_id: str
    full_name: str
    is_verified: bool
    is_business: bool
    is_private: bool
    follower_count: int
    following_count: int
    media_count: int
    external_url: Optional[str]
    biography: Optional[str]
    public_email: Optional[str]
    public_phone_number: Optional[str]
    profile_pic_url: Optional[str]
    obfuscated_email: Optional[str] = None
    obfuscated_phone: Optional[str] = None


@dataclass
class APIResponse:
    """Standardized API response container."""

    data: Any
    error: Optional[str] = None
    rate_limited: bool = False


class InstagramAPI:
    """Instagram API client with retry logic and rate limit handling."""

    BASE_URL = "https://i.instagram.com/api/v1"
    USERS_LOOKUP_URL = "https://i.instagram.com/api/v1/users/lookup/"
    SIG_KEY_VERSION = "4"
    IG_SIG_KEY = "e6358aeede676184b9fe702b30f4fd35e71744605e39d2181a34cede076b3c33"

    def __init__(
        self,
        session_id: Optional[str] = None,
        proxy: Optional[str] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        """
        Initialize Instagram API client.

        Args:
            session_id: Instagram session ID cookie (optional for public data)
            proxy: Optional proxy URL (e.g., http://user:pass@host:port)
            max_retries: Maximum number of retry attempts
            retry_delay: Base delay between retries
        """
        self.session_id = session_id
        self.proxy = proxy
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        headers = {
            "User-Agent": "Instagram 101.0.0.15.120",
            "Accept-Language": "en-US",
        }
        
        cookies = {}
        if session_id:
            cookies["sessionid"] = session_id

        self._client = httpx.Client(
            cookies=cookies if cookies else None,
            headers=headers,
            proxy=proxy,
            timeout=30.0,
        )

    def _generate_signature(self, data: str) -> str:
        """
        Generate Instagram API signature.

        Args:
            data: JSON-encoded data string

        Returns:
            Signed request body
        """
        signature = hmac.new(
            self.IG_SIG_KEY.encode("utf-8"),
            data.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return f"ig_sig_key_version={self.SIG_KEY_VERSION}&signed_body={signature}.{urllib.parse.quote_plus(data)}"

    def _get_user_id(self, username: str) -> APIResponse:
        """
        Get Instagram user ID from username.

        Args:
            username: Instagram username

        Returns:
            APIResponse with user ID or error
        """
        try:
            # Try the mobile API endpoint first
            response = self._client.get(
                f"{self.BASE_URL}/users/{username}/usernameinfo/",
                headers={
                    "User-Agent": "Instagram 101.0.0.15.120",
                    "Accept": "*/*",
                }
            )
            response.raise_for_status()
            info = response.json()

            user = info.get("user", {})
            user_id = user.get("pk") or user.get("id")
            
            if not user_id:
                return APIResponse(
                    data=None, error="User not found", rate_limited=False
                )

            return APIResponse(data={"user_id": str(user_id)}, error=None)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                return APIResponse(
                    data=None, error="Rate limit exceeded", rate_limited=True
                )
            if e.response.status_code == 401:
                return APIResponse(
                    data=None, error="Invalid session ID", rate_limited=False
                )
            # Fallback: try web scraping
            return self._get_user_id_web(username)
        except json.JSONDecodeError:
            # Fallback: try web scraping
            return self._get_user_id_web(username)
        except Exception as e:
            return self._get_user_id_web(username)

    def _get_user_id_web(self, username: str) -> APIResponse:
        """
        Fallback method to get user ID from web page.

        Args:
            username: Instagram username

        Returns:
            APIResponse with user ID or error
        """
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml",
            }
            response = self._client.get(
                f"https://www.instagram.com/{username}/",
                headers=headers,
            )
            response.raise_for_status()
            
            # Try to extract user ID from page
            import re
            match = re.search(r'"profilePage_(\d+)"', response.text)
            if match:
                return APIResponse(data={"user_id": match.group(1)}, error=None)
            
            # Page exists but couldn't extract ID - profile exists
            return APIResponse(data={"user_id": None}, error="Could not extract user ID")

        except Exception as e:
            return APIResponse(data=None, error=f"User not found: {e}", rate_limited=False)

    @retry(
        retry=retry_if_exception_type(httpx.RequestError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    def get_user_info(self, username: str) -> APIResponse:
        """
        Get detailed user information.

        Args:
            username: Instagram username

        Returns:
            APIResponse with UserInfo or error
        """
        user_id_response = self._get_user_id(username)
        if user_id_response.error:
            return APIResponse(
                data=None, error=user_id_response.error, rate_limited=user_id_response.rate_limited
            )

        user_id = user_id_response.data.get("user_id") if user_id_response.data else None
        
        # Always try API first with session
        if user_id:
            try:
                # Use the mobile API endpoint which returns full data with auth
                response = self._client.get(
                    f"{self.BASE_URL}/users/{user_id}/info/",
                    headers={
                        "User-Agent": "Instagram 101.0.0.15.120",
                        "Accept": "*/*",
                    }
                )
                response.raise_for_status()
                info = response.json()

                user_data = info.get("user", {})
                if not user_data:
                    return APIResponse(data=None, error="User data not found", rate_limited=False)

                user_info = UserInfo(
                    username=user_data.get("username", ""),
                    user_id=user_id,
                    full_name=user_data.get("full_name", ""),
                    is_verified=user_data.get("is_verified", False),
                    is_business=user_data.get("is_business", False),
                    is_private=user_data.get("is_private", False),
                    follower_count=user_data.get("follower_count", 0),
                    following_count=user_data.get("following_count", 0),
                    media_count=user_data.get("media_count", 0),
                    external_url=user_data.get("external_url"),
                    biography=user_data.get("biography"),
                    public_email=user_data.get("public_email"),
                    public_phone_number=user_data.get("public_phone_number"),
                    profile_pic_url=user_data.get("hd_profile_pic_url_info", {}).get("url"),
                )

                return APIResponse(data=user_info, error=None)

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    return APIResponse(data=None, error="Rate limit exceeded", rate_limited=True)
                return APIResponse(data=None, error=f"HTTP error: {e}", rate_limited=False)
            except json.JSONDecodeError:
                return APIResponse(data=None, error="Invalid JSON response", rate_limited=False)
            except Exception as e:
                return APIResponse(data=None, error=str(e), rate_limited=False)
        
        return APIResponse(data=None, error="Could not get user ID", rate_limited=False)

    def _get_user_info_web(self, username: str, user_id: Optional[str] = None) -> APIResponse:
        """
        Get user info by scraping public web page.

        Args:
            username: Instagram username
            user_id: Optional user ID if already known

        Returns:
            APIResponse with UserInfo or error
        """
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml",
            }
            response = self._client.get(
                f"https://www.instagram.com/{username}/",
                headers=headers,
            )
            response.raise_for_status()
            
            import re
            
            # Method 1: Extract sharedData JSON
            match = re.search(r'window\._sharedData\s*=\s*({.+?});\s*</script>', response.text)
            
            if match:
                try:
                    data = json.loads(match.group(1))
                    user_data = None
                    
                    if 'entry_data' in data:
                        profile_data = data['entry_data'].get('ProfilePage', [{}])[0]
                        user_data = profile_data.get('graphql', {}).get('user', {})
                    elif 'graphql' in data:
                        user_data = data.get('graphql', {}).get('user', {})
                    
                    if user_data and user_data.get('id'):
                        user_info = UserInfo(
                            username=user_data.get('username', username),
                            user_id=user_data.get('id', user_id or 'unknown'),
                            full_name=user_data.get('full_name', ''),
                            is_verified=user_data.get('is_verified', False),
                            is_business=user_data.get('is_business_account', False),
                            is_private=user_data.get('is_private', False),
                            follower_count=user_data.get('edge_followed_by', {}).get('count', 0),
                            following_count=user_data.get('edge_follow', {}).get('count', 0),
                            media_count=user_data.get('edge_owner_to_timeline_media', {}).get('count', 0),
                            biography=user_data.get('biography', ''),
                            external_url=user_data.get('external_url'),
                            public_email=user_data.get('business_email'),
                            public_phone_number=user_data.get('business_phone_number'),
                            profile_pic_url=user_data.get('profile_pic_url_hd') or user_data.get('profile_pic_url'),
                        )
                        return APIResponse(data=user_info, error=None)
                except (json.JSONDecodeError, KeyError, IndexError) as e:
                    pass
            
            # Method 2: Extract from meta tags and visible text
            try:
                # Get follower count from meta tag
                followers_match = re.search(r'"edge_followed_by":\s*\{"count":\s*(\d+)\}', response.text)
                following_match = re.search(r'"edge_follow":\s*\{"count":\s*(\d+)\}', response.text)
                posts_match = re.search(r'"edge_owner_to_timeline_media":\s*\{"count":\s*(\d+)', response.text)
                
                # Get full name from meta tag
                full_name_match = re.search(r'<meta property="og:title" content="([^"]+)"', response.text)
                
                # Get bio from page
                bio_match = re.search(r'"biography":\s*"([^"]*)"', response.text)
                
                # Get profile pic
                profile_pic_match = re.search(r'"profile_pic_url_hd":\s*"([^"]+)"', response.text)
                if not profile_pic_match:
                    profile_pic_match = re.search(r'<meta property="og:image" content="([^"]+)"', response.text)
                
                # Get external URL
                ext_url_match = re.search(r'"external_url":\s*"([^"]*)"', response.text)
                
                # Get is_private and is_verified
                is_private_match = re.search(r'"is_private":\s*(true|false)', response.text)
                is_verified_match = re.search(r'"is_verified":\s*(true|false)', response.text)
                
                user_info = UserInfo(
                    username=username,
                    user_id=user_id or "unknown",
                    full_name=full_name_match.group(1).replace(f" (@{username})", "") if full_name_match else username,
                    is_verified=is_verified_match.group(1) == "true" if is_verified_match else False,
                    is_business=False,  # Can't determine without full data
                    is_private=is_private_match.group(1) == "true" if is_private_match else False,
                    follower_count=int(followers_match.group(1)) if followers_match else 0,
                    following_count=int(following_match.group(1)) if following_match else 0,
                    media_count=int(posts_match.group(1)) if posts_match else 0,
                    biography=bio_match.group(1) if bio_match else None,
                    external_url=ext_url_match.group(1) if ext_url_match and ext_url_match.group(1) else None,
                    public_email=None,
                    public_phone_number=None,
                    profile_pic_url=profile_pic_match.group(1) if profile_pic_match else None,
                )
                
                if user_info.follower_count > 0 or user_info.following_count > 0 or user_info.media_count > 0:
                    return APIResponse(data=user_info, error=None)
                    
            except Exception:
                pass
            
            # Basic fallback - profile exists but limited data
            user_info = UserInfo(
                username=username,
                user_id=user_id or "unknown",
                full_name=username,
                is_verified=False,
                is_business=False,
                is_private=False,
                follower_count=0,
                following_count=0,
                media_count=0,
                biography=None,
                external_url=None,
                public_email=None,
                public_phone_number=None,
                profile_pic_url=None,
            )
            return APIResponse(data=user_info, error="Limited data - public profile only")

        except Exception as e:
            return APIResponse(data=None, error=f"Could not fetch profile: {e}", rate_limited=False)

    def advanced_lookup(self, username: str) -> APIResponse:
        """
        Perform advanced user lookup to get obfuscated contact info.

        Args:
            username: Instagram username

        Returns:
            APIResponse with lookup data or error
        """
        data_dict = {
            "login_attempt_count": "0",
            "directly_sign_in": "true",
            "source": "default",
            "q": username,
            "ig_sig_key_version": self.SIG_KEY_VERSION,
        }
        data = self._generate_signature(json.dumps(data_dict))

        headers = {
            "Accept-Language": "en-US",
            "User-Agent": "Instagram 101.0.0.15.120",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Accept-Encoding": "gzip, deflate",
            "X-FB-HTTP-Engine": "Liger",
            "Connection": "close",
        }

        try:
            response = self._client.post(
                self.USERS_LOOKUP_URL, headers=headers, data=data
            )
            response.raise_for_status()
            result = response.json()

            if result.get("message") == "No users found":
                return APIResponse(
                    data=None, error="No users found", rate_limited=False
                )

            return APIResponse(data=result, error=None)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                return APIResponse(
                    data=None, error="Rate limit exceeded", rate_limited=True
                )
            return APIResponse(data=None, error=f"HTTP error: {e}", rate_limited=False)
        except json.JSONDecodeError:
            return APIResponse(data=None, error="Invalid JSON response", rate_limited=False)
        except Exception as e:
            return APIResponse(data=None, error=str(e), rate_limited=False)

    def get_user_media(self, user_id: str, count: int = 12) -> APIResponse:
        """
        Get user's recent media posts.

        Args:
            user_id: Instagram user ID
            count: Number of posts to fetch

        Returns:
            APIResponse with media list or error
        """
        try:
            response = self._client.get(
                f"{self.BASE_URL}/feed/user/{user_id}/",
                params={"count": count},
            )
            response.raise_for_status()
            data = response.json()

            items = data.get("items", [])
            media_list = []

            for item in items:
                media_info = {
                    "id": item.get("id"),
                    "code": item.get("code"),
                    "taken_at": item.get("taken_at"),
                    "like_count": item.get("like_count", 0),
                    "comment_count": item.get("comment_count", 0),
                    "caption": item.get("caption", {}).get("text", "") if item.get("caption") else "",
                    "media_type": item.get("media_type", 1),
                    "thumbnail_url": item.get("image_versions2", {}).get("candidates", [{}])[0].get("url"),
                }
                media_list.append(media_info)

            return APIResponse(data=media_list, error=None)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                return APIResponse(data=None, error="Rate limit exceeded", rate_limited=True)
            return APIResponse(data=None, error=f"HTTP error: {e}", rate_limited=False)
        except json.JSONDecodeError:
            return APIResponse(data=None, error="Invalid JSON response", rate_limited=False)
        except Exception as e:
            return APIResponse(data=None, error=str(e), rate_limited=False)

    def get_user_highlights(self, user_id: str) -> APIResponse:
        """
        Get user's story highlights.

        Args:
            user_id: Instagram user ID

        Returns:
            APIResponse with highlights list or error
        """
        try:
            response = self._client.get(
                f"{self.BASE_URL}/highlights/{user_id}/seen/"
            )
            response.raise_for_status()
            data = response.json()

            highlights = []
            for item in data.get("tray", []):
                highlight = {
                    "id": item.get("id"),
                    "title": item.get("title"),
                    "cover_url": item.get("cover_media", {}).get("cropped_image_version", {}).get("url"),
                    "media_count": item.get("media_count", 0),
                }
                highlights.append(highlight)

            return APIResponse(data=highlights, error=None)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                return APIResponse(data=None, error="Rate limit exceeded", rate_limited=True)
            return APIResponse(data=None, error=f"HTTP error: {e}", rate_limited=False)
        except Exception as e:
            return APIResponse(data=None, error=str(e), rate_limited=False)

    def get_related_profiles(self, user_id: str) -> APIResponse:
        """
        Get related/suggested profiles.

        Args:
            user_id: Instagram user ID

        Returns:
            APIResponse with related profiles or error
        """
        try:
            response = self._client.get(
                f"{self.BASE_URL}/feed/user/{user_id}/related/"
            )
            response.raise_for_status()
            data = response.json()

            related = []
            for item in data.get("related_profiles", []):
                profile = {
                    "username": item.get("username"),
                    "full_name": item.get("full_name"),
                    "is_verified": item.get("is_verified", False),
                    "is_private": item.get("is_private", False),
                    "follower_count": item.get("follower_count", 0),
                    "profile_pic_url": item.get("profile_pic_url"),
                }
                related.append(profile)

            return APIResponse(data=related, error=None)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                return APIResponse(data=None, error="Rate limit exceeded", rate_limited=True)
            return APIResponse(data=None, error=f"HTTP error: {e}", rate_limited=False)
        except Exception as e:
            return APIResponse(data=None, error=str(e), rate_limited=False)

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()
