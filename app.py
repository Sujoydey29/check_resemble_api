import gradio as gr
import os
from dotenv import load_dotenv
from resemble import Resemble
import base64
from pydub import AudioSegment
import requests
import time
import mimetypes
import websocket # New import
import json # New import

# Optional translation support
try:
    from googletrans import Translator
    _translator: Translator | None = Translator()
except Exception:
    _translator = None

# --- Step 1: Setup API Key ---
load_dotenv()
RESEMBLE_API_KEY = os.getenv("RESEMBLE_API_KEY")
if not RESEMBLE_API_KEY:
    raise ValueError("RESEMBLE_API_KEY not found! Please create a .env file and add your key.")

Resemble.api_key(RESEMBLE_API_KEY)

# --- Model version choices from the docs ---
# Note: Language support depends on the selected voice, not directly on the model version.
TTS_MODELS = [
    ("Resemble Legacy TTS", "tts-legacy"),
    ("Resemble Enhanced TTS V1", "tts-v1"),
    ("Resemble Enhanced TTS V2", "tts-v2"),
    ("Resemble Enhanced TTS V3", "tts-v3"),
]
STS_MODELS = [
    ("Resemble Legacy STS", "sts-legacy"),
    ("Resemble Core STS V1", "sts-v1"),
    ("Resemble Core STS V2", "sts-v2"),
]

# --- Helpers --- 

def trim_audio(input_path, output_path, max_ms=1000):
    audio = AudioSegment.from_file(input_path)
    trimmed = audio[:max_ms]
    trimmed.export(output_path, format="wav")
    return output_path

def decode_and_save_base64_wav(audio_base64, output_filename):
    audio_bytes = base64.b64decode(audio_base64)
    with open(output_filename, "wb") as f:
        f.write(audio_bytes)
    return output_filename

def download_audio_from_url(url, output_path="output_audio.wav"):
    """Downloads an audio file from a given URL and saves it to the specified path."""
    print(f"Downloading audio from {url} to {output_path}...")
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        print(f"Audio downloaded and saved to {output_path}")
        return output_path
    except Exception as e:
        print(f"Error downloading audio: {e}")
        return None

def _extract_primary_lang(bcp47_code: str) -> str:
    """Return primary language subtag for translation (e.g., 'mr-IN' -> 'mr')."""
    return (bcp47_code or "").split("-")[0].lower()

def maybe_translate_text(input_text: str, target_bcp47_code: str) -> tuple[str, str]:
    """
    Translate input_text to target language if translator is available and the
    language is supported. Returns (text_to_use, note).
    """
    if not input_text:
        return input_text, ""
    if _translator is None:
        return input_text, ""
    try:
        target_primary = _extract_primary_lang(target_bcp47_code)
        # Perform translation only if target is not English and text appears English.
        if target_primary and target_primary != "en":
            translated = _translator.translate(input_text, dest=target_primary)
            return translated.text, f" (translated to {target_primary})"
        return input_text, ""
    except Exception:
        # If translation fails, fall back silently
        return input_text, ""

# --- ENHANCEMENT FUNCTION ---

def enhance_audio(audio_file_path, enhancement_level=1.0, target_loudness=-14, peak_limit=-1):
    if not audio_file_path:
        return None, "Please upload an audio file to enhance."
    print("Enhancing audio via Resemble API...")
    headers = {
        "Authorization": f"Bearer {RESEMBLE_API_KEY}"
    }
    url = "https://app.resemble.ai/api/v2/audio_enhancements"
    mime_type, _ = mimetypes.guess_type(audio_file_path)
    with open(audio_file_path, "rb") as f:
        files = {
            "audio_file": (os.path.basename(audio_file_path), f, mime_type)
        }
        data = {
            "enhancement_level": str(enhancement_level),  # 0.0–1.0
            "loudness_target_level": str(target_loudness),  # -70 to -5
            "loudness_peak_limit": str(peak_limit)  # -9 to 0
        }
        try:
            res = requests.post(url, headers=headers, files=files, data=data)
            if not res.ok:
                print("RESPONSE:", res.text)
            res.raise_for_status()
            result = res.json()
            if not result.get('success', False):
                return None, result.get('error_message', 'Enhancement failed!')
            job_uuid = result['uuid']
            get_url = f"https://app.resemble.ai/api/v2/audio_enhancements/{job_uuid}"
            for _ in range(60):
                poll = requests.get(get_url, headers=headers)
                poll.raise_for_status()
                poll_res = poll.json()
                if poll_res["status"] == "completed" and poll_res.get("enhanced_audio_url"):
                    print("Enhancement successful!")
                    return poll_res["enhanced_audio_url"], "Audio enhanced successfully"
                elif poll_res["status"] == "failed":
                    return None, poll_res.get("error_message", "Enhancement failed!")
                elif poll_res["status"] == "in_progress":
                    print("Enhancement still in progress...")
                time.sleep(2)
            return None, "Timeout: Enhancement not completed in time."
        except Exception as e:
            return None, f"Enhancement error: {e}"

