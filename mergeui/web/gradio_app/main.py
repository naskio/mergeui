import gradio as gr
from mergeui.web.gradio_app.theming import custom_theme
from mergeui.web.gradio_app.functions import get_model_lineage, list_models
from mergeui.core.dependencies import get_settings, get_model_service
from mergeui.core.schema import SortByOptionType, ExcludeOptionType, DisplayColumnType
from mergeui.web.schema import LabelFieldType, ColorFieldType, GetModelLineageInputDTO
from mergeui.utils.types import get_literal_type_options
from mergeui.utils.web import list_as_choices

if gr.NO_RELOAD:
    settings = get_settings()
    model_service = get_model_service()

    # choices
    MERGED_MODEL_ID_CHOICES = model_service.get_model_id_choices(private=False, merged_only=True)
    MODEL_ID_CHOICES = model_service.get_model_id_choices(private=False)
    SORT_BY_CHOICES = list_as_choices(get_literal_type_options(SortByOptionType))
    DISPLAY_COLUMN_CHOICES = list_as_choices(get_literal_type_options(DisplayColumnType))
    EXCLUDE_CHOICES = list_as_choices(get_literal_type_options(ExcludeOptionType))
    AUTHOR_CHOICES = model_service.get_author_choices()
    LICENSE_CHOICES = model_service.get_license_choices()
    MERGE_METHOD_CHOICES = model_service.get_merge_method_choices()
    ARCHITECTURE_CHOICES = model_service.get_architecture_choices()
    LABEL_FIELD_CHOICES = list_as_choices(get_literal_type_options(LabelFieldType))
    COLOR_FIELD_CHOICES = list_as_choices(get_literal_type_options(ColorFieldType))

    LEADERBOARD__SORT_BY_SET = {"average score", "ARC", "HellaSwag", "MMLU", "TruthfulQA", "Winogrande", "GSM8k"}

    # lineage tab
    LINEAGE__DEFAULT_MODEL_ID = model_service.get_default_model_id()
    LINEAGE__DEFAULT_DIRECTED = GetModelLineageInputDTO.model_fields['directed'].default
    LINEAGE__DEFAULT_MAX_HOPS = GetModelLineageInputDTO.model_fields['max_hops'].default
    LINEAGE__DEFAULT_LABEL_FIELD = GetModelLineageInputDTO.model_fields['label_field'].default
    LINEAGE__DEFAULT_COLOR_FIELD = GetModelLineageInputDTO.model_fields['color_field'].default
    # discover tab
    DISCOVER__SORT_BY_CHOICES = [c for c in SORT_BY_CHOICES if c[1] not in LEADERBOARD__SORT_BY_SET]
    DISCOVER__DEFAULT_SORT_BY = "default"
    DISCOVER__HIDDEN_BY_DEFAULT_COLUMNS = {'url', 'name', 'author', 'description', 'created_at',
                                           'arc_score', 'hella_swag_score', 'mmlu_score', 'truthfulqa_score',
                                           'winogrande_score', 'gsm8k_score', 'evaluated_at'}
    DISCOVER__DEFAULT_DISPLAY_COLUMNS = [x[1] for x in DISPLAY_COLUMN_CHOICES if
                                         x[1] not in DISCOVER__HIDDEN_BY_DEFAULT_COLUMNS]
    DISCOVER__DEFAULT_EXCLUDES = ['private', 'base models']
    # leaderboard tab
    LEADERBOARD__SORT_BY_CHOICES = [c for c in SORT_BY_CHOICES if c[1] in LEADERBOARD__SORT_BY_SET]
    LEADERBOARD__DEFAULT_SORT_BY = "average score"
    LEADERBOARD__HIDDEN_BY_DEFAULT_COLUMNS = {'url', 'name', 'author', 'description', 'license', 'architecture',
                                              'likes', 'downloads', 'created_at', 'updated_at', 'evaluated_at'}
    LEADERBOARD__DEFAULT_DISPLAY_COLUMNS = [x[1] for x in DISPLAY_COLUMN_CHOICES if
                                            x[1] not in LEADERBOARD__HIDDEN_BY_DEFAULT_COLUMNS]
    LEADERBOARD__DEFAULT_EXCLUDES = ['private', 'base models']

    # gradio
    DB_IS_EMPTY = not bool(MODEL_ID_CHOICES)

    custom_css = (settings.gradio_load_custom_css and (
            settings.project_dir / 'static/gradio_app/custom.css').read_text().strip()) or None
    custom_js = (settings.gradio_load_custom_js and (
            settings.project_dir / 'static/gradio_app/custom.js').read_text().strip()) or None

