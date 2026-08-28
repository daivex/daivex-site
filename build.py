# -*- coding: utf-8 -*-
"""
Сборщик сайта daivex.

    python build.py

Читает .md из папок разделов (content/<папка>/), прогоняет тело через
markdown, подставляет в шаблон страницы раздела и кладёт готовые страницы
в корень папки сайта; из тех же исходников собирает index.html
по templates/index.html.

Имя файла: content/keysy/finansovyj-reestr.md -> kejs-finansovyj-reestr.html
(префикс раздела, чтобы адреса совпадали с уже опубликованными).

Всё, что отличает один раздел от другого, лежит в RAZDELY ниже.

Порог: раздел выходит на главную, только когда в папке набралось 'porog'
записей. Одно это число управляет сразу всем — секцией, пунктом меню,
ссылкой в подвале, карточкой входа и обратной ссылкой со страниц
материалов, — поэтому ссылок на скрытый раздел не бывает по построению.
Страницы самих материалов собираются всегда, независимо от порога.

Ничего, кроме собственных .html, сборщик не трогает.
"""

import io
import os
import sys

import markdown

ROOT = os.path.dirname(os.path.abspath(__file__))
KONTENT = os.path.join(ROOT, 'content')
SHABLONY = os.path.join(ROOT, 'templates')
SHABLON_INDEX = os.path.join(SHABLONY, 'index.html')

# Разделы сайта. Порядок — порядок секций на главной и строк отчёта.
#
#   klyuch     ключ подстановки {{sekciya_<klyuch>}} в templates/index.html
#   papka      папка в content/
#   imya       человеческое имя раздела (отчёт)
#   prefiks    приставка имени выходного html
#   shablon    шаблон страницы материала в templates/
#   karta      вид карточки: 'stroka' (кейсы), 'plitka', 'stiker'
#   sekciya    id секции на главной, он же якорь ссылок
#   menyu      текст пункта меню в шапке
#   podval     текст ссылки в подвале
#   nazad      подпись обратной ссылки на странице материала
#   sled       подпись ссылки на следующий материал
#   zagolovok  заголовок секции на главной
#   said       подводка под заголовком секции
#   porog      сколько записей нужно, чтобы раздел вышел на сайт
#   gate       карточка входа в скрытом пока блоке входов (или None)
RAZDELY = [
    {
        'klyuch': 'keysy',
        'papka': 'keysy',
        'imya': 'Кейсы',
        'prefiks': 'kejs-',
        'shablon': 'material.html',
        'karta': 'stroka',
        'sekciya': 'keysy',
        'menyu': 'Кейсы',
        'podval': 'Кейсы',
        'nazad': 'Все кейсы',
        'sled': 'Следующий кейс',
        'zagolovok': 'Кейсы',
        'said': ('Разобранный процесс: что делалось руками, сколько это '
                 'занимало, что осталось за человеком. Со своими замерами '
                 'и без выдуманных цифр.'),
        'porog': 1,
        'gate': ('    <a class="gate g2" href="#keysy"><span class="wash"></span>\n'
                 '      <h3>Кейсы применения ИИ</h3>\n'
                 '      <p>Разобранные процессы: что делалось руками, сколько это занимало, где встал ИИ и что осталось за человеком. Со своими замерами и без выдуманных цифр.</p>\n'
                 '      <span class="go">Смотреть кейсы →</span></a>'),
    },
    {
        'klyuch': 'instrumenty',
        'papka': 'instrumenty',
        'imya': 'Инструменты',
        'prefiks': 'instrument-',
        'shablon': 'instrument.html',
        'karta': 'plitka',
        'sekciya': 'instr',
        'menyu': 'Инструменты',
        'podval': 'Инструменты',
        'nazad': 'Все инструменты',
        'sled': 'Следующий инструмент',
        'zagolovok': 'Новые инструменты',
        'said': ('Разбор инструмента: что он делает, как устроен внутри, '
                 'сколько стоит и в каких задачах имеет смысл.'),
        'porog': 3,
        'gate': None,
    },
    {
        'klyuch': 'zametki',
        'papka': 'zametki',
        'imya': 'Заметки',
        'prefiks': 'zametka-',
        'shablon': 'zametka.html',
        'karta': 'stiker',
        'sekciya': 'zametki',
        'menyu': 'Заметки',
        'podval': 'Заметки',
        'nazad': 'Все заметки',
        'sled': 'Следующая заметка',
        'zagolovok': 'Новые заметки',
        'said': ('Короткие наблюдения по ходу работы: что сломалось, что '
                 'оказалось проще, чем казалось, и какие выводы пришлось '
                 'переписать.'),
        'porog': 3,
        'gate': None,
    },
    {
        'klyuch': 'baza',
        'papka': 'baza',
        'imya': 'База знаний',
        'prefiks': 'baza-',
        'shablon': 'zametka.html',
        'karta': 'plitka',
        'sekciya': 'baza',
        'menyu': 'База знаний',
        'podval': 'База знаний',
        'nazad': 'Вся база знаний',
        'sled': 'Следующий материал',
        'zagolovok': 'Новое в базе знаний',
        'said': ('Справочник по чужим технологиям: что это такое, зачем '
                 'нужно, сколько стоит и в каких задачах имеет смысл '
                 'применять.'),
        'porog': 3,
        'gate': ('    <a class="gate g3" href="#baza"><span class="wash"></span>\n'
                 '      <h3>Пошаговые материалы по автоматизации</h3>\n'
                 '      <p>Технологии, сервисы и приёмы разобраны по шагам: что умеют, где ломаются, сколько стоят и в каких задачах имеют смысл.</p>\n'
                 '      <span class="go">Открыть материалы →</span></a>'),
    },
]

