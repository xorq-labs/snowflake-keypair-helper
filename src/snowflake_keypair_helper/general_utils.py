import operator
import random
import re
import string


HEADER_DASHES = "-----"
BEGIN = "BEGIN"
END = "END"


def make_private_key_pwd(k=20, choices=string.ascii_letters + string.digits):
    return "".join(random.choices(choices, k=k))


encode_utf8 = operator.methodcaller("encode", "utf-8")


decode_ascii = operator.methodcaller("decode", "ascii")


def filter_none_one(el):
    # for use with *args
    return filter(None, (el,))


def remove_delimiters(key_str):
    def maybe_match(string):
        return f"(?:{string})?"

    def named_group(name, pattern):
        return f"(?P<{name}>{pattern})"

    def named_backreference(name):
        return f"(?P={name})"

    infix_name, infix_pattern = "infix", "[A-Z\\s]+?"
    inner_text_name, inner_text_pattern = "inner_text", "[^-]+"
    begin_pattern = f"{HEADER_DASHES}{BEGIN} {named_group(infix_name, infix_pattern)}{HEADER_DASHES}"
    end_pattern = (
        f"{HEADER_DASHES}{END} {named_backreference(infix_name)}{HEADER_DASHES}"
    )
    pattern = f"{maybe_match(begin_pattern)}{named_group(inner_text_name, inner_text_pattern)}{maybe_match(end_pattern)}"
    match = re.match(pattern, key_str)
    if match:
        dct = match.groupdict()
        inner_text = dct[inner_text_name]
        infix = dct.get(infix_name)
        return inner_text, infix
    else:
        raise ValueError("key_str does not match key-with-headers pattern")


def remove_public_key_delimiters(public_key_str):
    # https://docs.snowflake.com/en/user-guide/key-pair-auth#assign-the-public-key-to-a-snowflake-user
    # # Note: Exclude the public key delimiters in the SQL statement.
    inner_text, infix = remove_delimiters(public_key_str)
    assert infix == "PUBLIC KEY"
    return inner_text


def ensure_header_footer(key_str, private_key_pwd=None, infix="PRIVATE KEY"):
    if not key_str.startswith(HEADER_DASHES):
        header = f"{HEADER_DASHES}{BEGIN} {'ENCRYPTED ' if private_key_pwd else ''}{infix}{HEADER_DASHES}"
        footer = f"{HEADER_DASHES}{END} {'ENCRYPTED ' if private_key_pwd else ''}{infix}{HEADER_DASHES}"
        key_str = "\n".join((header, key_str, footer, ""))
    return key_str


def make_oneline(string):
    try:
        string, _ = remove_delimiters(string)
        string = re.sub("\\s", "", string)
    except ValueError:
        pass
    assert "\n" not in string
    return string
