import base64
import json
import os
import re
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs
from urllib.request import Request, urlopen

# ─── CONFIG ───────────────────────────────────────────────────────────────────
# Mail goes out over Resend's HTTPS API instead of SMTP, because Render's free
# web services block outbound traffic on the SMTP ports 25, 465 and 587.
RESEND_ENDPOINT = "https://api.resend.com/emails"
RESEND_API_KEY  = os.environ.get("RESEND_API_KEY", "")   # set via environment variable
SENDER_NAME     = "CoreVanta"
SENDER_EMAIL    = "onboarding@resend.dev"                # swap for an address on your verified domain
RECEIVER_EMAIL  = "applicationwfhr@gmail.com"
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


def send_via_resend(subject, html_body, reply_to=None, attachment=None):
    """POST an email to Resend. Raises on failure so callers can report it."""
    payload = {
        "from":    f"{SENDER_NAME} <{SENDER_EMAIL}>",
        "to":      [RECEIVER_EMAIL],
        "subject": subject,
        "html":    html_body,
    }
    if reply_to:
        payload["reply_to"] = reply_to
    if attachment:
        filename, data = attachment
        payload["attachments"] = [{
            "filename": filename,
            "content":  base64.b64encode(data).decode(),
        }]

    request = Request(
        RESEND_ENDPOINT,
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type":  "application/json",
            "User-Agent":    "CoreVanta/1.0",   # Cloudflare rejects urllib's default UA with error 1010
        },
        method="POST",
    )
    with urlopen(request, timeout=30) as response:
        return response.status


def send_email(fields, resume_data=None, resume_name=None):
    subject = f"New Job Application: {fields.get('position','N/A')} – {fields.get('full_name','N/A')}"

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
    send_via_resend(
        subject,
        body,
        attachment=(resume_name, resume_data) if resume_data and resume_name else None,
    )


def send_contact_email(fields):
    subject = f"New Contact Message: {fields.get('full_name','N/A')}"

    body = f"""
<h2 style="color:#06A3DA;">New Contact Message — CoreVanta</h2>
<table style="width:100%;border-collapse:collapse;font-family:Arial,sans-serif;font-size:14px;">
  <tr><td style="padding:8px;font-weight:bold;width:180px;">Full Name</td><td style="padding:8px;">{fields.get('full_name','')}</td></tr>
  <tr style="background:#f5f5f5;"><td style="padding:8px;font-weight:bold;">Email</td><td style="padding:8px;">{fields.get('email','')}</td></tr>
  <tr><td style="padding:8px;font-weight:bold;">Phone</td><td style="padding:8px;">{fields.get('phone_number','Not provided')}</td></tr>
  <tr style="background:#f5f5f5;"><td style="padding:8px;font-weight:bold;vertical-align:top;">Message</td><td style="padding:8px;">{fields.get('message','').replace(chr(10),'<br>')}</td></tr>
</table>
"""
    send_via_resend(subject, body, reply_to=fields.get("email") or None)


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
    port = int(os.environ.get("PORT", 8080))
    server = ThreadingHTTPServer(("", port), CoreVantaHandler)
    print(f"CoreVanta server running on port {port}")
    server.serve_forever()