# noinspection PyUnboundLocalVariable
with gr.Blocks(theme=custom_theme, title=settings.project_name, css=custom_css, js=custom_js) as demo:
    with gr.Row():
        with gr.Column(visible=False) as main_page:
            gr.HTML((settings.project_dir / 'static/partials/header.html').read_text())
            with gr.Tab("🧬 Lineage") as lineage_tab:
                with gr.Row():
                    # noinspection PyUnboundLocalVariable
                    lineage_in__model_id = gr.Dropdown(
                        interactive=True,
                        choices=MERGED_MODEL_ID_CHOICES,
                        value=LINEAGE__DEFAULT_MODEL_ID,
                        multiselect=False, filterable=True,
                        label="Model ID", show_label=False,
                        info="Select a merged model to visualize its lineage",
                        container=True,
                        scale=4,
                    )
                    # noinspection PyUnboundLocalVariable
                    lineage_in__directed = gr.Checkbox(
                        interactive=True,
                        value=LINEAGE__DEFAULT_DIRECTED,
                        label="Hide derivatives", show_label=False,
                        info="Exclude children",
                        container=True,
                        scale=1,
                    )
                    # noinspection PyUnboundLocalVariable
                    lineage_in__max_hops = gr.Slider(
                        interactive=True,
                        randomize=LINEAGE__DEFAULT_MAX_HOPS is None,
                        value=LINEAGE__DEFAULT_MAX_HOPS,
                        minimum=1, maximum=settings.max_hops, step=1,
                        label="Max hops", show_label=False,
                        info="Max distance",
                        container=True,
                        scale=1,
                    )
                    # noinspection PyUnboundLocalVariable
                    lineage_in__label_field = gr.Dropdown(
                        interactive=True,
                        multiselect=False,
                        filterable=True,
                        choices=LABEL_FIELD_CHOICES,
                        value=LINEAGE__DEFAULT_LABEL_FIELD,
                        label="Label field", show_label=False,
                        info="Use as node label",
                        container=True,
                        scale=1,
                    )
                    # noinspection PyUnboundLocalVariable
                    lineage_in__color_field = gr.Dropdown(
                        interactive=True,
                        multiselect=False,
                        filterable=True,
                        choices=COLOR_FIELD_CHOICES,
                        value=LINEAGE__DEFAULT_COLOR_FIELD,
                        label="Color field", show_label=False,
                        info="Node color based on",
                        container=True,
                        scale=1,
                    )
                lineage_inputs = [
                    lineage_in__model_id,
                    lineage_in__directed,
                    lineage_in__max_hops,
                    lineage_in__label_field,
                    lineage_in__color_field,
                ]
                lineage_message = gr.Label("Select a model to visualize its lineage 🧐", visible=True, show_label=False)
                lineage_out = gr.Plot(visible=False)
                for lineage_in in lineage_inputs:
                    lineage_in.change(
                        fn=get_model_lineage,
                        inputs=lineage_inputs,
                        outputs=[lineage_out, lineage_message],
                    )
                gr.Markdown("""
                > **Hints**
                > - *Select* <small>*label* and *color* fields to customize the graph 
                according to the analysis that you want to perform.</small>
                > - *Play* <small>with *max distance* and *exclude children* fields to display
                 a partial lineage.</small>
                > - *Hover* <small>over a node to view more details.</small>
                > - *Hover* <small>over a relationship to view the data provenance.</small>
                > - *Click* <small>on a node to visit its repository for additional information.</small>
                > - *Click* <small>on a relationship to visit the data source page 
                (after switching the click tool on the right panel).</small>
                > - *Use* <small>the tools from the right panel to interact with the graph: 
                zoom, save, center, etc.</small>
                """)

            with gr.Tab("🔎 Discover") as discover_tab:
                with gr.Row():
                    with gr.Column():
                        # noinspection PyUnboundLocalVariable
                        discover_in__query = gr.Textbox(
                            interactive=True,
                            placeholder="Example: MistralAI, OpenAI, MIT, Apache 2.0, ...",
                            label="label", show_label=False,
                            info="Search authors, licenses, architectures, models, ...",
                            max_lines=1, autofocus=True,
                            container=True,
                        )
                        # noinspection PyUnboundLocalVariable
                        discover_in__sort_by = gr.Radio(
                            interactive=True,
                            choices=DISCOVER__SORT_BY_CHOICES,
                            value=DISCOVER__DEFAULT_SORT_BY,
                            label="Sort by", show_label=False,
                            info="Sort by",
                            container=True,
                        )
                        # noinspection PyUnboundLocalVariable
                        discover_in__display_columns = gr.CheckboxGroup(
                            interactive=True,
                            choices=DISPLAY_COLUMN_CHOICES,
                            value=DISCOVER__DEFAULT_DISPLAY_COLUMNS,
                            label="Display columns", show_label=False,
                            info="Columns to display",
                            container=True,
                        )
                        # noinspection PyUnboundLocalVariable
                        discover_in__excludes = gr.CheckboxGroup(
                            interactive=True,
                            choices=EXCLUDE_CHOICES,
                            value=DISCOVER__DEFAULT_EXCLUDES,
                            label="Hide models", show_label=False,
                            info="Exclude",
                            container=True,
                        )

                    with gr.Column():
                        # noinspection PyUnboundLocalVariable
                        discover_in__base_model = gr.Dropdown(
                            interactive=True,
                            choices=MODEL_ID_CHOICES,
                            multiselect=False, filterable=True,
                            label="Base Model", show_label=False,
                            info="Only if derived from",
                            container=True,
                        )
                        # noinspection PyUnboundLocalVariable
                        discover_in__merge_method = gr.Dropdown(
                            interactive=True,
                            choices=MERGE_METHOD_CHOICES,
                            multiselect=False, filterable=True,
                            label="Merge method", show_label=False,
                            info="Merge method/strategy",
                            container=True,
                        )
                        # noinspection PyUnboundLocalVariable
                        discover_in__architecture = gr.Dropdown(
                            interactive=True,
                            choices=ARCHITECTURE_CHOICES,
                            multiselect=False, filterable=True,
                            label="Architecture", show_label=False,
                            info="Architecture",
                            container=True,
                        )
                        # noinspection PyUnboundLocalVariable
                        discover_in__author = gr.Dropdown(
                            interactive=True,
                            choices=AUTHOR_CHOICES,
                            multiselect=False, filterable=True,
                            label="Author", show_label=False,
                            info="Author",
                            container=True,
                        )
                        # noinspection PyUnboundLocalVariable
                        discover_in__license = gr.Dropdown(
                            interactive=True,
                            choices=LICENSE_CHOICES,
                            multiselect=False, filterable=True,
                            label="License", show_label=False,
                            info="Repository license",
                            container=True,
                        )
                        discover_inputs = [
                            discover_in__query,
                            discover_in__sort_by,
                            discover_in__display_columns,
                            discover_in__excludes,
                            discover_in__author,
                            discover_in__license,
                            discover_in__merge_method,
                            discover_in__architecture,
                            discover_in__base_model,
                        ]
                        discover_reset = gr.ClearButton(
                            [c for c in discover_inputs if
                             c not in {discover_in__sort_by, discover_in__display_columns, discover_in__excludes}],
                            value="Reset",
                        )

                discover_message = gr.Label("Start exploring our list of models 🧐", visible=True, show_label=False)
                discover_out = gr.DataFrame(visible=False)
                for discover_in in discover_inputs:
                    discover_in.change(
                        fn=list_models,
                        inputs=discover_inputs,
                        outputs=[discover_out, discover_message],
                    )
                if settings.gradio_auto_invoke_on_load:
                    discover_tab.select(fn=list_models, inputs=discover_inputs,
                                        outputs=[discover_out, discover_message])
                gr.Markdown("""
                > **Hints**
                > - *Hover* <small>over a *model Id* to view its description.</small>
                > - *Click* <small>on a *model Id* to visit its repository for additional information.</small>
                > - *Use* <small>the text-search feature to find specific models.</small>
                > - *Play* <small>with filters to discover new models.</small>
                """)

            with gr.Tab("🥇 Merged LLM Leaderboard") as leaderboard_tab:
                with gr.Row():
                    with gr.Column():
                        leaderboard_in__query = gr.Textbox(
                            interactive=True,
                            placeholder="Example: MistralAI, OpenAI, MIT, Apache 2.0, ...",
                            label="label", show_label=False,
                            info="Search authors, licenses, architectures, models, ...",
                            max_lines=1, autofocus=True,
                            container=True,
                        )
                        # noinspection PyUnboundLocalVariable
                        leaderboard_in__sort_by = gr.Radio(
                            interactive=True,
                            choices=LEADERBOARD__SORT_BY_CHOICES,
                            value=LEADERBOARD__DEFAULT_SORT_BY,
                            label="Sort by", show_label=False,
                            info="Sort by",
                            container=True,
                        )
                        # noinspection PyUnboundLocalVariable
                        leaderboard_in__display_columns = gr.CheckboxGroup(
                            interactive=True,
                            choices=DISPLAY_COLUMN_CHOICES,
                            value=LEADERBOARD__DEFAULT_DISPLAY_COLUMNS,
                            label="Display columns", show_label=False,
                            info="Columns to display",
                            container=True,
                        )
                        # noinspection PyUnboundLocalVariable
                        leaderboard_in__excludes = gr.CheckboxGroup(
                            interactive=False,
                            visible=False,
                            choices=EXCLUDE_CHOICES,
                            value=LEADERBOARD__DEFAULT_EXCLUDES,
                            label="Hide models", show_label=False,
                            info="Exclude",
                            container=True,
                        )
                    with gr.Column():
                        leaderboard_in__base_model = gr.Dropdown(
                            interactive=True,
                            choices=MODEL_ID_CHOICES,
                            multiselect=False, filterable=True,
                            label="Base Model", show_label=False,
                            info="Only if derived from",
                            container=True,
                        )
                        leaderboard_in__merge_method = gr.Dropdown(
                            interactive=True,
                            choices=MERGE_METHOD_CHOICES,
                            multiselect=False, filterable=True,
                            label="Merge method", show_label=False,
                            info="Merge method/strategy",
                            container=True,
                        )
                        leaderboard_in__architecture = gr.Dropdown(
                            interactive=True,
                            choices=ARCHITECTURE_CHOICES,
                            multiselect=False, filterable=True,
                            label="Architecture", show_label=False,
                            info="Architecture",
                            container=True,
                        )
                        leaderboard_in__author = gr.Dropdown(
                            interactive=True,
                            choices=AUTHOR_CHOICES,
                            multiselect=False, filterable=True,
                            label="Author", show_label=False,
                            info="Author",
                            container=True,
                        )
                        leaderboard_in__license = gr.Dropdown(
                            interactive=True,
                            choices=LICENSE_CHOICES,
                            multiselect=False, filterable=True,
                            label="License", show_label=False,
                            info="Repository license",
                            container=True,
                        )
                        leaderboard_inputs = [
                            leaderboard_in__query,
                            leaderboard_in__sort_by,
                            leaderboard_in__display_columns,
                            leaderboard_in__excludes,
                            leaderboard_in__author,
                            leaderboard_in__license,
                            leaderboard_in__merge_method,
                            leaderboard_in__architecture,
                            leaderboard_in__base_model,
                        ]
                        leaderboard_reset = gr.ClearButton(
                            [c for c in leaderboard_inputs if
                             c not in {leaderboard_in__sort_by, leaderboard_in__display_columns,
                                       leaderboard_in__excludes}],
                            value="Reset",
                        )
                leaderboard_message = gr.Label("Leaderboard for merged LLMs 🧐", visible=True, show_label=False)
                leaderboard_out = gr.DataFrame(visible=False)
                for leaderboard_in in leaderboard_inputs:
                    leaderboard_in.change(
                        fn=list_models,
                        inputs=leaderboard_inputs,
                        outputs=[leaderboard_out, leaderboard_message],
                    )
                if settings.gradio_auto_invoke_on_load:
                    leaderboard_tab.select(fn=list_models, inputs=leaderboard_inputs,
                                           outputs=[leaderboard_out, leaderboard_message])
                gr.Markdown("""
                > **Hints**
                > - *LEADERBOARD* <small>for merged models based on the 
                [Open LLM Leaderboard results](https://huggingface.co/datasets/open-llm-leaderboard/results).</small>
                """)

            with gr.Tab("❗ About"):
                gr.Markdown((settings.project_dir / 'static/partials/about.md').read_text())

        with gr.Column() as landing_page:
            gr.HTML((settings.project_dir / 'static/partials/hero.html').read_text())
            # noinspection PyUnboundLocalVariable
            btn = gr.Button(
                "Explore the secrets of merged LLMs!" if not DB_IS_EMPTY
                else f"Unexpected problem with the database! Please create an issue on GitHub",
                variant='primary',
                interactive=not DB_IS_EMPTY,
            )
            btn.click(fn=lambda: (gr.Column(visible=True), gr.Column(visible=False)), outputs=[main_page, landing_page])
    if settings.gradio_auto_invoke_on_load:
        demo.load(fn=get_model_lineage, inputs=lineage_inputs, outputs=[lineage_out, lineage_message])

    with gr.Row():
        gr.HTML((settings.project_dir / 'static/partials/footer.html').read_text())

if __name__ == '__main__':
    demo.queue(api_open=False).launch(show_api=False, show_error=False, favicon_path=settings.favicon_path)
