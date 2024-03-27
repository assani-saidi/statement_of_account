# -*- coding: utf-8 -*-


# NOTE REFACTOR TO DO CONVERSION RATHER THAN FILTERING CURRENCIES

from odoo import models, fields
import datetime

from odoo.exceptions import UserError, Warning, ValidationError


class PartnerStatement(models.Model):
    _inherit = 'res.partner'

    def open_statement(self):
        active_ids = self.env.context.get('active_ids', []) or [self.id]
        return {
            'type': 'ir.actions.act_window',
            'name': 'Print Statement',
            'res_model': 'statement_of_account.statement',
            'view_mode': 'form',
            'view_id': self.env.ref('statement_of_account.statement_form_view').id,
            'target': 'new',
            'context': {'partners': active_ids}
        }


class Statement(models.TransientModel):
    _name = 'statement_of_account.statement'
    _description = 'Statement Print Model'

    statement_from = fields.Date(string='Date From', default=fields.Date.today())
    statement_to = fields.Date(string='Date To', default=datetime.date.today() + datetime.timedelta(days=30))
    currency = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)

    def prepare_statement_data(self, partners=None):
        partners_ids = self.env.context.get('partners', []) if partners is None else partners
        partners = self.env['res.partner'].browse(partners_ids)
        rows = []  # note the first index will have the name, the last index the data

        # we get the currencies
        currencies = [self.currency.id] if self.currency else self.env['res.currency'].search([]).ids

        for partner in partners:
            # we set partner variables
            partner_row = []
            current_balance = 0
            # we must check if the partner has specific payable and receivable accounts
            try:
                payable_account = partner.property_account_payable_id or self.env.ref(
                    'account.data_account_type_payable')
                receivable_account = partner.property_account_receivable_id or self.env.ref(
                    'account.data_account_type_receivable')
                if not payable_account or not receivable_account:
                    raise UserError(f"Please check if {partner.name} has receivable and payable accounts")
            except Exception as e:
                raise UserError(f"PLease check if partner {partner.name} has receivable and payable accounts")

            # get closing balance
            all_journal_items = self.env['account.move.line'].search([
                ('partner_id', '=', partner.id),
                ("parent_state", "=", "posted"),
                ('account_id', 'in', [payable_account.id, receivable_account.id])
            ], order='date asc')

            closing_balance = 0
            for journal_item in all_journal_items:
                closing_balance += journal_item.balance

            # getting the opening balance
            preceding_journal_items = self.env['account.move.line'].search([
                ('partner_id', '=', partner.id),
                ('date', '<', self.statement_from),
                ("parent_state", "=", "posted"),
                ('account_id', 'in', [payable_account.id, receivable_account.id]),
                ('account_id', 'in', [payable_account.id, receivable_account.id])
            ], order='date asc')

            opening_balance = 0
            for journal_item in preceding_journal_items:
                print(f"{journal_item.date} * {journal_item.name} * {journal_item.balance}")
                opening_balance += journal_item.balance
            current_balance = -opening_balance
            opening_balance = "{0:,.2f}".format(opening_balance) if opening_balance >= 0 else "({0:,.2f})".format(
                abs(opening_balance))
            closing_balance = "{0:,.2f}".format(closing_balance) if closing_balance >= 0 else "({0:,.2f})".format(
                abs(closing_balance))

            # we get the journal items for the partner
            journal_items = self.env['account.move.line'].search([
                ('partner_id', '=', partner.id),
                ('date', '>=', self.statement_from),
                ('date', '<=', self.statement_to),
                ("parent_state", "=", "posted"),
                ('account_id', 'in', [payable_account.id, receivable_account.id]),
                # ('currency_id', '=', self.currency.id),
            ], order='date asc, create_date asc')

            for journal_item in journal_items:
                # get the corresponding credit or debit journal item for this journal item
                counter_entry = self.env["account.move.line"].search([
                    ('move_id', '=', journal_item.move_id.id),
                    ('account_id', '!=', journal_item.account_id.id),
                    ('currency_id', '=', journal_item.currency_id.id),
                    ('date', '=', journal_item.date),
                    ('partner_id', '=', journal_item.partner_id.id),
                    ('balance', '=', -journal_item.balance),
                    ("parent_state", "=", "posted"),
                    ('move_name', '=', journal_item.move_name)
                ], limit=1)
                # get base currency to foreign currency conversion rate
                rate = self.currency._get_conversion_rate(journal_item.currency_id, self.currency,
                                                          journal_item.company_id, journal_item.date)

                # we check if the journal item is a debit or credit (only applies to foreign currencies)
                debit = abs(journal_item.amount_currency) if journal_item.debit > 0 else False
                credit = abs(journal_item.amount_currency) if journal_item.credit > 0 else False

                # we get the current balance
                balance = journal_item.balance
                current_balance += -balance  # we invert the balance because to the perspective of the partner, the balance is inverted

                # we append the data to the partner row
                partner_row.append({
                    'rate': rate,
                    'date': journal_item.date,
                    'entry_type': journal_item.journal_id.name,
                    'reference': journal_item.move_name,
                    'description': journal_item.name or journal_item.ref,
                    'batch': journal_item.name,
                    'product': counter_entry.product_id.name,
                    'quantity': counter_entry.quantity,
                    'debit': "{0:,.2f}".format(debit * rate) or "{0:,.2f}".format(journal_item.debit * rate),
                    'credit': "{0:,.2f}".format(credit * rate) or "{0:,.2f}".format(journal_item.credit * rate),
                    'balance': "{0:,.2f}".format(current_balance),
                    'amount_in_currency': "{0:,.2f}".format(
                        abs(journal_item.amount_currency)) if journal_item.currency_id.id != journal_item.company_currency_id.id else '',
                    'formatted_balance': "{0:,.2f}".format(
                        abs(current_balance)) if current_balance <= 0 else "({0:,.2f})".format(
                        current_balance),
                    'currency': journal_item.currency_id.name,
                })

            rows.append([partner.name, partner_row, closing_balance, opening_balance])

        data = {
            'statement_from': self.statement_from,
            'statement_to': self.statement_to,
            'currency': self.currency.name,
            'rows': rows,
        }

        return data

    def print_statement(self):
        partners_ids = self.env.context.get('partners', [])
        data = self.prepare_statement_data()
        action = self.env.ref('statement_of_account.action_print_statement').report_action(docids=partners_ids,
                                                                                           data=data)
        return action

    def _send_statement_by_email(self):
        partners_ids = self.env.context.get('partners', [])
        partners = self.env['res.partner'].browse(partners_ids)
        statement = self.print_statement()

        # send email to each partner
        template = self.env.ref('statement_of_account.account_statement_email')
        template = template.with_context(statement=statement)
        for partner in partners:
            template.send_mail(partner.id, force_send=True, email_values={'email_to': partner.email})

    def send_statement_by_email(self):
        for partner in self.env.context.get('partners', []):
            partner = self.env['res.partner'].browse(partner)
            partners_ids = (partner.id,)
            data = self.prepare_statement_data(partners=partners_ids)
            statement = self.env.ref('statement_of_account.action_print_statement')._render_qweb_pdf(
                res_ids=partners_ids,
                data=data)


            # create attachment
            statement_name = f"{partner.name} Statement of Account - {self.statement_from} to {self.statement_to}"
            attachment = self.env['ir.attachment'].create({
                'name': statement_name,
                'type': 'binary',
                'raw': statement[0],
                'mimetype': 'application/pdf',
                'res_model': 'statement_of_account.statement',
                'res_id': self.id,
            })

            # create the email
            email = self.env['mail.mail'].create({
                'subject': f"{partner.name} Statement of Account",
                'email_from': self.env.user.email,
                'email_to': partner.email,
                'body_html': f"<h3>Dear {partner.name}</h3> <br/> Please find attached your statement of account for the period {self.statement_from} to {self.statement_to}",
                'attachment_ids': [(4, attachment.id)]
            })

            # send the email
            email.send()

