# -*- coding: utf-8 -*-
"""
Сборщик сайта daivex.

    python build.py

Читает content/keysy/*.md, прогоняет тело через markdown,
подставляет в templates/material.html и кладёт готовые
страницы в корень папки сайта; из тех же исходников собирает
index.html по templates/index.html.

Имя файла: content/keysy/finansovyj-reestr.md -> kejs-finansovyj-reestr.html
(префикс раздела, чтобы адреса совпадали с уже опубликованными).

Ничего, кроме собственных .html, сборщик не трогает.
"""

import io
import os
import sys

import markdown

ROOT = os.path.dirname(os.path.abspath(__file__))
SHABLON_MATERIAL = os.path.join(ROOT, 'templates', 'material.html')
SHABLON_INDEX = os.path.join(ROOT, 'templates', 'index.html')

KEYSY = os.path.join(ROOT, 'content', 'keysy')
PREFIKS = 'kejs-'

# подписи и порядок строк отчёта; собирается пока только раздел кейсов
OTCHET_RAZDELY = ['Кейсы', 'Инструменты', 'Заметки', 'База знаний']

# tip -> текст плашки над заголовком и класс плашки в карточке на главной
PLASHKA = {
    'nash': 'Наш кейс',
    'rynok': 'Пример рынка',
}
PLASHKA_KLASS = {
    'nash': 'own',
    'rynok': 'mkt',
}

NEXT_PODPIS = 'Следующий кейс'

# приставки строки «было/стало»; значение иногда уже набрано с ними
PRIPISKI = ('было', 'стало')

# заголовок и подводка раздела кейсов на главной
SEKCIYA_ZAGOLOVOK = 'Кейсы'
SEKCIYA_SAID = ('Разобранный процесс: что делалось руками, сколько это '
                'занимало, что осталось за человеком. Со своими замерами '
                'и без выдуманных цифр.')
MENYU_PUNKT = '<a href="#keysy">Кейсы</a>'

# карточка входа в раздел на скрытом пока блоке входов;
# у остальных разделов схема повторится как {{gate_instr}} и далее
GATE_PUNKT = '''    <a class="gate g2" href="#keysy"><span class="wash"></span>
      <h3>Кейсы применения ИИ</h3>
      <p>Разобранные процессы: что делалось руками, сколько это занимало, где встал ИИ и что осталось за человеком. Со своими замерами и без выдуманных цифр.</p>
      <span class="go">Смотреть кейсы →</span></a>'''


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


def sobrat_next(adres):
    if not adres:
        return ''
    return ('    <a class="next" href="%s">%s <i>→</i></a>'
            % (adres, NEXT_PODPIS))


def chitat_keysy():
    """Все кейсы из content/keysy, отсортированные по data: старые сверху."""
    if not os.path.isdir(KEYSY):
        return []

    materialy = []
    for imya in sorted(os.listdir(KEYSY)):
        if not imya.endswith('.md'):
            continue
        polya, telo = chitat_md(os.path.join(KEYSY, imya))
        materialy.append({
            'imya': PREFIKS + imya[:-3] + '.html',
            'polya': polya,
            'telo': telo,
        })

    materialy.sort(key=lambda m: m['polya'].get('data', ''))
    return materialy


def sobrat_stranicy(materialy):
    """Страницы материалов. Порядок .pager — по data, старые сверху."""
    shablon = io.open(SHABLON_MATERIAL, encoding='utf-8').read()
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
            ('{{next_ssylka}}', sobrat_next(sled)),
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


def sobrat_stroku(m):
    """Строка кейса в списке на главной. Вид зависит от tip."""
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


def sobrat_index(materialy):
    """Главная. Порядок кейсов — от новых к старым."""
    shablon = io.open(SHABLON_INDEX, encoding='utf-8').read()

    if materialy:
        stroki = '\n'.join(sobrat_stroku(m) for m in reversed(materialy))
        sekciya = ('<section class="wrap sec" id="keysy">\n'
                   '  <div class="bar"><h2>%s</h2></div>\n'
                   '  <p class="said">%s</p>\n'
                   '  <div id="rows">\n'
                   '%s\n'
                   '  </div>\n'
                   '</section>'
                   % (SEKCIYA_ZAGOLOVOK, SEKCIYA_SAID, stroki))
        menyu = MENYU_PUNKT
        gate = GATE_PUNKT
    else:
        sekciya = ''
        menyu = ''
        gate = ''

    stranica = shablon.replace('{{sekciya_keysy}}', sekciya)
    stranica = stranica.replace('{{menyu_keysy}}', menyu)
    stranica = stranica.replace('{{gate_keysy}}', gate)

    put = os.path.join(ROOT, 'index.html')
    io.open(put, 'w', encoding='utf-8', newline='\n').write(stranica)


def sobrat():
    materialy = chitat_keysy()
    sobrat_stranicy(materialy)
    sobrat_index(materialy)
    return {'Кейсы': len(materialy)}


def pechat(skolko):
    print('')
    for podpis in OTCHET_RAZDELY:
        tochki = '.' * max(3, 15 - len(podpis))
        print('%s %s %d' % (podpis, tochki, skolko.get(podpis, 0)))
    print('')


if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    pechat(sobrat())
