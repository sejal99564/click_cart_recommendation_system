"""Report production configuration without printing credentials or calling providers."""
import argparse
import os
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import dotenv_values


GROUPS = {
    "Amazon India": ("AMAZON_CREDENTIAL_ID", "AMAZON_CREDENTIAL_SECRET", "AMAZON_PARTNER_TAG"),
    "Flipkart": ("FLIPKART_AFFILIATE_ID", "FLIPKART_AFFILIATE_TOKEN"),
    "Production SMTP": ("SMTP_HOST", "SMTP_FROM"),
    "Deployment": ("DATABASE_URL", "FRONTEND_ORIGIN", "APP_ENV"),
}


def configuration_gaps(settings):
    gaps = {label: [name for name in names if not (settings.get(name) or "").strip()]
            for label, names in GROUPS.items()}
    provider = (settings.get("SHOPPING_AI_PROVIDER") or "openai").strip().lower()
    if provider == "gemini":
        gaps["Gemini"] = [] if (settings.get("GEMINI_API_KEY") or "").strip() else ["GEMINI_API_KEY"]
    elif provider == "openai":
        gaps["OpenAI"] = [name for name in ("OPENAI_API_KEY", "OPENAI_MODEL") if not (settings.get(name) or "").strip()]
    else:
        gaps["Deployment"].append("SHOPPING_AI_PROVIDER must be openai or gemini")
    database = settings.get("DATABASE_URL") or ""
    origin = settings.get("FRONTEND_ORIGIN") or ""
    if database and not database.startswith("postgresql+psycopg://"):
        gaps["Deployment"].append("DATABASE_URL must use postgresql+psycopg")
    if origin:
        try:
            parsed = urlsplit(origin)
            valid_origin = parsed.scheme == "https" and bool(parsed.hostname) and not (
                parsed.username or parsed.password or parsed.path.rstrip("/") or parsed.query or parsed.fragment
            )
        except ValueError:
            valid_origin = False
        if not valid_origin:
            gaps["Deployment"].append("FRONTEND_ORIGIN must be an HTTPS origin")
    if settings.get("APP_ENV") and settings["APP_ENV"] != "production":
        gaps["Deployment"].append("APP_ENV must be production")
    if settings.get("SMTP_USERNAME") and not settings.get("SMTP_PASSWORD"):
        gaps["Production SMTP"].append("SMTP_PASSWORD")
    if (settings.get("AMAZON_CREDENTIAL_VERSION") or "3.2") not in {"3.1", "3.2", "3.3"}:
        gaps["Amazon India"].append("AMAZON_CREDENTIAL_VERSION must be 3.1, 3.2 or 3.3")
    return gaps


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=Path(__file__).resolve().parents[1] / ".env")
    args = parser.parse_args()
    gaps = configuration_gaps({**dotenv_values(args.env_file), **os.environ})
    for label, issues in gaps.items():
        print(f"{label}: {'; '.join(issues) if issues else 'configuration present'}")
    return int(any(gaps.values()))


if __name__ == "__main__":
    raise SystemExit(main())