# --- Step 2: Core Functions ---

def get_all_projects():
    print("Fetching projects...")
    try:
        response = Resemble.v2.projects.all(page=1, page_size=20)
        if 'items' in response:
            project_names = [p['name'] for p in response['items']]
            all_projects_data = response['items']
            print(f"Found {len(project_names)} projects.")
            return gr.update(choices=project_names), all_projects_data
        else:
            print(f"Error: Could not fetch projects. API Response: {response}")
            return gr.update(choices=[]), []
    except Exception as e:
        print(f"An exception occurred while fetching projects: {e}")
        return gr.update(choices=[]), []

def get_voices_in_project(selected_project_name, all_projects_data):
    if not selected_project_name:
        return gr.update(choices=[]), "", []
    print(f"Fetching voices for project: {selected_project_name}")
    project_uuid = next((p['uuid'] for p in all_projects_data if p['name'] == selected_project_name), None)
    if not project_uuid:
        print("Error: Project UUID not found.")
        return gr.update(choices=[]), "Project UUID not found", []
    try:
        response = Resemble.v2.voices.all(page=1, page_size=20)
        if 'items' in response:
            project_voices = response['items']
            voice_names = [v['name'] for v in project_voices]
            print(f"Found {len(voice_names)} voices.")
            return gr.update(choices=voice_names), project_uuid, project_voices
        else:
            print(f"Error fetching voices: The API response did not contain an 'items' key. Full response: {response}")
            return gr.update(choices=[]), project_uuid, []
    except Exception as e:
        print(f"An unexpected exception occurred while fetching voices: {e}")
        return gr.update(choices=[]), project_uuid, []

def get_voice_uuid(selected_voice_name, all_voices_data):
    if not selected_voice_name:
        return "Please select a voice"
    voice_uuid = next((v['uuid'] for v in all_voices_data if v['name'] == selected_voice_name), "Voice UUID not found")
    print(f"Selected voice '{selected_voice_name}' with UUID: {voice_uuid}")
    return voice_uuid

def generate_tts_clip(text, voice_uuid, project_uuid, language_code="en-US", auto_translate=True):
    if not all([text, voice_uuid, project_uuid]):
        return None, "Missing text, voice UUID, or project UUID."
    print(f"Generating TTS for voice: {voice_uuid} in language: {language_code}")
    start_time = time.time()
    try:
        # Optionally translate user input text into selected language
        text_to_use = text
        translate_note = ""
        if auto_translate:
            text_to_use, translate_note = maybe_translate_text(text, language_code)
        # Wrap the text in an SSML <lang> tag
        ssml_body = f'<speak><lang xml:lang="{language_code}">{text_to_use}</lang></speak>'
        response = Resemble.v2.clips.create_sync(
            project_uuid=project_uuid,
            voice_uuid=voice_uuid,
            body=ssml_body,
            title="TTS Clip",
            output_format="wav",
        )

        print(f"DEBUG: TTS create_sync response: {response}")
        clip_src = response['item']['audio_src']
        output_filename = "tts_output.wav"
        downloaded_path = download_audio_from_url(clip_src, output_filename)
        end_time = time.time()
        rtt = round((end_time - start_time) * 1000, 2)
        if downloaded_path:
            print("TTS clip generated and saved successfully.")
            return downloaded_path, f"TTS clip generated successfully. RTT: {rtt} ms{translate_note}"
        else:
            return None, "Failed to download TTS clip."
    except Exception as e:
        error_message = f"Error generating TTS clip: {e}"
        return None, f"{error_message} RTT: N/A"

