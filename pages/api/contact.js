import nodemailer from "nodemailer";

const MAIL_TO = process.env.MAIL_TO || "applicationwfhr@gmail.com";

const transporter = nodemailer.createTransport({
  host: "smtp.gmail.com",
  port: 465,
  secure: true,
  auth: {
    user: process.env.GMAIL_USER,
    pass: process.env.GMAIL_APP_PASSWORD,
  },
});

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

export default async function handler(req, res) {
  if (req.method !== "POST") {
    res.setHeader("Allow", "POST");
    return res.status(405).json({ error: "Method not allowed" });
  }

  const body = req.body || {};

  // Honeypot: only bots fill this in, so pretend everything is fine.
  if (body["bot-field"]) {
    return res.status(200).json({ ok: true });
  }

  const fullName = String(body.full_name || "").trim();
  const email = String(body.email || "").trim();
  const phone = String(body.phone_number || "").trim();
  const message = String(body.message || "").trim();

  if (!fullName || !email || !message) {
    return res.status(400).json({ error: "Please fill in your name, email and message." });
  }

  const html = `
<h2 style="color:#06A3DA;">New Contact Message — CoreVanta</h2>
<table style="width:100%;border-collapse:collapse;font-family:Arial,sans-serif;font-size:14px;">
  <tr><td style="padding:8px;font-weight:bold;width:180px;">Full Name</td><td style="padding:8px;">${escapeHtml(fullName)}</td></tr>
  <tr style="background:#f5f5f5;"><td style="padding:8px;font-weight:bold;">Email</td><td style="padding:8px;">${escapeHtml(email)}</td></tr>
  <tr><td style="padding:8px;font-weight:bold;">Phone</td><td style="padding:8px;">${escapeHtml(phone) || "Not provided"}</td></tr>
  <tr style="background:#f5f5f5;"><td style="padding:8px;font-weight:bold;vertical-align:top;">Message</td><td style="padding:8px;">${escapeHtml(message).replace(/\n/g, "<br>")}</td></tr>
</table>
`;

  try {
    await transporter.sendMail({
      from: `"CoreVanta Website" <${process.env.GMAIL_USER}>`,
      to: MAIL_TO,
      replyTo: email,
      subject: `New Contact Message: ${fullName}`,
      html,
    });
    return res.status(200).json({ ok: true });
  } catch (error) {
    console.error("Contact email failed:", error);
    return res.status(500).json({ error: "We couldn't send your message. Please try again." });
  }
}
