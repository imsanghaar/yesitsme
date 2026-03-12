<p align="center">
    <img src="https://github.com/blackeko/yesitsme/blob/media/logo.png" alt="yesitsme logo">
</p>

<h3 align="center">Yes, it's me!</h3>
<p align="center">
   Advanced Instagram OSINT Tool - Find Instagram profiles by username, name, e-mail, and phone even if they are locked. 
</p>

<p align="center">
    <a href="https://github.com/imsanghaar/yesitsme"><img src="https://img.shields.io/badge/version-2.0-blue.svg" alt="Version"></a>
    <a href="https://github.com/imsanghaar/yesitsme"><img src="https://img.shields.io/badge/maintainer-imsanghaar-green.svg" alt="Maintainer"></a>
    <a href="https://github.com/imsanghaar/yesitsme/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-red.svg" alt="License"></a>
</p>

<p align="center">
    <strong>Maintained by <a href="https://github.com/imsanghaar">@imsanghaar</a></strong>
</p>

---

## 📋 Overview

**yesitsme** is a Python-based OSINT tool that searches for Instagram accounts associated with a specific name, e-mail, and phone number. It leverages dumpor.com indexing capabilities and Instagram's API to retrieve and match user information, saving time during online investigations.

### ✨ New Features (v2.0)

- 🔄 **Automatic retry logic** with exponential backoff
- 🛡️ **Rate limit detection** and automatic cooldown
- 🌐 **Proxy support** for anonymity
- 📁 **JSON/CSV export** for results
- ⚙️ **Configuration file** and environment variable support
- 🎨 **Rich terminal UI** with tables and panels
- 🔍 **Improved matching algorithms** for email/phone
- 📦 **Modular architecture** for easier maintenance

---

## ⚙️ Installation

### Prerequisites

- Python 3.8+
- pip

### Setup

```console
# Clone the repository
git clone https://github.com/imsanghaar/yesitsme/
cd yesitsme

# Install dependencies
pip3 install -r requirements.txt

# Copy environment example and configure
cp .env.example .env
# Edit .env and add your INSTAGRAM_SESSION_ID

# (Optional) Copy config example
cp config.example.yaml config.yaml
```

---

## 🚀 Quick Start

### Simple Mode - Lookup by Username (Session Required)

Get complete profile data including exact follower/following counts:

```console
python yesitsme.py -u username
```

With session ID:

```console
# Windows
set INSTAGRAM_SESSION_ID=your_session_id
python yesitsme.py -u imsanghaar

# Or pass directly
python yesitsme.py -s YOUR_SESSION_ID -u imsanghaar
```

### Advanced Mode - Search by Name/Email/Phone

```console
python yesitsme.py -s YOUR_SESSION_ID -n "John Doe" -e "j*****e@gmail.com" -p "+39 *** **09"
```

### With Export

```console
python yesitsme.py -s YOUR_SESSION_ID -u username --export json
```

---

## 📖 Command Reference

### Modes

#### Simple Mode (Username Lookup)

| Argument | Description |
|----------|-------------|
| `-u, --username` | Instagram username to lookup |

**Example:**
```console
python yesitsme.py -u elonmusk
```

#### Advanced Mode (OSINT Search)

| Argument | Description |
|----------|-------------|
| `-n, --name` | Target name & surname (case insensitive) |
| `-e, --email` | Target email (first and last character + domain) |
| `-p, --phone` | Target phone (area code + last 2 digits) |

**Example:**
```console
python yesitsme.py -n "Elon Musk" -e "e***k@tesla.com" -p "+1 *** *** **89"
```

### Common Options

| Argument | Description | Default |
|----------|-------------|---------|
| `-s, --session-id` | Instagram session ID | `INSTAGRAM_SESSION_ID` env var |
| `-t, --timeout` | Timeout between requests (seconds) | 10 |
| `--proxy` | Proxy URL (e.g., `http://user:pass@host:port`) | None |
| `--export` | Export format: `json`, `csv`, `none` | `json` |
| `--output-dir` | Output directory for exports | `output` |
| `--config` | Path to config file | `config.yaml` |
| `-v, --verbose` | Enable verbose output | False |
| `--media-count` | Number of recent posts to fetch | 12 |

---

