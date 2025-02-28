from odoo import fields, models, api,_
from datetime import datetime

class AccountPaymentInherit(models.Model):
    _inherit = "account.payment"
    partner_type = fields.Selection([
        ('customer', 'Customer'),
        ('supplier', 'Vendor'),
        ('sfc', 'SFC'),
        ('employee','Employee'),
    ], default='customer', tracking=True, required=True)
    
    def _get_default_pay_req_id(self):
        return self.env.context.get('default_pay_req_id')
    payment_request_id = fields.Many2one('payment.request',string="Payment Request", default=_get_default_pay_req_id)

    # override the original functions in account module
    
    def _prepare_payment_display_name(self):
        result = super(AccountPaymentInherit,self)._prepare_payment_display_name()
        result['outbound-sfc'] = _('SFC Payment')
        return result
    
    def action_post(self):
        result = super(AccountPaymentInherit, self).action_post()
        if self.payment_request_id:
            self.payment_request_id.write({
                'state':'paid',
                'payment_date':datetime.today()
            })
            if self.payment_request_id.sfc_source:
                self.payment_request_id.sfc_source.write({
                    'state':'paid'
                })

        return result
    def action_draft(self):
        result = super(AccountPaymentInherit, self).action_draft()
        self.payment_request_id.write({
            'state':'payment_draft'
        })
        if self.payment_request_id.sfc_source:
            self.payment_request_id.sfc_source.write({
                'state':'payment_request'
            })
        return result

    