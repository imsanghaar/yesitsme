#!/usr/bin/env python3
"""
yesitsme - Instagram OSINT Tool

Simple OSINT script to find Instagram profiles by name and e-mail/phone.
"""

import argparse
import os
import sys
import time
from typing import List, Optional

from colorama import Fore, Style, init
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.table import Table
from rich.prompt import Confirm
from rich.markdown import Markdown
from rich.text import Text
from rich import box

from api import InstagramAPI, UserInfo
from config import Config
from utils import (
    dumpor_search,
    match_email,
    match_name,
    match_phone,
    calculate_match_level,
    export_to_json,
    export_to_csv,
    export_profile_json,
    format_media_posts,
)

init(autoreset=True)
console = Console()


def banner() -> None:
    """Display application banner."""
    banner_text = r"""
╔═══════════════════════════════════════════════════════════╗
║    _  _ ___ ___ (_) |_( )___  _ __  ___                   ║
║   | || / -_|_-< | |  _|/(_-< | '  \/ -_)                  ║
║    \_, \___/__/ |_|\__| /__/ |_|_|_\___|                  ║
║    |__/                 Instagram OSINT Tool              ║
╚═══════════════════════════════════════════════════════════╝
    """
    console.print(Panel(
        Text(banner_text, style="bold magenta"),
        border_style="bright_magenta",
        padding=(0, 0),
    ))
    console.print(f"\n[dim]Maintained by [link=https://github.com/imsanghaar]@imsanghaar[/link] | v2.0[/dim]\n")


def create_match_table(
    username: str,
    user_info: UserInfo,
    name_match: bool,
    email_match: bool,
    phone_match: bool,
    match_level: str,
) -> Table:
    """
    Create a rich table for displaying user information.

    Args:
        username: Instagram username
        user_info: UserInfo object
        name_match: Whether name matched
        email_match: Whether email matched
        phone_match: Whether phone matched
        match_level: Match level string

    Returns:
        Rich Table object
    """
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="white")

    checkmark = Fore.GREEN + " ✓" + Style.RESET_ALL

    table.add_row("Username", username)
    table.add_row("User ID", user_info.user_id)

    name_display = user_info.full_name
    if name_match:
        name_display += checkmark
    table.add_row("Full Name", name_display)

    table.add_row("Verified", str(user_info.is_verified))
    table.add_row("Business Account", str(user_info.is_business))
    table.add_row("Private Account", str(user_info.is_private))
    table.add_row("Followers", str(user_info.follower_count))
    table.add_row("Following", str(user_info.following_count))
    table.add_row("Posts", str(user_info.media_count))

    if user_info.external_url:
        table.add_row("External URL", user_info.external_url)
    if user_info.biography:
        table.add_row("Biography", user_info.biography)
    if user_info.public_email:
        email_display = user_info.public_email
        if email_match:
            email_display += checkmark
        table.add_row("Public Email", email_display)
    if user_info.public_phone_number:
        phone_display = str(user_info.public_phone_number)
        if phone_match:
            phone_display += checkmark
        table.add_row("Public Phone", phone_display)

    return table


