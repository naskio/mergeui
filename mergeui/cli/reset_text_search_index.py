from mergeui.core.dependencies import get_model_repository


def main():
    model_repository = get_model_repository()
    model_repository.drop_text_search_index()


if __name__ == '__main__':
    main()