def generate_ssml_tts_clip(ssml, voice_uuid, project_uuid, language_code="en-US"):
    if not all([ssml, voice_uuid, project_uuid]):
        return None, "Missing SSML, voice UUID, or project UUID."
    print(f"Generating SSML TTS for voice: {voice_uuid} in language: {language_code}")
    print("Note: For SSML, please ensure your SSML body includes the <lang xml:lang='your-code'> tag for language specification.")
    start_time = time.time()
    try:
        response = Resemble.v2.clips.create_sync(
            project_uuid=project_uuid,
            voice_uuid=voice_uuid,
            body=ssml, # User is responsible for including <lang> tag in SSML
            title="SSML Clip",
            output_format="wav",
        )
        print(f"DEBUG: SSML TTS create_sync response: {response}")
        if not response.get('success'):
            error_message = response.get('message', 'Unknown SSML synthesis error.')
            print(f"Error generating SSML TTS clip: {error_message}")
            return None, error_message
        clip_src = response['item']['audio_src']
        output_filename = "ssml_tts_output.wav"
        downloaded_path = download_audio_from_url(clip_src, output_filename)
        end_time = time.time()
        rtt = round((end_time - start_time) * 1000, 2)
        if downloaded_path:
            print("SSML TTS clip generated and saved successfully.")
            return downloaded_path, f"SSML TTS clip generated successfully. RTT: {rtt} ms"
        else:
            return None, "Failed to download SSML TTS clip."
    except Exception as e:
        error_message = f"Error generating SSML TTS clip: {e}"
        print(error_message)
        return None, f"{error_message} RTT: N/A"

