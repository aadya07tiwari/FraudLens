# FraudLens AI — Local Setup

1. Clone the repo:
   git clone https://github.com/millyshreenp-ship-it/FraudLens.git
   cd FraudLens

2. Install dependencies:
   python -m pip install -r requirements.txt

3. Copy the env template and add your API key:
   cp .env.example .env
   # then edit .env and paste your real Anthropic API key

4. Run the app:
   python -m streamlit run app.py

