import gradio as gr

# custom_theme = gr.Theme.from_hub("freddyaboulton/test-blue")
# custom_theme = gr.Theme.from_hub("ParityError/Anime")
# custom_theme = gr.Theme.from_hub("ParityError/Interstellar")
custom_theme = gr.themes.Default(
    primary_hue='purple',
    secondary_hue='rose',
    font=[gr.themes.GoogleFont('Open Sans'), gr.themes.GoogleFont('Roboto'), 'sans-serif'],
)
