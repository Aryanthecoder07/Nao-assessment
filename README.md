# Healthcare Doctor–Patient Translation Web Application

## 📋 Project Overview
This project is a full-stack real-time translation bridge designed to facilitate communication between doctors and patients who speak different languages. It acts as an intelligent intermediary, translating spoken or typed input instantly and providing AI-powered medical summarization of the session.

**Live Demo:** https://nao-assessment.streamlit.app/

## 🚀 Features Implemented
* **Real-Time Translation:** Bi-directional translation between Doctor (English) and Patient (Spanish, French, Hindi, Mandarin, etc.).
* **Role-Based Interface:** Distinct UI for Doctors and Patients with session isolation using Room IDs.
* **Audio Handling:** Users can record voice messages which are stored and playable in the chat log.
* **Conversation Search:** Regex-powered search functionality that highlights specific keywords (e.g., symptoms) in the chat history.
* **AI Summarization:** One-click generation of medical notes (Symptoms, Diagnoses, Medications) using a Large Language Model.
* **Data Persistence:** Chat history is saved locally via SQLite, ensuring data persists across session refreshes.

## 🛠️ Tech Stack & AI Tools
* **Frontend & Backend:** Streamlit (Python)
* **Database:** SQLite (Embedded relational DB)
* **AI Model:** `Qwen/Qwen2.5-7B-Instruct` (via Hugging Face Inference API)
* **Libraries:** `pandas` (Data handling), `huggingface_hub` (API integration)

## ⚙️ Setup & Installation
1.  **Clone the repository:**
    ```bash
    git clone <your-repo-link>
    cd <repo-name>
    ```
2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
3.  **Configure Environment:**
    Create a `.env` file in the root directory:
    ```text
    HF_API_KEY=your_hugging_face_token
    ```
4.  **Run the application:**
    ```bash
    streamlit run main.py
    ```
DEMO-laptop
<img width="1510" height="713" alt="image" src="https://github.com/user-attachments/assets/8695578a-a410-4aa0-9483-eee5707c2adb" />
<img width="1510" height="713" alt="image" src="https://github.com/user-attachments/assets/8695578a-a410-4aa0-9483-eee5707c2adb" />
IN-mobile
Press arrows from left for summary and search option

## ⚠️ Known Limitations & Trade-offs
* **Audio Transcription:** Due to the strict 1-hour time limit and API constraints, audio is stored as `.wav` files for playback but is not automatically transcribed to text. In a production environment, I would integrate OpenAI Whisper for Speech-to-Text.
* **Database:** SQLite was chosen for ease of deployment and speed. For a scaled production app, this would be replaced with PostgreSQL (RDS) to handle concurrent writes better.
* **AI Latency:** The application relies on the free tier of Hugging Face, which may occasionally experience cold starts or rate limits (handled via error catching in the code).

## 🤖 AI Integration Decisions
I selected the **Qwen 2.5 7B** model because it offers the best balance of reasoning capability (for medical summarization) and free-tier availability. It outperforms smaller models in following formatting instructions for the medical summary.

---
*Built for the Nao Medical SDE Assessment*

