# Email Generation Setup

This document describes the technical setup for generating and previewing the Kubi Weekly Digest email.

## 🛠️ Technology Stack

The system consists of two main components:

1.  **Data Processing (Python)**
    *   **Language**: Python 3.11+
    *   **Libraries**: `json` (Standard Lib), `datetime`
    *   **Role**: Processes `films.json`, filters for new arrivals, calculates ratings, and exports the data.

2.  **Email Templating (Node.js + React)**
    *   **Framework**: [React Email](https://react.email/)
    *   **Language**: TypeScript / React
    *   **Role**: Renders the data into a responsive HTML email template.

---

## 🚀 Installation

### 1. Python Environment

Ensure you have Python 3 installed. Install the requirements (if using a virtual environment, activate it first):

```bash
cd backend
pip install -r requirements.txt
```

### 2. Node.js Environment

Navigate to the emails directory and install dependencies:

```bash
cd backend/emails
npm install
```

---

## 🏃‍♂️ Running the Server (Email Preview)

React Email provides a local development server to preview templates with live reloading.

1.  Start the development server:

    ```bash
    cd backend/emails
    npm run dev
    ```

2.  Open your browser to [http://localhost:3000](http://localhost:3000)

3.  Select **weekly-digest** from the sidebar to view the template.

---

## 💾 Data Generation

The email template (`weekly-digest.tsx`) is designed to read dynamic data from a JSON file.

*   **Input**: `films.json` (Source of Truth)
*   **Intermediate**: `tmp/weekly_digest.json` (Consumed by React Email)
*   **Component Path**: `backend/emails/emails/weekly-digest.tsx`

> **Note**: The React component looks for `tmp/weekly_digest.json`. If this file is missing, it falls back to hardcoded sample data (e.g., "Senna").

The generation step is fully wired into CI. The [`weekly-digest.yml`](../.github/workflows/weekly-digest.yml)
workflow runs every Friday: it fetches `films.json.gz` from the `database` branch,
unzips it, and runs `backend/generate_weekly_digest.py` to produce the digest artifact
before rendering and sending the email via React Email.

To reproduce it locally, run the generation script against a local `films.json`:

```bash
python3 backend/generate_weekly_digest.py --input films.json --output backend/tmp/weekly_digest.md
```

---

_Last updated: 2026-09-03_
