import streamlit as st
from docx import Document
import os, time, json, sqlite3
from dotenv import load_dotenv
import chromadb
import smtplib
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain_groq import ChatGroq
from prompts.extracted_text_prompt_template import extracted_text_prompt_template
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from prompts.job_description_prompt_template import job_description_prompt_template
from prompts.email_generation_prompt import email_generation_prompt

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
os.environ["GROQ_API_KEY"] = GROQ_API_KEY

chroma_client = chromadb.Client()
collection = chroma_client.get_or_create_collection(name="my_collection")

llm = ChatGroq(model_name="llama-3.3-70b-versatile")
llm_jd = ChatGroq(model_name="llama3-8b-8192")

def extract_text_from_document(document):
    doc = Document(document)
    text = "\n".join([para.text for para in doc.paragraphs])
    return text

def cv_summary(extracted_text):
    chain = LLMChain(llm=llm, prompt=extracted_text_prompt_template)
    summarized_text = chain.run(extracted_text=extracted_text)
    return summarized_text

def save_to_chromaDB(summarized_text):
    collection.add(
        documents=[summarized_text],
        ids=[str(hash(summarized_text))]
    )

def summarize_job_description(job_description):
    chain = LLMChain(llm=llm_jd, prompt=job_description_prompt_template)
    return chain.run(job_description=job_description)

def query_top_matches(formatted_jd_prompt_template):
    num_vectors = int(0.8 * collection.count())
    results = collection.query(query_texts=[formatted_jd_prompt_template], n_results=num_vectors, include=["documents"])
    documents = results.get("documents", [])
    extracted_list = []

    for doc in documents[0]:
        try:
            doc_dict = json.loads(doc)
            extracted_list.append({
                "Full Name": doc_dict.get("Full Name", "N/A"),
                "Email": doc_dict.get("Email", "N/A")
            })
        except Exception as e:
            print("Error:", e)
    return extracted_list

def save_to_sqlite(data):
    conn = sqlite3.connect('new.db')
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS shortlisted (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            [Full Name] TEXT,
            [Email] TEXT
        )
    """)
    for item in data:
        cursor.execute("INSERT INTO shortlisted ([Full Name], [Email]) VALUES (?, ?)", 
                       (item["Full Name"], item["Email"]))
    conn.commit()
    conn.close()

def generate_custom_email(name, job_role, date, venue):
    chain = LLMChain(llm=llm, prompt=email_generation_prompt)
    return chain.run(name=name, job_role=job_role, date=date, venue=venue)



# Streamlit App

# user side
st.title("Resume Shortlisting & Email Automation")
st.subheader("User Section")
doc_upload = st.file_uploader("Upload Document", type=["pdf", "txt", "docx"])
if st.button("Saving in vector store"):
    if not doc_upload:
        st.warning("Please upload a Document.")
    else:
        extracted_text = extract_text_from_document(doc_upload)
        cv_summary = cv_summary(extracted_text)
        save_to_chromaDB(cv_summary)

# admin side
st.subheader("Admin Section")
job_description = st.text_area("Enter Job Description")
sender_email = st.text_input("Enter Sender Email")
password = st.text_input("Enter Email Password", type="password")
job_role = st.text_input("Job Role")
date = st.date_input("Interview Date")
venue = st.text_input("Interview Venue")

if st.button("Shortlist & Send Emails"):
    if not job_description:
        st.warning("Please enter a job description.")
    elif not sender_email or not password:
        st.warning("Please enter both sender email and password.")
    else:
        formatted_jd = summarize_job_description(job_description)
        top_matches = query_top_matches(formatted_jd)
        save_to_sqlite(top_matches)

        try:
            server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
            server.login(sender_email, password)

            for person in top_matches:
                name = person['Full Name']
                email = person['Email']
                customized_body = generate_custom_email(name, job_role, str(date), venue)
                msg = MIMEMultipart()
                msg['From'] = sender_email
                msg['To'] = email
                msg['Subject'] = f"Shortlisted for {job_role} Interview"
                msg.attach(MIMEText(customized_body, 'plain'))

                try:
                    server.sendmail(sender_email, email, msg.as_string())
                    st.success(f"Email sent to {name} at {email}")
                except Exception as e:
                    st.error(f"Failed to send email to {email}: {e}")

            server.quit()
        except Exception as e:
            st.error(f"SMTP error: {e}")
