# Resemble AI Feature Tester - Metrics and Settings

This document outlines the key metrics and settings observed and calculated from the Resemble AI Feature Tester application.

## 1. Application Overview
The application (`app.py`) provides a Gradio interface to test various Resemble AI functionalities including:
- Text-to-Speech (TTS)
- SSML Text-to-Speech
- Streaming TTS (HTTP)
- Streaming TTS (WebSocket)
- Speech-to-Speech (STS)
- Voice Cloning
- Audio Enhancement

## 2. Key Settings and Configuration

### API Key
- **`RESEMBLE_API_KEY`**: Loaded from a `.env` file for secure API access. This is essential for all API interactions.

### Project and Voice Selection
- **Selected Project UUID (Example)**: `682842c1`
- **Selected Voice UUID (Example)**: `abbbc383`
- **Supported Languages**:
    - English (US): `en-US`
    - Spanish (Spain): `es-ES`
    - French (France): `fr-FR`
    - German (Germany): `de-DE`
    - Italian (Italy): `it-IT`
    - Japanese (Japan): `ja-JP`
    - Korean (Korea): `ko-KR`
    - Mandarin (China): `zh-CN`
    - Dutch (Netherlands): `nl-NL`
    - Hindi (India): `hi-IN`
    - Assamese: `as-IN`
    - Bengali: `bn-IN`
    - Bodo: `brx-IN`
    - Dogri: `doi-IN`
    - Gujarati: `gu-IN`
    - Kashmiri: `ks-IN`
    - Kannada: `kn-IN`
    - Konkani: `kok-IN`
    - Maithili: `mai-IN`
    - Malayalam: `ml-IN`
    - Manipuri (or Meitei): `mni-IN`
    - Marathi: `mr-IN`
    - Nepali: `ne-IN`
    - Odia (formerly Oriya): `or-IN`
    - Punjabi: `pa-IN`
    - Sanskrit: `sa-IN`
    - Santali: `sat-IN`
    - Sindhi: `sd-IN`
    - Tamil: `ta-IN`
    - Telugu: `te-IN`
    - Urdu: `ur-IN`

### Model Versions
- **Text-to-Speech (TTS) Models**:
    - Resemble Legacy TTS (`tts-legacy`)
    - Resemble Enhanced TTS V1 (`tts-v1`)
    - Resemble Enhanced TTS V2 (`tts-v2`)
    - Resemble Enhanced TTS V3 (`tts-v3`)
- **Speech-to-Speech (STS) Models**:
    - Resemble Legacy STS (`sts-legacy`)
    - Resemble Core STS V1 (`sts-v1`)
    - Resemble Core STS V2 (`sts-v2`)

### Audio Enhancement Parameters
- **`enhancement_level`**: Range 0.0-1.0 (Default: 1.0)
- **`loudness_target_level`**: Range -70 to -5 (Default: -14)
- **`loudness_peak_limit`**: Range -9 to 0 (Default: -1)

### Streaming TTS Parameters
- **`precision`**: `PCM_16`
- **`sample_rate`**: `44100`

## 3. Performance Metrics (Round Trip Time - RTT)

RTT measures the time taken for a request to be sent to the Resemble AI API and for the complete response (audio clip) to be received.

### Text-to-Speech (Plain Text)
- **Calculation**: Time from API call initiation to audio download completion.
- **Example RTT (from screenshot)**: Not explicitly shown in the provided TTS clip, but the format is `TTS clip generated successfully. RTT: XXXX.XX ms`.

### SSML Text-to-Speech
- **Calculation**: Time from API call initiation to audio download completion.
- **Example RTT (from screenshot)**: `18145.86 ms`

### Streaming TTS (HTTP POST)
- **Calculation**:
    - **Total RTT**: Time from API call initiation to complete audio stream reception.
    - **First Byte Latency**: Time from API call initiation to the reception of the first audio chunk.
- **Example Total RTT (from screenshot)**: `17501.26 ms`
- **Example First Byte Latency (from screenshot)**: `1092.38 ms`

### Streaming TTS (WebSocket)
- **Calculation**:
    - **Total RTT**: Time from WebSocket connection initiation to complete audio stream reception.
    - **First Byte Latency**: Time from WebSocket connection initiation to the reception of the first audio chunk.
- **Note**: This feature requires a Resemble AI Business Plan or higher.

### Speech-to-Speech (Batch)
- **Calculation**: Time from API call initiation (including audio upload) to decoded audio reception it has a limit of 2000 words.
- **Example RTT (from app.py logic)**: RTT is calculated and displayed in the format `Speech-to-Speech clip generated! RTT: unknown`.

### Clone Voice (Batch)
- **Calculation**: Time from Cloned Voice.
- **Example RTT (from app.py logic)**: Time from WebSocket connection initiation to the reception of the first audio chunk.
- **Note**: Time from WebSocket connection initiation to the reception of the first audio chunk. This feature requires a Resemble AI Business Plan or higher.

### Audio Enchancement (Batch)
- **Calculation**: Time from API call initiation (including audio upload) to decoded audio reception.
- **Example RTT (from app.py logic)**: RTT is calculated and displayed in the format `Audio Enchancement clip generated! RTT: 10345.87 ms`.

## 4. Cost Considerations

The application itself does not calculate direct costs. However, usage of the Resemble AI API typically incurs costs based on:
- **Character Count**: For TTS and SSML TTS, the number of characters processed.
- **Audio Duration**: For STS, Streaming TTS, and possibly enhancement, the duration of generated or processed audio.
- **API Calls**: The number of requests made to the Resemble AI API.
- **Plan Type**: Different Resemble AI subscription plans (e.g., Business Plan) offer varying features and pricing structures, especially for advanced features like WebSocket streaming.

For detailed pricing information, please refer to the official Resemble AI pricing page.

## 5. Auto-Translation to Selected Language

When you enter text in any language and choose a target language (e.g., select `Marathi (mr-IN)` while the text is in English), the app can automatically translate the text to the selected language before synthesis.

### How it works
- A checkbox "Auto-translate input text to selected language" is available near the language selector.
- When enabled, the input text is translated to the selected language's primary locale before TTS synthesis and streaming.
- This applies to:
    - Text-to-Speech
    - Streaming TTS (HTTP)
    - Streaming TTS (WebSocket)
- SSML mode is unchanged; SSML you paste is sent as-is.

### Notes
- Translation uses `googletrans` if available. If it is not installed or fails, the app falls back to the original text.
- The synthesized voice remains the selected Resemble voice; only the text content is translated.
