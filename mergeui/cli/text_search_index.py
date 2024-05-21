from core.dependencies import get_model_repository


def main(force: bool = True):
    model_repository = get_model_repository()
    model_repository.create_text_search_index(reset_if_not_empty=force)


if __name__ == '__main__':
    main()
