"""Miscellaneous report classes.
"""
import datetime
import re

from beancount.reports import report
from beancount.reports import table
from beancount.parser import printer
from beancount.parser import options
from beancount.core import data
from beancount.core import realization
from beancount.core import amount
from beancount.core import getters
from beancount.core import account_types
from beancount.ops import prices


class ErrorReport(report.Report):
    """Report the errors."""

    names = ['check', 'validate', 'errors']
    default_format = 'text'

    def render_text(self, entries, errors, options_map, file):
        printer.print_errors(errors, file=file)


class PrintReport(report.Report):
    """Print out the entries."""

    names = ['print']
    default_format = 'beancount'

    def render_beancount(self, entries, errors, options_map, file):
        printer.print_entries(entries, file=file)


class PricesReport(report.Report):
    """Print out the unnormalized price entries that we input.
    Unnormalized means that we may render both (base,quote) and (quote,base).
    This can be used to rebuild a prices database without having to share the
    entire ledger file.

    Note: this type of report should be removed once we have filtering on
    directive type, this is simply the 'print' report with type:price. Maybe
    rename the 'pricedb' report to just 'prices' for simplicity's sake.
    """

    names = ['prices']
    default_format = 'beancount'

    def render_beancount(self, entries, errors, options_map, file):
        price_entries = [entry
                         for entry in entries
                         if isinstance(entry, data.Price)]
        printer.print_entries(price_entries, file=file)


class PriceDBReport(report.Report):
    """Print out the normalized price entries from the price db.
    Normalized means that we print prices in the most common (base, quote) order.
    This can be used to rebuild a prices database without having to share the
    entire ledger file.

    Only the forward prices are printed; which (base, quote) pair is selected is
    selected based on the most common occurrence between (base, quote) and
    (quote, base). This is done in the price map.
    """

    names = ['pricedb', 'prices_db']
    default_format = 'beancount'

    def render_beancount(self, entries, errors, options_map, file):
        price_map = prices.build_price_map(entries)
        source = data.Source('<report_prices_db>', 0)
        for base_quote in price_map.forward_pairs:
            price_list = price_map[base_quote]
            base, quote = base_quote
            for date, price in price_list:
                entry = data.Price(source, date, base, amount.Amount(price, quote))
                file.write(printer.format_entry(entry))
            file.write('\n')


class AccountsReport(report.Report):
    """Print out the list of all accounts."""

    names = ['accounts']
    default_format = 'beancount'

    def render_beancount(self, entries, errors, options_map, file):
        if not entries:
            return

        open_close = getters.get_account_open_close(entries)

        # Render to stdout.
        maxlen = max(len(account) for account in open_close)
        sortkey_fun = account_types.get_account_sort_function(
            options.get_account_types(options_map))
        for account, (open, close) in sorted(open_close.items(),
                                             key=lambda entry: sortkey_fun(entry[0])):
            open_date = open.date if open else ''
            close_date = close.date if close else ''
            file.write('{:{len}}  {}  {}\n'.format(account, open_date, close_date,
                                                   len=maxlen))


class CurrentEventsReport(report.TableReport):
    """Produce a table of the current values of all event types."""

    names = ['current_events', 'latest_events']

    def generate_table(self, entries, errors, options_map):
        events = {}
        for entry in entries:
            if isinstance(entry, data.Event):
                events[entry.type] = entry.description
        return table.create_table([(type_, description)
                                   for type_, description in sorted(events.items())],
                                  [(0, "Type", self.formatter.render_event_type),
                                   (1, "Description")])


class EventsReport(report.TableReport):
    """Produce a table of all the values of a particular event."""

    names = ['events']

    @classmethod
    def add_args(cls, parser):
        parser.add_argument('-e', '--expr',
                            action='store', default=None,
                            help="A regexp to filer on which events to display.")

    def generate_table(self, entries, errors, options_map):
        event_entries = []
        for entry in entries:
            if not isinstance(entry, data.Event):
                continue
            if self.args.expr and not re.match(self.args.expr, entry.type):
                continue
            event_entries.append(entry)
        return table.create_table([(entry.date, entry.type, entry.description)
                                   for entry in event_entries],
                                  [(0, "Date", datetime.date.isoformat),
                                   (1, "Type"),
                                   (2, "Description")])


__reports__ = [
    ErrorReport,
    PrintReport,
    PricesReport,
    PriceDBReport,
    AccountsReport,
    CurrentEventsReport,
    EventsReport,
    ]
