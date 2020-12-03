import os, json

geographies = ["constituencies", "countries", "regions"]

def convert(geographies, input_dir="json", choice_dir="choices", dict_dir="dictionaries", py_dir="python"):
    for geo in geographies:
        choices, dictionary, python = {}, {}, {}
        path = os.path.dirname(os.path.abspath(__file__))
        source = os.path.join(path, input_dir, (geo + ".json"))
        choices["file"] = os.path.join(path, choice_dir, (geo + ".py"))
        dictionary["file"] = os.path.join(path, dict_dir, (geo + ".py"))
        python["file"] = os.path.join(path, py_dir, (geo + ".py"))

        locales = read(source)

        choices["list"] = to_choices(locales)
        dictionary["list"] = to_dictionary(geo, locales)
        check_unique(choices["list"], geo)

        write(dictionary["file"], geo.upper(),  dictionary["list"], as_list=True)
        write(choices["file"], geo.upper(), choices["list"], as_list=True)
        write(python["file"], geo.upper(), locales, as_list=False)


def read(source):
    with open(source, "r") as json_file:
        return json.loads(json_file.read())

def to_choices(locales):
    return [(k, v) for k, v in locales.items()]

def to_dictionary(geo, locales):
    code = "code" if geo == "countries" else "ons_code"
    return [{code: k, "name": v} for k, v in locales.items()]

def check_unique(choices, geo):
    unique = len(set(choices)) == len(choices)
    if not unique:
        raise ValueError(f"{geo} locales must be unique, duplicates found")

# pickle could be used here
def write(filename, variable, content, as_list):
    indent, newline, comma = "    ", "\n", ","
    open_br, close_br = "[", "]"
    f_line = lambda content: f"{indent}{content}{comma}{newline}"

    with open(filename, "w") as write_list:
        if as_list:
            write_list.write(f"{variable} = {open_br}{newline}")
            for item in content:
                write_list.write(f_line(item))
            write_list.write(f"{close_br}{newline}")
        else:
            dumped = json.dumps(content, indent=4, sort_keys=True)
            write_list.write(f"{variable} = {dumped}")



convert(geographies)