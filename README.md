# Trendly Support Agent

A Streamlit customer-support chatbot for Trendly orders, returns, shipping, and
policy questions. It uses Groq function calling to ground answers in the local
order data and policy document.

## Run locally

1. Create a Groq API key in the [Groq Console](https://console.groq.com/keys).
2. Set it in your environment:

   ```powershell
   $env:GROQ_API_KEY = "your-key"
   ```

3. Install and run:

   ```powershell
   pip install -r requirements.txt
   streamlit run app.py
   ```

## Deploy to Render

The included `render.yaml` creates a Python web service. In Render, connect the
GitHub repository, select **New +** → **Blueprint**, and set `GROQ_API_KEY` as
a secret environment variable. Render provides the `PORT` value automatically.

Never commit your Groq key. The application will show a clear setup message if
the key has not been configured.
