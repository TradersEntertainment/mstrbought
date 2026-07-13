import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import bot

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixtures')


def load_tables(name):
    with open(os.path.join(FIXTURES, name), encoding='utf-8') as f:
        return bot.extract_filing_tables(f.read())


def test_july13_atm_table_mstr_only():
    atm = bot.parse_atm_table(load_tables('july13_hold_atm.html'))
    assert atm is not None
    assert atm['sold_any'] is True
    assert atm['sold_tickers'] == ['MSTR']
    assert atm['total_net_proceeds'] == '$466.7M'
    assert atm['period'] == 'July 6, 2026 to July 12, 2026'

    by_ticker = {s['ticker']: s for s in atm['securities']}
    assert set(by_ticker) == {'MSTR', 'STRF', 'STRC', 'STRK', 'STRD'}
    mstr = by_ticker['MSTR']
    assert mstr['shares_sold'] == '4,818,781'
    assert mstr['shares_sold_num'] == 4818781
    assert mstr['net_proceeds'] == '$466.7M'
    assert by_ticker['STRC']['shares_sold_num'] == 0
    assert by_ticker['STRC']['available'] == '$17,510.8M'


def test_atm_only_filing_strc_sale():
    atm = bot.parse_atm_table(load_tables('atm_only.html'))
    assert atm['sold_tickers'] == ['STRC']
    assert atm['total_net_proceeds'] == '$119.4M'
    strc = next(s for s in atm['securities'] if s['ticker'] == 'STRC')
    assert strc['shares_sold_num'] == 1200000
    assert strc['net_proceeds'] == '$119.4M'
    assert strc['notional'] == '$120.0M'


def test_no_atm_table_returns_none():
    atm = bot.parse_atm_table(load_tables('july06_double_sale.html'))
    assert atm is None


def test_weekly_table_is_period_scoped():
    atm = bot.parse_atm_table(load_tables('july13_hold_atm.html'))
    assert atm['period_scoped'] is True
    assert atm['fmt'] == 3


def test_net_proceeds_clamped_to_notional_when_impossible():
    """Net proceeds can't exceed gross notional. A net cell that does
    (e.g. the Available-for-Issuance capacity leaking in) is clamped, so
    STRC shows its real ~$445M, not the inflated $5,350M."""
    atm = bot.parse_atm_table(load_tables('atm_misaligned.html'))
    strc = next(s for s in atm['securities'] if s['ticker'] == 'STRC')
    assert strc['net_proceeds_num_m'] == 445.0
    assert strc['suspect'] is not None and 'net>notional' in strc['suspect']
    # The badge total reflects the corrected value
    assert atm['total_net_proceeds'] == '$445.0M'
    assert strc['fmt'] if 'fmt' in strc else True  # sanity


def test_fmt_bumped_to_3():
    atm = bot.parse_atm_table(load_tables('july13_hold_atm.html'))
    assert atm['fmt'] == 3


def test_cumulative_program_table_is_not_period_scoped():
    """'Inception to date' summaries match the same headers but must never
    be treated as one week's sales — the source of inflated ATM totals."""
    atm = bot.parse_atm_table(load_tables('cumulative_atm.html'))
    assert atm is not None
    assert atm['period'] is None
    assert atm['period_scoped'] is False
    assert atm['sold_tickers'] == ['STRC']  # parsed, but flagged


def test_financing_source_from_atm():
    atm = bot.parse_atm_table(load_tables('july13_hold_atm.html'))
    assert bot.financing_source_from_atm(atm) == 'MSTR ATM ($466.7M)'
    assert bot.financing_source_from_atm(None) == '-'
    assert bot.financing_source_from_atm({'sold_any': False}) == '-'


def test_financing_source_multiple_tickers():
    atm = {
        'sold_any': True,
        'sold_tickers': ['STRC', 'STRK'],
        'total_net_proceeds': '$120.3M',
    }
    assert bot.financing_source_from_atm(atm) == 'STRC & STRK ATM ($120.3M)'
