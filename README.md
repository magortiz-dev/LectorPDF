# Lector PDF

Aplicación Streamlit que extrae texto de PDF, permite revisarlo y genera un MP3 con voces de Azure Speech. Lee el texto literalmente: no resume ni traduce.

## Instalación

```bash
python -m venv .venv
source .venv/bin/activate  # En Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Introduce la **clave** y la **región** del recurso Azure Speech en la interfaz, o copia `.streamlit/secrets.toml.example` como `.streamlit/secrets.toml` y completa los valores. No subas ese último archivo a un repositorio. En Streamlit Community Cloud, configura los mismos secretos desde la administración de la app. Azure puede cobrar por los caracteres sintetizados según tu plan.

## Uso

1. Sube el PDF y elige el intervalo de páginas. Excluye índice, glosario o anexos indicando páginas como `2, 4-7`.
2. Ajusta los márgenes y la exclusión de cabeceras, pies repetidos y pies de figuras. Pulsa **Preparar lectura**.
3. Revisa el texto y borra lo que sobre. Si el documento es escaneado, aplica OCR antes de subirlo; esta versión no incorpora OCR.
4. Elige una voz española, mexicana o chilena y la velocidad. Pulsa **Generar MP3** y descárgalo o escúchalo en la página.

El PDF no se almacena en disco. El texto y el MP3 viven en la sesión de Streamlit; al cerrar la sesión pueden perderse. El texto se envía a Azure Speech para la síntesis. Archivos grandes y sesiones largas consumen más memoria y pueden alcanzar límites de recursos de Streamlit Cloud. Las fórmulas y tablas complejas no se interpretan de manera semántica; revísalas en el cuadro de texto.

Para que el MP3 sea continuo, la app envía el texto a Azure por fragmentos y une el audio PCM antes de codificar una sola vez a MP3. `imageio-ffmpeg` proporciona el codificador sin instalación de ffmpeg del sistema.