# tip -> текст плашки над заголовком и класс плашки в карточке на главной.
# Плашки живут только у кейсов.
PLASHKA = {
    'nash': 'Наш кейс',
    'rynok': 'Пример рынка',
}
PLASHKA_KLASS = {
    'nash': 'own',
    'rynok': 'mkt',
}

# приставки строки «было/стало»; значение иногда уже набрано с ними
PRIPISKI = ('было', 'стало')


def chitat_md(put):
    """Разбирает файл на блок --- ... --- и тело."""
    tekst = io.open(put, encoding='utf-8').read().replace('\r\n', '\n')
    polya = {}
    telo = tekst

    if tekst.startswith('---\n'):
        konec = tekst.find('\n---', 3)
        if konec != -1:
            shapka = tekst[4:konec]
            telo = tekst[konec + 4:].lstrip('\n')
            for stroka in shapka.split('\n'):
                if not stroka.strip() or ':' not in stroka:
                    continue
                klyuch, znachenie = stroka.split(':', 1)
                polya[klyuch.strip()] = znachenie.strip()

    return polya, telo


def sobrat_temy(znachenie):
    """'A, B' -> строки <span class="tag">…</span>."""
    temy = [t.strip() for t in znachenie.split(',') if t.strip()]
    return '\n'.join('      <span class="tag">%s</span>' % t for t in temy)


def sobrat_meta(polya):
    """Строка выходных данных материала.

    Отсутствующее поле просто не даёт своего блока: у заметки нет ни
    подзаголовка, ни отрасли, и пустых <span> в разметке не остаётся.
    """
    chasti = []
    for klyuch in ('podzagolovok', 'chtenie'):
        znachenie = polya.get(klyuch, '').strip()
        if znachenie:
            chasti.append('      <span>%s</span>' % znachenie)

    stroki = '\n      <span class="dot">·</span>\n'.join(chasti)

    temy = sobrat_temy(polya.get('temy', ''))
    if temy:
        stroki = stroki + '\n' + temy if stroki else temy

    return stroki


def sobrat_next(adres, podpis):
    if not adres:
        return ''
    return '    <a class="next" href="%s">%s <i>→</i></a>' % (adres, podpis)


def chitat_razdel(razdel):
    """Материалы раздела, отсортированные по data: старые сверху."""
    papka = os.path.join(KONTENT, razdel['papka'])
    if not os.path.isdir(papka):
        return []

    materialy = []
    for imya in sorted(os.listdir(papka)):
        if not imya.endswith('.md'):
            continue
        polya, telo = chitat_md(os.path.join(papka, imya))
        materialy.append({
            'imya': razdel['prefiks'] + imya[:-3] + '.html',
            'polya': polya,
            'telo': telo,
        })

    materialy.sort(key=lambda m: m['polya'].get('data', ''))
    return materialy


