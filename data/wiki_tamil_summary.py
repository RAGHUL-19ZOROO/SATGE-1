import wikipedia

# Fetch Tamil Wikipedia summary for a topic.
wikipedia.set_lang("ta")


def get_tamil_summary(topic: str) -> str:
    try:
        return wikipedia.summary(topic)
    except wikipedia.exceptions.DisambiguationError as exc:
        options = ", ".join(exc.options[:5])
        return f"Multiple matches found for '{topic}'. Try one of: {options}"
    except wikipedia.exceptions.PageError:
        return f"No Tamil Wikipedia page found for '{topic}'."


if __name__ == "__main__":
    print(get_tamil_summary("Data Science"))
