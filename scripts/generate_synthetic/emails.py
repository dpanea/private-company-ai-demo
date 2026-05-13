from __future__ import annotations

import mailbox
from email.message import EmailMessage
from email.utils import format_datetime
from pathlib import Path

from .accounts import EmailSpec


def write_mbox(path: Path, emails: tuple[EmailSpec, ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()

    mbox = mailbox.mbox(path)
    try:
        for email in emails:
            message = EmailMessage()
            message["Message-ID"] = email.message_id
            message["Date"] = format_datetime(email.sent_at)
            message["From"] = email.sender
            message["To"] = ", ".join(email.recipients)
            if email.cc:
                message["Cc"] = ", ".join(email.cc)
            message["Subject"] = email.subject
            if email.in_reply_to:
                message["In-Reply-To"] = email.in_reply_to
            if email.references:
                message["References"] = " ".join(email.references)
            message.set_content(email.body)
            message.set_unixfrom(f"From {email.sender} {format_datetime(email.sent_at)}")
            mbox.add(message)
        mbox.flush()
    finally:
        mbox.close()