def sobrat_stranicy(razdel, materialy, obshchee):
    """Страницы материалов раздела. Порядок .pager — по data, старые сверху."""
    shablon = io.open(os.path.join(SHABLONY, razdel['shablon']),
                      encoding='utf-8').read()
    md = markdown.Markdown(extensions=['tables', 'attr_list'])

    for i, m in enumerate(materialy):
        polya = m['polya']
        tip = polya.get('tip', 'nash')
        sled = materialy[i + 1]['imya'] if i + 1 < len(materialy) else ''

        md.reset()
        stranica = shablon
        for klyuch, znachenie in (
            ('{{zagolovok}}', polya.get('zagolovok', '')),
            ('{{lid}}', polya.get('lid', '')),
            ('{{opisanie}}', polya.get('opisanie') or polya.get('lid', '')),
            ('{{podzagolovok}}', polya.get('podzagolovok', '')),
            ('{{chtenie}}', polya.get('chtenie', '')),
            ('{{badge}}', PLASHKA.get(tip, PLASHKA['nash'])),
            ('{{temy}}', sobrat_temy(polya.get('temy', ''))),
            ('{{meta}}', sobrat_meta(polya)),
            ('{{next_ssylka}}', sobrat_next(sled, razdel['sled'])),
            ('{{nazad_adres}}', obshchee['nazad_adres'][razdel['klyuch']]),
            ('{{nazad_podpis}}', obshchee['nazad_podpis'][razdel['klyuch']]),
            ('{{menyu}}', obshchee['menyu']),
            ('{{podval}}', obshchee['podval']),
            ('{{telo}}', md.convert(m['telo'])),
        ):
            stranica = stranica.replace(klyuch, znachenie)

        put = os.path.join(ROOT, m['imya'])
        io.open(put, 'w', encoding='utf-8', newline='\n').write(stranica)


def s_pripiskoj(pripiska, znachenie):
    """'35 мин' -> 'было 35 мин'. Если приставка уже есть — второй раз не ставим."""
    znachenie = znachenie.strip()
    if not znachenie:
        return znachenie

    nizhnij = znachenie.lower()
    for slovo in PRIPISKI:
        # именно слово: «былое» приставкой не считается
        if nizhnij.startswith(slovo) and not nizhnij[len(slovo):len(slovo) + 1].isalpha():
            return znachenie

    return '%s %s' % (pripiska, znachenie)


def karta_stroka(m):
    """Строка кейса в списке на главной: плашка типа и замер было/стало."""
    polya = m['polya']
    tip = polya.get('tip', 'nash')

    shapka = ('    <a class="case-row" href="%s">\n'
              '      <span><span class="badge %s">%s</span>'
              '<span class="name">%s</span></span>\n'
              % (m['imya'],
                 PLASHKA_KLASS.get(tip, 'own'),
                 PLASHKA.get(tip, PLASHKA['nash']),
                 polya.get('zagolovok', '')))

    if tip == 'rynok':
        nutro = ('<span class="task">%s</span>' % polya.get('zadacha', ''))
    else:
        nutro = ('<span class="was">%s</span>'
                 '<span class="now">%s</span>'
                 % (s_pripiskoj('было', polya.get('bylo', '')),
                    s_pripiskoj('стало', polya.get('stalo', ''))))

    return (shapka +
            '      <span class="who">%s</span>%s'
            '<span class="go">Читать подробнее →</span></a>'
            % (polya.get('otrasl', ''), nutro))


def kartochka(m, verhushka):
    """Карточка материала в ленте: без замеров и без плашки типа.

    verhushka — то, чем карточка начинается: заглушка под картинку
    или узкая лента.
    """
    polya = m['polya']

    temy = [t.strip() for t in polya.get('temy', '').split(',') if t.strip()]
    tegi = ''
    if temy:
        tegi = ('\n      <span class="tags">%s</span>'
                % ''.join('<span class="tag">%s</span>' % t for t in temy))

    return ('    <a class="item" href="%s">%s<span class="body">\n'
            '      <h3>%s</h3>\n'
            '      <p>%s</p>%s</span></a>'
            % (m['imya'],
               verhushka,
               polya.get('zagolovok', ''),
               polya.get('opisanie') or polya.get('lid', ''),
               tegi))


def karta_plitka(m):
    """Плитка с заглушкой под картинку."""
    return kartochka(m, '<span class="ph"></span>')


def karta_stiker(m):
    """Стикер: вместо заглушки — полоса клейкой ленты у верхнего края."""
    return kartochka(m, '<span class="tape"></span>')


# вид карточки -> сборщик карточки и открывающий тег списка
KARTY = {
    'stroka': (karta_stroka, '  <div id="rows">'),
    'plitka': (karta_plitka, '  <div class="feed">'),
    'stiker': (karta_stiker, '  <div class="feed">'),
}


def sobrat_sekciyu(razdel, materialy):
    """Секция раздела на главной. Порядок карточек — от новых к старым."""
    karta, konteyner = KARTY[razdel['karta']]
    kartochki = '\n'.join(karta(m) for m in reversed(materialy))

    return ('<section class="wrap sec" id="%s">\n'
            '  <div class="bar"><h2>%s</h2></div>\n'
            '  <p class="said">%s</p>\n'
            '%s\n'
            '%s\n'
            '  </div>\n'
            '</section>'
            % (razdel['sekciya'], razdel['zagolovok'], razdel['said'],
               konteyner, kartochki))


