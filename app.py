"""Lector PDF · Streamlit UI."""

from __future__ import annotations

import hashlib
import re

import streamlit as st

from reader import extract_pdf, page_count
from speech import VOICES, synthesize_mp3


st.set_page_config(page_title="Lector PDF", page_icon="🔊", layout="centered")
st.markdown("""<style>
.block-container {max-width: 920px; padding-top: 2rem;}
h1 {font-size: 3rem !important; letter-spacing: -0.04em;}
div[data-testid="stButton"] button[kind="primary"] {border-radius: 10px; font-weight: 700;}
</style>""", unsafe_allow_html=True)
st.title("🔊 Lector PDF")
st.caption("Del documento al paseo · lectura íntegra, con una voz a tu gusto")

uploaded = st.file_uploader("Sube un documento PDF", type="pdf")
if uploaded is None:
    st.info("Sube un PDF para preparar la lectura.")
    st.stop()

pdf = uploaded.getvalue()
identity = hashlib.sha256(pdf).hexdigest()
if st.session_state.get("pdf_identity") != identity:
    st.session_state.pdf_identity = identity
    st.session_state.pop("clean_text", None)
    st.session_state.pop("mp3", None)
    st.session_state.pop("audio_identity", None)

try:
    total = page_count(pdf)
except Exception:
    st.error("No se puede abrir este PDF. Comprueba que no esté dañado ni protegido con contraseña.")
    st.stop()

st.subheader("1. Prepara el texto")
st.caption(f"{uploaded.name} · {total} páginas. Selecciona solo las páginas que quieras escuchar.")
c1, c2 = st.columns(2)
with c1:
    first = st.number_input("Desde la página", min_value=1, max_value=total, value=1, step=1)
with c2:
    last = st.number_input("Hasta la página", min_value=1, max_value=total, value=total, step=1)
excluded = st.text_input("Otras páginas a omitir (opcional)", placeholder="2, 4-7, 25")
with st.expander("Limpieza del documento", expanded=True):
    top = st.slider("Recortar margen superior (%)", 0, 20, 7)
    bottom = st.slider("Recortar margen inferior (%)", 0, 20, 7)
    repeated = st.checkbox("Omitir cabeceras y pies repetidos", value=True)
    captions = st.checkbox("Omitir pies de figuras y tablas", value=True)


def parse_pages(value: str, maximum: int) -> set[int]:
    numbers: set[int] = set()
    for item in value.split(","):
        item = item.strip()
        if not item:
            continue
        if not re.fullmatch(r"\d+(?:\s*-\s*\d+)?", item):
            raise ValueError(f"Intervalo de páginas no válido: {item}")
        bounds = [int(x) for x in item.split("-")]
        start, end = (bounds[0], bounds[-1])
        if not 1 <= start <= end <= maximum:
            raise ValueError(f"Página fuera de rango: {item}")
        numbers.update(range(start, end + 1))
    return numbers


settings = (identity, first, last, excluded, top, bottom, repeated, captions)
if st.button("Preparar lectura", type="primary", use_container_width=True):
    try:
        st.session_state.clean_text = extract_pdf(
            pdf, int(first), int(last), parse_pages(excluded, total),
            top, bottom, captions, repeated,
        )
        st.session_state.text_settings = settings
        st.session_state.pop("mp3", None)
        st.session_state.pop("audio_identity", None)
    except ValueError as error:
        st.error(str(error))
    except Exception as error:
        st.error(f"No se pudo extraer el texto: {error}")

if "clean_text" not in st.session_state:
    st.stop()
if st.session_state.get("text_settings") != settings:
    st.warning("Has cambiado la limpieza. Pulsa «Preparar lectura» para aplicar los cambios.")
    st.stop()

st.subheader("2. Revisa lo que se leerá")
text = st.text_area("Texto editable", key="clean_text", height=300,
                    help="Borra el índice, glosario, referencias, figuras u otros pasajes que no quieras oír.")
if not text.strip():
    st.warning("No se ha detectado texto. Un PDF escaneado necesita OCR previo.")
    st.stop()
st.caption(f"{len(text):,} caracteres · aproximadamente {max(1, len(text.split()) // 150)} minutos de audio.")
st.download_button("Descargar texto depurado (.txt)", text.encode("utf-8"),
                   file_name="lectura_depurada.txt", mime="text/plain")

st.subheader("3. Elige voz y genera el audio")
voice_label = st.selectbox("Voz", list(VOICES))
rate = st.slider("Velocidad de lectura", -30, 40, 0, 5, format="%d %%")
try:
    key = st.secrets.get("AZURE_SPEECH_KEY", "")
    region = st.secrets.get("AZURE_SPEECH_REGION", "")
except FileNotFoundError:
    key, region = "", ""

audio_identity = hashlib.sha256((text + VOICES[voice_label] + str(rate)).encode()).hexdigest()
if st.button("Generar MP3", type="primary", use_container_width=True):
    if not key.strip() or not region.strip():
        st.error("Configura AZURE_SPEECH_KEY y AZURE_SPEECH_REGION en los secretos de Streamlit.")
    else:
        bar = st.progress(0, text="Generando audio…")
        try:
            st.session_state.mp3 = synthesize_mp3(
                text, VOICES[voice_label], rate, key.strip(), region.strip(),
                lambda done, total_parts: bar.progress(done / total_parts,
                    text=f"Voz: fragmento {done} de {total_parts}"),
            )
            st.session_state.audio_identity = audio_identity
            bar.empty()
            st.success("Audio preparado.")
        except Exception as error:
            bar.empty()
            st.session_state.pop("mp3", None)
            st.error(f"No se pudo generar el audio: {error}")

if st.session_state.get("mp3") and st.session_state.get("audio_identity") == audio_identity:
    st.audio(st.session_state.mp3, format="audio/mp3")
    st.download_button("Descargar MP3", st.session_state.mp3,
                       file_name="lectura_pdf.mp3", mime="audio/mpeg", use_container_width=True)
elif st.session_state.get("mp3"):
    st.info("Has cambiado el texto o la voz. Genera el MP3 de nuevo para descargar la versión actual.")
