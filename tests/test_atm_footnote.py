"""The August 30, 2026 "MSTR: satış yok" regression.

The channel got:

    💸 ATM Satışı VAR: MSTR: 4,531,421 adet → $602.8M net
       STRF / STRC / STRK / STRD / MSTR: satış yok

MSTR was in both lists. SEC renders a footnote as a <tr> INSIDE the table:

    (4) As previously disclosed, on March 23, 2026, Strategy announced a new
        $21.0 billion offering of MSTR Stock.

ATM_TICKER_RE matched the MSTR in that sentence, so parse_atm_table built a
second, all-blank MSTR security, and shares_sold_num == 0 put it on the
no-sales line.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import bot

HEADER = ['Security', 'Shares Sold(1)', 'Notional Value (in millions)(2)',
          'Net Proceeds (in millions)(3)',
          'Available for Issuance and Sale (in millions)(4)']

FOOTNOTE = ('(4) As previously disclosed, on March 23, 2026, Strategy '
            'announced a new $21.0 billion offering of MSTR Stock.')


def atm_table(extra_rows=()):
    """The real August 2026 ATM table: MSTR sold, the preferreds did not."""
    return [[
        ['During Period August 24, 2026 to August 30, 2026', 'As of August 30, 2026'],
        HEADER,
        ['STRF Stock 10.00% Series A Perpetual Strife Preferred Stock',
         '-', '$', '-', '$', '-', '$', '1,619.3'],
        ['STRC Stock Variable Rate Series A Perpetual Stretch Preferred Stock',
         '-', '$', '-', '$', '-', '$', '17,510.8'],
        ['STRK Stock 8.00% Series A Perpetual Strike Preferred Stock',
         '-', '$', '-', '$', '-', '$', '2,100.0'],
        ['STRD Stock 10.00% Series A Perpetual Stride Preferred Stock',
         '-', '$', '-', '$', '-', '$', '4,014.8'],
        ['MSTR Stock Class A Common Stock',
         '4,531,421', '$', '610.0', '$', '602.8', '$', '23,790.3'],
        *extra_rows,
    ]]


def test_an_in_table_footnote_is_not_a_security():
    """The exact failure. The footnote names MSTR; it is not a holding."""
    atm = bot.parse_atm_table(atm_table(extra_rows=[[FOOTNOTE]]))

    tickers = [s['ticker'] for s in atm['securities']]
    assert tickers == ['STRF', 'STRC', 'STRK', 'STRD', 'MSTR']
    assert tickers.count('MSTR') == 1


def test_the_alert_never_lists_a_seller_as_not_selling():
    parsed = {"event_type": "no_purchase",
              "atm": bot.parse_atm_table(atm_table(extra_rows=[[FOOTNOTE]]))}
    block = bot._atm_block(parsed, emoji="💵")

    assert 'MSTR: 4,531,421 adet' in block
    assert 'STRF / STRC / STRK / STRD: satış yok' in block
    # the whole point:
    assert 'MSTR: satış yok' not in block
    assert 'MSTR' not in block.split('satış yok')[0].split('\n')[-1]


def test_a_blank_row_naming_a_ticker_is_ignored():
    """Belt and braces: prose that mentions a ticker but carries no figures
    is not a security, footnote marker or not."""
    prose = ['Strategy may issue additional MSTR Stock under the program.']
    atm = bot.parse_atm_table(atm_table(extra_rows=[prose]))

    assert [s['ticker'] for s in atm['securities']].count('MSTR') == 1


def test_a_duplicate_ticker_row_keeps_the_first():
    dupe = ['MSTR Stock Class A Common Stock', '-', '$', '-', '$', '-', '$', '1.0']
    atm = bot.parse_atm_table(atm_table(extra_rows=[dupe]))

    mstr = [s for s in atm['securities'] if s['ticker'] == 'MSTR']
    assert len(mstr) == 1
    assert mstr[0]['shares_sold'] == '4,531,421'


def test_a_flagged_figure_is_not_stated_as_fact():
    """A security the sanity guards distrust (counts=False) used to be
    printed on the sold line as though it were verified, while also being
    absent from the no-sales line. It now gets its own hedged line."""
    atm = bot.parse_atm_table(atm_table())
    for s in atm['securities']:
        if s['ticker'] == 'MSTR':
            s['counts'] = False

    block = bot._atm_block({"atm": atm})

    assert 'MSTR: satış var, rakam doğrulanamadı' in block
    assert 'MSTR: 4,531,421 adet' not in block
    assert 'MSTR: satış yok' not in block


def test_partition_is_exhaustive_and_disjoint():
    atm = bot.parse_atm_table(atm_table(extra_rows=[[FOOTNOTE]]))
    sold, flagged, unsold = bot.partition_atm_securities(atm)

    buckets = [s['ticker'] for s in sold + flagged + unsold]
    assert sorted(buckets) == sorted(set(buckets)), "a ticker landed in two buckets"
    assert set(buckets) == {'STRF', 'STRC', 'STRK', 'STRD', 'MSTR'}
