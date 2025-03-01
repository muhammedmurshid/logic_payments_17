from odoo import fields, api, models

class MailActivityInherit(models.Model):
    _inherit = "mail.activity"
    payment_request = fields.Many2one('payment.request',string="Payment Request")
    is_pay_approve_request = fields.Boolean(string="Is Pay Approve Request")