def display_result(
    user_info: UserInfo,
    name_match: bool,
    email_match: bool,
    phone_match: bool,
    match_level: str,
    match_count: int,
    obfuscated_email: Optional[str] = None,
    obfuscated_phone: Optional[str] = None,
) -> None:
    """
    Display search result with rich formatting.

    Args:
        user_info: UserInfo object
        name_match: Whether name matched
        email_match: Whether email matched
        phone_match: Whether phone matched
        match_level: Match level string
        match_count: Number of matches
        obfuscated_email: Obfuscated email from advanced lookup
        obfuscated_phone: Obfuscated phone from advanced lookup
    """
    # Color based on match level
    level_colors = {
        "HIGH": "bold green",
        "MEDIUM": "bold yellow",
        "LOW": "bold red",
        "NONE": "white",
    }
    level_emojis = {
        "HIGH": "🎯",
        "MEDIUM": "🎪",
        "LOW": "🔎",
        "NONE": "❓",
    }

    color = level_colors.get(match_level, "white")
    emoji = level_emojis.get(match_level, "")

    # Profile header
    console.print(Panel(
        Text(f"👤 @{user_info.username}", style="bold white"),
        subtitle=f"User ID: {user_info.user_id}",
        border_style="cyan",
        padding=(0, 2),
    ))

    # Info table
    table = Table(
        box=box.SIMPLE,
        show_header=False,
        padding=(0, 2),
    )
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="white")

    checkmark = "[green] ✓[/green]"

    # Name with match indicator
    name_display = user_info.full_name
    if name_match:
        name_display += f" [green]{checkmark}[/green]"
    table.add_row("Full Name", name_display)

    # Stats
    table.add_row("Stats", f"👥 {user_info.follower_count:,} followers • 📝 {user_info.media_count:,} posts")

    # Badges
    badges = []
    if user_info.is_verified:
        badges.append("[green]✅ Verified[/green]")
    if user_info.is_business:
        badges.append("[blue]💼 Business[/blue]")
    if user_info.is_private:
        badges.append("[red]🔒 Private[/red]")
    table.add_row("Badges", " ".join(badges) if badges else "None")

    # Contact info
    if user_info.public_email:
        email_display = user_info.public_email
        if email_match:
            email_display += f" [green]{checkmark}[/green]"
        table.add_row("Email", f"📧 {email_display}")

    if user_info.public_phone_number:
        phone_display = str(user_info.public_phone_number)
        if phone_match:
            phone_display += f" [green]{checkmark}[/green]"
        table.add_row("Phone", f"📱 {phone_display}")

    # Obfuscated data
    if obfuscated_email:
        email_display = obfuscated_email
        if email_match:
            email_display += f" [green]{checkmark}[/green]"
        table.add_row("Obfuscated Email", f"📩 {email_display}")

    if obfuscated_phone:
        phone_display = obfuscated_phone
        if phone_match:
            phone_display += f" [green]{checkmark}[/green]"
        table.add_row("Obfuscated Phone", f"📱 {phone_display}")

    console.print(table)

    # Match level panel
    match_panel = Panel(
        Text(f"{emoji} Profile match level: {match_level}", style=color),
        title="🎯 Match Result",
        border_style="green" if match_level == "HIGH" else "yellow" if match_level == "MEDIUM" else "red",
    )
    console.print(match_panel)


