import gradio as gr
from web.gradio_app.theming import custom_theme
from web.gradio_app.functions import get_model_lineage, list_models
from core.dependencies import get_settings, get_model_service
from core.schema import SortByOptionType, ExcludeOptionType, DisplayColumnType
from web.schema import LabelFieldType, ColorFieldType
from utils.types import get_literal_type_options
from utils.web import list_as_choices

# if gr.NO_RELOAD:
settings = get_settings()
model_service = get_model_service()

MODEL_ID_CHOICES = model_service.get_model_id_choices(private=False)
SORT_BY_CHOICES = list_as_choices(get_literal_type_options(SortByOptionType))
DISPLAY_COLUMN_CHOICES = list_as_choices(get_literal_type_options(DisplayColumnType))
EXCLUDE_CHOICES = list_as_choices(get_literal_type_options(ExcludeOptionType))
LICENSE_CHOICES = model_service.get_license_choices()
MERGE_METHOD_CHOICES = model_service.get_merge_method_choices()
ARCHITECTURE_CHOICES = model_service.get_architecture_choices()
LABEL_FIELD_CHOICES = list_as_choices(get_literal_type_options(LabelFieldType))
COLOR_FIELD_CHOICES = list_as_choices(get_literal_type_options(ColorFieldType))

HIDDEN_BY_DEFAULT_COLUMNS = ['url', 'name', 'description', 'author', 'created_at', 'arc_score', 'hella_swag_score',
                             'mmlu_score', 'truthfulqa_score', 'winogrande_score', 'gsm8k_score', 'evaluated_at']

DEFAULT_SORT_BY = "default"
DEFAULT_DISPLAY_COLUMNS = [x[1] for x in DISPLAY_COLUMN_CHOICES if x[1] not in HIDDEN_BY_DEFAULT_COLUMNS]
DEFAULT_LABEL_FIELD = "id"
DEFAULT_COLOR_FIELD = "average_score"
DEFAULT_MODEL_ID = model_service.get_default_model_id()

DB_IS_EMPTY = not bool(MODEL_ID_CHOICES)

custom_css = (settings.load_custom_js and (
        settings.project_dir / 'static/gradio_app/custom.css').read_text().strip()) or None
custom_js = (settings.load_custom_js and (
        settings.project_dir / 'static/gradio_app/custom.js').read_text().strip()) or None

