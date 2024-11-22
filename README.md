# **Simple Archive Website**

A simple production-ready project for educational purpose. It is a web-based archive system for managing and searching newspaper issues, built using Flask and MySQL with full-text search functionality. The project is deployed on Google Cloud Run.

---

## **Features**

- **Search Functionality:** Full-text search using MySQL.
- **Organized Storage:** Archive newspaper issues with metadata like issue date and author.
- **Efficient Deployment:** Deployed on Google Cloud Run for scalability and accessibility.
- **User-Friendly Design:** Simple and intuitive web interface for searching and viewing archives.

---

## **Table of Contents**

1. [Installation](#installation)
2. [Usage](#usage)
3. [Features](#features)
4. [Technologies Used](#technologies-used)
5. [Deployment](#deployment)
6. [License](#license)

---

## **Installation**

### Prerequisites

- Python 3.11 or later
- MySQL server
- Google Cloud CLI (for deployment)
- Flask and related dependencies

### Steps

1. **Clone the Repository**

   ```bash
   git clone https://github.com/username/archive-website.git
   cd archive-website
   ```

2. **Set Up Virtual Environment**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Set Up MySQL**
   - Create a database for the archive.
   - Run the provided SQL script to set up the schema:

     ```bash
     mysql -u your_username -p your_database < schema.sql
     ```

5. **Configure Configs**
   Follow the comment in the `config.py`

6. **Run the Application**

   ```bash
   python app.py
   ```

---

## **Usage**

Open your browser and navigate to `http://127.0.0.1:5000`. Use admin account to login to manage issues and users using 'Admin' panel in menu; Or login with a normal user for basic search and download documents.

---

## **Technologies Used**

- **Backend:** Flask, SQLAlchemy
- **Database:** MySQL with full-text search
- **Deployment:** Google Cloud Run
- **Storage:** Google Cloud Storage
- **Frontend:** Basic HTML/CSS templates rendered via Jinja2

---

## **Deployment**

### Deploy on Google Cloud Run

Fork this repo and deploy this repo using Google Cloud Run

---

## **License**

This project is licensed under the MIT License. See `LICENSE` for details.