def display_full_profile(
    user_info: UserInfo,
    media: Optional[List[Dict]] = None,
    highlights: Optional[List[Dict]] = None,
    related: Optional[List[Dict]] = None,
) -> None:
    """
    Display complete profile information.

    Args:
        user_info: UserInfo object
        media: List of recent media posts
        highlights: List of story highlights
        related: List of related profiles
    """
    # Header panel with username
    header_style = "bold white on blue"
    console.print(Panel(
        Text(f"📸 @{user_info.username}", style="bold white"),
        subtitle="Instagram Profile",
        border_style="bright_blue",
        padding=(1, 2),
    ))

    # Main info table
    info_table = Table(
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
        border_style="bright_cyan",
        padding=(0, 2),
    )
    info_table.add_column("📋 Property", style="bold cyan", width=20)
    info_table.add_column("Value", style="white", width=50)

    # Verification badges
    verified_badge = " ✅ Verified" if user_info.is_verified else ""
    business_badge = " 💼 Business" if user_info.is_business else ""
    private_badge = " 🔒 Private" if user_info.is_private else ""

    info_table.add_row("👤 Full Name", f"{user_info.full_name}{verified_badge}")
    info_table.add_row("🆔 User ID", f"[dim]{user_info.user_id}[/dim]")
    info_table.add_row("📊 Stats", f"👥 {user_info.follower_count:,} followers • {user_info.following_count:,} following • 📝 {user_info.media_count:,} posts")
    info_table.add_row("🏷️  Tags", f"{verified_badge}{business_badge}{private_badge}" if any([user_info.is_verified, user_info.is_business, user_info.is_private]) else "None")

    if user_info.biography:
        bio_text = user_info.biography[:200] + "..." if len(user_info.biography) > 200 else user_info.biography
        info_table.add_row("📖 Biography", bio_text)

    if user_info.external_url:
        info_table.add_row("🌐 Website", f"[link={user_info.external_url}]{user_info.external_url}[/link]")

    if user_info.public_email:
        info_table.add_row("📧 Public Email", f"📩 {user_info.public_email}")

    if user_info.public_phone_number:
        info_table.add_row("📱 Public Phone", f"📞 {user_info.public_phone_number}")

    console.print(info_table)

    # Profile picture
    if user_info.profile_pic_url:
        console.print(Panel(
            f"[link={user_info.profile_pic_url}]🖼️  [blue]{user_info.profile_pic_url}[/blue][/link]",
            title="Profile Picture",
            border_style="green",
            padding=(1, 2),
        ))

    # Recent posts section
    if media:
        console.print(Panel(
            "[bold green]📷 Recent Posts[/bold green]",
            border_style="bright_green",
        ))
        media_table = Table(
            box=box.SIMPLE,
            show_header=True,
            header_style="bold green",
            border_style="green",
        )
        media_table.add_column("#", style="dim", width=4)
        media_table.add_column("❤️ Likes", justify="right", width=12)
        media_table.add_column("💬 Comments", justify="right", width=12)
        media_table.add_column("📝 Caption", overflow="ellipsis", width=60)

        for i, post in enumerate(media[:6], 1):
            caption = post.get("caption", "") or "[no caption]"
            caption = caption.replace("\n", " ")[:58]
            media_table.add_row(
                f"[cyan]{i}[/cyan]",
                f"[yellow]{post.get('like_count', 0):,}[/yellow]",
                f"[blue]{post.get('comment_count', 0):,}[/blue]",
                f"[dim]{caption}[/dim]",
            )
        console.print(media_table)

    # Story highlights section
    if highlights:
        console.print(Panel(
            "[bold magenta]⭐ Story Highlights[/bold magenta]",
            border_style="bright_magenta",
        ))
        highlights_text = ""
        for hl in highlights:
            highlights_text += f"  📁 [cyan]{hl.get('title', 'Untitled')}[/cyan] [dim]({hl.get('media_count', 0)} items)[/dim]\n"
        console.print(Panel(highlights_text, border_style="magenta", padding=(1, 2)))

    # Related profiles section
    if related:
        console.print(Panel(
            "[bold yellow]👥 Related Profiles[/bold yellow]",
            border_style="bright_yellow",
        ))
        related_table = Table(
            box=box.SIMPLE,
            show_header=True,
            header_style="bold yellow",
            border_style="yellow",
        )
        related_table.add_column("Username", style="bold green", width=25)
        related_table.add_column("Name", width=30)
        related_table.add_column("Followers", justify="right", width=15)
        related_table.add_column("Verified", width=10)

        for profile in related[:5]:
            verified_icon = "✅" if profile.get('is_verified') else ""
            related_table.add_row(
                f"[@{profile.get('username', '')}](https://instagram.com/{profile.get('username', '')})",
                profile.get('full_name', '')[:28],
                f"[cyan]{profile.get('follower_count', 0):,}[/cyan]",
                verified_icon,
            )
        console.print(related_table)


def export_results(
    results: List[dict], export_format: str, output_dir: str
) -> None:
    """
    Export results to file.

    Args:
        results: List of result dictionaries
        export_format: Export format (json or csv)
        output_dir: Output directory
    """
    timestamp = time.strftime("%Y%m%d_%H%M%S")

    if export_format.lower() == "json":
        output_path = f"{output_dir}/yesitsme_results_{timestamp}.json"
        if export_to_json(results, output_path):
            console.print(
                f"[green]Results exported to {output_path}[/green]"
            )
    elif export_format.lower() == "csv":
        output_path = f"{output_dir}/yesitsme_results_{timestamp}.csv"
        if export_to_csv(results, output_path):
            console.print(
                f"[green]Results exported to {output_path}[/green]"
            )


