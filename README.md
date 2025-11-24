# Bangla Voice Assistant Agent

This is a Python-based voice assistant that speaks and understands Bangla using LiveKit, Gemini, and Deepgram.

## Prerequisites

1.  **Python 3.9+** installed.
2.  **LiveKit Cloud Account** (Free): [https://cloud.livekit.io/](https://cloud.livekit.io/)
    -   Create a project and get `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`.
3.  **Google Gemini API Key**: [https://aistudio.google.com/](https://aistudio.google.com/)
    -   Get `GOOGLE_API_KEY`.
4.  **Deepgram API Key**: [https://console.deepgram.com/](https://console.deepgram.com/)
    -   Get `DEEPGRAM_API_KEY`.
5.  **Google Cloud Credentials** (Optional but recommended for TTS):
    -   For `google.TTS` to work best, you might need Application Default Credentials if the API key isn't enough for Cloud TTS.
    -   Alternatively, you can try switching to Deepgram TTS in `agent.py` if you don't have GCP set up, but Bangla support might be limited.

## Setup

1.  Navigate to the agent directory:
    ```bash
    cd agent
    ```

2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

3.  Set up environment variables:
    -   Edit `.env` and fill in your API keys.

## Running the Agent

To run the agent in development mode (connects to your LiveKit project):

```bash
python agent.py dev
```

## Testing

1.  Go to the **LiveKit Agents Playground**: [https://agents-playground.livekit.io/](https://agents-playground.livekit.io/)
2.  Connect using your LiveKit URL and Token (you can generate a token in your LiveKit Cloud dashboard).
3.  Or, simply use the "Connect" button in the Playground if you are logged in.
4.  Once connected, the agent should join the room and greet you in Bangla.
