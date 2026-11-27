import fs from "fs";
import formidable from "formidable";
import nodemailer from "nodemailer";

// Multipart bodies (the resume upload) must not be pre-parsed by Next.js.
export const config = {
  api: { bodyParser: false },
};

const MAIL_TO = process.env.MAIL_TO || "applicationwfhr@gmail.com";
const MAX_RESUME_BYTES = 4 * 1024 * 1024; // Vercel rejects request bodies over 4.5 MB

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

  // allowEmptyFiles keeps submissions working when no resume is chosen:
  // browsers still send the file input as an empty part in that case.
  const form = formidable({
    maxFileSize: MAX_RESUME_BYTES,
    allowEmptyFiles: true,
    minFileSize: 0,
    multiples: false,
  });

  let fields;
  let files;
  try {
    [fields, files] = await form.parse(req);
  } catch (error) {
    console.error("Could not read application:", error);
    if (error && error.code === 1009) {
      return res.status(413).json({ error: "Your resume is too large. Please upload a file under 4 MB." });
    }
    return res.status(400).json({ error: "We couldn't read your application. Please try again." });
  }

  const flat = {};
  for (const [key, value] of Object.entries(fields || {})) {
    flat[key] = Array.isArray(value) ? value[0] ?? "" : value ?? "";
  }

  // Honeypot: only bots fill this in, so pretend everything is fine.
  if (flat["bot-field"]) {
    return res.status(200).json({ ok: true });
  }

  const resumeEntry = files && files.resume;
  const resume = Array.isArray(resumeEntry) ? resumeEntry[0] : resumeEntry;

  const required = ["full_name", "email", "position", "cover_letter"];
  if (required.some((field) => !String(flat[field] || "").trim())) {
    return res.status(400).json({ error: "Please fill in all the required fields." });
  }

  const html = `
<h2 style="color:#06A3DA;">New Job Application — CoreVanta</h2>
<table style="width:100%;border-collapse:collapse;font-family:Arial,sans-serif;font-size:14px;">
  <tr><td style="padding:8px;font-weight:bold;width:180px;">Full Name</td><td style="padding:8px;">${escapeHtml(flat.full_name)}</td></tr>
  <tr style="background:#f5f5f5;"><td style="padding:8px;font-weight:bold;">Email</td><td style="padding:8px;">${escapeHtml(flat.email)}</td></tr>
  <tr><td style="padding:8px;font-weight:bold;">Phone</td><td style="padding:8px;">${escapeHtml(flat.phone_number) || "Not provided"}</td></tr>
  <tr style="background:#f5f5f5;"><td style="padding:8px;font-weight:bold;">Position</td><td style="padding:8px;">${escapeHtml(flat.position)}</td></tr>
  <tr><td style="padding:8px;font-weight:bold;">Country</td><td style="padding:8px;">${escapeHtml(flat.country) || "Not provided"}</td></tr>
  <tr style="background:#f5f5f5;"><td style="padding:8px;font-weight:bold;">State</td><td style="padding:8px;">${escapeHtml(flat.state) || "Not provided"}</td></tr>
  <tr><td style="padding:8px;font-weight:bold;vertical-align:top;">Cover Letter</td><td style="padding:8px;">${escapeHtml(flat.cover_letter).replace(/\n/g, "<br>")}</td></tr>
</table>
`;

  const attachments = [];
  if (resume && resume.size > 0) {
    attachments.push({
      filename: resume.originalFilename || "resume",
      content: fs.readFileSync(resume.filepath),
    });
  }

  try {
    await transporter.sendMail({
      from: `"CoreVanta Website" <${process.env.GMAIL_USER}>`,
      to: MAIL_TO,
      replyTo: String(flat.email).trim(),
      subject: `New Job Application: ${flat.position} - ${flat.full_name}`,
      html,
      attachments,
    });
    return res.status(200).json({ ok: true });
  } catch (error) {
    console.error("Application email failed:", error);
    return res.status(500).json({ error: "We couldn't send your application. Please try again." });
  }
}
