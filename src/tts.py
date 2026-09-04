import edge_tts
import base64

async def generate_audio_base64(text: str, voice: str = "en-US-AriaNeural") -> str:
    """
    Generates spoken audio from text using Microsoft Edge TTS
    and returns it as a base64 encoded string.
    """
    if not text:
        return None
        
    try:
        communicate = edge_tts.Communicate(text, voice)
        audio_data = bytearray()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data.extend(chunk["data"])
        
        return base64.b64encode(audio_data).decode("utf-8")
    except Exception as e:
        print(f"TTS Error: {e}")
        return None
