import sqlite3
#sample database name 
conn = sqlite3.connect('shortlist.db')
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS candidates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE
    )
''')

sample_data = [
    ('Kanishka Maurya', 'kanishkamauryaofficial@gmail.com'),
    ('Bob Smith', 'bob@example.com'),
    ('Charlie Ray', 'charlie@example.com')
]

for name, email in sample_data:
    try:
        cursor.execute("INSERT INTO candidates (full_name, email) VALUES (?, ?)", (name, email))
    except sqlite3.IntegrityError:
        print(f"{email} already exists")

conn.commit()
conn.close()

conn = sqlite3.connect('shortlist.db')
cursor = conn.cursor()

cursor.execute("SELECT * FROM candidates")
rows = cursor.fetchall()

for row in rows:
    print(row)

conn.close()
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

conn = sqlite3.connect('shortlist.db')
cursor = conn.cursor()

cursor.execute("SELECT full_name, email FROM candidates")
candidates = cursor.fetchall()
conn.close()

import os
sender_email = os.environ["SENDER_EMAIL"]
password = os.environ["SENDER_PASSWORD"]

server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
server.login(sender_email, password)

for name, email in candidates:
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = email
    msg['Subject'] = "Interview Shortlisting Confirmation"

    body = f"Hello {name},\n\nCongratulations! You have been shortlisted for the interview round. We'll get back to you soon with the details.\n\nBest regards,\nTeam"
    msg.attach(MIMEText(body, 'plain'))

    try:
        server.sendmail(sender_email, email, msg.as_string())
        print(f"Email sent to {name} at {email}")
    except Exception as e:
        print(f"Failed to send email to {email}: {e}")

server.quit()
