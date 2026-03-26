import re

# Known package name → friendly name mapping
PACKAGE_NAMES = {
    "com.whatsapp":             "WhatsApp",
    "com.whatsapp.w4b":         "WhatsApp Business",
    "com.google.android.gm":    "Gmail",
    "com.google.android.apps.messaging": "Messages",
    "com.instagram.android":    "Instagram",
    "com.facebook.katana":      "Facebook",
    "com.facebook.orca":        "Messenger",
    "com.twitter.android":      "Twitter/X",
    "org.telegram.messenger":   "Telegram",
    "com.snapchat.android":     "Snapchat",
    "com.linkedin.android":     "LinkedIn",
    "com.spotify.music":        "Spotify",
    "com.amazon.mShop.android.shopping": "Amazon",
    "com.phonepe.app":          "PhonePe",
    "com.google.android.apps.tachyon": "Google Meet",
    "com.microsoft.teams":      "Teams",
    "com.slack":                "Slack",
}

# System packages to always ignore
IGNORED_PACKAGES = {
    "android",
    "com.android.systemui",
    "com.android.phone",
    "com.android.settings",
    "com.google.android.gms",
    "com.android.launcher3",
    "com.miui.home",
    "com.oneplus.launcher",
}


def _friendly_name(pkg_name: str) -> str:
    """Convert package name to human-readable app name"""
    if pkg_name in PACKAGE_NAMES:
        return PACKAGE_NAMES[pkg_name]
    # Fallback: take last segment and capitalize
    return pkg_name.split('.')[-1].replace('_', ' ').capitalize()


def clean_adb_notification(raw_dump: str) -> list:
    """
    Parses raw dumpsys notification output into a list of clean strings.
    Handles multiple Android version formats.
    """
    results = []

    # Split by NotificationRecord to isolate each notification block
    records = raw_dump.split('NotificationRecord(')[1:]

    for record in records:
        pkg_name = ""
        title = ""
        text = ""
        big_text = ""

        # --- Extract Package Name ---
        pkg_match = re.search(r'pkg=([\w\.]+)', record)
        if pkg_match:
            pkg_name = pkg_match.group(1)

        # Skip system/ignored packages
        if not pkg_name or pkg_name in IGNORED_PACKAGES:
            continue
        if any(record_pkg in record for record_pkg in ['pkg=android ', 'pkg=com.android.systemui']):
            continue

        # Skip if it's a foreground service notification (usually silent background stuff)
        if 'foregroundService' in record or 'isForegroundService=true' in record:
            continue

        # --- Extract Title ---
        # Try multiple patterns for different Android versions
        for pattern in [
            r'android\.title=String\s*\(([^)]+)\)',
            r'android\.title=String\s*\[([^\]]+)\]',
            r'android\.title=CharSequence\s*\(([^)]+)\)',
            r'android\.title=CharSequence\s*\[([^\]]+)\]',
            r'android\.title=SpannableString\s*\(([^)]+)\)',
            r'android\.title=SpannableString\s*\[([^\]]+)\]',
            r'android\.title=([^\n,}]+)',
        ]:
            m = re.search(pattern, record)
            if m:
                title = m.group(1).strip().strip('"').strip("'")
                if title.lower() != 'null':
                    break
                title = ""

        # --- Extract Text ---
        for pattern in [
            r'android\.text=String\s*\(([^)]+)\)',
            r'android\.text=String\s*\[([^\]]+)\]',
            r'android\.text=CharSequence\s*\(([^)]+)\)',
            r'android\.text=CharSequence\s*\[([^\]]+)\]',
            r'android\.text=SpannableString\s*\(([^)]+)\)',
            r'android\.text=SpannableString\s*\[([^\]]+)\]',
            r'android\.text=([^\n,}]+)',
        ]:
            m = re.search(pattern, record)
            if m:
                text = m.group(1).strip().strip('"').strip("'")
                if text.lower() != 'null':
                    break
                text = ""

        # --- Extract BigText (longer messages) ---
        for pattern in [
            r'android\.bigText=String\s*\(([^)]{10,})\)',
            r'android\.bigText=String\s*\[([^\]]{10,})\]',
        ]:
            m = re.search(pattern, record)
            if m:
                big_text = m.group(1).strip()
                break

        # Use bigText over text if it's more informative
        final_text = big_text if big_text and len(big_text) > len(text) else text

        # Skip if both are null or empty after extraction
        if not title and not final_text:
            continue
        if title.lower() == 'null' and (not final_text or final_text.lower() == 'null'):
            continue

        # Build the clean notification string
        app = _friendly_name(pkg_name)
        notif = f"{app}"
        if title:
            notif += f" | {title}"
        if final_text:
            notif += f": {final_text}"

        results.append(notif)

    return results