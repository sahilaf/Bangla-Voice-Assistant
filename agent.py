import logging
import os
from dotenv import load_dotenv

from livekit.agents import AutoSubscribe, JobContext, JobProcess, WorkerOptions, cli, llm
from livekit.agents import Agent, AgentSession
from livekit.plugins import google, silero

from local_stt import LocalBanglaSpeechSTT
from local_tts import LocalEdgeTTS

load_dotenv(dotenv_path=".env")

logger = logging.getLogger("voice-agent")

def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()

async def entrypoint(ctx: JobContext):
    instructions = (
        "আপনি টিম ডিপথিঙ্কারস দ্বারা তৈরি একটি সহায়ক ভয়েস অ্যাসিস্ট্যান্ট। "
        "আপনি বাংলা ভাষা খুব ভালোভাবে বুঝতে ও বলতে পারেন। "
        "সবসময় বাংলা ভাষায় উত্তর দেবেন, যদি ভিন্ন ভাষায় উত্তর দিতে বিশেষভাবে বলা না হয়। "
        "উত্তরগুলো সংক্ষিপ্ত, স্বাভাবিক ও কথোপকথনধর্মী রাখবেন।"
    )

    logger.info(f"connecting to room {ctx.room.name}")
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    # Wait for the first participant to connect
    participant = await ctx.wait_for_participant()
    logger.info(f"starting voice assistant for participant {participant.identity}")

    # Initialize STT with your Colab Gradio URL
    # IMPORTANT: Replace this URL with your actual Gradio URL from Colab
    

    session = AgentSession(
        vad=ctx.proc.userdata["vad"],
        stt = LocalBanglaSpeechSTT(
            api_url="https://88a06ccbe8e9fdd60e.gradio.live",
            username="deepthinkers",
            password="bangla2025",
            timeout=30,  # Optional: request timeout
            max_retries=3  # Optional: retry attempts
        ),
        llm=google.LLM(model="gemini-2.5-flash"),  # Gemini LLM
        tts=LocalEdgeTTS(voice="bn-IN-TanishaaNeural"),  # Edge TTS with Bangla female voice
    )

    agent = Agent(instructions=instructions)

    await session.start(agent, room=ctx.room)

    await session.say("আসসালামু আলাইকুম! আমি কীভাবে আপনাকে সাহায্য করতে পারি?", allow_interruptions=True)

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))