def lookup_profile(username: str, api: InstagramAPI, export: bool, output_dir: str) -> None:
    """
    Lookup a single username and display all details.

    Args:
        username: Instagram username
        api: InstagramAPI instance
        export: Whether to export results
        output_dir: Output directory for exports
    """
    console.print(f"\n[bold cyan]🔍 Looking up profile:[/bold cyan] [green]@{username}[/green]\n")

    # Fetch user info with spinner
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        console=console,
    ) as progress:
        task1 = progress.add_task("Fetching profile info...", total=1)
        user_response = api.get_user_info(username)
        progress.update(task1, advance=1)

        if user_response.error and "not found" in user_response.error.lower():
            console.print(f"[red]❌ Error: Profile not found or private[/red]")
            return

        user_info = user_response.data

        media = None
        highlights = None
        related = None

        # Only fetch additional data if we have user_id
        if user_info and user_info.user_id and user_info.user_id != "unknown":
            task2 = progress.add_task("Fetching recent posts...", total=1)
            media_response = api.get_user_media(user_info.user_id, count=12)
            if not media_response.error and media_response.data:
                media = media_response.data
                # Update media count if we got posts but count was 0
                if media and user_info.media_count == 0:
                    user_info.media_count = len(media)
            progress.update(task2, advance=1)

            task3 = progress.add_task("Fetching story highlights...", total=1)
            highlights_response = api.get_user_highlights(user_info.user_id)
            if not highlights_response.error:
                highlights = highlights_response.data
            progress.update(task3, advance=1)

            task4 = progress.add_task("Finding related profiles...", total=1)
            related_response = api.get_related_profiles(user_info.user_id)
            if not related_response.error:
                related = related_response.data
            progress.update(task4, advance=1)

    console.print()
    
    if user_info:
        display_full_profile(user_info, media, highlights, related)
        
        # Show helpful message about data limitations
        if user_info.follower_count == 0 and user_info.following_count == 0:
            console.print(Panel(
                "[yellow]⚠️  Follower/Following counts are restricted by Instagram for public access.\n\n"
                "For complete data, use a session ID:\n"
                "[green]python yesitsme.py -s YOUR_SESSION_ID -u username[/green]",
                title="Data Limitation",
                border_style="yellow",
                padding=(1, 2),
            ))
        
        if user_response.error:
            console.print(f"\n[yellow]⚠️  Note: {user_response.error}[/yellow]")

        if export and user_info.user_id != "unknown":
            profile_data = {
                "username": user_info.username,
                "user_id": user_info.user_id,
                "full_name": user_info.full_name,
                "is_verified": user_info.is_verified,
                "is_private": user_info.is_private,
                "is_business": user_info.is_business,
                "follower_count": user_info.follower_count,
                "following_count": user_info.following_count,
                "media_count": user_info.media_count,
                "biography": user_info.biography,
                "external_url": user_info.external_url,
                "public_email": user_info.public_email,
                "public_phone": str(user_info.public_phone_number) if user_info.public_phone_number else None,
                "profile_pic_url": user_info.profile_pic_url,
                "recent_posts": media or [],
                "highlights": highlights or [],
                "related_profiles": related or [],
            }

            from utils import export_profile_json
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            output_path = f"{output_dir}/profile_{username}_{timestamp}.json"

            if export_profile_json(profile_data, output_path):
                console.print(f"\n[green]✅ Profile exported to {output_path}[/green]")
        elif export:
            console.print("[yellow]⚠️  Export skipped - limited data available[/yellow]")
    else:
        console.print("[red]❌ Could not retrieve profile data[/red]")


