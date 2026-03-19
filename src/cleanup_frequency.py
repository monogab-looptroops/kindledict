"""
One-time cleanup: remove garbage entries from wiktionary-frequency import.

The wiktionary-frequency source had corrupted data where Hungarian words,
names, places, and dash-separated pairs leaked into the Dutch dictionary.
"""

import os
import yaml

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DICT_DIR = os.path.join(PROJECT_ROOT, 'dictionary', 'nl')

# All garbage entries to remove, keyed by yaml filename
TO_REMOVE = {
    'a.yaml': {'Agnes', 'Andrea', 'Andrew', 'Attila', 'abba', 'adhat', 'adj', 'adunk', 'adva',
                'akarta', 'akit', 'alig', 'alpha', 'ama', 'amibe', 'amin', 'amire', 'amolyan',
                'anders-', 'antal', 'apja', 'arra', 'auto - autó'},
    'b.yaml': {'BBCode', 'BSD', 'Balaton', 'Balogh', 'Balázs', 'Bartók', 'Bill', 'Boedapest',
                'Bálint', 'Béla', 'baja', 'bajom', 'basics', 'berg-', 'bort', 'budai'},
    'c.yaml': {'Charles', 'Csaba', 'Csongrád', 'checker', 'claims', 'credit'},
    'd.yaml': {'Denes', 'Desi', 'dalt', 'dating', 'deelnemer - résztvevő', 'detail-', 'deur-',
                'deák', 'div', 'dkg', 'dolga', 'drives'},
    'e.yaml': {'ELTE', 'Ernő', 'Eötvös', 'egri', 'einem', 'eme', 'emeli', 'endre', 'esete',
                'essence', 'tegen - ellen, vmikorra'},
    'f.yaml': {'Ferenc', 'Fidesz', 'Finoman', 'fakad', 'false', 'filmje', 'fodor', 'forint', 'formai'},
    'g.yaml': {'Gaspar', 'George', 'Gyula', 'Győr', 'Gábor', 'Géza', 'gas-',
                'gedachte - gondoloat', 'gergely'},
    'h.yaml': {'HUF', 'Halkan', 'Horváth', 'haar-', 'hadd', 'haja', 'halad', 'hand-', 'hart-',
                'headers', 'helemaal - teljesen', 'hidd', 'hoofd - fej'},
    'i.yaml': {'Ildikó', 'Ilona', 'Imre', 'Ivan', 'ily', 'intel', 'items'},
    'j.yaml': {'Jakab', 'Jenő', 'Joseph', 'Judit', 'jaj', 'januari-', 'jele', 'jeles',
                'juli-', 'juni-', 'jusson'},
    'k.yaml': {'KDE', 'Katalin', 'Kerstmis-', 'Kossuth', 'Kálmán', 'Können', 'kapja', 'kari',
                'kepi', 'keuken-', 'kht.', 'kis', 'knoop - gomb', 'komen - jönni', 'kora',
                'korig', 'krant - újság', 'krant-'},
    'l.yaml': {'LED', 'Laci', 'Lajos', 'Lakos', 'Lapon', 'Lapot', 'Lucky', 'Luke', 'lakik',
                'lalja', 'land-', 'landol', 'lapra', 'later - később', 'levele',
                'levering - szállítás', 'lied - ének', 'linket', 'linkre', 'linux', 'ltd.'},
    'm.yaml': {'MDF', 'Margit', 'Martha', 'Martin', 'Matthew', 'Matáv', 'Medgyessy', 'Michael',
                'Miket', 'Miskolc', 'MÁV', 'massa-', 'mayoral', 'meddig', 'meer - még', 'merre',
                'miatti', 'minap', 'model-', 'moder', 'moedertaalspreker - anyanyelvi beszélő',
                'moedig - bátor', 'musical', 'muziek-'},
    'n.yaml': {'Nee.', 'Neves', 'Norbi', 'Németh', 'naast - mellett', 'napig', 'napra',
                'native', 'netto-', 'nevezi', 'nk'},
    'o.yaml': {'Onderzoek - kutatás', 'Orbán', 'Otto', 'ochtend-', 'okai', 'okán', 'olie-',
                'olva', 'oly', 'olyat', 'ongelooflijk - hihetetlen', 'oosten-'},
    'p.yaml': {'Pannon', 'Pentium', 'Petofi', 'Php', 'Pécs', 'papi', 'papok', 'par', 'parti',
                'parton', 'patak', 'pert', 'pesti', 'progi'},
    'r.yaml': {'RTL', 'Roma', 'Rákóczi', 'Réka', 'rangot', 'rejlik', 'rendre', 'rivier-', 'rovat'},
    's.yaml': {'SZDSZ', 'Satan', 'Sept.', 'Simon', 'Somogy', 'Soros', 'Sorra', 'Sovjet-',
                'Szabolcs', 'Szeged', 'Szekler', 'Szolnok', 'Széchenyi', 'scherp - éles',
                'school-', 'sg', 'sms - sms', 'sopron', 'sora', 'soron', 'sorsa', 'sport-',
                'spreadsheet - táblázat', 'standaard-', 'sterker - erőssebb', 'strategie -',
                'strijd - harc', 'sy', 'sztem', 'veel - sok'},
    't.yaml': {'Tibor', 'Tilos', 'Tóth', 'telik', 'temperatuur-', 'tennie', 'tisza',
                'toespraak - beszéd <speech>', 'tok', 'tram-', 'trustee', 'tuin-', 'tus'},
    'u.yaml': {'USB', 'uhu', 'ura', 'urak', 'urat', 'urunk', 'uális'},
    'v.yaml': {'Viktor', 'Villusi', 'Vilmos', 'Viszi', 'vedd', 'veld-', 'vervoer-', 'veti',
                'video-', 'vinni', 'viseli', 'volta', 'von', 'vén'},
    'w.yaml': {'webes'},
    'z.yaml': {'Zala', 'Zoltán', 'Zsolt', 'Zsuzsa', 'Zsuzsanna', 'za', 'zoet - édes', 'zoiets - ilyen'},
}


def main():
    total_removed = 0
    for filename, bad_words in sorted(TO_REMOVE.items()):
        filepath = os.path.join(DICT_DIR, filename)
        if not os.path.exists(filepath):
            print(f'  {filename}: not found, skipping')
            continue
        with open(filepath, 'r', encoding='utf-8') as f:
            entries = yaml.safe_load(f) or []
        before = len(entries)
        entries = [e for e in entries if e['word'] not in bad_words]
        removed = before - len(entries)
        if removed > 0:
            with open(filepath, 'w', encoding='utf-8') as f:
                yaml.dump(entries, f, allow_unicode=True, default_flow_style=False,
                          sort_keys=False, width=120)
            print(f'  {filename}: removed {removed} entries ({len(entries)} remaining)')
            total_removed += removed
        else:
            print(f'  {filename}: nothing to remove')

    print(f'\nTotal removed: {total_removed} garbage entries')


if __name__ == '__main__':
    main()
