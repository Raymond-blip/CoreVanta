import smtplib
import os
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import parse_qs

# ─── CONFIG ───────────────────────────────────────────────────────────────────
SMTP_HOST      = "smtp.gmail.com"
SMTP_PORT      = 587
SENDER_EMAIL   = "applicationwfhr@gmail.com"
SENDER_PASS    = os.environ.get("GMAIL_APP_PASSWORD", "")   # set via environment variable
RECEIVER_EMAIL = "applicationwfhr@gmail.com"
# ───────────────────────────────────────────────────────────────────────────────


def parse_multipart(data, boundary):
    """Parse multipart/form-data manually."""
    fields = {}
    files = {}
    boundary = boundary.encode()
    delimiter = b"--" + boundary
    parts = data.split(delimiter)
    for part in parts:
        if part in (b"", b"--\r\n", b"--"):
            continue
        if part.startswith(b"\r\n"):
            part = part[2:]
        if part.endswith(b"\r\n"):
            part = part[:-2]
        # Split headers from body
        try:
            headers_raw, body = part.split(b"\r\n\r\n", 1)
        except ValueError:
            continue
        headers = {}
        for line in headers_raw.decode("utf-8", errors="replace").split("\r\n"):
            if ":" in line:
                k, v = line.split(":", 1)
                headers[k.strip().lower()] = v.strip()
        disp = headers.get("content-disposition", "")
        name_match = re.search(r'name="([^"]+)"', disp)
        file_match = re.search(r'filename="([^"]+)"', disp)
        if not name_match:
            continue
        name = name_match.group(1)
        if file_match:
            files[name] = {"filename": file_match.group(1), "data": body}
        else:
            fields[name] = body.decode("utf-8", errors="replace").strip()
    return fields, files


def send_email(fields, resume_data=None, resume_name=None):
    msg = MIMEMultipart()
    msg["From"]    = SENDER_EMAIL
    msg["To"]      = RECEIVER_EMAIL
    msg["Subject"] = f"New Job Application: {fields.get('position','N/A')} – {fields.get('full_name','N/A')}"

    body = f"""
<h2 style="color:#06A3DA;">New Job Application — CoreVanta</h2>
<table style="width:100%;border-collapse:collapse;font-family:Arial,sans-serif;font-size:14px;">
  <tr><td style="padding:8px;font-weight:bold;width:180px;">Full Name</td><td style="padding:8px;">{fields.get('full_name','')}</td></tr>
  <tr style="background:#f5f5f5;"><td style="padding:8px;font-weight:bold;">Email</td><td style="padding:8px;">{fields.get('email','')}</td></tr>
  <tr><td style="padding:8px;font-weight:bold;">Phone</td><td style="padding:8px;">{fields.get('phone_number','Not provided')}</td></tr>
  <tr style="background:#f5f5f5;"><td style="padding:8px;font-weight:bold;">Position</td><td style="padding:8px;">{fields.get('position','')}</td></tr>
  <tr><td style="padding:8px;font-weight:bold;">Country</td><td style="padding:8px;">{fields.get('country','Not provided')}</td></tr>
  <tr style="background:#f5f5f5;"><td style="padding:8px;font-weight:bold;">State</td><td style="padding:8px;">{fields.get('state','Not provided')}</td></tr>
  <tr><td style="padding:8px;font-weight:bold;vertical-align:top;">Cover Letter</td><td style="padding:8px;">{fields.get('cover_letter','').replace(chr(10),'<br>')}</td></tr>
</table>
"""
    msg.attach(MIMEText(body, "html"))

    if resume_data and resume_name:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(resume_data)
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f'attachment; filename="{resume_name}"')
        msg.attach(part)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASS.replace(" ", ""))
        server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())


def send_contact_email(fields):
    msg = MIMEMultipart()
    msg["From"]     = SENDER_EMAIL
    msg["To"]       = RECEIVER_EMAIL
    msg["Reply-To"] = fields.get("email", "")
    msg["Subject"]  = f"New Contact Message: {fields.get('full_name','N/A')}"

    body = f"""
<h2 style="color:#06A3DA;">New Contact Message — CoreVanta</h2>
<table style="width:100%;border-collapse:collapse;font-family:Arial,sans-serif;font-size:14px;">
  <tr><td style="padding:8px;font-weight:bold;width:180px;">Full Name</td><td style="padding:8px;">{fields.get('full_name','')}</td></tr>
  <tr style="background:#f5f5f5;"><td style="padding:8px;font-weight:bold;">Email</td><td style="padding:8px;">{fields.get('email','')}</td></tr>
  <tr><td style="padding:8px;font-weight:bold;">Phone</td><td style="padding:8px;">{fields.get('phone_number','Not provided')}</td></tr>
  <tr style="background:#f5f5f5;"><td style="padding:8px;font-weight:bold;vertical-align:top;">Message</td><td style="padding:8px;">{fields.get('message','').replace(chr(10),'<br>')}</td></tr>
</table>
"""
    msg.attach(MIMEText(body, "html"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASS.replace(" ", ""))
        server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())


class CoreVantaHandler(SimpleHTTPRequestHandler):

    def do_POST(self):
        if self.path == "/send-application":
            self.handle_application()
        elif self.path == "/send-message":
            self.handle_contact()
        else:
            self.send_error(404)

    def handle_application(self):
        content_type  = self.headers.get("Content-Type", "")
        content_length = int(self.headers.get("Content-Length", 0))
        raw_data = self.rfile.read(content_length)

        # Extract boundary
        boundary_match = re.search(r"boundary=(.+)", content_type)
        if not boundary_match:
            self._redirect("apply.html?status=error")
            return
        boundary = boundary_match.group(1).strip()

        fields, files = parse_multipart(raw_data, boundary)

        # Resume
        resume_data = None
        resume_name = None
        if "resume" in files and files["resume"]["data"]:
            resume_data = files["resume"]["data"]
            resume_name = files["resume"]["filename"]

        # Validate required fields
        required = ["full_name", "email", "position", "cover_letter"]
        if not all(fields.get(f) for f in required):
            self._redirect("apply.html?status=error")
            return

        try:
            send_email(fields, resume_data, resume_name)
            self._redirect("apply.html?status=success")
        except Exception as e:
            print(f"Email error: {e}")
            self._redirect("apply.html?status=error")

    def handle_contact(self):
        content_length = int(self.headers.get("Content-Length", 0))
        raw_data = self.rfile.read(content_length)
        parsed = parse_qs(raw_data.decode("utf-8", errors="replace"))
        fields = {k: v[0] for k, v in parsed.items()}

        required = ["full_name", "email", "message"]
        if not all(fields.get(f) for f in required):
            self._redirect("contact.html?status=error")
            return

        try:
            send_contact_email(fields)
            self._redirect("contact.html?status=success")
        except Exception as e:
            print(f"Contact email error: {e}")
            self._redirect("contact.html?status=error")

    def _redirect(self, location):
        self.send_response(302)
        self.send_header("Location", f"/{location}")
        self.end_headers()

    def log_message(self, fmt, *args):
        print(f"[{self.address_string()}] {fmt % args}")


if __name__ == "__main__":
    port = 8080
    server = HTTPServer(("", port), CoreVantaHandler)
    print(f"CoreVanta server running at http://127.0.0.1:{port}")
    server.serve_forever()
