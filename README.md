# Resemble AI Feature Tester

This project provides a Gradio-based interface to test various features of the Resemble AI API, including Text-to-Speech (TTS), SSML TTS, Streaming TTS (HTTP and WebSocket), Speech-to-Speech (STS), Voice Cloning, and Audio Enhancement. It incorporates multilingual support using SSML `<lang>` tags and saves generated audio outputs to local files.

## Table of Contents

- [Project Overview](#project-overview)
- [Setup](#setup)
- [Features](#features)
  - [Text-to-Speech (TTS)](#text-to-speech-tts)
  - [SSML Text-to-Speech (SSML TTS)](#ssml-text-to-speech-ssml-tts)
  - [Streaming Text-to-Speech (HTTP)](#streaming-text-to-speech-http)
  - [Streaming Text-to-Speech (Websocket)](#streaming-text-to-speech-websocket)
  - [Speech-to-Speech (Long Audio)](#speech-to-speech-long-audio)
  - [Clone Voices](#clone-voices)
  - [Audio Enhancement](#audio-enhancement)
- [Multilingual Support](#multilingual-support)
- [Output File Saving](#output-file-saving)
- [Running the Application](#running-the-application)

## Project Overview

The `app.py` script sets up a Gradio application that allows users to interact with the Resemble AI API. It handles authentication, project and voice selection, and demonstrates various synthesis and voice manipulation capabilities provided by Resemble AI.

## Setup

1.  **Clone the repository (if applicable) or ensure you have `app.py`, `requirements.txt` and a `.env` file in your project directory.**

2.  **Install dependencies:**
    It's recommended to use a virtual environment.
    ```bash
    pip install -r requirements.txt
    ```

3.  **Set up your Resemble AI API Key:**
    Create a `.env` file in the root directory of the project (the same directory as `app.py`) and add your Resemble AI API key:
    ```
    RESEMBLE_API_KEY=``
    ```
    Replace `Resemble AI API Key` with your actual Resemble AI API key.

## Features

The Gradio interface is organized into several tabs, each demonstrating a specific Resemble AI feature.

### 1. Connect & Select Project/Voice

Upon launching the application, you'll need to:
1.  Click "1. Connect & Fetch Projects" to populate the project dropdown.
2.  Select a project from "2. Select a Project".
3.  Select a voice from "3. Select a Voice".

The UUIDs for the selected project and voice will be displayed. A "Select Language (for SSML <lang> tag)" dropdown is also available to choose the desired language for synthesis.

### Text-to-Speech (TTS)

This tab allows you to convert plain text into speech using a selected voice and model.

-   **Input:** Text to Synthesize, TTS Model Version, Selected Voice, Selected Project, Selected Language.
-   **Output:** Generated audio clip (`tts_output.wav`) and status messages.
-   **Multilingual Support:** The input text is automatically wrapped in an SSML `<lang>` tag based on the selected language from the "Select Language" dropdown. **Note:** The voice you choose must support the selected language for proper synthesis.

### SSML Text-to-Speech (SSML TTS)

This tab supports synthesizing speech from SSML (Speech Synthesis Markup Language), allowing for fine-grained control over pitch, emphasis, prosody, and more.

-   **Input:** SSML markup, TTS Model Version, Selected Voice, Selected Project, Selected Language.
-   **Output:** Generated SSML audio clip (`ssml_tts_output.wav`) and status messages.
-   **Multilingual Support:** The `language_code` is passed to the function, but for SSML input, it is the user's responsibility to include the `<lang xml:lang="your-code">` tag directly within their SSML body for language specification.

### Streaming Text-to-Speech (HTTP)

This feature demonstrates real-time audio streaming of TTS output via an HTTP POST request.

-   **Input:** Text to Synthesize (streamed), TTS Model Version, Selected Voice, Selected Project, Selected Language.
-   **Output:** Streamed audio saved to `tts_streamed_output.wav` and status messages.
-   **Multilingual Support:** The input text is automatically wrapped in an SSML `<lang>` tag based on the selected language from the "Select Language" dropdown. **Note:** The voice you choose must support the selected language for proper synthesis.

### Streaming Text-to-Speech (Websocket)

This tab provides real-time audio streaming of TTS output via a WebSocket connection. This feature is typically available for Resemble AI Business plan users or higher.

-   **Input:** Text to Synthesize (streamed via WebSocket), TTS Model Version, Selected Voice, Selected Project, Selected Language.
-   **Output:** Streamed audio saved to `tts_streamed_websocket_output.wav` and status messages.
-   **Multilingual Support:** The input text is automatically wrapped in an SSML `<lang>` tag based on the selected language from the "Select Language" dropdown. **Note:** The voice you choose must support the selected language for proper synthesis.

### Speech-to-Speech (Long Audio)

This tab allows for batch Speech-to-Speech conversion, supporting longer audio inputs.

-   **Input:** Source audio file, STS Model Version, Selected Voice, Selected Project, Selected Language.
-   **Output:** Converted audio file (`resemble_sts_output.wav`) and status messages.
-   **Multilingual Support:** The base64 encoded audio data is wrapped in an SSML `<lang>` tag with the selected language code. **Note:** The voice you choose must support the selected language for proper synthesis.

### Clone Voices

This feature allows you to create new voices by uploading an audio sample.

-   **Input:** New Voice Name, Clean Audio Sample, Selected Project, Selected Language (informative).
-   **Output:** Cloning status.
-   **Multilingual Support:** The `language_code` is passed to the `clone_voice` function but is primarily informative. The actual language capabilities of the cloned voice depend on the language(s) present in the uploaded training audio.

### Audio Enhancement

This tab provides functionality to enhance an uploaded audio recording using the Resemble AI audio enhancement API.

-   **Input:** Audio file to enhance.
-   **Output:** Enhanced audio file (URL returned by API) and status messages.

## Multilingual Support

Multilingual support in this application is implemented by leveraging Resemble AI's SSML capabilities. The selected language from the Gradio dropdown is used to construct an `<lang xml:lang="your-language-code">` tag that wraps the input text/data sent to the Resemble AI API.

**Crucially, the ability of a voice to speak in a specific language depends on whether that voice has been trained for that language.** If a voice is not trained for a particular language, even with the `<lang>` tag, it may default to its primary trained language or produce inaccurate speech. For comprehensive multilingual support with a single voice, consider using Resemble AI's "Resemble Localize" feature to adapt your voices for multiple languages.

## Output File Saving

All generated audio outputs from the TTS, SSML TTS, and Streaming TTS functions are saved to local `.wav` files in the project directory:

-   **Text-to-Speech:** `tts_output.wav`
-   **SSML Text-to-Speech:** `ssml_tts_output.wav`
-   **Streaming Text-to-Speech (HTTP):** `tts_streamed_output.wav`
-   **Streaming Text-to-Speech (Websocket):** `tts_streamed_websocket_output.wav`
-   **Speech-to-Speech (Long Audio):** `resemble_sts_output.wav`

## Running the Application

To start the Gradio interface, run the `app.py` script:

```bash
python app.py
```

The application will launch in your web browser, typically at `http://127.0.0.1:7860` (or another port if 7860 is in use).
