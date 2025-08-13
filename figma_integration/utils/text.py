import re


class TextUtils:
    @staticmethod
    def count_words(text: str) -> int:
        if not text:
            return 0
        return len([w for w in re.split(r"\s+", text) if w.strip()])

    @staticmethod
    def count_sentences(text: str) -> int:
        if not text:
            return 0
        split_result = [s for s in re.split(r"[.!?]", text)]
        n = len([s for s in split_result if s.strip()])
        return n if n > 0 else 1
