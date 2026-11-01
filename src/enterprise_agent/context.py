"""Small user-statement ledger. It never treats prior assistant answers as facts."""
import re
from decimal import Decimal


def user_facts(state):
    facts = {}
    messages = [m['content'] for m in state.history if m['role'] == 'user'] + [state.question]
    for index, text in enumerate(messages):
        # Latest explicit self statement wins; do not carry a disproved role forward.
        events = []
        hypothetical = re.search(r"如果|假如|假设|要是", text)
        if not hypothetical:
            for match in re.finditer(r"(?:我|本人)(?:目前|现在|已经|已|刚刚|刚)?(?:已经|已)?是(?:个)?(正式员工|实习生)", text):
                events.append((match.start(), match[1], match[0]))
            for match in re.finditer(r"(?:我|本人)?(?:并)?不是(正式员工|实习生)", text):
                events.append((match.start(), None, match[0]))
            # A corrective second clause: “我不是正式员工，是实习生”.
            if events:
                for match in re.finditer(r"(?:^|[，,。；;])\s*(?:而)?是(正式员工|实习生)", text):
                    events.append((match.start(), match[1], match[0]))
            for match in re.finditer(r"(?:我|本人)(?:目前|现在|已经|已|刚刚|刚)?(?:已经|已)?转正(?:了)?", text):
                events.append((match.start(), '正式员工', match[0]))
        for _, role, quote in sorted(events, key=lambda item: item[0]):
            if role is None:
                facts.pop('role', None)
            else:
                facts['role'] = {'value': role, 'user_message': index, 'quote': quote}
        if re.search(r'(?:这是|是|住了|住的|为|共|只住了)一晚|一晚住的', text):
            facts['one_night'] = {'value': True, 'user_message': index, 'quote': text}
        # Yesterday alone does not establish the number of hotel nights.
        for match in re.finditer(r'(?:宾馆|住宿)(?:费用|费)?(?:为|是)?\s*(\d+(?:\.\d+)?)元', text):
            facts['hotel_amount'] = {'value': match[1], 'user_message': index, 'quote': match[0]}
    return facts


def hotel_comparison(state, verified):
    facts = user_facts(state)
    if facts.get('role', {}).get('value') != '正式员工' or not facts.get('one_night') or not facts.get('hotel_amount'):
        return ''
    for c in verified:
        # Derive only from an actually verified source sentence with explicit scope and units.
        if c['scope'] != '正式员工' or '中国大陆出差' not in c['quote']:
            continue
        match = re.search(r'住宿费用上限为每晚(\d+(?:\.\d+)?)元', c['quote'])
        if match:
            amount = Decimal(facts['hotel_amount']['value'])
            cap = Decimal(match[1])
            relation = '未超过' if amount <= cap else '超过'
            return (f"根据你提供的信息，正式员工一晚住宿费为{amount}元，{relation}资料规定的每晚{cap}元上限。"
                    f"若本次是在中国大陆出差，该比较适用；这是金额标准比较，不代表已确认全部报销条件。[{c['doc_id']}]")
    return ''