def sekciya_pod_zamkom(razdel, materialy):
    """Скрытый раздел: та же секция, но закомментированная целиком."""
    skolko = len(materialy)
    povod = ('РАЗДЕЛ СКРЫТ: %s — %d из %d записей, не хватает %d. '
             'Секцию раскомментирует сборка, когда наберётся порог.'
             % (razdel['imya'].lower(), skolko, razdel['porog'],
                razdel['porog'] - skolko))

    if not skolko:
        return '<!-- %s -->' % povod

    telo = sobrat_sekciyu(razdel, materialy)
    if '--' in telo:
        # двойной дефис внутри html-комментария недопустим — оставляем повод
        return '<!-- %s -->' % povod

    return '<!-- %s\n%s\n-->' % (povod, telo)


def vidno(razdel, materialy):
    """Единственное условие видимости раздела на сайте."""
    return len(materialy) >= razdel['porog']


def obshchie_ssylki(sobrannoe):
    """Меню, подвал, карточки входов и обратные ссылки — по видимым разделам.

    Обратная ссылка ведёт на секцию раздела, только если раздел виден;
    иначе — просто на главную, чтобы не появилось битого якоря.
    """
    menyu = []
    podval = []
    gates = []
    menyu_index = []
    podval_index = []
    nazad_adres = {}
    nazad_podpis = {}

    for razdel in RAZDELY:
        if vidno(razdel, sobrannoe[razdel['klyuch']]):
            menyu_index.append('<a href="#%s">%s</a>'
                               % (razdel['sekciya'], razdel['menyu']))
            podval_index.append('<a href="#%s">%s</a>'
                                % (razdel['sekciya'], razdel['podval']))
            menyu.append('<a href="index.html#%s">%s</a>'
                         % (razdel['sekciya'], razdel['menyu']))
            podval.append('<a href="index.html#%s">%s</a>'
                          % (razdel['sekciya'], razdel['podval']))
            if razdel['gate']:
                gates.append(razdel['gate'])
            nazad_adres[razdel['klyuch']] = 'index.html#%s' % razdel['sekciya']
            nazad_podpis[razdel['klyuch']] = razdel['nazad']
        else:
            nazad_adres[razdel['klyuch']] = 'index.html'
            nazad_podpis[razdel['klyuch']] = 'На главную'

    return {
        'menyu': ''.join(menyu),
        'podval': ''.join(podval),
        'menyu_index': ''.join(menyu_index),
        'podval_index': ''.join(podval_index),
        'gates': '\n'.join(gates),
        'nazad_adres': nazad_adres,
        'nazad_podpis': nazad_podpis,
    }


def sobrat_index(sobrannoe, obshchee):
    """Главная. Скрытый раздел не даёт ни секции, ни ссылок на себя."""
    stranica = io.open(SHABLON_INDEX, encoding='utf-8').read()

    for razdel in RAZDELY:
        materialy = sobrannoe[razdel['klyuch']]
        if vidno(razdel, materialy):
            sekciya = sobrat_sekciyu(razdel, materialy)
        else:
            sekciya = sekciya_pod_zamkom(razdel, materialy)
        stranica = stranica.replace('{{sekciya_%s}}' % razdel['klyuch'], sekciya)

    stranica = stranica.replace('{{menyu}}', obshchee['menyu_index'])
    stranica = stranica.replace('{{podval}}', obshchee['podval_index'])
    stranica = stranica.replace('{{gates}}', obshchee['gates'])

    put = os.path.join(ROOT, 'index.html')
    io.open(put, 'w', encoding='utf-8', newline='\n').write(stranica)


def sobrat():
    sobrannoe = dict((r['klyuch'], chitat_razdel(r)) for r in RAZDELY)
    obshchee = obshchie_ssylki(sobrannoe)

    for razdel in RAZDELY:
        sobrat_stranicy(razdel, sobrannoe[razdel['klyuch']], obshchee)

    sobrat_index(sobrannoe, obshchee)
    return sobrannoe


def sklonenie(n):
    if n % 10 == 1 and n % 100 != 11:
        return 'запись'
    if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14):
        return 'записи'
    return 'записей'


def pechat(sobrannoe):
    print('')
    for razdel in RAZDELY:
        materialy = sobrannoe[razdel['klyuch']]
        skolko = len(materialy)
        ne_hvataet = max(0, razdel['porog'] - skolko)

        if vidno(razdel, materialy):
            sostoyanie = 'на сайте'
        else:
            sostoyanie = ('скрыт, не хватает %d %s'
                          % (ne_hvataet, sklonenie(ne_hvataet)))

        podpis = razdel['imya']
        tochki = '.' * max(3, 15 - len(podpis))
        print('%s %s %d %s  ·  %s'
              % (podpis, tochki, skolko, sklonenie(skolko), sostoyanie))
    print('')


if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    pechat(sobrat())
