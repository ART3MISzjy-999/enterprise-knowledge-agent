"""Provider-enforced wire schema; action selection remains entirely model-owned."""
def obj(properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}

TEXT = {'type': 'string'}
RESULT = obj({'status': {'type': 'string', 'enum': ['answered','conflict','insufficient','incomplete','needs_clarification']},
              'citations': {'type': 'array', 'items': obj({'doc_id': TEXT, 'quote': TEXT})},
              'missing_info': {'type': 'array', 'items': TEXT}, 'question': TEXT})
BRANCHES = [obj({'action': {'type':'string','enum':[action]}, 'reason': TEXT, 'arguments': args})
            for action,args in [('search_documents', obj({'query': TEXT, 'top_k': {'type':'integer'}})),
                                ('read_document', obj({'doc_id': TEXT}))]]
BRANCHES += [obj({'action': {'type':'string','enum':[action]}, 'reason': TEXT, 'result': RESULT})
             for action in ['finish','clarify']]
RESPONSE_FORMAT = {'type':'json_schema', 'json_schema': {'name':'agent_decision', 'strict':True,
                   'schema': obj({'decision': {'anyOf': BRANCHES}})}}
