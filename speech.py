"""Azure Speech synthesis in bounded chunks, with one continuous MP3 output."""

from __future__ import annotations

import subprocess
import xml.sax.saxutils

import azure.cognitiveservices.speech as speechsdk
import imageio_ffmpeg

from reader import chunks


VOICES = {
    "Elvira · España · femenina": "es-ES-ElviraNeural",
    "Alvaro · España · masculina": "es-ES-AlvaroNeural",
    "Abril · España · femenina": "es-ES-AbrilNeural",
    "Arnau · España · masculino": "es-ES-ArnauNeural",
    "Dalia · México · femenina": "es-MX-DaliaNeural",
    "Jorge · México · masculina": "es-MX-JorgeNeural",
    "Catalina · Chile · femenina": "es-CL-CatalinaNeural",
    "Lorenzo · Chile · masculina": "es-CL-LorenzoNeural",
}


def synthesize_mp3(text: str, voice: str, rate: int, key: str, region: str, progress=None) -> bytes:
    parts = chunks(text)
    if not parts:
        raise ValueError("No hay texto para leer.")
    if voice not in VOICES.values():
        raise ValueError("La voz seleccionada no es válida.")
    config = speechsdk.SpeechConfig(subscription=key, region=region)
    config.set_speech_synthesis_output_format(
        speechsdk.SpeechSynthesisOutputFormat.Raw24Khz16BitMonoPcm
    )
    synthesizer = speechsdk.SpeechSynthesizer(speech_config=config, audio_config=None)
    pcm = bytearray()
    locale = voice[:5]
    for index, part in enumerate(parts, 1):
        safe_text = xml.sax.saxutils.escape(part)
        ssml = (f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" '
                f'xml:lang="{locale}"><voice name="{voice}"><prosody rate="{rate:+d}%">'
                f'{safe_text}</prosody></voice></speak>')
        response = synthesizer.speak_ssml_async(ssml).get()
        if response.reason != speechsdk.ResultReason.SynthesizingAudioCompleted or not response.audio_data:
            detail = speechsdk.SpeechSynthesisCancellationDetails.from_result(response)
            raise RuntimeError(f"Azure Speech no pudo generar el fragmento {index}: {detail.error_details or detail.reason}")
        pcm.extend(response.audio_data)
        if progress:
            progress(index, len(parts))

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    process = subprocess.run(
        [ffmpeg, "-hide_banner", "-loglevel", "error", "-f", "s16le", "-ar", "24000",
         "-ac", "1", "-i", "pipe:0", "-codec:a", "libmp3lame", "-b:a", "64k",
         "-f", "mp3", "pipe:1"],
        input=bytes(pcm), stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    if process.returncode or not process.stdout:
        raise RuntimeError("No se pudo codificar el MP3: " + process.stderr.decode(errors="replace")[-500:])
    return process.stdout