def main() -> None:
    """Main entry point."""
    banner()

    parser = argparse.ArgumentParser(
        description="Find Instagram profiles by name and e-mail/phone"
    )

    parser.add_argument(
        "-u", "--username",
        help="Lookup a specific username",
        required=False,
    )
    parser.add_argument(
        "-s", "--session-id",
        help="Instagram session ID (or set INSTAGRAM_SESSION_ID env var)",
        required=False,
    )
    parser.add_argument(
        "-n", "--name", help="Target name & surname (for advanced search)", required=False
    )
    parser.add_argument(
        "-e", "--email", help="Target email - partial ok (for advanced search)", required=False
    )
    parser.add_argument(
        "-p", "--phone", help="Target phone - partial ok (for advanced search)", required=False
    )
    parser.add_argument(
        "-t",
        "--timeout",
        help="Timeout between requests (seconds)",
        type=int,
        default=None,
    )
    parser.add_argument(
        "--proxy",
        help="Proxy URL (e.g., http://user:pass@host:port)",
        default=None,
    )
    parser.add_argument(
        "--export",
        choices=["json", "csv", "none"],
        default="json",
        help="Export format (default: json)",
    )
    parser.add_argument(
        "--output-dir",
        default="output",
        help="Output directory for exports (default: output)",
    )
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Path to config file (default: config.yaml)",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Verbose output"
    )
    parser.add_argument(
        "--media-count",
        type=int,
        default=12,
        help="Number of recent posts to fetch (default: 12)",
    )

    args = parser.parse_args()

    config = Config.load(args.config)

    session_id = args.session_id or config.session_id or os.getenv("INSTAGRAM_SESSION_ID")

    if args.username:
        # Username lookup mode - session ID is now required for accurate data
        if not session_id:
            console.print(
                "[red]❌ Session ID required for accurate data![/red]\n"
                "[cyan]Why? Instagram restricts follower/following counts for public access.[/cyan]\n\n"
                "[cyan]Set it one of these ways:[/cyan]\n"
                "  1. [green]set INSTAGRAM_SESSION_ID=your_id[/green] (Windows)\n"
                "  2. [green]export INSTAGRAM_SESSION_ID=your_id[/green] (Linux/Mac)\n"
                "  3. [green]python yesitsme.py -s your_id -u username[/green]\n"
                "\n[dim]To get your session ID:[/dim]\n"
                "  1. Log in to Instagram in your browser\n"
                "  2. Open DevTools (F12) → Storage/Application tab\n"
                "  3. Find cookies for instagram.com\n"
                "  4. Copy the 'sessionid' value"
            )
            sys.exit(1)

        api = InstagramAPI(
            session_id=session_id,
            proxy=args.proxy or config.proxy,
            max_retries=config.max_retries,
            retry_delay=config.retry_delay,
        )

        try:
            lookup_profile(args.username, api, args.export != "none", args.output_dir)
        except KeyboardInterrupt:
            console.print("\n[yellow]Lookup interrupted by user[/yellow]")
        finally:
            api.close()
        return

    if not args.name or not args.email or not args.phone:
        console.print("[red]Error: For advanced search, -n, -e, and -p are required[/red]")
        console.print("\n[cyan]Usage examples:[/cyan]")
        console.print("  [green]python yesitsme.py -u username[/green]  - Lookup a username (no session needed)")
        console.print("  [green]python yesitsme.py -n \"Name\" -e \"email@test.com\" -p \"+1234567890\" -s SESSION_ID[/green] - Advanced search")
        sys.exit(1)

    # Advanced search requires session ID
    if not session_id:
        console.print(
            "[red]❌ Error: Session ID required for advanced search![/red]\n"
            "[cyan]Set it one of these ways:[/cyan]\n"
            "  1. [green]set INSTAGRAM_SESSION_ID=your_id[/green] (Windows)\n"
            "  2. [green]export INSTAGRAM_SESSION_ID=your_id[/green] (Linux/Mac)\n"
            "  3. [green]python yesitsme.py -s your_id -n \"Name\" -e \"email\" -p \"phone\"[/green]\n"
        )
        sys.exit(1)

    timeout = args.timeout if args.timeout is not None else config.timeout
    proxy = args.proxy or config.proxy
    export_format = args.export
    output_dir = args.output_dir

    console.print(Panel(
        f"[bold]🎯 Target:[/bold] {args.name}\n"
        f"[bold]📧 Email pattern:[/bold] {args.email}\n"
        f"[bold]📱 Phone pattern:[/bold] {args.phone}",
        title="Search Parameters",
        border_style="cyan",
        padding=(1, 2),
    ))

    api = InstagramAPI(
        session_id=session_id,
        proxy=proxy,
        max_retries=config.max_retries,
        retry_delay=config.retry_delay,
    )

    try:
        # Search dumpor.com
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            search_task = progress.add_task("Searching dumpor.com...", total=1)
            console.print("[cyan]Searching for usernames...[/cyan]")
            dumpor_result = dumpor_search(args.name)
            progress.update(search_task, advance=1)

        if dumpor_result["error"]:
            console.print(f"[red]❌ Error: {dumpor_result['error']}[/red]")
            sys.exit(1)

        usernames = dumpor_result.get("usernames", [])
        if not usernames:
            console.print("[yellow]⚠️  No usernames found[/yellow]")
            sys.exit(0)

        console.print(f"[green]✅ Found {len(usernames)} potential matches[/green]\n")

        results = []
        stop_search = False

        # Progress bar for username processing
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console,
        ) as progress:
            search_progress = progress.add_task("Processing profiles...", total=len(usernames))

            for idx, username in enumerate(usernames, 1):
                if stop_search:
                    break

                username_clean = username[1:]
                progress.update(search_progress, description=f"[cyan]Checking {idx}/{len(usernames)}: @{username_clean}[/cyan]")

                name_match_flag, email_match_flag, phone_match_flag = False, False, False

                user_response = api.get_user_info(username_clean)
                if user_response.error:
                    console.print(f"[red]❌ Error: {user_response.error}[/red]")
                    if user_response.rate_limited:
                        console.print("[yellow]⏳ Rate limited. Waiting 60 seconds...[/yellow]")
                        time.sleep(60)
                    progress.advance(search_progress)
                    continue

                user_info = user_response.data

                name_match_flag = match_name(args.name, user_info.full_name)

                if user_info.public_email:
                    email_match_flag = match_email(args.email, user_info.public_email)

                if user_info.public_phone_number:
                    phone_match_flag = match_phone(
                        args.phone, str(user_info.public_phone_number)
                    )

                obfuscated_email = None
                obfuscated_phone = None

                lookup_response = api.advanced_lookup(username_clean)
                if lookup_response.error:
                    if lookup_response.rate_limited:
                        console.print("[yellow]⏳ Rate limited on advanced lookup. Waiting 60 seconds...[/yellow]")
                        time.sleep(60)
                else:
                    lookup_data = lookup_response.data
                    obfuscated_email = lookup_data.get("obfuscated_email")
                    obfuscated_phone = lookup_data.get("obfuscated_phone")

                    if obfuscated_email and not email_match_flag:
                        email_match_flag = match_email(args.email, obfuscated_email)

                    if obfuscated_phone and not phone_match_flag:
                        phone_match_flag = match_phone(
                            args.phone, str(obfuscated_phone)
                        )

                match_level, match_count = calculate_match_level(
                    name_match_flag, email_match_flag, phone_match_flag
                )

                display_result(
                    user_info=user_info,
                    name_match=name_match_flag,
                    email_match=email_match_flag,
                    phone_match=phone_match_flag,
                    match_level=match_level,
                    match_count=match_count,
                    obfuscated_email=obfuscated_email,
                    obfuscated_phone=obfuscated_phone,
                )

                result_dict = {
                    "username": user_info.username,
                    "user_id": user_info.user_id,
                    "full_name": user_info.full_name,
                    "is_verified": user_info.is_verified,
                    "is_private": user_info.is_private,
                    "is_business": user_info.is_business,
                    "follower_count": user_info.follower_count,
                    "following_count": user_info.following_count,
                    "media_count": user_info.media_count,
                    "public_email": user_info.public_email or "",
                    "public_phone": str(user_info.public_phone_number or ""),
                    "obfuscated_email": obfuscated_email or "",
                    "obfuscated_phone": obfuscated_phone or "",
                    "match_level": match_level,
                    "match_count": match_count,
                    "profile_pic_url": user_info.profile_pic_url or "",
                }
                results.append(result_dict)

                if match_count == 3:
                    if Confirm.ask(
                        "\n[green]🎯 High match found! Stop searching?[/green]", default=True
                    ):
                        stop_search = True
                elif match_count == 2:
                    console.print("[yellow]⚠️  Medium match - consider investigating further[/yellow]")

                console.print("-" * 50)
                progress.advance(search_progress)

                if timeout and not stop_search:
                    time.sleep(timeout)

        if results and export_format != "none":
            export_results(results, export_format, output_dir)

        console.print(
            f"\n[bold green]✅ Search complete. Found {len(results)} profiles.[/bold green]"
        )

    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️  Search interrupted by user[/yellow]")
        sys.exit(0)
    finally:
        api.close()


if __name__ == "__main__":
    main()
