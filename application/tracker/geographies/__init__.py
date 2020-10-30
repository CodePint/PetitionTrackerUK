import os, json

def deserialize(input_dir, output_dir, geographies):
    for geography in geographies:
        path = os.path.dirname(os.path.abspath(__file__))
        input_file = os.path.join(path, input_dir, (geography + '.json'))
        output_file = os.path.join(path, output_dir, (geography + '.py'))
        init_choice(geography, input_file, output_file)


def init_choice(geography, source, dest):
    with open(source, 'r') as json_file:
        data = json.loads(json_file.read())
        choice_list = list(data.items())

    with open(dest, 'w') as py_file:
        py_file.write("{} = [\n".format(geography.upper()))
        for choice_tuple in choice_list:
            py_file.write("    {},\n".format(choice_tuple))
        py_file.write("]\n")

    return choice_list

deserialize(
    input_dir='json',
    output_dir='choices',
    geographies=['constituencies', 'countries', 'regions']
)