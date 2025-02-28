from odoo import fields,models,api
from datetime import datetime
class  PayWizard(models.TransientModel):
    _name="payment.register.wizard"
    journal = fields.Many2one('account.journal',string="Journal",required=True)
    # recipient_bank = fields.Many2one('res.partner.bank',string="Recipient Bank Account")
    company_id = fields.Many2one(
            'res.company', store=True, copy=False,
            string="Company",
            default=lambda self: self.env.user.company_id.id,
            readonly=True)
    currency_id = fields.Many2one(
            'res.currency', string="Currency",
            related='company_id.currency_id',
            default=lambda
            self: self.env.user.company_id.currency_id.id,
            readonly=True)
    amount = fields.Monetary(string="Amount",default=lambda self: self._context.get('amount'))
    date = fields.Date(string="Date",default=datetime.today())
    payment_request_id = fields.Many2one('payment.request',string="Payment Request",default = lambda self: self.env.context.get('active_id'))
    destination_account_id = fields.Many2one('account.account',string="Destination Account")
    ref = fields.Char(string="Memo")
    partner_type = fields.Selection([
    ('customer', 'Customer'),
    ('supplier', 'Vendor'),
    ('sfc', 'SFC'),
    ('employee','Employee'),]
    , default=lambda self: self._context.get('partner_type'), tracking=True, required=True)
    def action_create_payments(self):
        # need to add methods to create payment record in db
        payment_obj = self.env['account.payment'].create({
            'payment_type': 'outbound',
            'partner_type': self.partner_type,
            'payment_request_id':self.payment_request_id.id,
            'destination_account_id': self.destination_account_id.id,
            'amount': self.amount,
            'ref': self.ref,
            'date': self.date,
            'is_internal_transfer':False,

        })
        payment_obj.action_post()
        # set the last activity to registered
        activity_ids = self.env['mail.activity'].search([('payment_request','=',self.payment_request_id.id)],order='create_date asc')
        if activity_ids:
            activity_id = activity_ids[-1]
            activity_id.action_feedback(feedback=f'Registered Payment of {activity_id.payment_request.currency_id.symbol}{activity_id.payment_request.amount}')
        # need to handle condition where there is no activity present 

            
        self.payment_request_id.write({
            'state':'paid',
        })
        # pay_req_objs = self.env['payment.request'].search([('id','=',self.payment_request_id.id)],limit=1)
        # if self.payment_request_id.source_type =='sfc':
        #     sfc_objs = self.env['student.faculty'].search([('id','=',self.payment_request_id.sfc_source.id)],limit=1)
        #     if sfc_objs:
        #         sfc_objs[0].write({
        #             'state':'paid'
        #         })
        # if pay_req_objs:
        #     pay_req_objs[0].write({
        #         'state':'paid',
        #     })
        
