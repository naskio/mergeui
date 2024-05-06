import typing as t


def extract_base_models_from_mergekit_config(mergekit_config: dict) -> set[str]:
    """https://github.com/arcee-ai/mergekit#merge-configuration"""
    found = []
    # base_model (str)
    if "base_model" in mergekit_config:
        if isinstance(mergekit_config["base_model"], str):
            found.append(mergekit_config["base_model"])
        elif isinstance(mergekit_config["base_model"], list):
            found.extend(mergekit_config["base_model"])
    # models (list of dict)
    ld = []
    models_list = mergekit_config.get("models", [])
    if isinstance(models_list, list):
        ld.extend(models_list)
    # slices.sources (list of dict)
    if "slices" in mergekit_config and isinstance(mergekit_config["slices"], list):
        for slice_ in mergekit_config["slices"]:
            sources_list = slice_.get("sources", [])
            if isinstance(sources_list, list):
                ld.extend(sources_list)
    # experts (list of dict)
    experts_list = mergekit_config.get("experts", [])
    if isinstance(experts_list, list):
        found.extend([expert.get("source_model") for expert in experts_list])
    # collect all
    found.extend([model.get("model") for model in ld])
    return set(f for f in found if isinstance(f, str) and "/" in f)


def extract_merge_method_from_mergekit_config(mergekit_config: dict) -> t.Optional[str]:
    return mergekit_config.get("merge_method")


def extract_base_models_from_card_data(card_data: dict) -> set[str]:
    # https://huggingface.co/docs/hub/en/model-cards#model-card-metadata
    found = []
    base_model = card_data.get("base_model", None)
    if isinstance(base_model, str):
        found.append(base_model)
    elif isinstance(base_model, list):
        found.extend(base_model)
    return set(f for f in found if isinstance(f, str) and "/" in f)


def extract_license_from_card_data(card_data: dict) -> t.Optional[str]:
    # return card_data.get("license_name") # any string
    return card_data.get("license")  # one from https://huggingface.co/docs/hub/en/repositories-licenses


def extract_base_models_from_tags(tags: list[str]) -> set[str]:
    found = set()
    if not tags:
        return set()
    for tag in tags:
        if tag.startswith('base_model:'):
            found.add(tag.replace('base_model:', ''))
    return found


def extract_card_data_string_from_readme(readme: str) -> t.Optional[str]:
    # extracting card_data from Model Card
    if readme.startswith('---\n'):
        return readme.split('---\n')[1]


def extract_mergekit_config_string_from_readme(readme: str) -> t.Optional[str]:
    config_strings = []
    config_string = None
    start = False
    for line in readme.splitlines():
        if line.startswith('```yaml') or line.startswith('```yml'):
            start = True
            config_string = ''
            continue
        if line.startswith('```'):
            start = False
            if config_string:
                config_strings.append(config_string)
        if start:
            config_string += f"{line}\n"
    if config_strings:
        return "---\n".join(config_strings)
