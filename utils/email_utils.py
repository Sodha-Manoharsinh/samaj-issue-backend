from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from config import Config
import smtplib

def send_email(to, otp_code):
    msg = MIMEMultipart("alternative")
    msg['Subject'] = "🔐 Your SAMAJ ISSUE OTP Code"
    msg['From'] = Config.EMAIL_FROM
    msg['To'] = to

    text = f"""
    Your OTP code is: {otp_code}
    Use this to verify your identity on SAMAJ ISSUE.
    This code will expire in 5 minutes.
    """

    html = f"""
    <html>
      <body style="font-family: Arial, sans-serif; line-height: 1.6;">
        <h2 style="color: #1a73e8;">SAMAJ ISSUE Verification</h2>
        <p>Hello,</p>
        <p>Your OTP code is:</p>
        <h1 style="background: #f2f2f2; padding: 10px; border-radius: 5px; width: fit-content;">{otp_code}</h1>
        <p>This code is valid for <strong>5 minutes</strong>.</p>
        <p>If you didn’t request this code, you can safely ignore this email.</p>
        <br/>
        <p>— Team SAMAJ ISSUE</p>
      </body>
    </html>
    """

    part1 = MIMEText(text, "plain")
    part2 = MIMEText(html, "html")

    msg.attach(part1)
    msg.attach(part2)

    try:
        server = smtplib.SMTP(Config.EMAIL_HOST, Config.EMAIL_PORT)
        server.starttls()
        server.login(Config.EMAIL_USERNAME, Config.EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        print("✅ Email sent successfully to", to)
        return True  # ✅ indicate success
    except Exception as e:
        print("❌ Failed to send email:", e)
        return False  # ❌ indicate failure
