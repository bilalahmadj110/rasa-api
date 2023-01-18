import ruamel.yaml
yaml = ruamel.yaml.YAML()
import yaml as yamlreader
from flask import Flask, jsonify, request, abort
from flask_cors import CORS, cross_origin

app = Flask(__name__)

FILE_PATH_STORIES = r'/home/user/Downloads/AIBot/data/stories.yml'
FILE_PATH_NLU = r'/home/user/Downloads/AIBot/data/nlu.yml'
DOMAIN_FILE_PATH = r'/home/user/Downloads/AIBot/domain.yml'

# add new intent with examples
def write_nlu(name, examples):
    with open(FILE_PATH_NLU) as fp:
        data = yaml.load(fp)
    # if intent already exists
    for intent in data['nlu']:
        if intent['intent'] == name:
            new_intent = {'intent': name, 'examples': examples}
            intent.update(new_intent)
            yaml.indent(mapping=2, sequence=4, offset=2)
            with open(FILE_PATH_NLU, 'w') as f:
                yaml.dump(data, f)
            break
    else:
        print ("intent not found")
        # CommentedMap
        new_intent = {'intent': name, 'examples': examples}
        data['nlu'].append(new_intent)
        yaml.indent(mapping=2, sequence=4, offset=2)
        with open(FILE_PATH_NLU, 'w') as f:
            yaml.dump(data, f)

def get_intent_list():
    with open(FILE_PATH_NLU, 'r') as stream:
        try:
            nlu = yamlreader.load(stream)
            intents = [i['intent'].split('\n') for i in nlu['nlu']]
            # flatten list
            intents = [item.strip('- ') for sublist in intents for item in sublist if item]
            return intents
        except Exception as e:
            abort(500, str(e))
    return []

def get_response_list():
    responses = []
    with open(DOMAIN_FILE_PATH, 'r') as stream:
        try:
            domain = yamlreader.load(stream)
            responses = domain['responses']
        except Exception as e:
            abort(500, str(e))
    return responses

def add_new_response(name, text):
    file_name = DOMAIN_FILE_PATH
    with open(file_name) as fp:
        data = yaml.load(fp)
    # if intent already exists
    for intent in data['responses']:
        if intent == name:
            # support multiple lines
            data['responses'][intent].append({'text': text})
            with open(file_name, 'w') as fp:
                yaml.dump(data, fp)
            return

    data['responses'][name] = [{'text': text}]
    with open(file_name, 'w') as fp:
        yaml.dump(data, fp)

def add_intent_domain(intent_name):
    file_name = DOMAIN_FILE_PATH
    with open(file_name) as fp:
        data = yaml.load(fp)
    for intent in data['intents']:
        if intent == intent_name:
            print ("intent already exists")
            return
    data['intents'].append(intent_name)
    with open(file_name, 'w') as fp:
        yaml.dump(data, fp)

@app.route('/story', methods=['GET'])
def get_stories():
    stories = []
    with open(FILE_PATH_STORIES, 'r') as stream:
        try:
            stories = yamlreader.load(stream)
            stories = [story['story'] for story in stories['stories']]
        except Exception as e:
            abort(500, str(e))
    if not stories:
        abort(404, 'No data found')
    return jsonify(stories), 200


@app.route('/story/<story_name>', methods=['GET'])
def get_story(story_name):
    story = {}
    with open(FILE_PATH_STORIES, 'r') as stream:
        try:
            stories = yamlreader.safe_load(stream)
            for story in stories['stories']:
                if story['story'] == story_name:
                    steps = story['steps'] 
                    output = []
                    intent_action = {}
                    for step in steps:
                        if 'action' not in intent_action and 'intent' in intent_action and 'action' in step:
                            intent_action['action'] = step['action']
                            output.append(intent_action)
                            intent_action = {}
                        if 'intent' not in intent_action and 'intent' in step:
                            intent_action['intent'] = step['intent']
                       
                    return jsonify(output), 200
        except Exception as e:
            abort(500, str(e))
    abort(404, 'No data found')

# add new story
@app.route('/story', methods=['POST'])
def add_story():
    story = request.get_json()
    if not story:
        abort(400, 'No data provided')

    with open(FILE_PATH_STORIES, 'r') as stream:
        try:
            stories = yamlreader.safe_load(stream)
            stories['stories'].append(story)
            # yaml.dump(stories, stream, default_flow_style=False, indent=4)
        except Exception as e:
            # throw server error, 500
            print (e)
            abort(500, str(e))
    
    with open(FILE_PATH_STORIES, 'w') as stream:
        yaml.indent(mapping=2, sequence=4, offset=2)
        yaml.dump(stories, stream)

    return jsonify(story), 201


@app.route('/intent', methods=['GET'])
def get_intents():
    # check if search query is provided
    name = request.args.get('name')
    intents = get_intent_list()
    if not intents:
        abort(404, 'No data found')
    return jsonify({"count": len(intents), "data":intents}), 200

@app.route('/intent/<intent_name>', methods=['GET'])
def get_intent(intent_name):
    intent = {}
    with open(FILE_PATH_NLU, 'r') as stream:
        try:
            nlu = yamlreader.safe_load(stream)
            for intent in nlu['nlu']:
                if intent['intent'] == intent_name:
                    intent['examples'] = intent['examples'].split('\n')
                    intent['examples'] = [item.strip('- ') for item in intent['examples'] if item]
                    return jsonify(intent), 200
        except Exception as e:
            abort(500, str(e))
    abort(404, 'No data found')

# add new intent with examples
@app.route('/intent', methods=['POST'])
def add_intent():
    intent = request.get_json()
    if not intent:
        abort(400, 'No data provided')
    intent_name = intent.get('intent')
    intent_examples = intent.get('examples')
    if not intent_name or not intent_examples:
        abort(400, 'Invalid data provided')

    # write to NLU.yml
    write_nlu(intent_name, intent_examples)

    # replace all examples: with examples: |
    string = open(FILE_PATH_NLU).read()
    string  = string.replace("examples: |", "examples:")
    string  = string.replace("examples:", "examples: |")
    with open(FILE_PATH_NLU, 'w') as f1:
        f1.write(string)

    # writing intent name to domain.yml
    add_intent_domain(intent_name)

    return jsonify(intent), 201

# get responses
@app.route('/response', methods=['GET'])
def get_responses():
    # check if search query is provided
    name = request.args.get('name')
    responses = get_response_list()
    if not responses:
        abort(404, 'No data found')
    return jsonify({"count": len(responses), "data":responses}), 200

# add new response
@app.route('/response', methods=['POST'])
def add_response():
    response = request.get_json()
    if not response:
        abort(400, 'No data provided')
    resp_name = response.get('name')
    text = response.get('text')
        
    if not resp_name or not text:
        abort(400, 'Invalid data provided')

    # write to domain.yml
    add_new_response(resp_name, text)

    return jsonify(response), 201



if __name__ == '__main__':
    app.run(debug=True)