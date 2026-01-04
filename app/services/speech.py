
def generate_ssml(text: str) -> str:
    """
    Generates SSML for Azure TTS with a friendly, professional tone.
    """
    # Escaping XML special characters is important in production, 
    # for simplicity we assume safe text from LLM, but 'replace' is a minimal safety net.
    safe_text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    
    ssml = f"""
    <speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US">
        <voice name="en-US-AvaMultilingualNeural"> 
            <prosody rate="0.9">
                {safe_text}
            </prosody>
        </voice>
    </speak>
    """
    return ssml.strip()
