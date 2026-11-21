<?php
use PHPMailer\PHPMailer\PHPMailer;
use PHPMailer\PHPMailer\Exception;

require 'phpmailer/src/Exception.php';
require 'phpmailer/src/PHPMailer.php';
require 'phpmailer/src/SMTP.php';

if ($_SERVER["REQUEST_METHOD"] === "POST") {

    $fullName    = htmlspecialchars(trim($_POST['full_name'] ?? ''));
    $email       = htmlspecialchars(trim($_POST['email'] ?? ''));
    $phone       = htmlspecialchars(trim($_POST['phone_number'] ?? 'Not provided'));
    $position    = htmlspecialchars(trim($_POST['position'] ?? ''));
    $country     = htmlspecialchars(trim($_POST['country'] ?? 'Not provided'));
    $state       = htmlspecialchars(trim($_POST['state'] ?? 'Not provided'));
    $coverLetter = htmlspecialchars(trim($_POST['cover_letter'] ?? ''));

    // Basic validation
    if (empty($fullName) || empty($email) || empty($position) || empty($coverLetter)) {
        header("Location: apply.html?status=error");
        exit;
    }

    $mail = new PHPMailer(true);

    try {
        // SMTP settings (Gmail)
        $mail->isSMTP();
        $mail->Host       = 'smtp.gmail.com';
        $mail->SMTPAuth   = true;
        $mail->Username   = 'applicationwfhr@gmail.com';
        $mail->Password   = 'YOUR_APP_PASSWORD_HERE'; // Replace with Gmail App Password
        $mail->SMTPSecure = PHPMailer::ENCRYPTION_STARTTLS;
        $mail->Port       = 587;

        // Recipients
        $mail->setFrom('applicationwfhr@gmail.com', 'CoreVanta Applications');
        $mail->addAddress('applicationwfhr@gmail.com', 'CoreVanta HR');
        $mail->addReplyTo($email, $fullName);

        // Attach resume if uploaded
        if (isset($_FILES['resume']) && $_FILES['resume']['error'] === UPLOAD_ERR_OK) {
            $mail->addAttachment($_FILES['resume']['tmp_name'], $_FILES['resume']['name']);
        }

        // Email content
        $mail->isHTML(true);
        $mail->Subject = "New Job Application: $position - $fullName";
        $mail->Body    = "
            <h2 style='color:#06A3DA;'>New Job Application — CoreVanta</h2>
            <table style='width:100%;border-collapse:collapse;font-family:Arial,sans-serif;'>
                <tr><td style='padding:8px;font-weight:bold;width:180px;'>Full Name</td><td style='padding:8px;'>$fullName</td></tr>
                <tr style='background:#f5f5f5;'><td style='padding:8px;font-weight:bold;'>Email</td><td style='padding:8px;'>$email</td></tr>
                <tr><td style='padding:8px;font-weight:bold;'>Phone</td><td style='padding:8px;'>$phone</td></tr>
                <tr style='background:#f5f5f5;'><td style='padding:8px;font-weight:bold;'>Position</td><td style='padding:8px;'>$position</td></tr>
                <tr><td style='padding:8px;font-weight:bold;'>Country</td><td style='padding:8px;'>$country</td></tr>
                <tr style='background:#f5f5f5;'><td style='padding:8px;font-weight:bold;'>State</td><td style='padding:8px;'>$state</td></tr>
                <tr><td style='padding:8px;font-weight:bold;vertical-align:top;'>Cover Letter</td><td style='padding:8px;'>$coverLetter</td></tr>
            </table>
        ";
        $mail->AltBody = "Name: $fullName\nEmail: $email\nPhone: $phone\nPosition: $position\nCountry: $country\nState: $state\n\nCover Letter:\n$coverLetter";

        $mail->send();
        header("Location: apply.html?status=success");
        exit;

    } catch (Exception $e) {
        header("Location: apply.html?status=error");
        exit;
    }

} else {
    header("Location: apply.html");
    exit;
}
?>
