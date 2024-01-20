def prettyPrintSection(word: str, total_width: int = 80):
    position = (total_width - len(word)) // 2
    line = '=' * position + word + '=' * (total_width - position - len(word))
    return line