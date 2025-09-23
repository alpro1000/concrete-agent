class SmetaParser:
    """
    Заглушка для парсера смет.
    Пока ничего не делает, но позволяет избежать ImportError.
    """
    def __init__(self, *args, **kwargs):
        pass

    def parse(self, file_path: str):
        # Возвращаем пустую структуру
        return {"items": [], "summary": {}}