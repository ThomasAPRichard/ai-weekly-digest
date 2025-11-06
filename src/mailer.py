from __future__ import annotations
import os, smtplib
from email.message import EmailMessage

def send_email(subject: str, html_body: str, text_body: str):
  host = os.environ["SMTP_HOST"]
  port = int(os.environ.get("SMTP_PORT", "587"))
  user = os.environ["SMTP_USER"]
  password = os.environ["SMTP_PASS"]
  starttls = os.environ.get("SMTP_STARTTLS", "true").lower() in ("1","true","yes","on")
  mail_from = os.environ["MAIL_FROM"]
  mail_to = [e.strip() for e in os.environ["MAIL_TO"].split(",") if e.strip()]

  msg = EmailMessage()
  msg["Subject"] = subject
  msg["From"] = mail_from
  msg["To"] = ", ".join(mail_to)
  msg.set_content(text_body)
  msg.add_alternative(html_body, subtype="html")

  with smtplib.SMTP(host, port) as s:
    if starttls:
      s.starttls()
    if user or password:
      s.login(user, password)
    s.send_message(msg)