with gr.Blocks(theme=custom_theme, title=settings.app_name, css=custom_css, js=custom_js) as demo:
    with gr.Row():
        with gr.Column(visible=False) as main_page:
            gr.HTML((settings.project_dir / 'static/partials/header.html').read_text())
            with gr.Tab("🧬 Lineage"):
                with gr.Row():
                    lineage_in__model_id = gr.Dropdown(
                        interactive=True,
                        choices=MODEL_ID_CHOICES,
                        value=DEFAULT_MODEL_ID,
                        multiselect=False,
                        filterable=True,
                        label="Model ID", show_label=False,
                        info="Select a model to visualize its lineage",
                        container=True,
                        scale=4,
                    )
                    lineage_in__label_field = gr.Dropdown(
                        interactive=True,
                        multiselect=False,
                        filterable=True,
                        choices=LABEL_FIELD_CHOICES,
                        value=DEFAULT_LABEL_FIELD,
                        label="Label field", show_label=False,
                        info="Use as node label",
                        container=True,
                        scale=1,
                    )
                    lineage_in__color_field = gr.Dropdown(
                        interactive=True,
                        multiselect=False,
                        filterable=True,
                        choices=COLOR_FIELD_CHOICES,
                        value=DEFAULT_COLOR_FIELD,
                        label="Color field", show_label=False,
                        info="Node color based on",
                        container=True,
                        scale=1,
                    )
                lineage_inputs = [
                    lineage_in__model_id,
                    lineage_in__label_field,
                    lineage_in__color_field,
                ]
                lineage_message = gr.Label("🧐 Select a model to visualize its lineage", visible=True, show_label=False)
                lineage_out = gr.Plot(visible=False)
                for lineage_in in lineage_inputs:
                    lineage_in.change(
                        fn=get_model_lineage,
                        inputs=lineage_inputs,
                        outputs=[lineage_out, lineage_message],
                        trigger_mode="once",
                    )
                gr.Markdown("""
                > **Hints**
                > - *Select* <small>label and color fields to customize the graph according to your preferences.</small>
                > - *Use* <small>the tools from the right panel to interact with the graph.</small>
                > - *Hover* <small>over a node to view more details.</small>
                > - *Click* <small>on a node to visit its repository for additional information.</small>
                """)

            with gr.Tab("🔎 Discover", render=True):
                with gr.Row():
                    with gr.Column():
                        discover_in__query = gr.Textbox(
                            interactive=True,
                            placeholder="Example: MistralAI, OpenAI, ChatGPT, MIT, Apache 2, ...",
                            label="label", show_label=False,
                            info="Search authors, licenses, architectures, models, ...",
                            max_lines=1, autofocus=True,
                            container=True,
                        )
                        discover_in__sort_by = gr.Radio(
                            interactive=True,
                            choices=SORT_BY_CHOICES,
                            value=DEFAULT_SORT_BY,
                            label="Sort by", show_label=False,
                            info="Sort by",
                            container=False,
                        )
                        discover_in__display_columns = gr.Dropdown(
                            interactive=True,
                            choices=DISPLAY_COLUMN_CHOICES,
                            value=DEFAULT_DISPLAY_COLUMNS,
                            multiselect=True,
                            label="Display columns", show_label=False,
                            info="Columns to display",
                            container=True,
                        )
                        discover_in__exclude = gr.Radio(
                            interactive=True,
                            choices=EXCLUDE_CHOICES,
                            label="Hide models", show_label=False,
                            info="Exclude",
                            container=False,
                        )

                    with gr.Column():
                        discover_in__base_model = gr.Dropdown(
                            interactive=True,
                            choices=MODEL_ID_CHOICES,
                            multiselect=False, filterable=True,
                            label="Base Model", show_label=False,
                            info="Only if derived from",
                            container=True,
                        )
                        discover_in__architecture = gr.Radio(
                            interactive=True,
                            choices=ARCHITECTURE_CHOICES,
                            label="Architecture", show_label=False,
                            info="Architecture",
                            container=False,
                        )
                        discover_in__merge_method = gr.Radio(
                            interactive=True,
                            choices=MERGE_METHOD_CHOICES,
                            label="Merge method", show_label=False,
                            info="Merge method/strategy",
                            container=False,
                        )
                        discover_in__license = gr.Radio(
                            interactive=True,
                            choices=LICENSE_CHOICES,
                            label="License", show_label=False,
                            info="Repository license",
                            container=False,
                        )
                        discover_inputs = [
                            discover_in__query,
                            discover_in__sort_by,
                            discover_in__display_columns,
                            discover_in__exclude,
                            discover_in__license,
                            discover_in__base_model,
                            discover_in__merge_method,
                            discover_in__architecture,
                        ]
                        discover_reset = gr.ClearButton(
                            [c for c in discover_inputs if
                             c not in {discover_in__sort_by, discover_in__display_columns}],
                            value="Reset",
                        )

                discover_message = gr.Label("🧐 Start exploring our list of models.", visible=True, show_label=False)
                discover_out = gr.DataFrame(visible=False)
                for discover_in in discover_inputs:
                    discover_in.change(
                        fn=list_models,
                        inputs=discover_inputs,
                        outputs=[discover_out, discover_message],
                        trigger_mode="once",
                    )
                gr.Markdown("""
                > **Hints**
                > - *Play* <small>with filters to discover new models.</small>
                > - *Hover* <small>over a model Id to view its description.</small>
                > - *Click* <small>on a model Id to visit its repository for additional information.</small>
                """)

        with gr.Column() as landing_page:
            gr.HTML((settings.project_dir / 'static/partials/hero.html').read_text())
            btn = gr.Button(
                "Explore the secrets of merged LLMs!" if not DB_IS_EMPTY
                else f"Unexpected problem with the database! Please create an issue on GitHub.",
                variant='primary',
                interactive=not DB_IS_EMPTY,
            )
            btn.click(fn=lambda: (gr.Column(visible=True), gr.Column(visible=False)), outputs=[main_page, landing_page])

if __name__ == '__main__':
    demo.queue(api_open=False).launch(show_api=False, show_error=False, favicon_path=settings.favicon_path)
