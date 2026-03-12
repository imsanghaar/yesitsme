"""Utility functions for yesitsme."""

import csv
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from bs4 import BeautifulSoup

from api import UserInfo


def dumpor_search(name: str, timeout: int = 10) -> Dict[str, Any]:
    """
    Search for Instagram usernames using dumpor.com.

    Args:
        name: Name to search for
        timeout: Request timeout in seconds

    Returns:
        Dictionary with usernames list or error
    """
    url = f"https://dumpor.com/search?query={name.replace(' ', '+')}"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/39.0.2171.95 Safari/537.36"
        )
    }

    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        accounts = soup.findAll("a", {"class": "profile-name-link"})

        account_list = [account.text for account in accounts]
        return {"usernames": account_list, "error": None}

    except requests.exceptions.RequestException as e:
        return {"usernames": None, "error": f"Request failed: {e}"}
    except Exception as e:
        return {"usernames": None, "error": str(e)}


def search_username_direct(username: str, timeout: int = 10) -> Dict[str, Any]:
    """
    Search for a specific username directly.

    Args:
        username: Instagram username to search
        timeout: Request timeout in seconds

    Returns:
        Dictionary with search results or error
    """
    url = f"https://dumpor.com/v/{username}"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/39.0.2171.95 Safari/537.36"
        )
    }

    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()

        if response.status_code == 200:
            return {"found": True, "error": None}
        return {"found": False, "error": None}

    except requests.exceptions.RequestException:
        return {"found": False, "error": "Request failed"}
    except Exception as e:
        return {"found": False, "error": str(e)}


def match_email(provided: str, public: Optional[str]) -> bool:
    """
    Check if provided email matches public/obfuscated email.

    Args:
        provided: Email provided by user (may be partial)
        public: Public or obfuscated email from API

    Returns:
        True if emails match based on available information
    """
    if not public or not provided or provided.strip() == "":
        return False

    provided = provided.strip()
    public = public.strip()

    try:
        if len(provided) < 2 or len(public) < 2:
            return False

        prov_parts = provided.split("@")
        pub_parts = public.split("@")

        if len(prov_parts) != 2 or len(pub_parts) != 2:
            return False

        prov_local, prov_domain = prov_parts
        pub_local, pub_domain = pub_parts

        domains_match = prov_domain.lower() == pub_domain.lower()
        first_char_match = prov_local[0].lower() == pub_local[0].lower()
        last_char_match = prov_local[-1].lower() == pub_local[-1].lower()

        return domains_match and first_char_match and last_char_match

    except (IndexError, AttributeError):
        return False


def match_phone(provided: str, public: Optional[str]) -> bool:
    """
    Check if provided phone number matches public/obfuscated phone.

    Args:
        provided: Phone number provided by user (may be partial)
        public: Public or obfuscated phone from API

    Returns:
        True if phone numbers match based on available information
    """
    if not public or not provided or provided.strip() == "":
        return False

    provided = provided.strip()
    public = str(public).strip()

    try:
        prov_digits = re.sub(r"\D", "", provided)
        pub_digits = re.sub(r"\D", "", public)

        if len(prov_digits) < 2 or len(pub_digits) < 2:
            return False

        area_code_match = prov_digits[:3] == pub_digits[:3]
        last_two_match = prov_digits[-2:] == pub_digits[-2:]

        return area_code_match and last_two_match

    except (IndexError, AttributeError):
        return False


def match_name(provided: str, full_name: str) -> bool:
    """
    Check if provided name matches full name.

    Args:
        provided: Name provided by user
        full_name: Full name from API

    Returns:
        True if names match (case-insensitive)
    """
    if not provided or not full_name:
        return False

    return provided.strip().lower() == full_name.strip().lower()


def calculate_match_level(
    name_match: bool, email_match: bool, phone_match: bool
) -> tuple[str, int]:
    """
    Calculate match level based on individual match results.

    Args:
        name_match: Whether name matched
        email_match: Whether email matched
        phone_match: Whether phone matched

    Returns:
        Tuple of (level_string, match_count)
    """
    match_count = sum([name_match, email_match, phone_match])

    if match_count == 3:
        return ("HIGH", match_count)
    elif match_count == 2:
        return ("MEDIUM", match_count)
    elif match_count == 1:
        return ("LOW", match_count)
    else:
        return ("NONE", match_count)