def generate_streaming_tts(text, voice_uuid, project_uuid, language_code="en-US", auto_translate=True):
    if not all([text, voice_uuid, project_uuid]):
        return None, "Missing streaming input"
    print(f"Streaming TTS: Streaming Text-to-Speech (HTTP POST, real-time audio), voice {voice_uuid}, language {language_code}")
    url = "https://f.cluster.resemble.ai/stream"
    headers = {
        "Authorization": f"Bearer {RESEMBLE_API_KEY}",
        "Content-Type": "application/json"
    }
    # Optionally translate
    text_to_use = text
    translate_note = ""
    if auto_translate:
        text_to_use, translate_note = maybe_translate_text(text, language_code)
    # Wrap the text in an SSML <lang> tag
    ssml_data = f'<speak><lang xml:lang="{language_code}">{text_to_use}</lang></speak>'
    payload = {
        "project_uuid": project_uuid,
        "voice_uuid": voice_uuid,
        "data": ssml_data,
        "precision": "PCM_16", # Optional, setting a default
        "sample_rate": 44100, # Optional, setting a default
    }
    start_time = time.time()
    first_chunk_time = None
    try:
        # Stream response as WAV
        r = requests.post(url, headers=headers, json=payload, stream=True)
        if not r.ok:
            error_details = r.text # Capture full error response
            print("Stream error:", error_details)
            return None, f"Streaming error: {error_details} RTT: N/A"
        wav_path = "tts_streamed_output.wav"
        with open(wav_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    if first_chunk_time is None:
                        first_chunk_time = time.time()
                    f.write(chunk)
        end_time = time.time()
        total_rtt = round((end_time - start_time) * 1000, 2)
        first_byte_latency = round((first_chunk_time - start_time) * 1000, 2) if first_chunk_time else "N/A"
        print("Streaming TTS completed.")
        return wav_path, f"Streaming TTS completed. Total RTT: {total_rtt} ms, First Byte Latency: {first_byte_latency} ms{translate_note}"
    except Exception as e:
        return None, f"Streaming error: {e} RTT: N/A"

def generate_streaming_tts_websocket(text, voice_uuid, project_uuid, language_code="en-US", auto_translate=True):
    if not all([text, voice_uuid, project_uuid]):
        return None, "Missing streaming input (WebSocket)"

    print(f"Streaming TTS (WebSocket): voice {voice_uuid}, language {language_code}")
    websocket_url = "wss://websocket.cluster.resemble.ai/stream"
    output_filename = "tts_streamed_websocket_output.wav"

    start_time = time.time()
    first_chunk_time = None
    try:
        ws = websocket.create_connection(websocket_url,
                                         header={'Authorization': f'Bearer {RESEMBLE_API_KEY}'})

        # Send synthesis request
        # Optionally translate
        text_to_use = text
        translate_note = ""
        if auto_translate:
            text_to_use, translate_note = maybe_translate_text(text, language_code)
        # Wrap the text in an SSML <lang> tag
        ssml_data = f'<speak><lang xml:lang="{language_code}">{text_to_use}</lang></speak>'
        payload = {
            "voice_uuid": voice_uuid,
            "project_uuid": project_uuid,
            "data": ssml_data,
            "binary_response": True,
            "output_format": "wav",
            "sample_rate": 44100,
            "precision": "PCM_16",
        }
        ws.send(json.dumps(payload))

        with open(output_filename, "wb") as f:
            while True:
                message = ws.recv()
                if isinstance(message, str):
                    # JSON message (e.g., termination or error)
                    data = json.loads(message)
                    if data.get("type") == "audio_end":
                        print("WebSocket audio stream ended.")
                        break
                    elif data.get("type") == "error":
                        error_message = data.get("message", "Unknown WebSocket error")
                        # Check for specific Unauthorized error from server
                        if "Unauthorized" in error_message:
                            error_message += ". Please ensure you have a Resemble AI Business Plan or higher."
                        print(f"WebSocket error: {error_message}")
                        ws.close()
                        return None, f"Streaming (WebSocket) error: {error_message} RTT: N/A"
                elif isinstance(message, bytes):
                    # Binary audio data
                    if first_chunk_time is None:
                        first_chunk_time = time.time()
                    f.write(message)

        ws.close()
        end_time = time.time()
        total_rtt = round((end_time - start_time) * 1000, 2)
        first_byte_latency = round((first_chunk_time - start_time) * 1000, 2) if first_chunk_time else "N/A"
        print("Streaming TTS (WebSocket) completed.")
        return output_filename, f"Streaming TTS (WebSocket) completed. Total RTT: {total_rtt} ms, First Byte Latency: {first_byte_latency} ms{translate_note}"

    except websocket.WebSocketConnectionClosedException:
        return None, "WebSocket connection closed unexpectedly. Ensure you have a Business Plan or higher. RTT: N/A"
    except Exception as e:
        return None, f"Streaming (WebSocket) error: {e} RTT: N/A"

def generate_sts_batch_clip(source_audio_path, voice_uuid, project_uuid, sts_model_code, language_code="en-US"):
    if not all([source_audio_path, voice_uuid, project_uuid]):
        return None, "Missing source audio, voice UUID, or project UUID."
    print(f"[STS BATCH] Batch STS with model {sts_model_code} and language {language_code}...")
    temp_path = None # Initialize temp_path for cleanup
    start_time = time.time()
    try:
        with open(source_audio_path, "rb") as f:
            audio_bytes = f.read()
            audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")

        # Check and auto-trim audio if base64 length exceeds limit (approx 2000 characters for a short clip)
        if len(audio_base64) > 2000:
            print("Input audio too long for low-latency STS. Attempting to trim to 900ms...")
            temp_path = "trimmed_sts_audio.wav"
            trim_audio(source_audio_path, temp_path, max_ms=900)
            with open(temp_path, "rb") as f_short:
                audio_bytes_short = f_short.read()
                audio_base64 = base64.b64encode(audio_bytes_short).decode("utf-8")
            if len(audio_base64) > 2000:
                return None, "Audio is too long for STS (even after trimming to 900ms). Use a shorter recording (~0.5 sec)."
            print("Audio trimmed successfully to 900ms.")

        url = "https://f.cluster.resemble.ai/synthesize"
        headers = {
            "Authorization": f"Bearer {RESEMBLE_API_KEY}",
            "Content-Type": "application/json",
            "Accept-Encoding": "gzip, deflate, br"
        }
        # Wrap the data payload in an SSML <lang> tag
        ssml_data = f'<speak><lang xml:lang="{language_code}"><resemble:convert src="data:audio/wav;base64,{audio_base64}"></resemble:convert></lang></speak>'
        payload = {
            "voice_uuid": voice_uuid,
            "project_uuid": project_uuid,
            "data": ssml_data,
            "output_format": "wav",
            "sample_rate": 44100 # Default sample rate, can be made configurable if needed
        }

        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()

        if not result.get('success'):
            error_message = result.get('message', 'Unknown STS synthesis error.')
            print(f"Error generating batch STS clip: {error_message}")
            return None, error_message

        # Decode base64 audio content from response
        audio_content_base64 = result['audio_content']
        decoded_audio_bytes = base64.b64decode(audio_content_base64)

        output_filename = "resemble_sts_output.wav"
        with open(output_filename, "wb") as f:
            f.write(decoded_audio_bytes)

        end_time = time.time()
        rtt = round((end_time - start_time) * 1000, 2)
        print("Batch STS clip generated successfully.")
        return output_filename, f"Speech-to-Speech clip generated! RTT: {rtt} ms"

    except Exception as e:
        error_message = f"Error generating batch STS clip: {e}"
        print(error_message)
        return None, f"{error_message} RTT: N/A"
    finally:
        # Cleanup temporary file if it was created
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)

