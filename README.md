# Email_To_Order_Automation
A system that extracts structured order information from unstructured email content using NLP and pattern matching.

## Overview
This system extracts structured order information from unstructured email content, including:
- Customer information
- Product details (SKU, quantity, price)
- Shipping address
- Delivery dates
- Contact information

## Features
- Processes multiple email formats
- Handles variations in product descriptions
- Extracts delivery dates in different formats
- Identifies priority/urgent orders
- Provides confidence scores for extracted data
- Streamlit web interface for easy interaction
- Export capabilities (JSON, CSV)


# 2. Create and activate a virtual environment:
- python -m venv venv
- source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3.Install dependencies:
pip install -r requirements.txt

# 4. Download spaCy language model:
python -m spacy download en_core_web_sm

# 5. Running the Application
* Web Interface (Streamlit)
  - streamlit run streamlit_app.py
 
* Command Line Interface
  - python main.py



## Sample Emails
The system handles various email formats including:

Simple personal orders

Complex corporate orders

Urgent/rush orders

Orders with special instructions
