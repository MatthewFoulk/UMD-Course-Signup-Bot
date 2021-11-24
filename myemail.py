"""Sends emails"""

import smtplib
import ssl
from email.mime.text import MIMEText

def send_email(message:str, subject:str, sender:str, receiver:str, password:str):
    """Send an email using gmail (sender must be a gmail account)

    Args:
        message (str): Body of email
        subject (str): Subject-line of email
        sender (str): Email address of sender
        receiver (str): Email address of reciever
        password (str): Password for sender's gmail account
    """

    port = 465  # For SSL
    smtp_server = "smtp.gmail.com"
    msg = MIMEText(message, 'plain')

    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = receiver

    # Create a secure SSL context
    context = ssl.create_default_context()

    with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
        server.login(sender, password)
        server.sendmail(sender, receiver, msg.as_string())