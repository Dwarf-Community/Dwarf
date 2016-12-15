"""Storing the various ways to format text on Discord at one place."""


def italics(text):
    return "*{}*".format(text)

i = italics

def bold(text):
    return "**{}**".format(text)

b = bold

def bold_italics(text):
    return "***{}***".format(text)

bi = bold_italics

def underline(text):
    return "__{}__".format(text)

u = underline

def strikethrough(text):
    return "~~{}~~".format(text)

s = strikethrough

def inline_code(text):
    return "`{}`".format(text)

c = inline_code

def block(text, lang=""):
    text = "```{}\n{}\n```".format(lang, text)
    return text

def pagify(text, delims=[], do_escape=True, shorten_by=8, page_length=2000):
    # DOES NOT RESPECT MARKDOWN BOXES OR INLINE CODE
    in_text = text
    while len(in_text) > page_length:
        closest_delim = max([in_text.rfind(d, 0, page_length - shorten_by)
                             for d in delims])
        closest_delim = closest_delim if closest_delim != -1 else page_length
        if do_escape:
            to_send = escape(in_text[:closest_delim], mass_mentions=True)
        else:
            to_send = in_text[:closest_delim]
        yield to_send
        in_text = in_text[closest_delim:]

    if do_escape:
        yield escape(in_text, mass_mentions=True)
    else:
        yield in_text

def escape(text, *, mass_mentions=False, formatting=False):
    if mass_mentions:
        text = text.replace("@everyone", "@\u200beveryone")
        text = text.replace("@here", "@\u200bhere")
    if formatting:
        text = (text.replace("`", "\\`")
                    .replace("*", "\\*")
                    .replace("_", "\\_")
                    .replace("~", "\\~"))
    return text
