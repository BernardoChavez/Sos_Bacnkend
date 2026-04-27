import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
def send_recovery_email(email_to: str, code: str):
    """
    Envía un correo real usando SMTP.
    """
    load_dotenv() # Forzar recarga de .env
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", 587))

    if not smtp_user or not smtp_password:
        print("\n[ADVERTENCIA] No se configuraron las credenciales de correo (SMTP_USER/SMTP_PASSWORD).")
        print(f"SMTP_USER actual: {smtp_user}")
        print(f"Código para {email_to}: {code}\n")
        return False

    subject = "Código de Recuperación - SOS Automotriz"
    body = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 10px;">
                <h2 style="color: #2563eb; text-align: center;">SOS Automotriz</h2>
                <p>Hola,</p>
                <p>Has solicitado restablecer tu contraseña. Usa el siguiente código de seguridad:</p>
                <div style="background-color: #f8fafc; padding: 20px; text-align: center; border-radius: 8px; margin: 20px 0;">
                    <span style="font-size: 32px; font-weight: bold; letter-spacing: 5px; color: #1e293b;">{code}</span>
                </div>
                <p>Este código expirará pronto. Si no solicitaste este cambio, puedes ignorar este correo.</p>
                <hr style="border: 0; border-top: 1px solid #e2e8f0; margin: 20px 0;">
                <p style="font-size: 12px; color: #64748b; text-align: center;">
                    Este es un mensaje automático, por favor no respondas.
                </p>
            </div>
        </body>
    </html>
    """

    msg = MIMEMultipart()
    msg['From'] = smtp_user
    msg['To'] = email_to
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'html'))

    try:
        server = smtplib.SMTP(smtp_host, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Error al enviar correo: {e}")
        return False