## 📝 Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
INSTAGRAM_SESSION_ID=your_session_id_here
YESITSME_TIMEOUT=10
YESITSME_PROXY=http://proxy.example.com:8080
YESITSME_MAX_RETRIES=3
```

### Configuration File

Create a `config.yaml` file:

```yaml
timeout: 10
max_retries: 3
retry_delay: 1.0
export_format: json
output_dir: output
log_level: INFO
verbose: false
```

### Priority Order

1. Command-line arguments
2. Environment variables
3. Configuration file
4. Default values

---

## 🎯 Usage Examples

### Example 1: Simple Username Lookup

```console
python yesitsme.py -u elonmusk
```

Output includes:
- Profile information (bio, followers, following, posts)
- Recent posts with likes/comments
- Story highlights
- Related profiles
- Public contact information
- Exported to JSON automatically

### Example 2: Advanced OSINT Search

```console
python yesitsme.py \
  -s YOUR_SESSION_ID \
  -n "Jane Smith" \
  -e "j***h@yahoo.com" \
  -p "+1 *** *** **45"
```

### Example 3: With Proxy and Export

```console
python yesitsme.py \
  -u username \
  --proxy "http://user:pass@proxy.example.com:8080" \
  --export json \
  --output-dir results
```

### Example 4: Using Environment Variables

```bash
export INSTAGRAM_SESSION_ID=your_session_id
python yesitsme.py -u instagram_username
```

---

## 📊 Output

### Match Levels

| Level | Description |
|-------|-------------|
| **HIGH** | Name, email, and phone all match |
| **MEDIUM** | Two out of three match |
| **LOW** | Only one matches |

### Exported Data

JSON and CSV exports include:
- Username and User ID
- Full name and verification status
- Account type (business/private)
- Follower/following counts
- Public email and phone
- Obfuscated email and phone
- Match level and count
- Profile picture URL

---

## 🍪 Getting Your Instagram Session ID

1. Log in to Instagram in your browser
2. Right-click and select **Inspect** (or press F12)
3. Go to the **Application** tab (Chrome) or **Storage** tab (Firefox)
4. Expand **Cookies** → `https://www.instagram.com`
5. Find the `sessionid` cookie and copy its value

⚠️ **Security Note:** Never share your session ID or commit it to version control!

---

## 🔒 Security Best Practices

- Use environment variables for sensitive data
- Never commit `.env` or `config.yaml` with real credentials
- Use a sockpuppet account for OSINT investigations
- Consider using proxies to avoid detection
- Respect rate limits to prevent IP bans

---

## 🧪 Testing

Run tests with:

```console
pytest tests/
```

---

## 📦 Dependencies

| Package | Purpose |
|---------|---------|
| httpx | Async HTTP client |
| requests | HTTP requests |
| beautifulsoup4 | HTML parsing |
| colorama | Terminal colors |
| rich | Rich terminal UI |
| python-dotenv | Environment variables |
| pyyaml | YAML configuration |
| tenacity | Retry logic |

---

## 🐛 Troubleshooting

### Rate Limit Errors

If you encounter rate limits:
1. Increase timeout between requests (`-t 30`)
2. Use a proxy
3. Wait a few minutes before retrying

### Session ID Invalid

- Make sure you're logged in to Instagram
- Clear browser cache and re-login
- Copy the session ID again

### No Results Found

- Verify the name spelling
- Try variations of the name
- The account might be private or deleted

---

## 🙏 Credits

Thanks to:
- [Toutatis](https://github.com/megadose/toutatis) - Instagram lookup inspiration
- [Dumpor](https://dumpor.com/) - Username indexing
- Original creator: [@blackeko5](https://twitter.com/blackeko5)

---

## 👨‍💻 Maintainer

This project is currently maintained by **[imsanghaar](https://github.com/imsanghaar)**.

For questions, issues, or feature requests, please open an issue on the [GitHub repository](https://github.com/imsanghaar/yesitsme/issues).

---

## 📄 License

This project is for educational and research purposes only. Use responsibly and respect Instagram's Terms of Service.

---

## 📬 Contact

Twitter: [@blackeko5](https://twitter.com/blackeko5) **Original Creator**
Linkedin: [@Imam Sanghaar](https://www.linkedin.com/in/imam-sanghaar-chandio-96780b274/) **Current Maintainer**

