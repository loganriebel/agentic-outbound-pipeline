"""
email_sender.py — reads the prospect list and sends personalized cold emails.

Run with --dry-run (or without a .env file) to preview output without sending.
"""

import argparse
import logging
import os
import re
import smtplib
import tempfile
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

import pandas as pd
from dotenv import dotenv_values
from jinja2 import Environment, FileSystemLoader


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

REQUIRED_SMTP_KEYS = ["SMTP_HOST", "SMTP_PORT", "SMTP_USERNAME", "SMTP_PASSWORD"]


def load_config() -> dict:
    """Load .env into a dict. Returns empty dict (demo mode) if .env is missing."""
    env_path = Path(".env")
    if not env_path.exists():
        return {}
    config = dotenv_values(env_path)
    missing = [k for k in REQUIRED_SMTP_KEYS if not config.get(k)]
    if missing:
        raise EnvironmentError(f"Missing required .env keys: {', '.join(missing)}")
    return config


# ---------------------------------------------------------------------------
# Prospects
# ---------------------------------------------------------------------------

def load_prospects(filepath: str) -> pd.DataFrame:
    """Return rows where Contacted? is blank — these are the ones to email."""
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Prospects file not found: {filepath}")

    df = pd.read_csv(filepath) if filepath.endswith(".csv") else pd.read_excel(filepath)
    df.columns = df.columns.str.strip()

    uncontacted = df[df["Contacted?"].isna() | (df["Contacted?"].astype(str).str.strip() == "")]
    logging.info(f"Loaded {len(df)} total prospects, {len(uncontacted)} uncontacted.")
    return df, uncontacted.copy()


def mark_contacted(df: pd.DataFrame, index: int) -> pd.DataFrame:
    df.at[index, "Contacted?"] = "X"
    return df


def save_prospects(df: pd.DataFrame, filepath: str) -> None:
    """Write to a temp file first, then replace — avoids corrupting on crash."""
    path = Path(filepath)
    suffix = path.suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, dir=path.parent) as tmp:
        tmp_path = tmp.name

    if filepath.endswith(".csv"):
        df.to_csv(tmp_path, index=False)
    else:
        df.to_excel(tmp_path, index=False, engine="openpyxl")

    os.replace(tmp_path, filepath)


# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------

def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def render_email(template_path: str, prospect: dict) -> str:
    template_file = Path(template_path)
    env = Environment(loader=FileSystemLoader(str(template_file.parent)))
    template = env.get_template(template_file.name)
    return template.render(
        name=prospect.get("Owner Name", "there"),
        bizname=prospect.get("Biz Name", ""),
        bizname_slug=_slugify(prospect.get("Biz Name", "")),
    )


def send_email(config: dict, to_address: str, subject: str, body: str) -> bool:
    """Send via STARTTLS. Returns True on success, False on any SMTP error."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{config.get('FROM_NAME', config['FROM_EMAIL'])} <{config['FROM_EMAIL']}>"
    msg["To"] = to_address
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(config["SMTP_HOST"], int(config["SMTP_PORT"])) as server:
            server.ehlo()
            server.starttls()
            server.login(config["SMTP_USERNAME"], config["SMTP_PASSWORD"])
            server.sendmail(config["FROM_EMAIL"], to_address, msg.as_string())
        return True
    except smtplib.SMTPAuthenticationError:
        raise  # auth failures should abort the whole run
    except smtplib.SMTPException as exc:
        logging.error(f"SMTP error sending to {to_address}: {exc}")
        return False


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def setup_logging(log_dir: str) -> None:
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    log_file = Path(log_dir) / f"outreach_{datetime.now().strftime('%Y-%m-%d')}.log"

    handlers = [
        TimedRotatingFileHandler(log_file, when="midnight", backupCount=7),
        logging.StreamHandler(),
    ]
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=handlers,
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Send cold emails to uncontacted prospects.")
    parser.add_argument("--dry-run", action="store_true", help="Log without sending email.")
    parser.add_argument("--limit", type=int, default=None, help="Max emails to send this run.")
    args = parser.parse_args()

    config = load_config()
    demo_mode = not config  # no .env = demo mode

    log_dir = config.get("LOG_DIR", "logs/")
    setup_logging(log_dir)

    if demo_mode:
        logging.info("No .env found — running in demo mode (no emails will be sent).")
        args.dry_run = True

    prospects_file = config.get("PROSPECTS_FILE", "data/prospects_example.csv")
    template_path = config.get("EMAIL_TEMPLATE", "templates/cold_email.txt")
    subject = config.get("EMAIL_SUBJECT", "missed a call?")
    limit = args.limit or int(config.get("DAILY_SEND_LIMIT", 20))
    dry_run = args.dry_run or config.get("DRY_RUN", "false").lower() == "true"

    if dry_run:
        logging.info("DRY RUN — emails will be previewed but not sent.")

    df, uncontacted = load_prospects(prospects_file)

    sent = skipped = failed = 0

    for i, (idx, row) in enumerate(uncontacted.iterrows()):
        if i >= limit:
            logging.info(f"Reached send limit ({limit}). Stopping.")
            break

        email = str(row.get("Email Address", "")).strip()
        name = str(row.get("Owner Name", "")).strip()
        biz = str(row.get("Biz Name", "")).strip()

        if not email or email.lower() in ("unknown", "nan", ""):
            logging.warning(f"Skipping {biz} — no email address.")
            skipped += 1
            continue

        body = render_email(template_path, row.to_dict())

        logging.info(f"{'[DRY RUN] Would send' if dry_run else 'Sending'} → {name} <{email}> ({biz})")

        if dry_run:
            logging.info(f"  Subject : {subject}")
            logging.info(f"  Preview : {body[:120].strip()}...")
            sent += 1
            continue

        try:
            success = send_email(config, email, subject, body)
        except smtplib.SMTPAuthenticationError as exc:
            logging.error(f"Authentication failed: {exc}. Aborting run.")
            raise SystemExit(1)

        if success:
            df = mark_contacted(df, idx)
            save_prospects(df, prospects_file)
            logging.info(f"  Sent and marked contacted.")
            sent += 1
        else:
            logging.warning(f"  Send failed — not marking as contacted.")
            failed += 1

    logging.info(
        f"\nRun complete — sent: {sent} | skipped (no email): {skipped} | failed: {failed}"
    )


if __name__ == "__main__":
    main()
