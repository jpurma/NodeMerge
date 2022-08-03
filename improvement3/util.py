import math


def hue(signal):
    h = 0.64 * signal
    return h - math.floor(h)


def find_edge(edges, start=None, end=None):
    for edge in edges:
        if edge.start == start and edge.end == end:
            return edge


def build_tree(word_parts):

    def build_label(label, adjs):
        for adj in adjs:
            if adj in tree_data:
                adj_data = tree_data[adj]
                label += f'+{build_label(adj_data["label"], adj_data["adjs"])}'
        return label

    def stringify(key=0, label='', heads=None, args=None, adjs=None, lparts=None, used=None, top=None):
        if not tree_data[key]['top']:
            tree_data[key]['top'] = top
        if not (args or lparts or adjs):
            return label + str(top)
        if key in used:
            return '<-' + label
        used.add(key)
        ss = label + str(top)
        label = build_label(label, adjs) + str(top)
        for adj in adjs:
            if adj in tree_data:
                if not tree_data[adj]['top']:
                    tree_data[adj]['top'] = top
                elif tree_data[adj]['top'] != top:
                    adj = tree_data[adj]['top']
                ss = f'[.{label} {ss} {stringify(**tree_data[adj], used=used)}]'

        for arg in args:
            if arg < key:
                if not tree_data[arg]['top']:
                    tree_data[arg]['top'] = top
                elif tree_data[arg]['top'] != top:
                    arg = tree_data[arg]['top']
                ss = f'[.{label} {stringify(**tree_data[arg], used=used)} {ss}]'
        for part in lparts:
            if part in tree_data:
                if not tree_data[part]['top']:
                    tree_data[part]['top'] = top
                elif tree_data[part]['top'] != top:
                    part = tree_data[part]['top']
                ss = f'[.{label} {ss} {stringify(**tree_data[part], used=used)}]'
        for arg in args:
            if arg > key:
                if not tree_data[arg]['top']:
                    tree_data[arg]['top'] = top
                elif tree_data[arg]['top'] != top:
                    arg = tree_data[arg]['top']
                ss = f'[.{label} {ss} {stringify(**tree_data[arg], used=used)}]'
        return ss

    def collect_adj_chain(wp_, adjs):
        for edge in wp_.li.adjunctions:
            if edge.end.signal in adjs and edge.start.signal not in adjs:
                adjs.append(edge.start.signal)
                #collect_adj_chain(edge.start, adjs)

    tree_data = {}
    used_items = set()
    parts = []
    for wp in word_parts:
        args = [e.start.signal for e in wp.li.arg_edges if e.end.signal == wp.signal]
        heads = [e.end.signal for e in wp.li.head_edges if e.start.signal == wp.signal]
        adjs = [wp.signal]
        collect_adj_chain(wp, adjs)
        adjs = adjs[1:]
        if wp.li.lex_parts and wp.li.lex_parts[0] == wp.li:
            lparts = [wp.signal + n + 1 for n, lp in enumerate(wp.li.lex_parts[1:])]
            used_items |= set(lparts)
        else:
            lparts = []
        used_items |= set(args)
        used_items |= set(adjs)
        label = wp.li.id
        tree_data[wp.signal] = {'key': wp.signal, 'label': label, 'heads': heads, 'args': args, 'adjs': adjs,
                                'lparts': lparts, 'top': None}
        print(wp.signal, tree_data[wp.signal])

    for wp in word_parts:
        if wp.signal in used_items:
            print('skipping ', wp.signal, ' because it is already used')
            continue
        tree_data[wp.signal]['top'] = wp.signal
        parts.append(stringify(**tree_data[wp.signal], used=set()))
        print(parts[-1])
    print(' '.join(parts))
    return ' '.join(parts)