def export_to_json(
    results: List[Dict[str, Any]], output_path: str
) -> bool:
    """
    Export search results to JSON file.

    Args:
        results: List of result dictionaries
        output_path: Path to output file

    Returns:
        True if successful, False otherwise
    """
    try:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        export_data = {
            "timestamp": datetime.now().isoformat(),
            "results": results,
        }

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)

        return True

    except Exception as e:
        print(f"Error exporting to JSON: {e}")
        return False


def export_to_csv(
    results: List[Dict[str, Any]], output_path: str
) -> bool:
    """
    Export search results to CSV file.

    Args:
        results: List of result dictionaries
        output_path: Path to output file

    Returns:
        True if successful, False otherwise
    """
    try:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        if not results:
            return False

        fieldnames = [
            "username",
            "user_id",
            "full_name",
            "is_verified",
            "is_private",
            "is_business",
            "follower_count",
            "following_count",
            "media_count",
            "public_email",
            "public_phone",
            "obfuscated_email",
            "obfuscated_phone",
            "match_level",
            "profile_pic_url",
        ]

        with open(output_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for result in results:
                row = {
                    "username": result.get("username", ""),
                    "user_id": result.get("user_id", ""),
                    "full_name": result.get("full_name", ""),
                    "is_verified": result.get("is_verified", False),
                    "is_private": result.get("is_private", False),
                    "is_business": result.get("is_business", False),
                    "follower_count": result.get("follower_count", 0),
                    "following_count": result.get("following_count", 0),
                    "media_count": result.get("media_count", 0),
                    "public_email": result.get("public_email", ""),
                    "public_phone": result.get("public_phone", ""),
                    "obfuscated_email": result.get("obfuscated_email", ""),
                    "obfuscated_phone": result.get("obfuscated_phone", ""),
                    "match_level": result.get("match_level", ""),
                    "profile_pic_url": result.get("profile_pic_url", ""),
                }
                writer.writerow(row)

        return True

    except Exception as e:
        print(f"Error exporting to CSV: {e}")
        return False


def format_user_info(user_info: UserInfo) -> str:
    """
    Format user info for display.

    Args:
        user_info: UserInfo object

    Returns:
        Formatted string representation
    """
    lines = [
        f"Username: {user_info.username}",
        f"User ID: {user_info.user_id}",
        f"Full Name: {user_info.full_name}",
        f"Verified: {user_info.is_verified}",
        f"Business Account: {user_info.is_business}",
        f"Private Account: {user_info.is_private}",
        f"Followers: {user_info.follower_count}",
        f"Following: {user_info.following_count}",
        f"Posts: {user_info.media_count}",
    ]

    if user_info.external_url:
        lines.append(f"External URL: {user_info.external_url}")
    if user_info.biography:
        lines.append(f"Biography: {user_info.biography}")
    if user_info.public_email:
        lines.append(f"Public Email: {user_info.public_email}")
    if user_info.public_phone_number:
        lines.append(f"Public Phone: {user_info.public_phone_number}")
    if user_info.profile_pic_url:
        lines.append(f"Profile Picture: {user_info.profile_pic_url}")

    return "\n".join(lines)


def export_profile_json(profile_data: Dict[str, Any], output_path: str) -> bool:
    """
    Export complete profile data to JSON.

    Args:
        profile_data: Complete profile dictionary
        output_path: Path to output file

    Returns:
        True if successful
    """
    try:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        export_data = {
            "timestamp": datetime.now().isoformat(),
            "profile": profile_data,
        }

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)

        return True
    except Exception as e:
        print(f"Error exporting profile: {e}")
        return False


def format_media_posts(media_list: List[Dict]) -> str:
    """
    Format media posts for display.

    Args:
        media_list: List of media post dictionaries

    Returns:
        Formatted string
    """
    if not media_list:
        return "No recent posts"

    lines = []
    for i, post in enumerate(media_list[:6], 1):
        lines.append(f"\n  [cyan]Post {i}[/cyan]:")
        lines.append(f"    Likes: {post.get('like_count', 0)}")
        lines.append(f"    Comments: {post.get('comment_count', 0)}")
        caption = post.get('caption', '')
        if caption:
            caption_text = caption[:100] + "..." if len(caption) > 100 else caption
            lines.append(f"    Caption: {caption_text}")

    return "\n".join(lines)
