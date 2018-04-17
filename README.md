text
====

Python library and tools for manipulating text document annotations.


Installation
------------

~~~~
python setup.py install
~~~~


App: web viewer
---------------

TODO: synchronize repository

1. Generate a JSON dump of a document, or use `docs/obnoxious.json`
2. Navigate to `apps/webviewer`
3. Setup a virtual environment:
   `virtualenv -p python3 venv;`
   `source venv/bin/activate;`
   `pip install -r requirements.txt`
4. Start the server: `./webapp.py ../../docs/obnoxious.json`
5. If you want to please your browser, install the root certificate in your browser
6. Point your browser to the web page at `http://localhost:8080`


App: privacy proxy
------------------

Dependencies:

- libffx, https://github.com/kpdyer/libffx
- FPE library, ssh://git@bitbucket.dev.holmes.nl:7999/kec/fpe.git
- python 2.7 (required by libffx)

1. Navigate to `apps/webviewer`
2. Setup a virtual environment:
   `virtualenv -p python2.7 venv;`
   `source venv/bin/activate;`
   `pip install -r requirements.txt`
3. Configure your browser to use HTTP proxy http://localhost:8080


App: Named Entity Recognition
-----------------------------

Basic NER tools using Conditional Random Fields.

Setup a NER environment:

1. Navigate to `apps/ner`
2. Setup a virtual environment:
   `virtualenv -p python3 venv;`
   `source venv/bin/activate;`
   `pip install -r requirements.txt`
3. Build a model using CoNLL data (Dutch):
   `./run.py --input-format conll --train ../../corpora/conll2002/ned.train`
   Alternatively, use Sonar (large dataset -- may take a long time):
   `./run.py --input-format sonar --train ../../corpora/sonar/*.iob`

Next, parse any Sonar file:

`./run.py --input-format sonar --tag ../../corpora/sonar/WR-P-E-I-0000000004.iob`

Or, parse a plain text file:

`./run.py --input-format text --tag MYTEXTFILE.txt`


Using the library
-----------------

Example application:

~~~~
import text

pipeline = text.Pipeline([text.tokenizer.Tokenizer()])

dict = text.dictionary.AnnotatorDictionary(':memory:', reset=True)
dict.add(['Dean'], 'person', {'type': 'name'})
dict.add(['redheaded', 'deputy'], 'person', {'type': 'reference'})
dict.add(['obnoxious', 'jerk'], 'person', {'type': 'reference'})
pipeline.append(text.dictionary.DictionaryAnnotator(dict))

doc = text.Document('Dean cursed himself for not wanting to talk to the redheaded deputy, who would have been infinitely preferable to this obnoxious jerk.')

pipeline.process(doc)
print(doc.toJson())
~~~~

Result:

~~~~
{
  "annotations": [
    {"span": [0, 4], "type": "token", "features": {"string": "Dean"}},
    {"span": [0, 4], "type": "person", "features": {"type": "name"}},
    {"span": [4, 5], "type": "space", "features": {"string": " "}},
    {"span": [5, 11], "type": "token", "features": {"string": "cursed"}},
    {"span": [11, 12], "type": "space", "features": {"string": " "}},
    {"span": [12, 19], "type": "token", "features": {"string": "himself"}},
    {"span": [19, 20], "type": "space", "features": {"string": " "}},
    {"span": [20, 23], "type": "token", "features": {"string": "for"}},
    {"span": [23, 24], "type": "space", "features": {"string": " "}},
    {"span": [24, 27], "type": "token", "features": {"string": "not"}},
    {"span": [27, 28], "type": "space", "features": {"string": " "}},
    {"span": [28, 35], "type": "token", "features": {"string": "wanting"}},
    {"span": [35, 36], "type": "space", "features": {"string": " "}},
    {"span": [36, 38], "type": "token", "features": {"string": "to"}},
    {"span": [38, 39], "type": "space", "features": {"string": " "}},
    {"span": [39, 43], "type": "token", "features": {"string": "talk"}},
    {"span": [43, 44], "type": "space", "features": {"string": " "}},
    {"span": [44, 46], "type": "token", "features": {"string": "to"}},
    {"span": [46, 47], "type": "space", "features": {"string": " "}},
    {"span": [47, 50], "type": "token", "features": {"string": "the"}},
    {"span": [50, 51], "type": "space", "features": {"string": " "}},
    {"span": [51, 60], "type": "token", "features": {"string": "redheaded"}},
    {"span": [51, 67], "type": "person", "features": {"type": "reference"}},
    {"span": [60, 61], "type": "space", "features": {"string": " "}},
    {"span": [61, 67], "type": "token", "features": {"string": "deputy"}},
    {"span": [67, 68], "type": "punct", "features": {"string": ","}},
    {"span": [68, 69], "type": "space", "features": {"string": " "}},
    {"span": [69, 72], "type": "token", "features": {"string": "who"}},
    {"span": [72, 73], "type": "space", "features": {"string": " "}},
    {"span": [73, 78], "type": "token", "features": {"string": "would"}},
    {"span": [78, 79], "type": "space", "features": {"string": " "}},
    {"span": [79, 83], "type": "token", "features": {"string": "have"}},
    {"span": [83, 84], "type": "space", "features": {"string": " "}},
    {"span": [84, 88], "type": "token", "features": {"string": "been"}},
    {"span": [88, 89], "type": "space", "features": {"string": " "}},
    {"span": [89, 99], "type": "token", "features": {"string": "infinitely"}},
    {"span": [99, 100], "type": "space", "features": {"string": " "}},
    {"span": [100, 110], "type": "token", "features": {"string": "preferable"}},
    {"span": [110, 111], "type": "space", "features": {"string": " "}},
    {"span": [111, 113], "type": "token", "features": {"string": "to"}},
    {"span": [113, 114], "type": "space", "features": {"string": " "}},
    {"span": [114, 118], "type": "token", "features": {"string": "this"}},
    {"span": [118, 119], "type": "space", "features": {"string": " "}},
    {"span": [119, 128], "type": "token", "features": {"string": "obnoxious"}},
    {"span": [119, 133], "type": "person", "features": {"type": "reference"}},
    {"span": [128, 129], "type": "space", "features": {"string": " "}},
    {"span": [129, 133], "type": "token", "features": {"string": "jerk"}},
    {"span": [133, 134], "type": "punct", "features": {"string": "."}}
  ],
  "content": "Dean cursed himself for not wanting to talk to the redheaded deputy, who would have been infinitely preferable to this obnoxious jerk.",
  "features": {}}
~~~~


Trouble shooting
----------------

### Problems installing Bottle using pip

Error message: pip._vendor.requests.exceptions.InvalidSchema: Missing dependencies for SOCKS support.

Solution: see http://stackoverflow.com/questions/38794015/pythons-requests-missing-dependencies-for-socks-support-when-using-socks5-fro
