import shutil
import mimetypes
import itertools
from pathlib import Path

from clldutils.misc import slug
from csvw.dsv import UnicodeWriter
import attr

import pylexibank


@attr.s
class Lexeme(pylexibank.Lexeme):
    Orthography = attr.ib(default=None)
    Phonetic = attr.ib(default=None)
    Phonemic = attr.ib(default=None)
    Village = attr.ib(default=None)
    Audio_Files = attr.ib(
        default=None,
        metadata=dict(
            separator=' ',
            propertyUrl="http://cldf.clld.org/v1.0/terms.rdf#mediaReference"),
    )


class Dataset(pylexibank.Dataset):
    dir = Path(__file__).parent
    id = "yamfinder"
    lexeme_class = Lexeme

    # register custom data types here (or language_class, lexeme_class, cognate_class):
    # concept_class = Concept

    # define the way in which forms should be handled
    form_spec = pylexibank.FormSpec(
        brackets={"(": ")"},  # characters that function as brackets
        separators=";/,",  # characters that split forms e.g. "a, b".
        missing_data=('?', '-'),  # characters that denote missing data.
        strip_inside_brackets=True  # do you want data removed in brackets or not?
    )

    def cmd_download(self, args):
        header = [
            'Gloss',
            'Orthography',
            'Phonetic',
            'Phonemic',
            'Language',
            'Family',
            'Clade',
            'Village',
            'Linguist',
            'Comment',
            'Audio']
        raw, lookup = None, None
        with self.raw_dir.temp_download("http://www.yamfinder.com", "yamfinder.html") as data:
            for line in data.open('r', encoding='utf8'):
                line = line.strip()
                if line.endswith(';'):
                    line = line[:-1].strip()
                if line.startswith('var arrayRaw ='):
                    raw = eval(line.partition('=')[2])
                if line.startswith('var lookup ='):
                    lookup = eval(line.partition('=')[2])
                    break
        assert raw and lookup
        with UnicodeWriter(self.raw_dir / 'data.csv') as w:
            w.writerow(header)
            for item in raw:
                w.writerow([lookup[i] if isinstance(i, int) else i for i in item])

    def audio_path(self, name):
        p = self.raw_dir / 'audiomp3' / name.replace('.wav', '.mp3')
        return p if p.exists() else None

    def cmd_makecldf(self, args):
        """
        Convert the raw data to a CLDF dataset.

        A `pylexibank.cldf.LexibankWriter` instance is available as `args.writer`. Use the methods
        of this object to add data.
        """
        args.writer.cldf.add_component('MediaTable')
        if not self.cldf_dir.joinpath('audio').exists():
            self.cldf_dir.joinpath('audio').mkdir()
        data = []
        for item in self.raw_dir.read_csv('data.csv', dicts=True):
            item['Gloss'] = item['Gloss'].replace('ŋ', 'n').replace('ʊ', 'u')
            if item['Village'] == 'Drabbe 1954':
                item['Linguist'] = item['Village']
                item['Village'] = ''
            if not item['Linguist']:
                if item['Language'] == 'Maklew':
                    item['Linguist'] = 'Tina Gregor'
                elif item['Language'] == 'Namna':
                    item['Linguist'] = 'Eri Kashima'
                elif item['Language'] == 'Ngkolmpu':
                    item['Linguist'] = 'Matthew Carroll'
                else:
                    assert item['Language'] == 'Marori'
            data.append(item)

        args.writer.add_languages()
        concepts = args.writer.add_concepts(lookup_factory=lambda c: slug(c.english))
        args.writer.add_sources(*self.etc_dir.read_bib())
        linguist2sources = {
            r['Linguist']: r['Sources'].split()
            for r in self.etc_dir.read_csv('sources.csv', dicts=True)}

        audio_id = 0
        for gloss, rows in itertools.groupby(
            sorted(data, key=lambda r: (r['Gloss'], r['Language'])),
            lambda r: r['Gloss'],
        ):
            if not gloss:
                args.log.warning('{} items without gloss'.format(len(list(rows))))
                continue
            for row in rows:
                if slug(row['Language']) == 'prototonda':
                    # Skip preliminary reconstructions.
                    continue
                al = None
                if row['Audio']:
                    audio_path = self.audio_path(row['Audio'])
                    if audio_path:
                        shutil.copy(audio_path, self.cldf_dir / 'audio' / audio_path.name)
                        audio_id += 1
                        al = [audio_id]
                        args.writer.objects['MediaTable'].append(dict(
                            ID=str(audio_id),
                            Name=row['Audio'],
                            Media_Type=mimetypes.guess_type(row['Audio'])[0],
                            Download_URL='audio/{}'.format(audio_path.name),
                        ))
                form = row['Phonetic'] or row['Orthography'] or row['Phonemic']
                lex = args.writer.add_form(
                    Language_ID=slug(row['Language']),
                    Parameter_ID=concepts[slug(gloss)],
                    Value=form,
                    Form=form,
                    Orthography=row['Orthography'],
                    Phonetic= row['Phonetic'],
                    Phonemic=row['Phonemic'],
                    Village=row['Village'],
                    Comment=row['Comment'],
                    Source=linguist2sources.get(row['Linguist'], []),
                    Audio_Files=al,
                )