def clone_voice(voice_name, audio_file_path, project_uuid, language_code="en-US"):
    if not all([voice_name, audio_file_path, project_uuid]):
        return "Missing voice name, audio file, or project UUID."
    print(f"Cloning voice '{voice_name}' for language {language_code}...")
    print("Note: The 'language_code' for cloning is informative; the cloned voice's language capabilities depend on the training audio provided.")
    try:
        with open(audio_file_path, 'rb') as f:
            voice_response = Resemble.v2.voices.create(project_uuid, {'name': voice_name})
            print(f"DEBUG: Voice create response: {voice_response}")
            voice_uuid = voice_response['item']['uuid']
            Resemble.v2.recordings.create(voice_uuid, f, name=f"{voice_name} sample")
            Resemble.v2.voices.build(voice_uuid)
            message = f"Voice '{voice_name}' (UUID: {voice_uuid}) is now being built. Check your Resemble project dashboard for progress."
            print(message)
            return message
    except Exception as e:
        error_message = f"Error cloning voice: {e}"
        print(error_message)
        return error_message

# --- Step 3: Build the Gradio Interface ---

with gr.Blocks(theme=gr.themes.Soft(), title="Resemble AI Test Suite") as demo:
    gr.Markdown("# Resemble AI Feature Tester")
    gr.Markdown("Test Resemble API: Text-to-Speech, SSML TTS, Streaming TTS, Speech-to-Speech, Cloning, Enhancing.")

    all_projects_data_state = gr.State([])
    all_voices_data_state = gr.State([])

    with gr.Row():
        fetch_projects_btn = gr.Button("1. Connect & Fetch Projects", variant="primary")
        project_dropdown = gr.Dropdown(label="2. Select a Project", interactive=True)
        voice_dropdown = gr.Dropdown(label="3. Select a Voice", interactive=True)
    with gr.Row():
        project_uuid_output = gr.Textbox(label="Selected Project UUID", interactive=False)
        voice_uuid_output = gr.Textbox(label="Selected Voice UUID", interactive=False)
    language_dropdown = gr.Dropdown(
        label="Select Language (for SSML <lang> tag)",
        choices=[
            ("English (US)", "en-US"),
            ("Spanish (Spain)", "es-ES"),
            ("French (France)", "fr-FR"),
            ("German (Germany)", "de-DE"),
            ("Italian (Italy)", "it-IT"),
            ("Japanese (Japan)", "ja-JP"),
            ("Korean (Korea)", "ko-KR"),
            ("Mandarin (China)", "zh-CN"),
            ("Dutch (Netherlands)", "nl-NL"),
            ("Hindi (India)", "hi-IN"),
            # Indian languages requested
            ("Assamese", "as-IN"),
            ("Bengali", "bn-IN"),
            ("Bodo", "brx-IN"),
            ("Dogri", "doi-IN"),
            ("Gujarati", "gu-IN"),
            ("Kashmiri", "ks-IN"),
            ("Kannada", "kn-IN"),
            ("Konkani", "kok-IN"),
            ("Maithili", "mai-IN"),
            ("Malayalam", "ml-IN"),
            ("Manipuri (Meitei)", "mni-IN"),
            ("Marathi", "mr-IN"),
            ("Nepali", "ne-IN"),
            ("Odia (Oriya)", "or-IN"),
            ("Punjabi", "pa-IN"),
            ("Sanskrit", "sa-IN"),
            ("Santali", "sat-IN"),
            ("Sindhi", "sd-IN"),
            ("Tamil", "ta-IN"),
            ("Telugu", "te-IN"),
            ("Urdu", "ur-IN"),
        ],
        value="en-US", # Default language
        interactive=True
    )
    auto_translate_checkbox = gr.Checkbox(value=True, label="Auto-translate input text to selected language")
    fetch_projects_btn.click(
        fn=get_all_projects,
        outputs=[project_dropdown, all_projects_data_state]
    )
    project_dropdown.change(
        fn=get_voices_in_project,
        inputs=[project_dropdown, all_projects_data_state],
        outputs=[voice_dropdown, project_uuid_output, all_voices_data_state]
    )
    voice_dropdown.change(
        fn=get_voice_uuid,
        inputs=[voice_dropdown, all_voices_data_state],
        outputs=[voice_uuid_output]
    )

    with gr.Tabs():
        with gr.TabItem("🎙️ Text-to-Speech"):
            gr.Markdown("## Text-to-Speech (plain text to voice)")
            tts_model_dropdown = gr.Dropdown(
                choices=[f"{n} ({c})" for n, c in TTS_MODELS],
                value=None,
                label="TTS Model Version"
            )
            with gr.Row():
                tts_input = gr.Textbox(label="Text to Synthesize", placeholder="Enter your text here...")
                tts_button = gr.Button("Generate TTS Clip", variant="primary")
            tts_audio_output = gr.Audio(label="Generated Audio")
            tts_status_output = gr.Textbox(label="Status", interactive=False)
            tts_button.click(
                fn=lambda text, vuuid, puuid, lang_code, do_tr: generate_tts_clip(text, vuuid, puuid, lang_code, do_tr),
                inputs=[tts_input, voice_uuid_output, project_uuid_output, language_dropdown, auto_translate_checkbox],
                outputs=[tts_audio_output, tts_status_output]
            )

        with gr.TabItem("📝 SSML TTS"):
            gr.Markdown("## SSML Text-to-Speech (voice with pitch, emphasis, audio, prosody, breaks, etc)")
            gr.Markdown("Paste SSML below (example: <speak>Hello <prosody pitch='high'>world</prosody>!</speak>). See [SSML Reference](https://docs.app.resemble.ai/docs/getting_started/ssml) for supported tags.")
            with gr.Row():
                tts_model_dropdown = gr.Dropdown(
                choices=[f"{n} ({c})" for n, c in TTS_MODELS],
                value=None,
                label="TTS Model Version"
            )
                ssml_input = gr.Textbox(label="SSML (paste markup)", placeholder="<speak><break time='500ms'/><prosody pitch='low'>Hello</prosody></speak>")
                ssml_button = gr.Button("Generate SSML TTS Clip", variant="primary")
            ssml_audio_output = gr.Audio(label="Generated SSML Audio")
            ssml_status_output = gr.Textbox(label="Status", interactive=False)
            ssml_button.click(
                fn=lambda ssml, vuuid, puuid, lang_code: generate_ssml_tts_clip(ssml, vuuid, puuid, lang_code),
                inputs=[ssml_input, voice_uuid_output, project_uuid_output, language_dropdown],
                outputs=[ssml_audio_output, ssml_status_output]
            )

        with gr.TabItem("🔊 Streaming TTS (HTTP)"):
            gr.Markdown("## Streaming Text-to-Speech (HTTP POST, real-time audio)")
            with gr.Row():
                tts_model_dropdown = gr.Dropdown(
                choices=[f"{n} ({c})" for n, c in TTS_MODELS],
                value=None,
                label="TTS Model Version"
            )
                stream_input = gr.Textbox(label="Text to Synthesize (streamed)", placeholder="Enter your text for streaming TTS here...")
                stream_button = gr.Button("Generate Streaming TTS", variant="primary")
            stream_audio_output = gr.Audio(label="Generated Streaming Audio")
            stream_status_output = gr.Textbox(label="Status", interactive=False)
            stream_button.click(
                fn=lambda text, vuuid, puuid, lang_code, do_tr: generate_streaming_tts(text, vuuid, puuid, lang_code, do_tr),
                inputs=[stream_input, voice_uuid_output, project_uuid_output, language_dropdown, auto_translate_checkbox],
                outputs=[stream_audio_output, stream_status_output]
            )

        with gr.TabItem("🔊 Streaming TTS (Websocket)"):
            gr.Markdown("## Streaming Text-to-Speech (Websocket, real-time audio)")
            gr.Markdown("Note: Websockets API is only available for Business plan users. If you're running into trouble, upgrade to a Business plan or higher on the billing page.")
            with gr.Row():
                tts_model_dropdown = gr.Dropdown(
                choices=[f"{n} ({c})" for n, c in TTS_MODELS],
                value=None,
                label="TTS Model Version"
            )
                websocket_stream_input = gr.Textbox(label="Text to Synthesize (streamed via WebSocket)", placeholder="Enter your text for streaming TTS via WebSocket here...")
                websocket_stream_button = gr.Button("Generate Streaming TTS (WebSocket)", variant="primary")
            websocket_stream_audio_output = gr.Audio(label="Generated Streaming Audio (WebSocket)")
            websocket_stream_status_output = gr.Textbox(label="Status (WebSocket)", interactive=False)
            websocket_stream_button.click(
                fn=lambda text, vuuid, puuid, lang_code, do_tr: generate_streaming_tts_websocket(text, vuuid, puuid, lang_code, do_tr),
                inputs=[websocket_stream_input, voice_uuid_output, project_uuid_output, language_dropdown, auto_translate_checkbox],
                outputs=[websocket_stream_audio_output, websocket_stream_status_output]
            )

        with gr.TabItem("🎙️ Speech-to-Speech (Long Audio)"):
            gr.Markdown("## Speech-to-Speech (Batch, Long Audio)")
            sts_model_dropdown = gr.Dropdown(
                choices=[f"{n} ({c})" for n, c in STS_MODELS],
                value=f"{STS_MODELS[-1][0]} ({STS_MODELS[-1][1]})",
                label="STS Model Version"
            )
            sts_batch_input_audio = gr.Audio(label="Upload Source Audio for STS (Long Audio Supported)", type="filepath")
            sts_batch_button = gr.Button("Generate STS Clip (Batch/Large Audio)", variant="primary")
            audio_output = gr.Audio(label="Generated Audio")
            status_output = gr.Textbox(label="Status", interactive=False)
            def extract_code(fancy):
                return fancy.split('(')[1].split(')')[0] if '(' in fancy and ')' in fancy else None
            sts_batch_button.click(
                fn=lambda audio, vuuid, puuid, fancy, lang_code: generate_sts_batch_clip(audio, vuuid, puuid, extract_code(fancy), lang_code),
                inputs=[sts_batch_input_audio, voice_uuid_output, project_uuid_output, sts_model_dropdown, language_dropdown],
                outputs=[audio_output, status_output]
            )

        with gr.TabItem("🧬 Clone Voices"):
            gr.Markdown("## Create New Voices")
            with gr.Row():
                with gr.Column():
                    gr.Markdown("### Clone a Voice from an Audio File")
                    clone_voice_name = gr.Textbox(label="New Voice Name")
                    clone_audio_sample = gr.Audio(label="Upload a clean audio sample (at least 30 seconds is recommended)", type="filepath")
                    clone_button = gr.Button("Start Cloning", variant="primary")
                    clone_status = gr.Textbox(label="Cloning Status", interactive=False)
                    clone_button.click(
                        fn=lambda name, audio, puuid, lang_code: clone_voice(name, audio, puuid, lang_code),
                        inputs=[clone_voice_name, clone_audio_sample, project_uuid_output, language_dropdown],
                        outputs=[clone_status]
                    )
        with gr.TabItem("✨ Audio Enhancement"):
            gr.Markdown("## Enhance an Audio Recording")
            gr.Markdown("Upload any audio file to see if enhancement is available.")
            with gr.Row():
                enhance_input_audio = gr.Audio(label="Upload Audio to Enhance", type="filepath")
                enhance_output_audio = gr.Audio(label="Enhanced Audio")
            enhance_button = gr.Button("Enhance Audio", variant="primary")
            enhance_status = gr.Textbox(label="Status", interactive=False)
            enhance_button.click(
                fn=enhance_audio,
                inputs=[enhance_input_audio],
                outputs=[enhance_output_audio, enhance_status]
            )

if __name__ == "__main__":
    demo.launch()
